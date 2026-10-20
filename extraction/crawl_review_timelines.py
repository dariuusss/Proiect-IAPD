"""Pas auxiliar: cât de repede se stabilizează scorul unui joc după lansare?

Pentru un eșantion de jocuri lansate de cel puțin un an descărcăm TOATE recenziile
(doar data și dacă e pozitivă), ca să putem reconstrui scorul pe care l-ar fi avut
jocul la 7, 30, 60, 90... zile după lansare. Rezultatul justifică empiric câte zile
trebuie să fi trecut de la lansare ca ținta să fie stabilă (RELEASE_END din config.py).

Rulare:  python extraction/crawl_review_timelines.py [--n 200]
Rezultat: data/raw/review_timelines.jsonl
"""
import argparse
import random
from datetime import date

from config import DELAY_REVIEWS, RAW_DIR, RELEASE_START, SEARCH_INDEX, SHUFFLE_SEED
from http_utils import append_jsonl, done_ids, get_json, read_jsonl

TIMELINES = RAW_DIR / "review_timelines.jsonl"
OLDEST_ALLOWED = date(2025, 9, 30)    # jocuri cu cel puțin ~1 an de istoric
MIN_REVIEWS, MAX_REVIEWS = 20, 3000   # peste 3000 ar fi prea multe pagini de descărcat
MAX_PAGES = 40


def sample(n):
    rows = [r for r in read_jsonl(SEARCH_INDEX)
            if r["release_date"] and RELEASE_START.isoformat() <= r["release_date"] <= OLDEST_ALLOWED.isoformat()
            and MIN_REVIEWS <= r["search_review_count"] <= MAX_REVIEWS]
    rows.sort(key=lambda r: r["appid"])
    random.Random(SHUFFLE_SEED).shuffle(rows)
    return rows[:n]


def fetch_timeline(appid):
    """Paginează prin toate recenziile (100 pe pagină) folosind cursorul API-ului."""
    reviews, cursor = [], "*"
    for _ in range(MAX_PAGES):
        data = get_json(f"https://store.steampowered.com/appreviews/{appid}",
                        params={"json": 1, "language": "all", "purchase_type": "all", "filter": "recent",
                                "num_per_page": 100, "cursor": cursor}, delay=DELAY_REVIEWS)
        if not data or not data.get("success"):
            return None
        batch = data.get("reviews", [])
        reviews += [[r["timestamp_created"], int(r["voted_up"])] for r in batch]
        if len(batch) < 100 or data.get("cursor") in (None, cursor):
            break
        cursor = data["cursor"]
    return reviews


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    args = parser.parse_args()

    done = done_ids(TIMELINES)
    todo = [r for r in sample(args.n) if r["appid"] not in done]
    print(f"{len(done)} deja descărcate, {len(todo)} de făcut")
    for k, row in enumerate(todo, 1):
        reviews = fetch_timeline(row["appid"])
        if reviews is None:
            continue
        # deduplicare: paginarea poate întoarce aceeași recenzie de două ori
        reviews = sorted({tuple(r) for r in reviews})
        append_jsonl(TIMELINES, {"appid": row["appid"], "name": row["name"],
                                 "release_date": row["release_date"], "reviews": reviews})
        if k % 10 == 0 or k == len(todo):
            print(f"{k}/{len(todo)}  {row['name']}: {len(reviews)} recenzii")


if __name__ == "__main__":
    main()
