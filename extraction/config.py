"""Setări comune pentru toate scripturile de colectare și preprocesare."""
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
FINAL_DIR = ROOT / "data" / "final"

# Fișierele brute (JSON Lines: un obiect JSON pe linie, adăugat pe măsură ce e descărcat)
SEARCH_INDEX = RAW_DIR / "search_index.jsonl"   # lista jocurilor din căutarea Steam
APPDETAILS = RAW_DIR / "appdetails.jsonl"       # metadate Store API
REVIEWS = RAW_DIR / "reviews.jsonl"             # sumarul recenziilor (ținta)
STEAMSPY = RAW_DIR / "steamspy.jsonl"           # tag-uri SteamSpy
TAG_NAMES = RAW_DIR / "tag_names.json"         # tagid -> nume (tag-urile din Store)
DEVELOPERS = RAW_DIR / "developers.jsonl"       # toate jocurile fiecărui dezvoltator (istoric)
CLEAN_CSV = FINAL_DIR / "steam_clean.csv"

# Fereastra de lansare studiată. Un joc intră în set doar dacă avea cel puțin MIN_AGE_DAYS
# zile când i-am descărcat recenziile: înainte de asta scorul încă se mișcă prea mult.
# Pragul de 120 de zile a fost ales empiric (analysis/review_stability.py): de la 60 la 120 de zile
# ponderea jocurilor cu scorul încă la > 5 pp de valoarea finală scade de la 33% la 21%, apoi stagnează.
RELEASE_START = date(2024, 1, 1)
MIN_AGE_DAYS = 120
RELEASE_END = date.today() - timedelta(days=MIN_AGE_DAYS)   # pentru coada de crawl

# Prag minim de recenzii (din sumarul căutării) pentru a intra în coada de crawl.
# Pragul final pentru modelare se alege în preprocesare/EDA.
MIN_REVIEWS_CRAWL = 20

# Ordinea crawl-ului e amestecată cu o sămânță fixă: dacă oprim scriptul oricând,
# ce am descărcat e un eșantion aleator (nu doar cele mai noi jocuri).
SHUFFLE_SEED = 42

# Politețe față de servere (limita Store API ~200 request-uri / 5 minute)
DELAY_STORE = 1.5
DELAY_REVIEWS = 1.0
DELAY_STEAMSPY = 1.0
DELAY_SEARCH = 1.0

COUNTRY = "ro"     # prețuri în EUR
LANGUAGE = "english"
USER_AGENT = "IAPD-student-project/1.0 (academic research, contact via GitHub)"
