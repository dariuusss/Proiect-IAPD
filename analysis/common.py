from pathlib import Path

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import pandas as pd
from cycler import cycler

ROOT = Path(__file__).resolve().parent.parent
CLEAN_CSV = ROOT / "data" / "final" / "steam_clean.csv"
FIG_DIR = ROOT / "analysis" / "figures"
RES_DIR = ROOT / "analysis" / "results"
FIG_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)


MIN_REVIEWS_MODEL = 20
RANDOM_STATE = 42

NUMERIC_FEATURES = [
    "price_eur", "is_free", "has_price_info", "required_age",
    "release_year", "release_month", "release_dayofweek",
    "n_genres", "n_categories", "has_windows", "has_mac", "has_linux",
    "n_languages", "has_full_audio_en", "n_achievements", "n_dlc",
    "n_screenshots", "n_movies", "description_length", "short_description_length",
    "has_website", "controller_support", "n_content_descriptors",
    "is_early_access", "is_self_published",
    "dev_prior_games", "dev_prior_rated_games", "dev_has_track_record", "dev_prior_mean_score",
]

POST_RELEASE_MUTABLE = ["n_dlc", "n_languages", "has_full_audio_en", "n_achievements", "is_early_access"]

LEAKY = {"total_positive", "total_negative", "total_reviews", "review_score_desc",
         "positive_ratio", "is_successful", "game_age_days"}


def load(min_reviews=MIN_REVIEWS_MODEL):
    df = pd.read_csv(CLEAN_CSV)
    df["release_date"] = pd.to_datetime(df["release_date"])
    return df[df["total_reviews"] >= min_reviews].reset_index(drop=True)


def feature_columns(df):
    one_hot = [c for c in df.columns if c.startswith(("genre_", "cat_", "tag_"))]
    cols = [c for c in NUMERIC_FEATURES + one_hot if df[c].nunique() > 1]
    assert not LEAKY & set(cols)
    return cols


def pretty(col):
    return col.replace("_", " ")


BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
TEXT, TEXT_2 = "#0b0b0b", "#52514e"


def set_style():
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
        "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
        "axes.edgecolor": "#c9c8c3", "axes.labelcolor": TEXT_2, "axes.titlecolor": TEXT,
        "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
        "xtick.color": TEXT_2, "ytick.color": TEXT_2, "font.size": 10,
        "axes.prop_cycle": cycler(color=[BLUE, ORANGE, AQUA]),
    })


def save(fig, name):
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  grafic: {path.relative_to(ROOT)}")
