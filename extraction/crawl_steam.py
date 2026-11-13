import argparse
import random
from datetime import datetime, timezone

from config import (APPDETAILS, COUNTRY, DELAY_REVIEWS, DELAY_SEARCH, DELAY_STEAMSPY,
                    DELAY_STORE, DEVELOPERS, LANGUAGE, MIN_REVIEWS_CRAWL, RELEASE_END,
                    RELEASE_START, REVIEWS, SEARCH_INDEX, SHUFFLE_SEED, STEAMSPY)
from get_app_list import ROW_RE, parse_row
from http_utils import append_jsonl, done_ids, get_json, read_jsonl, redirects_away


DROP_FIELDS = {"pc_requirements", "mac_requirements", "linux_requirements", "background",
               "background_raw", "legal_notice", "package_groups", "support_info",
               "capsule_image", "capsule_imagev5", "header_image",
               "about_the_game"}  


def candidates():
    rows = {r["appid"]: r for r in read_jsonl(SEARCH_INDEX)
            if r["release_date"] and r["release_date"] >= RELEASE_START.isoformat()
            and r["search_review_count"] >= MIN_REVIEWS_CRAWL}
    ids = sorted(rows)
    random.Random(SHUFFLE_SEED).shuffle(ids)
    return [i for i in ids if rows[i]["release_date"] <= RELEASE_END.isoformat()]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_details(appid):
    data = get_json("https://store.steampowered.com/api/appdetails",
                    params={"appids": appid, "cc": COUNTRY, "l": LANGUAGE}, delay=DELAY_STORE)
    entry = (data or {}).get(str(appid), {})
    if not entry.get("success"):
        return {"appid": appid, "success": False, "fetched_at": now()}
    details = {k: v for k, v in entry["data"].items() if k not in DROP_FIELDS}
    
    details["n_screenshots"] = len(details.pop("screenshots", []) or [])
    details["n_movies"] = len(details.pop("movies", []) or [])
    return {"appid": appid, "success": True, "fetched_at": now(), "data": details}


def fetch_reviews(appid):
    data = get_json(f"https://store.steampowered.com/appreviews/{appid}",
                    params={"json": 1, "language": "all", "purchase_type": "all",
                            "filter": "all", "num_per_page": 0}, delay=DELAY_REVIEWS)
    if not data or not data.get("success"):
        return {"appid": appid, "success": False, "fetched_at": now()}
    return {"appid": appid, "success": True, "fetched_at": now(), "summary": data["query_summary"]}


def fetch_steamspy(appid):
    data = get_json("https://steamspy.com/api.php",
                    params={"request": "appdetails", "appid": appid}, delay=DELAY_STEAMSPY)
    if not data:
        return {"appid": appid, "success": False, "fetched_at": now()}
    tags = data.get("tags") or {}
    return {"appid": appid, "success": True, "fetched_at": now(),
            
            "tags": tags if isinstance(tags, dict) else {},
            "developer": data.get("developer"), "publisher": data.get("publisher")}


def fetch_developer(developer):
    games = []
    for start in range(0, 500, 100):
        data = get_json("https://store.steampowered.com/search/results/", params={
            "query": "", "developer": developer, "start": start, "count": 100, "category1": 998,
            "sort_by": "Released_DESC", "infinite": 1, "cc": COUNTRY, "l": LANGUAGE}, delay=DELAY_SEARCH)
        if not data:
            return {"developer": developer, "success": False, "fetched_at": now()}
        rows = [parse_row(b) for b in ROW_RE.findall(data.get("results_html", ""))]
        games += [{k: r[k] for k in ("appid", "release_date", "search_review_pct", "search_review_count")}
                  for r in rows if r]
        if start + 100 >= data.get("total_count", 0):
            break
    return {"developer": developer, "success": True, "fetched_at": now(), "games": games}


def run_developers(limit):
    devs = {}
    for r in read_jsonl(APPDETAILS):
        if r.get("success") and r["data"].get("developers"):
            devs.setdefault(r["data"]["developers"][0], None)
    done = {r["developer"] for r in read_jsonl(DEVELOPERS)}
    todo = [d for d in devs if d not in done][:limit]
    print(f"[developers] {len(devs)} dezvoltatori, {len(done)} deja descărcați, {len(todo)} de făcut")
    for k, dev in enumerate(todo, 1):
        append_jsonl(DEVELOPERS, fetch_developer(dev))
        if k % 50 == 0 or k == len(todo):
            print(f"[developers] {k}/{len(todo)}")


STAGES = {
    "details": (APPDETAILS, fetch_details),
    "reviews": (REVIEWS, fetch_reviews),
    "steamspy": (STEAMSPY, fetch_steamspy),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=[*STAGES, "developers"], required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.stage == "developers":
        return run_developers(args.limit)
    if args.stage == "reviews" and redirects_away("https://store.steampowered.com/appreviews/730", {"json": 1}):
        print("[reviews] Endpoint-ul Steam /appreviews nu mai răspunde (redirecționează la prima pagină).\n"
              "          Etapa nu e necesară: preprocess.py ia ținta din search_index.jsonl\n"
              "          (procentul și numărul de recenzii afișate de Steam). Oprire.")
        return

    out_path, fetch = STAGES[args.stage]
    ids = candidates()
    done = done_ids(out_path)
    todo = [i for i in ids if i not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"[{args.stage}] {len(ids)} candidați, {len(done)} deja descărcați, {len(todo)} de făcut")

    for k, appid in enumerate(todo, 1):
        row = fetch(appid)
        append_jsonl(out_path, row)
        if k % 50 == 0 or k == len(todo):
            print(f"[{args.stage}] {k}/{len(todo)}  (ultimul appid {appid}, success={row['success']})")


if __name__ == "__main__":
    main()
