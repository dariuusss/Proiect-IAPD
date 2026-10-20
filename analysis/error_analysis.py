"""Analiza erorilor pentru cel mai bun model de regresie (salvat de models.py).

- unde greșește modelul: pe genuri, intervale de preț, număr de recenzii;
- ce feature-uri contează (SHAP);
- exemple concrete de jocuri prezise foarte greșit.

Rulare:  python analysis/error_analysis.py   (după models.py)
Rezultat: analysis/results/error_analysis.md, analysis/figures/err_*.png
"""
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from common import (BLUE, ORANGE, RES_DIR, TEXT_2, load, pretty, save, set_style)

lines = []


def md(text=""):
    lines.append(text)


def error_by(preds, column, labels_order=None):
    g = preds.groupby(column, observed=True).agg(n=("abs_err", "size"), MAE=("abs_err", "mean"),
                                                 bias=("err", "mean"))
    if labels_order is not None:
        g = g.reindex(labels_order)
    return g


def bar_mae(ax, g, title):
    ax.bar(g.index.astype(str), g["MAE"], color=BLUE, width=0.65)
    ax.set_title(title)
    ax.set_ylabel("MAE")
    ax.tick_params(axis="x", rotation=30)


def main():
    set_style()
    preds = pd.read_csv(RES_DIR / "test_predictions.csv")
    bundle = joblib.load(RES_DIR / "best_regressor.joblib")
    preds["err"] = preds["pred_ratio"] - preds["positive_ratio"]   # >0 = modelul supraestimează
    preds["abs_err"] = preds["err"].abs()

    md(f"# Analiza erorilor: {bundle['name']}")
    md()
    md(f"MAE total pe test: **{preds['abs_err'].mean():.4f}**, bias mediu: {preds['err'].mean():+.4f}")
    md()

    # --- pe intervale de preț, de recenzii și de țintă
    preds["price_bucket"] = pd.cut(preds["price_eur"], [-0.01, 0, 5, 10, 20, 30, 1000],
                                   labels=["gratuit", "≤5€", "5-10€", "10-20€", "20-30€", ">30€"])
    preds["reviews_bucket"] = pd.cut(preds["total_reviews"], [0, 50, 100, 500, 2000, 10**9],
                                     labels=["20-50", "51-100", "101-500", "501-2000", ">2000"])
    preds["target_bucket"] = pd.cut(preds["positive_ratio"], [-0.01, 0.5, 0.7, 0.8, 0.9, 1.0],
                                    labels=["<50%", "50-70%", "70-80%", "80-90%", "90-100%"])
    by_price = error_by(preds, "price_bucket")
    by_reviews = error_by(preds, "reviews_bucket")
    by_target = error_by(preds, "target_bucket")
    for title, g in [("interval de preț", by_price), ("număr de recenzii", by_reviews),
                     ("valoarea reală a țintei", by_target)]:
        md(f"## Eroarea pe {title}")
        md("`bias` > 0 înseamnă că modelul supraestimează receptarea.")
        md(g.to_markdown(floatfmt=".4f"))
        md()

    # --- pe genuri (un joc poate avea mai multe genuri)
    exploded = preds.assign(genre=preds["genres"].fillna("").str.split("|")).explode("genre")
    by_genre = error_by(exploded[exploded["genre"] != ""], "genre")
    by_genre = by_genre[by_genre["n"] >= 20].sort_values("MAE", ascending=False)
    md("## Eroarea pe gen (genuri cu ≥ 20 jocuri în test)")
    md(by_genre.to_markdown(floatfmt=".4f"))
    md()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    bar_mae(axes[0], by_price, "MAE pe interval de preț")
    bar_mae(axes[1], by_reviews, "MAE pe număr de recenzii")
    bar_mae(axes[2], by_target, "MAE pe receptarea reală")
    save(fig, "err_01_by_bucket")

    fig, ax = plt.subplots(figsize=(7, 0.35 * len(by_genre) + 1))
    ax.barh(by_genre.index, by_genre["MAE"], color=BLUE, height=0.65)
    ax.invert_yaxis()
    ax.set_title("MAE pe gen")
    ax.set_xlabel("MAE")
    ax.grid(axis="y", visible=False)
    save(fig, "err_02_by_genre")

    # --- cele mai mari erori
    cols = ["name", "genres", "price_eur", "total_reviews", "positive_ratio", "pred_ratio", "err"]
    md("## Cele mai mari supraestimări (modelul credea că va fi bine primit)")
    md(preds.sort_values("err", ascending=False).head(10)[cols].to_markdown(index=False, floatfmt=".3f"))
    md()
    md("## Cele mai mari subestimări (modelul credea că va fi slab primit)")
    md(preds.sort_values("err").head(10)[cols].to_markdown(index=False, floatfmt=".3f"))
    md()

    # --- SHAP: importanța feature-urilor (pe setul de test)
    df = load()
    features = bundle["features"]
    model = bundle["model"]
    test = df[df["appid"].isin(preds["appid"])]
    X_test = test[features].fillna(0).astype(float)
    if hasattr(model, "feature_importances_"):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
    else:  # model liniar într-un pipeline
        explainer = shap.Explainer(model.predict, X_test.sample(min(200, len(X_test)), random_state=0))
        shap_values = explainer(X_test).values
    importance = pd.Series(np.abs(shap_values).mean(axis=0), index=features).sort_values(ascending=False)
    md("## Importanța feature-urilor (media |SHAP|), top 20")
    md(importance.head(20).to_frame("mean_abs_shap").to_markdown(floatfmt=".4f"))
    md()

    top = importance.head(20)[::-1]
    fig, ax = plt.subplots(figsize=(7, 6.5))
    ax.barh([pretty(c) for c in top.index], top.values, color=BLUE, height=0.7)
    ax.set_title(f"Top 20 feature-uri ({bundle['name']}, |SHAP| mediu)")
    ax.set_xlabel("impact mediu asupra predicției positive_ratio")
    ax.grid(axis="y", visible=False)
    save(fig, "err_03_shap_importance")

    plt.figure()
    shap.summary_plot(shap_values, X_test, feature_names=[pretty(c) for c in features], max_display=15, show=False)
    fig = plt.gcf()
    fig.set_size_inches(8, 6.5)
    fig.axes[0].set_title("SHAP: direcția efectului (roșu = valoare mare a feature-ului)", color=TEXT_2)
    save(fig, "err_04_shap_beeswarm")

    out = RES_DIR / "error_analysis.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rezumat: {out}")


if __name__ == "__main__":
    main()
