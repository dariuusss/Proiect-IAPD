"""Pasul 3: din fișierele JSONL brute -> un singur CSV curat, cu un rând per joc.

Rulare:  python extraction/preprocess.py
Rezultat: data/final/steam_clean.csv  +  data/final/feature_dictionary.md
"""
import html
import json
import re
from datetime import datetime

import pandas as pd

from config import (APPDETAILS, CLEAN_CSV, FINAL_DIR, MIN_AGE_DAYS, MIN_REVIEWS_CRAWL,
                    DEVELOPERS, RELEASE_START, REVIEWS, SEARCH_INDEX, STEAMSPY, TAG_NAMES)
from http_utils import read_jsonl

TOP_TAGS = 40           # câte tag-uri devin coloane one-hot
MIN_GENRE_SHARE = 0.01  # genurile/categoriile mai rare de 1% nu primesc coloană proprie
MIN_CATEGORY_SHARE = 0.05

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text):
    text = TAG_RE.sub(" ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_release(text):
    for fmt in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt)
        except (ValueError, TypeError):
            pass
    return None


def parse_languages(raw):
    """'English<strong>*</strong>, French<br><strong>*</strong>languages with full audio support'
    -> (listă limbi, are audio complet în engleză)"""
    raw = (raw or "").split("<br>")[0]
    langs = [strip_html(x).replace("*", "").strip() for x in raw.split(",")]
    langs = [l for l in langs if l]
    full_audio_en = bool(re.search(r"English\s*<strong>\*</strong>", raw or ""))
    return langs, full_audio_en


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_row(details, reviews, spy, search_row, tag_names):
    d = details["data"]
    s = reviews["summary"]
    release = parse_release(d.get("release_date", {}).get("date"))
    price = d.get("price_overview") or {}
    langs, full_audio_en = parse_languages(d.get("supported_languages"))
    genres = [g["description"] for g in d.get("genres", [])]
    categories = [c["description"] for c in d.get("categories", [])]
    developers = d.get("developers") or []
    publishers = d.get("publishers") or []
    description = strip_html(d.get("detailed_description"))
    # Tag-urile din Store (cele afișate pe pagina jocului, ~7 per joc) sunt sursa principală:
    # SteamSpy are tag-uri doar pentru o mică parte din jocurile noi.
    tags = [tag_names.get(str(t), f"tag{t}") for t in (search_row or {}).get("search_tagids", [])]
    spy_tags = (spy or {}).get("tags") or {}

    try:
        required_age = int(str(d.get("required_age", 0)).strip("+") or 0)
    except ValueError:
        required_age = 0

    total = s.get("total_reviews", 0)
    return {
        "appid": details["appid"],
        "name": d.get("name"),
        "release_date": release.date().isoformat() if release else None,
        "release_year": release.year if release else None,
        "release_month": release.month if release else None,
        "release_dayofweek": release.weekday() if release else None,
        # prețul de listă (fără reducerea de moment), în EUR
        "price_eur": 0.0 if d.get("is_free") else price.get("initial", 0) / 100,
        "is_free": int(bool(d.get("is_free"))),
        "has_price_info": int(bool(price) or bool(d.get("is_free"))),
        "required_age": required_age,
        "n_genres": len(genres),
        "n_categories": len(categories),
        "has_windows": int(d.get("platforms", {}).get("windows", False)),
        "has_mac": int(d.get("platforms", {}).get("mac", False)),
        "has_linux": int(d.get("platforms", {}).get("linux", False)),
        "n_languages": len(langs),
        "has_full_audio_en": int(full_audio_en),
        "n_achievements": (d.get("achievements") or {}).get("total", 0),
        "n_dlc": len(d.get("dlc") or []),
        "n_screenshots": d.get("n_screenshots", 0),
        "n_movies": d.get("n_movies", 0),
        "description_length": len(description.split()),
        "short_description_length": len(strip_html(d.get("short_description")).split()),
        "has_website": int(bool(d.get("website"))),
        "controller_support": int(d.get("controller_support") == "full"),
        "n_content_descriptors": len((d.get("content_descriptors") or {}).get("ids") or []),
        "is_early_access": int("Early Access" in genres),
        "is_self_published": int(bool(developers) and set(developers) == set(publishers)),
        "n_steamspy_tags": len(spy_tags),  # doar pentru documentarea acoperirii, nu e feature
        "developer": developers[0] if developers else "",
        "publisher": publishers[0] if publishers else "",
        "genres": "|".join(genres),
        "categories": "|".join(categories),
        "tags": "|".join(tags),
        "short_description": strip_html(d.get("short_description")),
        # ținta
        "total_positive": s.get("total_positive", 0),
        "total_negative": s.get("total_negative", 0),
        "total_reviews": total,
        "review_score_desc": s.get("review_score_desc"),
        "positive_ratio": s.get("total_positive", 0) / total if total else None,
        # vârsta jocului când i-am descărcat recenziile; NU e feature, doar pentru controlul stabilității țintei
        "game_age_days": (datetime.fromisoformat(reviews["fetched_at"]).date() - release.date()).days if release else None,
    }


def add_one_hot(df, column, prefix, min_share=None, top_n=None):
    exploded = df[column].fillna("").str.split("|").explode()
    counts = exploded[exploded != ""].value_counts()
    if top_n is not None:
        keep = counts.head(top_n).index
    else:
        keep = counts[counts / len(df) >= min_share].index
    sets = df[column].fillna("").str.split("|").apply(set)
    new_cols = {f"{prefix}_{slug(v)}": sets.apply(lambda s, v=v: int(v in s)) for v in keep}
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)


def add_developer_history(df, developers):
    """Istoricul dezvoltatorului pe tot Steam-ul (din developers.jsonl), folosind DOAR jocurile
    lansate înaintea jocului curent, adică ce se știa deja în ziua lansării:
    - dev_prior_games: câte jocuri lansase înainte
    - dev_prior_rated_games: câte dintre ele au scor afișat (Steam îl arată de la 10 recenzii)
    - dev_prior_mean_score: media scorurilor lor (0-1); lipsă -> media coloanei + flag
    - dev_has_track_record: 1 dacă există cel puțin un joc anterior cu scor"""
    prior_games, prior_rated, prior_score = [], [], []
    for _, row in df.iterrows():
        games = developers.get(row["developer"], [])
        prior = [g for g in games if g["appid"] != row["appid"] and g["release_date"]
                 and g["release_date"] < row["release_date"]]
        rated = [g["search_review_pct"] / 100 for g in prior if g["search_review_pct"] is not None]
        prior_games.append(len(prior))
        prior_rated.append(len(rated))
        prior_score.append(sum(rated) / len(rated) if rated else None)
    df["dev_prior_games"] = prior_games
    df["dev_prior_rated_games"] = prior_rated
    df["dev_has_track_record"] = (df["dev_prior_rated_games"] > 0).astype(int)
    df["dev_prior_mean_score"] = pd.Series(prior_score, index=df.index, dtype=float)
    df["dev_prior_mean_score"] = df["dev_prior_mean_score"].fillna(df["dev_prior_mean_score"].mean())
    return df


def main():
    details = {r["appid"]: r for r in read_jsonl(APPDETAILS) if r.get("success")}
    reviews = {r["appid"]: r for r in read_jsonl(REVIEWS) if r.get("success")}
    spy = {r["appid"]: r for r in read_jsonl(STEAMSPY)}
    search = {r["appid"]: r for r in read_jsonl(SEARCH_INDEX)}
    tag_names = json.loads(TAG_NAMES.read_text(encoding="utf-8")) if TAG_NAMES.exists() else {}
    developers = {r["developer"]: r["games"] for r in read_jsonl(DEVELOPERS) if r.get("success")}
    print(f"appdetails={len(details)}  reviews={len(reviews)}  steamspy={len(spy)}  search={len(search)}")

    rows, dropped = [], {"not_game": 0, "no_reviews": 0, "out_of_window": 0}
    for appid, det in details.items():
        if det["data"].get("type") != "game":
            dropped["not_game"] += 1
            continue
        if appid not in reviews:
            dropped["no_reviews"] += 1
            continue
        row = build_row(det, reviews[appid], spy.get(appid), search.get(appid), tag_names)
        # Vârsta se măsoară la momentul descărcării recenziilor, nu față de azi:
        # contează câte zile avusese jocul ca să-și stabilizeze scorul când l-am măsurat.
        if (not row["release_date"] or row["release_date"] < RELEASE_START.isoformat()
                or row["game_age_days"] < MIN_AGE_DAYS):
            dropped["out_of_window"] += 1
            continue
        if row["total_reviews"] < MIN_REVIEWS_CRAWL:
            dropped["no_reviews"] += 1
            continue
        rows.append(row)
    print(f"Eliminate: {dropped}")

    df = pd.DataFrame(rows)
    df = add_developer_history(df, developers)
    df = add_one_hot(df, "genres", "genre", min_share=MIN_GENRE_SHARE)
    df = add_one_hot(df, "categories", "cat", min_share=MIN_CATEGORY_SHARE)
    df = add_one_hot(df, "tags", "tag", top_n=TOP_TAGS)
    # 0.80 = pragul Steam pentru „Very Positive”. Fișa cerea și total_reviews >= 50, dar asta ar fi făcut
    # eticheta să depindă și de popularitate (un joc bine primit cu 30 de recenzii ar fi fost „eșec”),
    # deci am fi amestecat două întrebări. Filtrul de recenzii se aplică deja la nivel de set.
    df["is_successful"] = (df["positive_ratio"] >= 0.80).astype(int)

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False, encoding="utf-8")
    print(f"Salvat {CLEAN_CSV}: {df.shape[0]} jocuri x {df.shape[1]} coloane")


if __name__ == "__main__":
    main()
