"""Pasul 1: lista jocurilor lansate în fereastra studiată.

În loc să descărcăm lista completă de ~200.000 de aplicații Steam și să cerem
appdetails pentru fiecare (zile întregi de crawl), folosim căutarea din magazin:
filtrată pe tipul „Games” (category1=998) și sortată după data lansării, descendent.
Un singur request întoarce 100 de jocuri cu appid, nume, dată de lansare, sumarul
recenziilor și tag-urile principale. Ne oprim când trecem de RELEASE_START.

Rezultat: data/raw/search_index.jsonl (câte o linie per joc).
Rulare:  python extraction/get_app_list.py
"""
import html
import json
import re
from datetime import datetime

from config import (COUNTRY, DELAY_SEARCH, LANGUAGE, RAW_DIR, RELEASE_START,
                    SEARCH_INDEX, TAG_NAMES)
from http_utils import append_jsonl, get_json, read_jsonl

SEARCH_URL = "https://store.steampowered.com/search/results/"
PAGE_SIZE = 100
STATE_FILE = RAW_DIR / "search_state.json"
# Ordinea căutării nu e perfect strictă, așa că ne oprim abia după multe jocuri la rând mai vechi
STOP_AFTER_OLD = 500

ROW_RE = re.compile(r'<a href="https://store\.steampowered\.com/(?:app|bundle|sub)/.*?</a>', re.S)
APPID_RE = re.compile(r'data-ds-appid="(\d+)"')
TAGIDS_RE = re.compile(r'data-ds-tagids="\[([\d,]*)\]"')
TITLE_RE = re.compile(r'<span class="title">(.*?)</span>', re.S)
RELEASED_RE = re.compile(r'search_released responsive_secondrow">\s*(.*?)\s*</div>', re.S)
REVIEW_RE = re.compile(r'(\d+)% of the ([\d,]+) user reviews')


def parse_date(text):
    for fmt in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None  # „Coming soon”, „Q3 2026”, „To be announced” etc.


def parse_row(block):
    appid = APPID_RE.search(block)
    if not appid or "," in appid.group(1):
        return None  # pachete/bundle-uri cu mai multe appid-uri
    title = TITLE_RE.search(block)
    released = RELEASED_RE.search(block)
    release_text = html.unescape(released.group(1)).strip() if released else ""
    release = parse_date(release_text)
    review = REVIEW_RE.search(html.unescape(html.unescape(block)))
    tags = TAGIDS_RE.search(block)
    return {
        "appid": int(appid.group(1)),
        "name": html.unescape(title.group(1)).strip() if title else None,
        "release_text": release_text,
        "release_date": release.isoformat() if release else None,
        "search_review_pct": int(review.group(1)) if review else None,
        "search_review_count": int(review.group(2).replace(",", "")) if review else 0,
        "search_tagids": [int(t) for t in tags.group(1).split(",") if t] if tags else [],
    }


def save_tag_names():
    """Căutarea dă doar ID-urile tag-urilor; numele lor vin din lista de tag-uri populare."""
    tags = get_json("https://store.steampowered.com/tagdata/populartags/english", delay=DELAY_SEARCH)
    if tags:
        TAG_NAMES.write_text(json.dumps({t["tagid"]: t["name"] for t in tags}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        print(f"Salvat {len(tags)} nume de tag-uri în {TAG_NAMES.name}")


def main():
    save_tag_names()
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"start": 0, "old_streak": 0}
    seen = {row["appid"] for row in read_jsonl(SEARCH_INDEX)}
    print(f"Reluare de la start={state['start']}, {len(seen)} jocuri deja salvate")

    while True:
        data = get_json(SEARCH_URL, params={
            "query": "", "start": state["start"], "count": PAGE_SIZE, "category1": 998,
            "sort_by": "Released_DESC", "infinite": 1, "cc": COUNTRY, "l": LANGUAGE,
        }, delay=DELAY_SEARCH)
        if not data or not data.get("results_html", "").strip():
            print("Nu mai sunt rezultate, oprire.")
            break

        new = 0
        for block in ROW_RE.findall(data["results_html"]):
            row = parse_row(block)
            if row is None:
                continue
            if row["release_date"] and row["release_date"] < RELEASE_START.isoformat():
                state["old_streak"] += 1
            elif row["release_date"]:
                state["old_streak"] = 0
            if row["appid"] not in seen:
                seen.add(row["appid"])
                append_jsonl(SEARCH_INDEX, row)
                new += 1

        state["start"] += PAGE_SIZE
        STATE_FILE.write_text(json.dumps(state))
        last = row["release_text"] if row else "?"
        print(f"start={state['start']:>6}  +{new:<3} jocuri  total={len(seen):>6}  ultima dată: {last}")

        if state["old_streak"] >= STOP_AFTER_OLD:
            print(f"Am trecut de {RELEASE_START}, oprire.")
            break


if __name__ == "__main__":
    main()
