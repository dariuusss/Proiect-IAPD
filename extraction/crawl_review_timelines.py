import argparse
import random
from datetime import date

from config import DELAY_REVIEWS, RAW_DIR, RELEASE_START, SEARCH_INDEX, SHUFFLE_SEED
from http_utils import append_jsonl, done_ids, get_json, read_jsonl, redirects_away

TIMELINES = RAW_DIR / "review_timelines.jsonl"
OLDEST_ALLOWED = date(2025, 9, 30)    
MIN_REVIEWS, MAX_REVIEWS = 20, 3000   
MAX_PAGES = 40


def sample(n):
    rows = [r for r in read_jsonl(SEARCH_INDEX)
            if r["release_date"] and RELEASE_START.isoformat() <= r["release_date"] <= OLDEST_ALLOWED.isoformat()
            and MIN_REVIEWS <= r["search_review_count"] <= MAX_REVIEWS]
    rows.sort(key=lambda r: r["appid"])
    random.Random(SHUFFLE_SEED).shuffle(rows)
    return rows[:n]


def fetch_timeline(appid):
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
    if redirects_away("https://store.steampowered.com/appreviews/730", {"json": 1}):
        print("Endpoint-ul Steam /appreviews nu mai răspunde (redirecționează la prima pagină), "
              "deci istoricul recenziilor nu poate fi descărcat. Oprire.")
        return

    done = done_ids(TIMELINES)
    todo = [r for r in sample(args.n) if r["appid"] not in done]
    print(f"{len(done)} deja descărcate, {len(todo)} de făcut")
    for k, row in enumerate(todo, 1):
        reviews = fetch_timeline(row["appid"])
        if reviews is None:
            continue
        
        reviews = sorted({tuple(r) for r in reviews})
        append_jsonl(TIMELINES, {"appid": row["appid"], "name": row["name"],
                                 "release_date": row["release_date"], "reviews": reviews})
        if k % 10 == 0 or k == len(todo):
            print(f"{k}/{len(todo)}  {row['name']}: {len(reviews)} recenzii")


if __name__ == "__main__":
    main()
