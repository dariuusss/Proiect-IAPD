# Cum a fost realizat proiectul, pas cu pas

Acest document explică **tot ce s-a făcut** în proiect, în ordine, și **de ce** s-a făcut așa.
Pornește de la fișa de proiect (`docs/fisa_proiect_steam.md`) și de la cerințele cursului
(`instructiuni.md`). Numerele concrete (câte jocuri, ce scoruri) sunt cele obținute la rularea
din 20 octombrie 2026; dacă rulezi din nou scripturile, ele se vor schimba puțin.

> Întrebarea de cercetare: **se poate prezice receptarea unui joc Steam (procentul de recenzii
> pozitive) doar din informațiile de pe pagina lui de magazin?**

---

## 0. Organizarea repo-ului

```
IAPD/
├── extraction/               # Faza 1: colectare + preprocesare
│   ├── config.py             # toate setările (căi, fereastra de date, pauze, praguri)
│   ├── http_utils.py         # request-uri cu reîncercare + citire/scriere JSONL
│   ├── get_app_list.py       # pasul 1: lista jocurilor 2024-2026
│   ├── crawl_steam.py        # pasul 2: appdetails / reviews / SteamSpy / dezvoltatori
│   ├── crawl_review_timelines.py  # istoricul recenziilor (stabilitatea țintei)
│   └── preprocess.py         # pasul 3: JSONL brut -> CSV curat
├── data/
│   ├── raw/                  # fișierele brute de la API (NU sunt în repo, vezi raw/README.md)
│   └── final/steam_clean.csv # setul de date final, un rând per joc
├── analysis/                 # Faza 2: EDA + modele
│   ├── common.py             # încărcare date, lista de feature-uri, stilul graficelor
│   ├── review_stability.py   # după câte zile se stabilizează scorul
│   ├── eda.py                # analiza exploratorie
│   ├── models.py             # antrenarea și compararea modelelor
│   ├── error_analysis.py     # unde și de ce greșește cel mai bun model
│   ├── figures/              # toate graficele (PNG), gata de pus în prezentări
│   └── results/              # tabele de rezultate (.md, .csv)
├── docs/                     # fișa, acest document, prezentările și raportul
├── requirements.txt
└── README.md
```

Structura urmează exact ce cere `instructiuni.md`: `/extraction` pentru crawling și preprocesare,
`/analysis` pentru modele, `/data` pentru seturile de date, `/docs` pentru documente.

Am ales **scripturi `.py`** în loc de notebook-uri: rulează cap-coadă dintr-o singură comandă,
rezultatele sunt reproductibile și diff-urile din Git se citesc ușor. Graficele și tabelele sunt
salvate în fișiere, deci se pot pune direct în prezentări și în raport.

### Cum se rulează totul

```bash
pip install -r requirements.txt

# Faza 1 - colectare (poate dura câteva ore; orice pas poate fi oprit și reluat)
python extraction/get_app_list.py
python extraction/crawl_steam.py --stage details     # aceste trei pot rula în paralel,
python extraction/crawl_steam.py --stage reviews     # în terminale separate
python extraction/crawl_steam.py --stage steamspy
python extraction/crawl_steam.py --stage developers  # după details
python extraction/crawl_review_timelines.py
python extraction/preprocess.py

# Faza 2 - analiză
python analysis/review_stability.py
python analysis/eda.py
python analysis/models.py
python analysis/error_analysis.py
```

---

## 1. Pasul 1: lista jocurilor (`extraction/get_app_list.py`)

### Problema
Fișa propunea: descărcăm lista tuturor aplicațiilor Steam (~200.000), apoi cerem `appdetails`
pentru fiecare ca să aflăm tipul și data lansării. La limita Store API (~200 request-uri / 5 min,
deci ~1,5 s per request) asta ar fi durat **peste 3 zile** doar ca să găsim jocurile din 2024–2026.

### Soluția
Am folosit **căutarea din magazinul Steam** (`store.steampowered.com/search/results/`), cu:
- `category1=998`: doar jocuri (fără DLC, soundtrack-uri, software);
- `sort_by=Released_DESC`: cele mai noi primele;
- `count=100`, `infinite=1`: 100 de jocuri per request, răspuns JSON cu HTML-ul rezultatelor.

Din fiecare rând HTML extragem cu expresii regulate: `appid`, numele, data lansării, sumarul
recenziilor (ex. „85% of the 1,234 user reviews…”) și ID-urile tag-urilor principale.
Paginăm până când trecem de 1 ianuarie 2024 (ne oprim după 500 de jocuri la rând mai vechi,
pentru că ordinea căutării nu e perfect strictă).

**Rezultat:** 56.949 de rânduri în `data/raw/search_index.jsonl`, dintre care **56.431 de jocuri
lansate între 1 ian. 2024 și 20 oct. 2026**, în aproximativ 1 oră (~570 de request-uri, cu pauze
automate când serverul a răspuns HTTP 429 „prea multe request-uri”).

Tot aici descărcăm și `data/raw/tag_names.json` (maparea `tagid → nume`, ex. `492 → Indie`),
pentru că rezultatele căutării conțin doar ID-urile tag-urilor.

### Detalii de robustețe (valabile pentru toate scripturile)
- **`http_utils.get_json`**: pauză fixă după fiecare request; la 429/403/5xx/timeout reîncearcă
  cu pauză exponențială (10 s, 20 s, 40 s… max 5 min).
- **Salvare incrementală în JSONL** (un obiect JSON per linie, adăugat imediat): dacă scriptul
  e oprit (Ctrl+C, laptop închis), nimic din ce s-a descărcat nu se pierde.
- **Reluare**: la repornire, scripturile citesc ce e deja în fișier și continuă de acolo
  (`search_state.json` pentru căutare, ID-urile deja salvate pentru celelalte etape). Asta chiar
  s-a întâmplat în timpul proiectului: crawl-ul s-a oprit la iulie 2024 și a fost reluat fără pierderi.

---

## 2. Pasul 2: detaliile fiecărui joc (`extraction/crawl_steam.py`)

### Ce jocuri intră în coadă
Din `search_index.jsonl` păstrăm jocurile cu:
- data lansării între `RELEASE_START` (2024-01-01) și `RELEASE_END` (vezi secțiunea 3: pragul
  a fost ales empiric, din cât de repede se stabilizează scorul);
- **cel puțin 20 de recenzii** în sumarul căutării (`MIN_REVIEWS_CRAWL`). Un scor calculat din
  3–4 recenzii e mai mult zgomot decât semnal, așa că nu are rost să cheltuim request-uri pe ele.

Rămân ~18.000 de candidați. **Ordinea lor e amestecată aleator cu o sămânță fixă (42).**
Lista vine sortată de la cel mai nou joc la cel mai vechi; dacă am fi descărcat în ordinea asta
și ne-am fi oprit la 5.000 de jocuri, am fi avut doar jocuri din 2026. Amestecate, *orice
prefix al cozii este un eșantion aleator* din toată perioada, deci ne putem opri oricând.
Amestecul se face înainte de filtrul `RELEASE_END`, ca să nu se schimbe ordinea dacă pragul se modifică.

### Trei etape independente
| Etapă | Endpoint | Ce păstrăm | Fișier |
|---|---|---|---|
| `details` | `api/appdetails?appids=ID&cc=ro` | toate metadatele (fără imagini și cerințe de sistem); doar *numărul* de screenshot-uri și trailere | `appdetails.jsonl` |
| `reviews` | `appreviews/ID?json=1&language=all&purchase_type=all&num_per_page=0` | `query_summary`: total pozitive/negative = **ținta** | `reviews.jsonl` |
| `steamspy` | `steamspy.com/api.php?request=appdetails` | tag-urile cu voturi, dezvoltator | `steamspy.jsonl` |

Etapele lovesc servere/limite diferite, așa că rulează **în paralel**, în procese separate.
`cc=ro` face ca prețurile să fie în EUR. Fiecare rând are `fetched_at` (momentul descărcării).

### O problemă găsită pe parcurs: SteamSpy nu are tag-uri pentru jocurile noi
La testul pe 12 jocuri, **niciunul** nu avea tag-uri în SteamSpy (este un serviciu care
estimează datele cu întârziere și acoperă slab jocurile mici/recente). Fișa anticipase riscul.
Soluția: tag-urile din **Store**, deja prezente în `search_index.jsonl` (cele ~7 tag-uri afișate
pe pagina jocului), traduse în nume cu `tag_names.json`. Sunt și mai potrivite pentru întrebarea
noastră, pentru că sunt exact ce vede cumpărătorul. SteamSpy a rămas în pipeline doar ca
indicator de acoperire (`n_steamspy_tags`).

Consecință: `n_tags` (din fișă) nu mai e feature, pentru că Store-ul afișează aproape mereu
exact 7 tag-uri (constantă = inutilă). În plus, la SteamSpy numărul de tag-uri crește cu
popularitatea jocului, deci ar fi fost o scurgere indirectă de informație despre țintă.

---

### Etapa `developers`: istoricul real al dezvoltatorului
Fișa propunea `developer_n_games` calculat *în setul nostru*. Pe primele 284 de jocuri aproape
toți dezvoltatorii apăreau o singură dată (valoare ~constantă = 1), pentru că eșantionăm doar
o parte din jocurile 2024–2026 și nu vedem deloc jocurile lor mai vechi.

Soluția: căutarea Store acceptă filtrul `developer=<nume>` și întoarce **toate** jocurile
dezvoltatorului (inclusiv cele din 2011, 2017…), cu data lansării și scorul afișat.
Etapa `--stage developers` face un request per dezvoltator unic și salvează
`data/raw/developers.jsonl`. Din el calculăm (secțiunea 4) doar ce se știa **înainte** de
lansarea jocului curent.

---

## 3. Cât timp trebuie să treacă de la lansare? (stabilitatea țintei)

### Întrebarea
Ținta este scorul de *azi*. Un joc lansat acum 3 săptămâni are puține recenzii, iar scorul lui
se mai poate schimba mult. Dacă îl includem, ținta are zgomot pe care niciun model nu-l poate
învăța. Prima variantă a pipeline-ului excludea ultimele 60 de zile, dar valoarea era aleasă
„din burtă”. Am vrut să o verificăm pe date.

### Metoda (`extraction/crawl_review_timelines.py` + `analysis/review_stability.py`)
1. Eșantion aleator de jocuri lansate între ian. 2024 și sept. 2025 (deci cu **cel puțin un an**
   de istoric), cu 20–3000 de recenzii.
2. Pentru fiecare, descărcăm **toate recenziile**, paginat (100 per pagină, cu cursor), dar păstrăm
   doar `(data, pozitivă/negativă)`, fără text și fără autor.
3. Reconstruim scorul pe care l-ar fi avut jocul la 7, 14, 30, 60, 90, 120, 180, 365 de zile
   după lansare și îl comparăm cu scorul de azi.

### Rezultat (103 jocuri; eșantionul complet de 200 se poate termina oricând, scriptul e reluabil)

| zile de la lansare | diferența mediană față de scorul final | jocuri încă la > 5 pp distanță | ce parte din recenzii existau |
|---:|---:|---:|---:|
| 7 | 4,2 pp | 39% | 25% |
| 30 | 2,8 pp | 37% | 42% |
| 60 | 2,9 pp | **33%** | 49% |
| 90 | 2,6 pp | 27% | 55% |
| **120** | 2,4 pp | **21%** | 59% |
| 180 | 2,3 pp | 22% | 68% |
| 365 | 1,4 pp | 10% | 82% |

Grafic: `analysis/figures/eda_00_review_stability.png`.

**Decizie: `MIN_AGE_DAYS = 120`.** Între 60 și 120 de zile proporția jocurilor „încă instabile”
scade de la 33% la 21%, iar apoi rămâne pe loc până la 180 de zile. Deci 120 e „cotul” curbei.
A aștepta un an ar mai câștiga ceva, dar am pierde aproape tot 2026.

Implementare: pragul se aplică pe **vârsta jocului în momentul în care i-am descărcat
recenziile** (`game_age_days`, calculat din `fetched_at`), nu pe o dată fixă. Astfel regula
rămâne corectă și dacă datele se colectează în mai multe sesiuni, la distanță de săptămâni.
`game_age_days` este doar o coloană de control, **nu e feature** (nu e informație de pe
pagina de magazin).

Observație onestă: chiar și după un an, 10% din jocuri se mai mișcă peste 5 pp, deci o parte
din eroarea modelelor e zgomot inevitabil al țintei.

---

## 4. Pasul 3: preprocesarea (`extraction/preprocess.py`)

Unește cele 5 surse după `appid` și produce `data/final/steam_clean.csv`, un rând per joc.

**Filtre** (în ordine): `type == "game"`, are sumar de recenzii, lansat după 2024-01-01,
`game_age_days ≥ 120`, `total_reviews ≥ 20`.

**Ținte**
- `positive_ratio = total_positive / total_reviews` (regresie);
- `is_successful = positive_ratio ≥ 0.80` (clasificare). 0,80 este pragul Steam pentru
  „Very Positive”. **Abatere de la fișă:** fișa cerea în plus `total_reviews ≥ 50`. Atunci un joc
  foarte bine primit, dar cu 30 de recenzii, ar fi fost etichetat „eșec”, iar clasificatorul ar fi
  învățat parțial *popularitatea*, care e altă întrebare. Pragul minim de recenzii se aplică
  deja la nivel de set (≥ 20).

**Feature-uri** (toate de pe pagina de magazin sau derivate din ea):

| Grup | Feature-uri | Note |
|---|---|---|
| Preț | `price_eur`, `is_free` | prețul **de listă** (`initial`), nu cel redus temporar |
| Dată | `release_year`, `release_month`, `release_dayofweek` | |
| Conținut | `n_genres`, `n_categories`, `n_achievements`, `n_dlc`, `required_age`, `n_content_descriptors`, `controller_support` | |
| Platforme / limbi | `has_mac`, `has_linux`, `n_languages`, `has_full_audio_en` | limbile se extrag din HTML-ul `supported_languages`; `*` marchează audio complet |
| Pagina | `n_screenshots`, `n_movies`, `description_length`, `short_description_length`, `has_website` | lungimile în cuvinte, după eliminarea HTML |
| Publicare | `is_early_access`, `is_self_published` | self-published = dezvoltator == publisher |
| **Istoric dezvoltator** | `dev_prior_games`, `dev_prior_rated_games`, `dev_has_track_record`, `dev_prior_mean_score` | doar jocurile lansate **înainte** de jocul curent |
| One-hot | `genre_*` (genuri cu ≥ 1%), `cat_*` (categorii cu ≥ 5%), `tag_*` (top 40 tag-uri Store) | |

`dev_prior_mean_score` lipsește când dezvoltatorul nu are jocuri anterioare cu scor. Atunci se
completează cu media coloanei, iar `dev_has_track_record = 0` îi spune modelului că valoarea e
„inventată”.

**Excluse intenționat (data leakage):** numărul de recenzii, proprietari, timp de joc, Metacritic,
`recommendations`, numărul de tag-uri SteamSpy. Toate apar *după* lansare sau sunt chiar
receptarea pe care vrem s-o prezicem. `analysis/common.py` are o listă `LEAKY` și un `assert`
care oprește programul dacă vreuna dintre ele ajunge din greșeală între feature-uri. Coloanele
constante (ex. `has_windows`, 1 peste tot) sunt eliminate automat.

---

## 5. Verificări de „gândire” făcute pe eșantionul de test (284 de jocuri)

Înainte de colectarea completă, am rulat **tot pipeline-ul pe ~300 de jocuri**, ca să vedem dacă
raționamentul e corect. Am găsit și corectat următoarele:

| # | Problema găsită | Ce am făcut |
|---|---|---|
| 1 | Lista vine sortată de la nou la vechi, deci o oprire timpurie ar fi dat doar jocuri recente | coadă amestecată aleator (secțiunea 2) |
| 2 | 60 de zile de la lansare nu ajung ca scorul să se stabilizeze | analiză empirică → 120 de zile (secțiunea 3) |
| 3 | SteamSpy nu are tag-uri pentru jocurile noi | tag-uri din Store (secțiunea 2) |
| 4 | `developer_n_games` calculat în set ≈ constant | istoric real din căutarea Store (secțiunea 2) |
| 5 | `is_successful` amesteca receptarea cu popularitatea | prag doar pe `positive_ratio` (secțiunea 4) |
| 6 | **F1 pe clasa pozitivă** dădea scorul cel mai mare baseline-ului care spune „succes” pentru toți (0,747), pentru că succesul e clasa majoritară | raportăm **F1 macro** și **balanced accuracy**; baseline-ul are acum 0,37 F1 macro |
| 7 | Cu doar 57 de jocuri în test, diferențele dintre modele pot fi zgomot | raportăm și scorul de **cross-validation (medie ± std)** pe train |
| 8 | Unele feature-uri se văd cum sunt *azi*, nu la lansare: un joc reușit primește DLC-uri, traduceri, achievement-uri, iese din Early Access | experiment de **ablație** fără ele (`POST_RELEASE_MUTABLE` în `common.py`) |

---

## 6. EDA (`analysis/eda.py`)

Produce `analysis/results/eda_summary.md` și graficele `analysis/figures/eda_01…08`:
pragul de recenzii, distribuția țintei, lansările pe lună, prețul, genurile, tag-urile,
corelațiile Spearman, ipotezele (publisher, media, Early Access, experiența dezvoltatorului).

Ce se vede deja pe eșantionul mic (de reconfirmat pe setul complet):
- ținta e asimetrică: mediana 0,83, coada lungă spre scoruri mici;
- **scorul jocurilor anterioare ale dezvoltatorului are corelație Spearman 0,60** cu scorul
  jocului nou (pe cele 122 de jocuri cu istoric). Restul feature-urilor au |ρ| < 0,18;
- jocurile gratuite și cele în Early Access sunt mai slab primite (median 0,79 / 0,78 vs. 0,84).

---

## 7. Modele (`analysis/models.py`)

- Split **80/20 stratificat** după `is_successful`, același pentru ambele sarcini.
- Hiperparametri aleși cu **`RandomizedSearchCV`, 5-fold, 20 de combinații**, doar pe train.
- Regresie: baseline (media), Ridge, Random Forest, XGBoost, LightGBM, Ridge pe TF-IDF
  (descrierea scurtă) și Ridge pe tabular + TF-IDF. Metrici: MAE, RMSE, R², CV-MAE.
- Clasificare: baseline (clasa majoritară), Logistic Regression, Random Forest, XGBoost, LightGBM
  (cu `class_weight` / `scale_pos_weight`), Logistic pe tabular + TF-IDF.
  Metrici: ROC-AUC, F1 macro, balanced accuracy, CV-AUC.
- **Split temporal:** antrenare pe 2024, test pe 2025–2026, ca la folosirea reală a modelului.
- **Ablație:** cel mai bun model fără feature-urile modificabile după lansare.

Rezultatele pe eșantionul de 284 de jocuri (`analysis/results/models_summary.md`) **nu sunt
rezultatele finale**, doar o verificare că totul funcționează:
- regresie: Ridge MAE 0,124 față de 0,136 baseline (R² ≈ 0,08);
- clasificare: ROC-AUC ~0,70 față de 0,50 baseline;
- deviația standard CV (0,06–0,10 AUC) arată că diferențele dintre modele nu sunt încă
  semnificative, deci avem nevoie de setul complet;
- ablația schimbă foarte puțin rezultatele, așa că feature-urile „post-lansare” nu par să
  umfle artificial performanța.

---

## 8. Analiza erorilor (`analysis/error_analysis.py`)

Pe cel mai bun model de regresie: eroarea pe intervale de preț, de recenzii, de țintă și pe
genuri; importanța feature-urilor cu **SHAP**; cele mai mari supra- și subestimări
(`analysis/results/error_analysis.md`, `analysis/figures/err_*`).

Tipare deja vizibile:
- **regresie spre medie**: jocurile slabe (< 50%) sunt supraestimate cu ~42 pp, iar cele foarte
  bune subestimate. Modelul „nu îndrăznește” să prezică extreme;
- eroarea scade mult cu numărul de recenzii (0,16 la 20–50 recenzii → 0,07 la peste 500).
  Asta confirmă că la jocurile cu puține recenzii ținta e zgomotoasă.

---

## 9. Pașii următori

1. **Colectarea completă** (rulează singură, se poate opri/relua oricând):
   ```bash
   python extraction/crawl_steam.py --stage details    # ~35 jocuri/min
   python extraction/crawl_steam.py --stage reviews
   python extraction/crawl_steam.py --stage steamspy
   # după details:
   python extraction/crawl_steam.py --stage developers
   python extraction/crawl_review_timelines.py --n 200  # termină eșantionul de stabilitate
   ```
   ~18.000 de candidați în total; 5.000–6.000 de jocuri ar dura ~3 ore.
2. Rerulare `preprocess.py` → `eda.py` → `review_stability.py` → `models.py` → `error_analysis.py`.
3. Idei de îmbunătățire după ce vedem rezultatele pe setul complet:
   - ponderarea jocurilor după numărul de recenzii (ținta e mai sigură la jocurile populare);
   - evaluare separată pe jocurile cu ≥ 100 de recenzii;
   - feature-uri din istoricul publisher-ului, similar cu cel al dezvoltatorului.
4. Prezentarea Faza 1 (`docs/`), cu graficele din `analysis/figures/`.
