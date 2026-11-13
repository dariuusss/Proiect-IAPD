import json
import time
from pathlib import Path

import requests

from config import USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def get_json(url, params=None, delay=1.0, max_retries=5):
    wait = 10
    for attempt in range(1, max_retries + 1):
        try:
            r = _session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                time.sleep(delay)
                return r.json()
            if r.status_code in (429, 403) or r.status_code >= 500:
                print(f"  HTTP {r.status_code}, pauză {wait}s (încercarea {attempt})")
            else:
                time.sleep(delay)
                return None
        except (requests.RequestException, ValueError) as e:
            print(f"  eroare {type(e).__name__}, pauză {wait}s (încercarea {attempt})")
        time.sleep(wait)
        wait = min(wait * 2, 300)
    return None


def redirects_away(url, params=None):
    try:
        r = _session.get(url, params=params, timeout=30, allow_redirects=False)
        return 300 <= r.status_code < 400
    except requests.RequestException:
        return False


def read_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  
    return rows


def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def done_ids(path: Path):
    return {row["appid"] for row in read_jsonl(path)}
