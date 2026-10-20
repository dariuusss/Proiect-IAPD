# Rezultatele modelelor

- jocuri: 284 (train 227 / test 57), feature-uri: 107
- clasa pozitivă `is_successful` în test: 59.6%

## Regresie (`positive_ratio`)

| model                    |    MAE |   RMSE |      R2 |   CV_MAE |   CV_MAE_std |
|:-------------------------|-------:|-------:|--------:|---------:|-------------:|
| Ridge                    | 0.1245 | 0.1662 |  0.0761 |   0.0978 |       0.0057 |
| Ridge (tabular + text)   | 0.1246 | 0.1658 |  0.0799 |   0.0981 |       0.0049 |
| Random Forest            | 0.1250 | 0.1651 |  0.0874 |   0.0988 |       0.0041 |
| XGBoost                  | 0.1268 | 0.1646 |  0.0937 |   0.1007 |       0.0027 |
| LightGBM                 | 0.1284 | 0.1692 |  0.0423 |   0.1038 |       0.0052 |
| Ridge (doar text TF-IDF) | 0.1358 | 0.1738 | -0.0106 |   0.1121 |       0.0085 |
| Baseline (media)         | 0.1358 | 0.1738 | -0.0108 |   0.1121 |       0.0085 |

Cel mai bun model (MAE): **Ridge**

## Clasificare (`is_successful`)

| model                       |   F1_macro |   ROC_AUC |   Balanced_acc |   CV_AUC |   CV_AUC_std |
|:----------------------------|-----------:|----------:|---------------:|---------:|-------------:|
| Random Forest               |     0.6818 |    0.7008 |         0.6931 |   0.7143 |       0.0570 |
| XGBoost                     |     0.6298 |    0.6893 |         0.6419 |   0.6874 |       0.0829 |
| Logistic Regression         |     0.6464 |    0.6573 |         0.6566 |   0.7211 |       0.0599 |
| Logistic (tabular + text)   |     0.6464 |    0.6560 |         0.6566 |   0.7171 |       0.0612 |
| LightGBM                    |     0.6081 |    0.6164 |         0.6132 |   0.6804 |       0.0985 |
| Baseline (clasa majoritară) |     0.3736 |    0.5000 |         0.5000 |   0.5000 |       0.0000 |

Cel mai bun model (ROC-AUC): **Random Forest**

## Split temporal (train 2024 → test 2025–2026)

| sarcina     | model                 |   n_train |   n_test |      MAE |     RMSE |       R2 |   F1_macro |   ROC_AUC |   Balanced_acc |
|:------------|:----------------------|----------:|---------:|---------:|---------:|---------:|-----------:|----------:|---------------:|
| regresie    | Ridge                 |       105 |      179 |   0.1219 |   0.1549 |   0.0478 |   nan      |  nan      |       nan      |
| regresie    | Baseline (media 2024) |       105 |      179 |   0.1270 |   0.1602 |  -0.0185 |   nan      |  nan      |       nan      |
| clasificare | Random Forest         |       105 |      179 | nan      | nan      | nan      |     0.5993 |    0.7155 |         0.6225 |

## Ablație: fără n_dlc, n_languages, has_full_audio_en, n_achievements, is_early_access

| set_feature                   |   n_features |   reg_MAE |   reg_RMSE |   reg_R2 |   clf_F1_macro |   clf_ROC_AUC |   clf_Balanced_acc |
|:------------------------------|-------------:|----------:|-----------:|---------:|---------------:|--------------:|-------------------:|
| toate feature-urile           |          107 |    0.1245 |     0.1662 |   0.0761 |         0.6818 |        0.7008 |             0.6931 |
| fără feature-uri post-lansare |          102 |    0.1248 |     0.1663 |   0.0749 |         0.6663 |        0.7072 |             0.6854 |
