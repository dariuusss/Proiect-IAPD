import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (BLUE, MIN_REVIEWS_MODEL, NUMERIC_FEATURES, ORANGE, RES_DIR,
                    TEXT_2, load, pretty, save, set_style)

lines = [] 


def md(text=""):
    lines.append(text)


def table(df, floatfmt=".3f"):
    md(df.to_markdown(floatfmt=floatfmt))
    md()


def review_threshold(df_all):
    
    thresholds = [20, 30, 50, 100, 200, 500, 1000]
    rows = []
    for t in thresholds:
        sub = df_all[df_all["total_reviews"] >= t]
        rows.append({"prag": t, "n_jocuri": len(sub),
                     "media_positive_ratio": sub["positive_ratio"].mean(),
                     "std_positive_ratio": sub["positive_ratio"].std()})
    res = pd.DataFrame(rows).set_index("prag")
    md("## Alegerea pragului minim de recenzii")
    md("Cu cât pragul e mai mare, ținta e mai stabilă (mai puțin zgomot), dar pierdem jocuri.")
    table(res)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(res.index, res["n_jocuri"], marker="o", color=BLUE, lw=2, ms=6)
    ax.axvline(MIN_REVIEWS_MODEL, color=ORANGE, lw=1.5, ls="--")
    ax.text(MIN_REVIEWS_MODEL * 1.08, res["n_jocuri"].max() * 0.95, f"prag ales = {MIN_REVIEWS_MODEL}", color=TEXT_2)
    ax.set_xscale("log")
    ax.set_xlabel("număr minim de recenzii (scală log)")
    ax.set_ylabel("jocuri rămase")
    ax.set_title("Câte jocuri păstrăm în funcție de prag")
    save(fig, "eda_01_review_threshold")


def target(df):
    md("## Ținta")
    table(df[["positive_ratio", "total_reviews"]].describe().T)
    share = df["is_successful"].mean()
    md(f"Clasificare `is_successful` (ratio ≥ 0.80, pragul Steam „Very Positive”): **{share:.1%}** pozitive, "
       f"{1 - share:.1%} negative.")
    md()

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    axes[0].hist(df["positive_ratio"], bins=40, color=BLUE, edgecolor="#fcfcfb", linewidth=1)
    axes[0].axvline(df["positive_ratio"].median(), color=ORANGE, lw=1.5, ls="--")
    axes[0].text(df["positive_ratio"].median() - 0.02, axes[0].get_ylim()[1] * 0.9,
                 f"mediana {df['positive_ratio'].median():.2f}", ha="right", color=TEXT_2)
    axes[0].set_title("Distribuția procentului de recenzii pozitive")
    axes[0].set_xlabel("positive_ratio")
    axes[0].set_ylabel("jocuri")
    axes[1].hist(np.log10(df["total_reviews"]), bins=40, color=BLUE, edgecolor="#fcfcfb", linewidth=1)
    axes[1].set_title("Numărul de recenzii (log10)")
    axes[1].set_xlabel("log10(total recenzii)")
    save(fig, "eda_02_target")


def releases_and_price(df):
    fig, ax = plt.subplots(figsize=(11, 3.5))
    monthly = df.set_index("release_date").resample("MS").size()
    ax.bar(monthly.index, monthly.values, width=24, color=BLUE)
    ax.set_title("Lansări pe lună (jocuri din set)")
    ax.set_ylabel("jocuri")
    save(fig, "eda_03_releases_per_month")

    md("## Prețul")
    md(f"- jocuri gratuite: **{df['is_free'].mean():.1%}**")
    md(f"- preț median (doar jocurile cu plată): **{df.loc[df['is_free'] == 0, 'price_eur'].median():.2f} €**")
    md()
    bins = [-0.01, 0, 5, 10, 20, 30, 1000]
    labels = ["gratuit", "≤5€", "5-10€", "10-20€", "20-30€", ">30€"]
    df["price_bucket"] = pd.cut(df["price_eur"], bins=bins, labels=labels)
    by_price = df.groupby("price_bucket", observed=True)["positive_ratio"].agg(["count", "mean", "median"])
    table(by_price)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    axes[0].bar(by_price.index.astype(str), by_price["count"], color=BLUE)
    axes[0].set_title("Jocuri pe interval de preț")
    axes[0].set_ylabel("jocuri")
    groups = [df.loc[df["price_bucket"] == l, "positive_ratio"] for l in labels]
    boxplot(axes[1], groups, labels)
    axes[1].set_title("Receptarea pe interval de preț")
    axes[1].set_ylabel("positive_ratio")
    save(fig, "eda_04_price")


def boxplot(ax, groups, labels, vert=True):
    bp = ax.boxplot(groups, tick_labels=labels, vert=vert, patch_artist=True, showfliers=False,
                    widths=0.6, medianprops={"color": ORANGE, "lw": 2})
    for box in bp["boxes"]:
        box.set(facecolor="#d6e5f7", edgecolor=BLUE)
    for part in ("whiskers", "caps"):
        for line in bp[part]:
            line.set(color=BLUE)


def by_multilabel(df, column, title, name, top=15):
    exploded = df[["positive_ratio", column]].assign(**{column: df[column].fillna("").str.split("|")}).explode(column)
    exploded = exploded[exploded[column] != ""]
    counts = exploded[column].value_counts().head(top)
    stats = exploded[exploded[column].isin(counts.index)].groupby(column)["positive_ratio"] \
        .agg(["count", "mean", "median"]).sort_values("median")
    md(f"## Receptarea pe {title}")
    table(stats)

    fig, ax = plt.subplots(figsize=(8, 0.35 * len(stats) + 1.2))
    groups = [exploded.loc[exploded[column] == g, "positive_ratio"] for g in stats.index]
    boxplot(ax, groups, [f"{g} ({n})" for g, n in zip(stats.index, stats["count"])], vert=False)
    ax.set_title(f"positive_ratio pe {title} (top {top} după frecvență)")
    ax.set_xlabel("positive_ratio")
    ax.grid(axis="y", visible=False)
    save(fig, name)


def correlations(df):
    corr = df[NUMERIC_FEATURES + ["positive_ratio"]].corr(method="spearman")["positive_ratio"] \
        .drop("positive_ratio").dropna().sort_values()
    md("## Corelații Spearman cu ținta (feature-uri numerice)")
    table(corr.to_frame("spearman_rho"))

    fig, ax = plt.subplots(figsize=(7, 0.28 * len(corr) + 1))
    colors = [ORANGE if v < 0 else BLUE for v in corr.values]
    ax.barh([pretty(c) for c in corr.index], corr.values, color=colors, height=0.7)
    ax.axvline(0, color=TEXT_2, lw=0.8)
    ax.set_title("Corelația Spearman cu positive_ratio")
    ax.set_xlabel("ρ (albastru = pozitivă, portocaliu = negativă)")
    ax.grid(axis="y", visible=False)
    save(fig, "eda_07_correlations")


def hypotheses(df):
    md("## Ipoteze specifice")
    pub = df.groupby("is_self_published")["positive_ratio"].agg(["count", "mean", "median"])
    pub.index = ["are publisher", "self-published"]
    md("**Self-published vs. cu publisher**")
    table(pub)

    df["media_bucket"] = pd.cut(df["n_screenshots"] + df["n_movies"], [-1, 5, 10, 15, 20, 1000],
                                labels=["≤5", "6-10", "11-15", "16-20", ">20"])
    media = df.groupby("media_bucket", observed=True)["positive_ratio"].agg(["count", "mean", "median"])
    md("**Conținut media (screenshot-uri + trailere)**")
    table(media)

    ea = df.groupby("is_early_access")["positive_ratio"].agg(["count", "mean", "median"])
    ea.index = ["lansare completă", "early access"]
    md("**Early Access**")
    table(ea)

    dev = df.assign(dev_bucket=pd.cut(df["dev_prior_games"], [-1, 0, 1, 3, 10**6],
                                      labels=["primul joc", "1 anterior", "2-3", "4+"]))
    dev = dev.groupby("dev_bucket", observed=True)["positive_ratio"].agg(["count", "mean", "median"])
    md("**Experiența dezvoltatorului (jocuri lansate anterior pe Steam)**")
    table(dev)
    rated = df[df["dev_has_track_record"] == 1]
    rho = rated[["dev_prior_mean_score", "positive_ratio"]].corr(method="spearman").iloc[0, 1]
    md(f"**Scorul jocurilor anterioare ale dezvoltatorului** ({len(rated)} jocuri cu istoric): "
       f"corelația Spearman cu scorul jocului nou = **{rho:.3f}**")
    md()

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    boxplot(axes[0], [df.loc[df["is_self_published"] == v, "positive_ratio"] for v in (0, 1)],
            ["are publisher", "self-published"])
    axes[0].set_title("Publisher")
    axes[0].set_ylabel("positive_ratio")
    boxplot(axes[1], [df.loc[df["media_bucket"] == b, "positive_ratio"] for b in media.index], list(media.index))
    axes[1].set_title("Screenshot-uri + trailere")
    boxplot(axes[2], [df.loc[df["is_early_access"] == v, "positive_ratio"] for v in (0, 1)],
            ["lansare completă", "early access"])
    axes[2].set_title("Early Access")
    save(fig, "eda_08_hypotheses")


def main():
    set_style()
    df_all = load(min_reviews=0)
    df = load()
    feature_cols = [c for c in df.columns if c in NUMERIC_FEATURES or c.startswith(("genre_", "cat_", "tag_"))]

    md("# Rezumat EDA")
    md()
    md(f"- jocuri în `steam_clean.csv`: **{len(df_all)}** (≥ 20 recenzii la colectare)")
    md(f"- jocuri folosite pentru modelare (≥ {MIN_REVIEWS_MODEL} recenzii): **{len(df)}**")
    md(f"- feature-uri candidate: **{len(feature_cols)}** "
       f"({len(NUMERIC_FEATURES)} numerice/binare + {len(feature_cols) - len(NUMERIC_FEATURES)} one-hot)")
    md(f"- interval lansări: {df['release_date'].min().date()} → {df['release_date'].max().date()}")
    md(f"- jocuri cu tag-uri în SteamSpy: {(df_all['n_steamspy_tags'] > 0).mean():.1%} "
       f"(de aceea folosim tag-urile din Store)")
    md()
    missing = df_all.isna().mean()
    missing = missing[missing > 0].sort_values(ascending=False)
    md("## Valori lipsă (proporție)")
    table(missing.to_frame("lipsa") if len(missing) else pd.DataFrame({"lipsa": ["niciuna"]}))
    md("## Statistici descriptive (feature-uri numerice)")
    table(df[NUMERIC_FEATURES].describe().T[["mean", "std", "min", "50%", "max"]], floatfmt=".2f")

    review_threshold(df_all)
    target(df)
    releases_and_price(df)
    by_multilabel(df, "genres", "genuri", "eda_05_genres")
    by_multilabel(df, "tags", "tag-uri", "eda_06_tags", top=20)
    correlations(df)
    hypotheses(df)

    out = RES_DIR / "eda_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rezumat: {out}")


if __name__ == "__main__":
    main()
