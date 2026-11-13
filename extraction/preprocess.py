import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import (APPDETAILS, CLEAN_CSV, MIN_AGE_DAYS, MIN_REVIEWS_CRAWL,
                    DEVELOPERS, RELEASE_START, REVIEWS, SEARCH_INDEX, STEAMSPY, TAG_NAMES)
from http_utils import read_jsonl

TOP_TAGS = 40           
MIN_GENRE_SHARE = 0.01  
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
    raw = (raw or "").split("<br>")[0]
    langs = [strip_html(x).replace("*", "").strip() for x in raw.split(",")]
    langs = [l for l in langs if l]
    full_audio_en = bool(re.search(r"English\s*<strong>\*</strong>", raw or ""))
    return langs, full_audio_en


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def steam_score_desc(ratio, total):
    if ratio is None or total < 10:
        return None
    pct = ratio * 100
    if pct >= 80:
        if pct >= 95 and total >= 500:
            return "Overwhelmingly Positive"
        return "Very Positive" if total >= 50 else "Positive"
    if pct >= 70:
        return "Mostly Positive"
    if pct >= 40:
        return "Mixed"
    if pct >= 20:
        return "Mostly Negative"
    if total >= 500:
        return "Overwhelmingly Negative"
    return "Very Negative" if total >= 50 else "Negative"


def build_target(reviews, search_row, search_date):
    
    if reviews is not None:
        s = reviews["summary"]
        total = s.get("total_reviews", 0)
        ratio = s.get("total_positive", 0) / total if total else None
        return {"total_positive": s.get("total_positive", 0), "total_negative": s.get("total_negative", 0),
                "total_reviews": total, "review_score_desc": s.get("review_score_desc"),
                "positive_ratio": ratio, "target_source": "reviews_api",
                "measured_on": datetime.fromisoformat(reviews["fetched_at"]).date()}
    if search_row and search_row.get("search_review_pct") is not None:
        total = search_row["search_review_count"]
        ratio = search_row["search_review_pct"] / 100
        positive = round(ratio * total)
        fetched = search_row.get("fetched_at")
        return {"total_positive": positive, "total_negative": total - positive, "total_reviews": total,
                "review_score_desc": steam_score_desc(ratio, total), "positive_ratio": ratio,
                "target_source": "search_summary",
                "measured_on": datetime.fromisoformat(fetched).date() if fetched else search_date}
    return None


def build_row(details, target, spy, search_row, tag_names):
    d = details["data"]
    release = parse_release(d.get("release_date", {}).get("date"))
    price = d.get("price_overview") or {}
    langs, full_audio_en = parse_languages(d.get("supported_languages"))
    genres = [g["description"] for g in d.get("genres", [])]
    categories = [c["description"] for c in d.get("categories", [])]
    developers = d.get("developers") or []
    publishers = d.get("publishers") or []
    description = strip_html(d.get("detailed_description"))
    
    tags = [tag_names.get(str(t), f"tag{t}") for t in (search_row or {}).get("search_tagids", [])]
    spy_tags = (spy or {}).get("tags") or {}

    try:
        required_age = int(str(d.get("required_age", 0)).strip("+") or 0)
    except ValueError:
        required_age = 0

    return {
        "appid": details["appid"],
        "name": d.get("name"),
        "release_date": release.date().isoformat() if release else None,
        "release_year": release.year if release else None,
        "release_month": release.month if release else None,
        "release_dayofweek": release.weekday() if release else None,
        
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
        "n_steamspy_tags": len(spy_tags),  
        "developer": developers[0] if developers else "",
        "publisher": publishers[0] if publishers else "",
        "genres": "|".join(genres),
        "categories": "|".join(categories),
        "tags": "|".join(tags),
        "short_description": strip_html(d.get("short_description")),
        
        **{k: v for k, v in target.items() if k != "measured_on"},
        
        "game_age_days": (target["measured_on"] - release.date()).days
                         if release and target["measured_on"] else None,
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--max-games", type=int, default=None)
    parser.add_argument("--out", type=Path, default=CLEAN_CSV)
    args = parser.parse_args()

    
    details = {r["appid"]: r for r in list(read_jsonl(APPDETAILS))[args.skip:] if r.get("success")}
    reviews = {r["appid"]: r for r in read_jsonl(REVIEWS) if r.get("success")}
    spy = {r["appid"]: r for r in read_jsonl(STEAMSPY)}
    search = {r["appid"]: r for r in read_jsonl(SEARCH_INDEX)}
    tag_names = json.loads(TAG_NAMES.read_text(encoding="utf-8")) if TAG_NAMES.exists() else {}
    developers = {r["developer"]: r["games"] for r in read_jsonl(DEVELOPERS) if r.get("success")}
    
    search_date = datetime.fromtimestamp(SEARCH_INDEX.stat().st_mtime).date() if SEARCH_INDEX.exists() else None
    print(f"appdetails={len(details)}  reviews={len(reviews)}  steamspy={len(spy)}  search={len(search)}")

    rows, dropped = [], {"not_game": 0, "no_reviews": 0, "out_of_window": 0}
    for appid, det in details.items():
        if det["data"].get("type") != "game":
            dropped["not_game"] += 1
            continue
        target = build_target(reviews.get(appid), search.get(appid), search_date)
        if target is None:
            dropped["no_reviews"] += 1
            continue
        row = build_row(det, target, spy.get(appid), search.get(appid), tag_names)
        
        if (not row["release_date"] or row["release_date"] < RELEASE_START.isoformat()
                or row["game_age_days"] < MIN_AGE_DAYS):
            dropped["out_of_window"] += 1
            continue
        if row["total_reviews"] < MIN_REVIEWS_CRAWL:
            dropped["no_reviews"] += 1
            continue
        rows.append(row)
        if args.max_games and len(rows) >= args.max_games:
            break
    print(f"Eliminate: {dropped}")

    df = pd.DataFrame(rows)
    print(f"Sursa țintei: {df['target_source'].value_counts().to_dict()}")
    df = add_developer_history(df, developers)
    df = add_one_hot(df, "genres", "genre", min_share=MIN_GENRE_SHARE)
    df = add_one_hot(df, "categories", "cat", min_share=MIN_CATEGORY_SHARE)
    df = add_one_hot(df, "tags", "tag", top_n=TOP_TAGS)
    df["is_successful"] = (df["positive_ratio"] >= 0.80).astype(int)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"Salvat {args.out}: {df.shape[0]} jocuri x {df.shape[1]} coloane")


if __name__ == "__main__":
    main()
