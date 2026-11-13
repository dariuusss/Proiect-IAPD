import json
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import BLUE, ORANGE, RES_DIR, ROOT, TEXT_2, save, set_style

TIMELINES = ROOT / "data" / "raw" / "review_timelines.jsonl"
AGES = [7, 14, 30, 60, 90, 120, 180, 365]
MIN_REVIEWS_AT_AGE = 10  
MIN_AGE_DAYS = 120        


def main():
    set_style()
    rows = []
    with open(TIMELINES, encoding="utf-8") as f:
        games = [json.loads(line) for line in f if line.strip()]
    for g in games:
        release = datetime.fromisoformat(g["release_date"]).replace(tzinfo=timezone.utc).timestamp()
        ts = np.array([r[0] for r in g["reviews"]])
        up = np.array([r[1] for r in g["reviews"]])
        if len(ts) < 20:
            continue
        final = up.mean()
        for d in AGES:
            mask = ts <= release + d * 86400
            n = mask.sum()
            rows.append({"appid": g["appid"], "age_days": d, "n_at_age": n, "share_of_reviews": n / len(ts),
                         "ratio_at_age": up[mask].mean() if n else np.nan, "ratio_final": final})
    df = pd.DataFrame(rows)
    df["abs_diff"] = (df["ratio_at_age"] - df["ratio_final"]).abs()
    valid = df[df["n_at_age"] >= MIN_REVIEWS_AT_AGE]

    summary = valid.groupby("age_days").agg(
        jocuri=("appid", "nunique"),
        diferenta_mediana=("abs_diff", "median"),
        diferenta_p90=("abs_diff", lambda s: s.quantile(0.9)),
        peste_5pp=("abs_diff", lambda s: (s > 0.05).mean()),
    ).join(df.groupby("age_days")["share_of_reviews"].median().rename("fractie_recenzii_mediana"))

    lines = [
        "# Stabilitatea scorului după lansare", "",
        f"Eșantion: {df['appid'].nunique()} jocuri lansate între 2024-01 și 2025-09 (≥ 1 an de istoric).",
        f"Pentru fiecare vârstă se iau doar jocurile cu ≥ {MIN_REVIEWS_AT_AGE} recenzii la acea vârstă.", "",
        "- `diferenta_mediana` / `diferenta_p90`: |scor la ziua d − scor actual| (0.05 = 5 puncte procentuale)",
        "- `peste_5pp`: ce parte din jocuri au scorul la ziua d mai departe de 5 pp de cel actual",
        "- `fractie_recenzii_mediana`: ce parte din recenziile de azi existau deja la ziua d", "",
        summary.to_markdown(floatfmt=".3f"), "",
    ]
    (RES_DIR / "review_stability.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    axes[0].plot(summary.index, summary["diferenta_mediana"], marker="o", ms=6, lw=2, color=BLUE, label="mediana")
    axes[0].plot(summary.index, summary["diferenta_p90"], marker="o", ms=6, lw=2, color=ORANGE, label="percentila 90")
    axes[0].axhline(0.05, color=TEXT_2, lw=0.8, ls="--")
    axes[0].text(AGES[0], 0.052, "5 pp", ha="left", va="bottom", color=TEXT_2)
    for ax in axes:
        ax.axvline(MIN_AGE_DAYS, color=TEXT_2, lw=0.8, ls=":")
    axes[1].text(MIN_AGE_DAYS * 1.06, 0.05, f"prag ales: {MIN_AGE_DAYS} zile", color=TEXT_2)
    axes[0].set_xscale("log")
    axes[0].set_xticks(AGES, [str(a) for a in AGES])
    axes[0].set_xlabel("zile de la lansare")
    axes[0].set_ylabel("|scor la ziua d − scor actual|")
    axes[0].set_title("Cât se mai schimbă scorul după ziua d")
    axes[0].legend(frameon=False)
    axes[1].plot(summary.index, summary["fractie_recenzii_mediana"], marker="o", ms=6, lw=2, color=BLUE)
    axes[1].set_xscale("log")
    axes[1].set_xticks(AGES, [str(a) for a in AGES])
    axes[1].set_ylim(0, 1)
    axes[1].set_xlabel("zile de la lansare")
    axes[1].set_ylabel("fracție (mediană)")
    axes[1].set_title("Ce parte din recenziile de azi existau la ziua d")
    save(fig, "eda_00_review_stability")


if __name__ == "__main__":
    main()
