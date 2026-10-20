# Fișă de proiect: Predicția receptării jocurilor video lansate pe Steam (2024–2026)

> Schelet de pornire. Câmpurile marcate cu `[TODO]` trebuie completate.

---

## 1. Echipa

| Nume | Grupă | Rol |
|---|---|---|
| [TODO] | [TODO] | Colectare date, modelare |
| [TODO, opțional] | [TODO] | EDA, raport |

---

## 2. Descriere pe scurt

Pe Steam apar zeci de mii de jocuri noi în fiecare an, iar receptarea lor variază enorm. Proiectul încearcă să afle **dacă receptarea unui joc (procentul de recenzii pozitive) poate fi prezisă doar din informațiile disponibile pe pagina de magazin**: preț, genuri, tag-uri, platforme, limbi, conținut media, istoricul dezvoltatorului.

**Ce aduce nou față de seturile existente (ex. Kaggle „Steam Store Games”):**
- set de date **colectat de la zero** prin API-urile publice, doar jocuri lansate în **2024–2026**, care lipsesc din seturile publice;
- feature-uri derivate proprii (istoricul dezvoltatorului, cât de bogată e pagina de magazin, lungimea descrierii);
- [TODO, opțional] o a doua țintă: dacă un joc aflat în Early Access ajunge la versiunea finală.

---

## 3. Întrebarea de cercetare și sarcina de predicție

**Întrebare principală:** Ce caracteristici vizibile pe pagina de magazin influențează receptarea unui joc și cât de bine o putem prezice?

| Variantă | Țintă | Tip |
|---|---|---|
| Principală | `positive_ratio` = recenzii pozitive / total recenzii | Regresie |
| Secundară | `is_successful` = `positive_ratio ≥ 0.80` și `total_reviews ≥ 50` | Clasificare binară |

Filtru: se păstrează doar jocurile cu **cel puțin 10–20 de recenzii**, ca ținta să fie stabilă. [TODO: pragul final se alege după EDA]

---

## 4. Surse de date

| Sursă | Endpoint | Ce furnizează |
|---|---|---|
| Steam App List | [IStoreService/GetAppList/v1](https://api.steampowered.com/IStoreService/GetAppList/v1/?key=<KEY>) (necesită [cheie Steam Web API](https://steamcommunity.com/dev/apikey)); alternativ fără cheie: [SteamSpy `request=all`](https://steamspy.com/api.php?request=all&page=0) (paginat, 1000 jocuri/pagină) | lista ID-urilor de aplicații |
| Steam Store API | [appdetails?appids=\<ID\>](https://store.steampowered.com/api/appdetails?appids=730) | metadatele jocului |
| Steam Reviews API | [appreviews/\<ID\>?json=1&language=all&purchase_type=all](https://store.steampowered.com/appreviews/730?json=1&language=all&purchase_type=all) | numărul de recenzii pozitive/negative (ținta) |
| SteamSpy API | [api.php?request=appdetails&appid=\<ID\>](https://steamspy.com/api.php?request=appdetails&appid=730) | tag-urile date de utilizatori |

*Linkurile folosesc ca exemplu jocul Counter-Strike 2 (`appid=730`); în cod, `<ID>` se înlocuiește cu ID-ul fiecărui joc.*

**Etica și limitele colectării:**
- pauză de 1–1,5 s între request-uri (limita Store API e de aproximativ 200 de request-uri la 5 minute);
- datele se salvează pe măsură ce sunt descărcate, ca scriptul să poată fi reluat după o întrerupere;
- se colectează doar date publice, fără date personale ale utilizatorilor.

---

## 5. Procesul de colectare (pipeline)

```
GetAppList ──► filtrare type == "game"
          ──► appdetails (metadate) ──► filtrare release_date ∈ [2024, 2026]
          ──► appreviews (țintă)
          ──► SteamSpy (tag-uri)
          ──► data/raw/*.jsonl ──► preprocess.py ──► data/final/steam_clean.csv
```

**Țintă de volum:** 3.000–5.000 de jocuri după filtrare (minimul cerut e 1.000).

---

## 6. Feature-uri planificate

| # | Feature | Tip | Sursă |
|---|---|---|---|
| 1 | `price_eur` | numeric | Store |
| 2 | `is_free` | binar | Store |
| 3 | `release_year`, `release_month`, `release_dayofweek` | numeric/categoric | Store |
| 4 | `genre_*` (one-hot) | binar | Store |
| 5 | `n_genres` | numeric | Store |
| 6 | `n_categories` (single/multiplayer, co-op etc.) | numeric | Store |
| 7 | `has_windows`, `has_mac`, `has_linux` | binar | Store |
| 8 | `n_languages`, `has_full_audio_en` | numeric/binar | Store |
| 9 | `required_age` | numeric | Store |
| 10 | `n_achievements` | numeric | Store |
| 11 | `n_dlc` | numeric | Store |
| 12 | `n_screenshots`, `n_movies` | numeric | Store |
| 13 | `description_length` | numeric | Store |
| 14 | `is_early_access` | binar | Store |
| 15 | `is_self_published` (dezvoltator == publisher) | binar | derivat |
| 16 | `developer_n_games` | numeric | derivat |
| 17 | `tag_*` (top N tag-uri, one-hot) | binar | SteamSpy |
| 18 | `n_tags` | numeric | SteamSpy |

**Excluse intenționat pentru a evita data leakage:** numărul de proprietari, timpul mediu de joc, numărul de recenzii (ca feature) și scorul Metacritic. Toate apar abia după lansare sau sunt rezultatul aceleiași receptări pe care vrem să o prezicem.

---

## 7. Analize planificate (EDA)

- distribuția țintei (`positive_ratio`) și dezechilibrul claselor pentru varianta binară;
- distribuția prețurilor, a genurilor și a numărului de lansări pe lună;
- corelații între feature-urile numerice și țintă;
- receptarea pe genuri și pe tag-uri (boxplot-uri);
- jocuri publicate de dezvoltator vs. de un publisher;
- efectul conținutului media (screenshot-uri, trailere) asupra receptării;
- [TODO] alte ipoteze după ce vezi datele.

---

## 8. Modele

| Model | Rol |
|---|---|
| Baseline naiv: media/mediana pentru regresie, clasa majoritară pentru clasificare | punct de referință minim |
| **Regresie liniară (Ridge) / Logistică** | baseline 1 |
| **Random Forest** | baseline 2 |
| XGBoost / LightGBM | model principal |
| [Opțional] TF-IDF pe descriere + model liniar | test: aduce textul informație în plus? |

**Validare:** split 80/20, stratificat la clasificare, plus 5-fold cross-validation pentru alegerea hiperparametrilor.
[Opțional] split temporal: antrenare pe 2024, testare pe 2025–2026.

**Metrici:**
- Regresie: MAE, RMSE, R²
- Clasificare: F1, ROC-AUC, matrice de confuzie

**Analiza erorilor:** pe ce genuri și intervale de preț greșește modelul cel mai mult; importanța feature-urilor (SHAP); exemple concrete de jocuri prezise greșit.

---

## 9. Plan de lucru

| Săptămâna | Activitate |
|---|---|
| 3 | Fișa de proiect trimisă, tema confirmată cu profesorul |
| 4–5 | Scripturile de colectare, rularea crawler-ului |
| 6 | Curățare și preprocesare, primele statistici descriptive |
| 7–9 | **Prezentarea Fazei 1** |
| 10–11 | EDA completă, modelele de baseline |
| 12 | Modelul principal, tuning, analiza erorilor |
| 13 | Raportul (max 10 pagini) |
| 14 | **Prezentarea finală** |

---

## 10. Structura repo-ului GitHub

```
/extraction
    get_app_list.py       # descarcă lista de ID-uri
    crawl_steam.py        # appdetails + appreviews + SteamSpy (cu reluare după întrerupere)
    preprocess.py         # JSON brut → CSV curat
/data
    raw/                  # .jsonl brute (sau link dacă sunt prea mari)
    final/steam_clean.csv
/analysis
    eda.ipynb
    models.ipynb
/docs
    faza1.pptx
    faza2.pptx
    raport.pdf
README.md
```

---

## 11. Riscuri și soluții

| Risc | Soluție |
|---|---|
| Rate limiting / blocare din partea Steam | pauze între request-uri, reluare automată, salvare pe parcurs |
| Multe jocuri au foarte puține recenzii | prag minim de recenzii, documentat în raport |
| Tema e considerată prea apropiată de Kaggle | perioada 2024–2026, feature-uri derivate proprii, confirmare la Faza 0 |
| SteamSpy indisponibil | tag-urile sunt opționale, modelul merge și doar cu datele din Store |
| Dezechilibru între clase | `class_weight`, metrici F1/AUC în loc de acuratețe |

---

## 12. Schelet pentru prezentarea din Faza 1 (5–7 min)

1. **Titlu + echipă**
2. **Ideea și motivația:** de ce contează receptarea unui joc; întrebarea de cercetare
3. **Surse de date:** cele 3 API-uri, ce aduce fiecare
4. **Colectarea:** diagrama pipeline-ului, limitele de request-uri, cât a durat
5. **Descrierea setului de date:** nr. de intrări, nr. de feature-uri, procentul de valori lipsă
6. **Primele statistici:** distribuția țintei, top genuri, distribuția prețurilor (2–3 grafice)
7. **Analize și modele planificate:** baseline-uri, metrici, ce vrem să aflăm
8. **Pașii următori și întrebări**

---

## 13. Bibliografie (de completat)

- [TODO] Lucrări despre predicția succesului jocurilor video / analiza recenziilor Steam
- [TODO] Documentația Steam Web API, documentația SteamSpy
- Breiman, L. (2001). *Random Forests*. Machine Learning, 45(1), 5–32.
- Chen, T., & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System*. KDD.
- Lundberg, S. M., & Lee, S.-I. (2017). *A Unified Approach to Interpreting Model Predictions* (SHAP). NeurIPS.
