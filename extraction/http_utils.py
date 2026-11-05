"""Utilitare HTTP și I/O: request-uri politicoase cu reîncercare și fișiere JSONL reluabile."""
import json
import time
from pathlib import Path

import requests

from config import USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def get_json(url, params=None, delay=1.0, max_retries=5):
    """GET care întoarce JSON. Așteaptă `delay` secunde după fiecare request și,
    la erori (429 = prea multe request-uri, 5xx, timeout), reîncearcă cu pauză exponențială."""
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
    """True dacă endpoint-ul răspunde cu o redirecționare (3xx). Steam trimite la prima pagină a
    magazinului endpoint-urile pe care nu le mai servește (așa s-a întâmplat cu /appreviews în nov. 2026);
    fără verificarea asta, get_json ar reîncerca minute întregi pentru fiecare joc."""
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
                    pass  # linie trunchiată de o oprire bruscă
    return rows


def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def done_ids(path: Path):
    """ID-urile deja descărcate: permit reluarea crawl-ului după o întrerupere."""
    return {row["appid"] for row in read_jsonl(path)}
