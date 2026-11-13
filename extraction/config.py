from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
FINAL_DIR = ROOT / "data" / "final"


SEARCH_INDEX = RAW_DIR / "search_index.jsonl"   
APPDETAILS = RAW_DIR / "appdetails.jsonl"       
REVIEWS = RAW_DIR / "reviews.jsonl"             
STEAMSPY = RAW_DIR / "steamspy.jsonl"           
TAG_NAMES = RAW_DIR / "tag_names.json"         
DEVELOPERS = RAW_DIR / "developers.jsonl"       
CLEAN_CSV = FINAL_DIR / "steam_clean.csv"

RELEASE_START = date(2024, 1, 1)
MIN_AGE_DAYS = 120
RELEASE_END = date.today() - timedelta(days=MIN_AGE_DAYS)  

MIN_REVIEWS_CRAWL = 20

SHUFFLE_SEED = 42

DELAY_STORE = 1.5
DELAY_REVIEWS = 1.0
DELAY_STEAMSPY = 1.0
DELAY_SEARCH = 1.0

COUNTRY = "ro"     
LANGUAGE = "english"
USER_AGENT = "IAPD-student-project/1.0 (academic research, contact via GitHub)"
