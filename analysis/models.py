"""Modele de predicție: regresie (positive_ratio) și clasificare (is_successful).

Pentru fiecare sarcină comparăm, pe ACELAȘI split 80/20:
  baseline naiv -> model liniar -> Random Forest -> XGBoost -> LightGBM
  + un experiment cu text (TF-IDF pe descrierea scurtă).
Hiperparametrii se aleg cu 5-fold cross-validation DOAR pe setul de antrenare.
La final: un split temporal (antrenare 2024, testare 2025-2026) pentru cel mai bun model.

Rulare:  python analysis/models.py
Rezultat: analysis/results/*.csv, models_summary.md, best_*.joblib; analysis/figures/model_*.png
"""
import json
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.sparse import hstack, csr_matrix
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (ConfusionMatrixDisplay, balanced_accuracy_score, f1_score,
                             mean_absolute_error, r2_score, roc_auc_score,
                             roc_curve, root_mean_squared_error)
from sklearn.model_selection import RandomizedSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from common import (BLUE, ORANGE, POST_RELEASE_MUTABLE, RANDOM_STATE, RES_DIR, TEXT_2,
                    feature_columns, load, save, set_style)

warnings.filterwarnings("ignore", category=UserWarning)
N_ITER = 20   # combinații de hiperparametri încercate per model
CV = 5


def search(estimator, grid, X, y, scoring):
    """Alege hiperparametrii cu 5-fold CV pe train. Întoarce și scorul CV (medie, deviație standard)
    al combinației alese: cu un set de test mic, el arată cât de mult variază rezultatele."""
    sign = -1 if scoring.startswith("neg_") else 1
    if not grid:
        scores = cross_val_score(estimator, X, y, cv=CV, scoring=scoring) * sign
        return estimator.fit(X, y), {}, (scores.mean(), scores.std())
    rs = RandomizedSearchCV(estimator, grid, n_iter=N_ITER, cv=CV, scoring=scoring,
                            random_state=RANDOM_STATE, n_jobs=-1)
    rs.fit(X, y)
    i = rs.best_index_
    cv = (rs.cv_results_["mean_test_score"][i] * sign, rs.cv_results_["std_test_score"][i])
    return rs.best_estimator_, rs.best_params_, cv


def regression_models():
    return {
        "Baseline (media)": (DummyRegressor(strategy="mean"), None),
        "Ridge": (make_pipeline(StandardScaler(), Ridge()),
                  {"ridge__alpha": np.logspace(-2, 3, 30)}),
        "Random Forest": (RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1),
                          {"n_estimators": [200, 400], "max_depth": [None, 10, 20],
                           "min_samples_leaf": [1, 3, 5, 10], "max_features": ["sqrt", 0.3, 0.5]}),
        "XGBoost": (XGBRegressor(random_state=RANDOM_STATE, n_jobs=1, tree_method="hist"),
                    {"n_estimators": [200, 400, 800], "learning_rate": [0.01, 0.03, 0.05, 0.1],
                     "max_depth": [3, 4, 6, 8], "subsample": [0.7, 0.85, 1.0],
                     "colsample_bytree": [0.5, 0.7, 1.0], "min_child_weight": [1, 5, 10]}),
        "LightGBM": (LGBMRegressor(random_state=RANDOM_STATE, n_jobs=1, verbose=-1),
                     {"n_estimators": [200, 400, 800], "learning_rate": [0.01, 0.03, 0.05, 0.1],
                      "num_leaves": [15, 31, 63], "min_child_samples": [10, 20, 50],
                      "subsample": [0.7, 0.85, 1.0], "subsample_freq": [1],
                      "colsample_bytree": [0.5, 0.7, 1.0]}),
    }


def classification_models(pos_weight):
    return {
        "Baseline (clasa majoritară)": (DummyClassifier(strategy="most_frequent"), None),
        "Logistic Regression": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
                                {"logisticregression__C": np.logspace(-3, 2, 30)}),
        "Random Forest": (RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1, class_weight="balanced"),
                          {"n_estimators": [200, 400], "max_depth": [None, 10, 20],
                           "min_samples_leaf": [1, 3, 5, 10], "max_features": ["sqrt", 0.3, 0.5]}),
        "XGBoost": (XGBClassifier(random_state=RANDOM_STATE, n_jobs=1, tree_method="hist",
                                  scale_pos_weight=pos_weight, eval_metric="logloss"),
                    {"n_estimators": [200, 400, 800], "learning_rate": [0.01, 0.03, 0.05, 0.1],
                     "max_depth": [3, 4, 6, 8], "subsample": [0.7, 0.85, 1.0],
                     "colsample_bytree": [0.5, 0.7, 1.0], "min_child_weight": [1, 5, 10]}),
        "LightGBM": (LGBMClassifier(random_state=RANDOM_STATE, n_jobs=1, verbose=-1, class_weight="balanced"),
                     {"n_estimators": [200, 400, 800], "learning_rate": [0.01, 0.03, 0.05, 0.1],
                      "num_leaves": [15, 31, 63], "min_child_samples": [10, 20, 50],
                      "subsample": [0.7, 0.85, 1.0], "subsample_freq": [1],
                      "colsample_bytree": [0.5, 0.7, 1.0]}),
    }


def reg_metrics(y, p):
    return {"MAE": mean_absolute_error(y, p), "RMSE": root_mean_squared_error(y, p), "R2": r2_score(y, p)}


def clf_metrics(y, proba, threshold=0.5):
    pred = (proba >= threshold).astype(int)
    # F1 macro (media F1 pe cele două clase) și balanced accuracy: F1 doar pe clasa pozitivă ar
    # favoriza modelul care prezice „succes” pentru toată lumea, fiindcă succesul e clasa majoritară.
    return {"F1_macro": f1_score(y, pred, average="macro", zero_division=0),
            "ROC_AUC": roc_auc_score(y, proba) if len(set(proba)) > 1 else 0.5,
            "Balanced_acc": balanced_accuracy_score(y, pred)}


def text_features(train_text, test_text):
    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=3, stop_words="english", sublinear_tf=True)
    return tfidf.fit_transform(train_text.fillna("")), tfidf.transform(test_text.fillna(""))


def run_regression(X_tr, X_te, y_tr, y_te, df_tr, df_te):
    results, preds, fitted, params = [], {}, {}, {}
    for name, (est, grid) in regression_models().items():
        print(f"  [regresie] {name}")
        model, best, (cv_m, cv_s) = search(est, grid, X_tr, y_tr, "neg_mean_absolute_error")
        p = np.clip(model.predict(X_te), 0, 1)
        results.append({"model": name, **reg_metrics(y_te, p), "CV_MAE": cv_m, "CV_MAE_std": cv_s})
        preds[name], fitted[name], params[name] = p, model, best

    # Experiment text: doar TF-IDF, apoi TF-IDF + feature-urile tabulare (scalate)
    T_tr, T_te = text_features(df_tr["short_description"], df_te["short_description"])
    scaler = StandardScaler().fit(X_tr)
    for name, A_tr, A_te in [
        ("Ridge (doar text TF-IDF)", T_tr, T_te),
        ("Ridge (tabular + text)", hstack([csr_matrix(scaler.transform(X_tr)), T_tr]).tocsr(),
         hstack([csr_matrix(scaler.transform(X_te)), T_te]).tocsr()),
    ]:
        print(f"  [regresie] {name}")
        model, best, (cv_m, cv_s) = search(Ridge(), {"alpha": np.logspace(-1, 3, 20)}, A_tr, y_tr, "neg_mean_absolute_error")
        p = np.clip(model.predict(A_te), 0, 1)
        results.append({"model": name, **reg_metrics(y_te, p), "CV_MAE": cv_m, "CV_MAE_std": cv_s})
        preds[name], params[name] = p, best
    return pd.DataFrame(results), preds, fitted, params


def run_classification(X_tr, X_te, y_tr, y_te, df_tr, df_te):
    results, probas, fitted, params = [], {}, {}, {}
    pos_weight = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
    for name, (est, grid) in classification_models(pos_weight).items():
        print(f"  [clasificare] {name}")
        model, best, (cv_m, cv_s) = search(est, grid, X_tr, y_tr, "roc_auc")
        proba = model.predict_proba(X_te)[:, 1]
        results.append({"model": name, **clf_metrics(y_te, proba), "CV_AUC": cv_m, "CV_AUC_std": cv_s})
        probas[name], fitted[name], params[name] = proba, model, best

    T_tr, T_te = text_features(df_tr["short_description"], df_te["short_description"])
    scaler = StandardScaler().fit(X_tr)
    A_tr = hstack([csr_matrix(scaler.transform(X_tr)), T_tr]).tocsr()
    A_te = hstack([csr_matrix(scaler.transform(X_te)), T_te]).tocsr()
    print("  [clasificare] Logistic (tabular + text)")
    model, best, (cv_m, cv_s) = search(LogisticRegression(max_iter=3000, class_weight="balanced"),
                                       {"C": np.logspace(-3, 1, 20)}, A_tr, y_tr, "roc_auc")
    proba = model.predict_proba(A_te)[:, 1]
    results.append({"model": "Logistic (tabular + text)", **clf_metrics(y_te, proba), "CV_AUC": cv_m, "CV_AUC_std": cv_s})
    probas["Logistic (tabular + text)"], params["Logistic (tabular + text)"] = proba, best
    return pd.DataFrame(results), probas, fitted, params


def plot_comparison(res, metric, title, name, higher_is_better):
    res = res.sort_values(metric, ascending=not higher_is_better)
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(res) + 1))
    best = res[metric].max() if higher_is_better else res[metric].min()
    colors = [ORANGE if v == best else BLUE for v in res[metric]]
    ax.barh(res["model"], res[metric], color=colors, height=0.65)
    for y, v in enumerate(res[metric]):
        ax.text(v, y, f" {v:.3f}", va="center", color=TEXT_2, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel(metric + (" (mai mare = mai bine)" if higher_is_better else " (mai mic = mai bine)"))
    ax.grid(axis="y", visible=False)
    save(fig, name)


def temporal_split(df, X, best_reg_name, best_clf_name, reg_fitted, clf_fitted):
    """Antrenare pe 2024, testare pe 2025-2026: simulează folosirea reală a modelului."""
    from sklearn.base import clone
    train = (df["release_year"] == 2024).values
    test = ~train
    rows = []
    reg = clone(reg_fitted[best_reg_name]).fit(X[train], df.loc[train, "positive_ratio"])
    rows.append({"sarcina": "regresie", "model": best_reg_name, "n_train": train.sum(), "n_test": test.sum(),
                 **reg_metrics(df.loc[test, "positive_ratio"], np.clip(reg.predict(X[test]), 0, 1))})
    mean_base = np.full(test.sum(), df.loc[train, "positive_ratio"].mean())
    rows.append({"sarcina": "regresie", "model": "Baseline (media 2024)", "n_train": train.sum(), "n_test": test.sum(),
                 **reg_metrics(df.loc[test, "positive_ratio"], mean_base)})
    clf = clone(clf_fitted[best_clf_name]).fit(X[train], df.loc[train, "is_successful"])
    rows.append({"sarcina": "clasificare", "model": best_clf_name, "n_train": train.sum(), "n_test": test.sum(),
                 **clf_metrics(df.loc[test, "is_successful"], clf.predict_proba(X[test])[:, 1])})
    return pd.DataFrame(rows)


def ablation(X_tr, X_te, df_tr, df_te, features, best_reg_name, best_clf_name, reg_fitted, clf_fitted):
    """Reantrenează cele mai bune modele (aceiași hiperparametri) fără feature-urile care pot fi
    modificate după lansare ca urmare a succesului (DLC, traduceri...). Dacă performanța scade
    mult, o parte din „predicție” era de fapt informație din viitor."""
    from sklearn.base import clone
    keep = [i for i, f in enumerate(features) if f not in POST_RELEASE_MUTABLE]
    rows = []
    for label, cols in [("toate feature-urile", list(range(len(features)))), ("fără feature-uri post-lansare", keep)]:
        reg = clone(reg_fitted[best_reg_name]).fit(X_tr[:, cols], df_tr["positive_ratio"])
        clf = clone(clf_fitted[best_clf_name]).fit(X_tr[:, cols], df_tr["is_successful"])
        rows.append({"set_feature": label, "n_features": len(cols),
                     **{f"reg_{k}": v for k, v in reg_metrics(df_te["positive_ratio"], np.clip(reg.predict(X_te[:, cols]), 0, 1)).items()},
                     **{f"clf_{k}": v for k, v in clf_metrics(df_te["is_successful"], clf.predict_proba(X_te[:, cols])[:, 1]).items()}})
    return pd.DataFrame(rows)


def main():
    set_style()
    df = load()
    features = feature_columns(df)
    X = df[features].fillna(0).astype(float).values
    print(f"{len(df)} jocuri, {len(features)} feature-uri")

    idx_tr, idx_te = train_test_split(np.arange(len(df)), test_size=0.2, random_state=RANDOM_STATE,
                                      stratify=df["is_successful"])
    df_tr, df_te = df.iloc[idx_tr], df.iloc[idx_te]
    X_tr, X_te = X[idx_tr], X[idx_te]

    # ---------- Regresie ----------
    y_tr, y_te = df_tr["positive_ratio"].values, df_te["positive_ratio"].values
    reg_res, reg_preds, reg_fitted, reg_params = run_regression(X_tr, X_te, y_tr, y_te, df_tr, df_te)
    reg_res.to_csv(RES_DIR / "regression_results.csv", index=False)
    plot_comparison(reg_res, "MAE", "Regresie: eroarea absolută medie pe setul de test", "model_01_regression_mae", False)
    plot_comparison(reg_res, "R2", "Regresie: R² pe setul de test", "model_02_regression_r2", True)
    best_reg = reg_res[reg_res["model"].isin(reg_fitted)].sort_values("MAE").iloc[0]["model"]

    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter(y_te, reg_preds[best_reg], s=10, alpha=0.4, color=BLUE, edgecolors="none")
    ax.plot([0, 1], [0, 1], color=ORANGE, lw=1.5, ls="--")
    ax.set_xlabel("positive_ratio real")
    ax.set_ylabel("positive_ratio prezis")
    ax.set_title(f"{best_reg}: real vs. prezis")
    save(fig, "model_03_regression_scatter")

    # ---------- Clasificare ----------
    c_tr, c_te = df_tr["is_successful"].values, df_te["is_successful"].values
    clf_res, clf_probas, clf_fitted, clf_params = run_classification(X_tr, X_te, c_tr, c_te, df_tr, df_te)
    clf_res.to_csv(RES_DIR / "classification_results.csv", index=False)
    plot_comparison(clf_res, "ROC_AUC", "Clasificare: ROC-AUC pe setul de test", "model_04_classification_auc", True)
    plot_comparison(clf_res, "F1_macro", "Clasificare: F1 macro pe setul de test", "model_05_classification_f1", True)
    best_clf = clf_res[clf_res["model"].isin(clf_fitted)].sort_values("ROC_AUC", ascending=False).iloc[0]["model"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    # cel mai bun model (portocaliu) + încă două de referință, fără duplicate
    others = [m for m in ("Logistic Regression", "Random Forest", "XGBoost") if m != best_clf][:2]
    for name, color in zip([best_clf, *others], [ORANGE, BLUE, "#1baf7a"]):
        fpr, tpr, _ = roc_curve(c_te, clf_probas[name])
        axes[0].plot(fpr, tpr, lw=2, color=color, label=f"{name} (AUC {roc_auc_score(c_te, clf_probas[name]):.3f})")
    axes[0].plot([0, 1], [0, 1], color="#c9c8c3", lw=1, ls="--")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].set_title("Curbe ROC")
    axes[0].legend(frameon=False, fontsize=9)
    ConfusionMatrixDisplay.from_predictions(c_te, (clf_probas[best_clf] >= 0.5).astype(int), ax=axes[1],
                                            cmap="Blues", colorbar=False, display_labels=["nu", "succes"])
    axes[1].grid(False)
    axes[1].set_title(f"Matricea de confuzie: {best_clf}")
    save(fig, "model_06_classification_roc_cm")

    # ---------- Split temporal ----------
    print("  split temporal 2024 -> 2025-2026")
    temporal = temporal_split(df, X, best_reg, best_clf, reg_fitted, clf_fitted)
    temporal.to_csv(RES_DIR / "temporal_split_results.csv", index=False)

    print("  ablație fără feature-uri post-lansare")
    abl = ablation(X_tr, X_te, df_tr, df_te, features, best_reg, best_clf, reg_fitted, clf_fitted)
    abl.to_csv(RES_DIR / "ablation_results.csv", index=False)

    # ---------- Salvare pentru analiza erorilor ----------
    joblib.dump({"model": reg_fitted[best_reg], "name": best_reg, "features": features}, RES_DIR / "best_regressor.joblib")
    joblib.dump({"model": clf_fitted[best_clf], "name": best_clf, "features": features}, RES_DIR / "best_classifier.joblib")
    preds = df_te[["appid", "name", "genres", "tags", "price_eur", "total_reviews", "release_year",
                   "positive_ratio", "is_successful"]].copy()
    preds["pred_ratio"] = reg_preds[best_reg]
    preds["pred_success_proba"] = clf_probas[best_clf]
    preds.to_csv(RES_DIR / "test_predictions.csv", index=False)
    (RES_DIR / "best_params.json").write_text(json.dumps(
        {"regression": reg_params, "classification": clf_params}, indent=2, default=str), encoding="utf-8")

    summary = [
        "# Rezultatele modelelor", "",
        f"- jocuri: {len(df)} (train {len(df_tr)} / test {len(df_te)}), feature-uri: {len(features)}",
        f"- clasa pozitivă `is_successful` în test: {c_te.mean():.1%}", "",
        "## Regresie (`positive_ratio`)", "", reg_res.sort_values("MAE").to_markdown(index=False, floatfmt=".4f"), "",
        f"Cel mai bun model (MAE): **{best_reg}**", "",
        "## Clasificare (`is_successful`)", "", clf_res.sort_values("ROC_AUC", ascending=False).to_markdown(index=False, floatfmt=".4f"), "",
        f"Cel mai bun model (ROC-AUC): **{best_clf}**", "",
        "## Split temporal (train 2024 → test 2025–2026)", "", temporal.to_markdown(index=False, floatfmt=".4f"), "",
        f"## Ablație: fără {', '.join(POST_RELEASE_MUTABLE)}", "", abl.to_markdown(index=False, floatfmt=".4f"), "",
    ]
    (RES_DIR / "models_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
