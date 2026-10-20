# Rezumat EDA

- jocuri în `steam_clean.csv`: **284** (≥ 20 recenzii la colectare)
- jocuri folosite pentru modelare (≥ 20 recenzii): **284**
- feature-uri candidate: **110** (29 numerice/binare + 81 one-hot)
- interval lansări: 2024-01-08 → 2026-06-19
- jocuri cu tag-uri în SteamSpy: 41.2% (de aceea folosim tag-urile din Store)

## Valori lipsă (proporție)
|    | lipsa   |
|---:|:--------|
|  0 | niciuna |

## Statistici descriptive (feature-uri numerice)
|                          |    mean |    std |     min |     50% |     max |
|:-------------------------|--------:|-------:|--------:|--------:|--------:|
| price_eur                |    9.75 |  10.53 |    0.00 |    7.79 |   59.99 |
| is_free                  |    0.22 |   0.41 |    0.00 |    0.00 |    1.00 |
| has_price_info           |    1.00 |   0.00 |    1.00 |    1.00 |    1.00 |
| required_age             |    0.06 |   1.07 |    0.00 |    0.00 |   18.00 |
| release_year             | 2024.85 |   0.75 | 2024.00 | 2025.00 | 2026.00 |
| release_month            |    5.84 |   3.46 |    1.00 |    5.00 |   12.00 |
| release_dayofweek        |    2.39 |   1.67 |    0.00 |    2.00 |    6.00 |
| n_genres                 |    3.22 |   1.40 |    1.00 |    3.00 |    9.00 |
| n_categories             |    7.40 |   4.84 |    2.00 |    7.00 |   27.00 |
| has_windows              |    1.00 |   0.00 |    1.00 |    1.00 |    1.00 |
| has_mac                  |    0.20 |   0.40 |    0.00 |    0.00 |    1.00 |
| has_linux                |    0.14 |   0.35 |    0.00 |    0.00 |    1.00 |
| n_languages              |    9.00 |  16.34 |    1.00 |    5.00 |  103.00 |
| has_full_audio_en        |    0.39 |   0.49 |    0.00 |    0.00 |    1.00 |
| n_achievements           |   23.45 |  36.55 |    0.00 |   14.00 |  375.00 |
| n_dlc                    |    0.74 |   3.10 |    0.00 |    0.00 |   45.00 |
| n_screenshots            |    9.62 |   5.44 |    5.00 |    8.00 |   41.00 |
| n_movies                 |    1.72 |   1.21 |    0.00 |    1.00 |   10.00 |
| description_length       |  286.22 | 220.43 |    8.00 |  229.00 | 1713.00 |
| short_description_length |   33.67 |  12.76 |    1.00 |   36.50 |   55.00 |
| has_website              |    0.48 |   0.50 |    0.00 |    0.00 |    1.00 |
| controller_support       |    0.31 |   0.46 |    0.00 |    0.00 |    1.00 |
| n_content_descriptors    |    0.39 |   0.76 |    0.00 |    0.00 |    3.00 |
| is_early_access          |    0.13 |   0.34 |    0.00 |    0.00 |    1.00 |
| is_self_published        |    0.67 |   0.47 |    0.00 |    1.00 |    1.00 |
| dev_prior_games          |    3.61 |  15.89 |    0.00 |    0.00 |  174.00 |
| dev_prior_rated_games    |    2.85 |  11.38 |    0.00 |    0.00 |  139.00 |
| dev_has_track_record     |    0.43 |   0.50 |    0.00 |    0.00 |    1.00 |
| dev_prior_mean_score     |    0.78 |   0.11 |    0.17 |    0.78 |    1.00 |

## Alegerea pragului minim de recenzii
Cu cât pragul e mai mare, ținta e mai stabilă (mai puțin zgomot), dar pierdem jocuri.
|   prag |   n_jocuri |   media_positive_ratio |   std_positive_ratio |
|-------:|-----------:|-----------------------:|---------------------:|
|     20 |    284.000 |                  0.809 |                0.152 |
|     30 |    251.000 |                  0.810 |                0.153 |
|     50 |    198.000 |                  0.816 |                0.145 |
|    100 |    139.000 |                  0.810 |                0.139 |
|    200 |     92.000 |                  0.797 |                0.151 |
|    500 |     55.000 |                  0.814 |                0.123 |
|   1000 |     33.000 |                  0.824 |                0.107 |

## Ținta
|                |   count |     mean |       std |    min |    25% |    50% |     75% |        max |
|:---------------|--------:|---------:|----------:|-------:|-------:|-------:|--------:|-----------:|
| positive_ratio | 284.000 |    0.809 |     0.152 |  0.253 |  0.731 |  0.834 |   0.923 |      1.000 |
| total_reviews  | 284.000 | 2156.049 | 25493.194 | 20.000 | 43.750 | 96.500 | 344.500 | 428201.000 |

Clasificare `is_successful` (ratio ≥ 0.80, pragul Steam „Very Positive”): **59.9%** pozitive, 40.1% negative.

## Prețul
- jocuri gratuite: **21.8%**
- preț median (doar jocurile cu plată): **9.75 €**

| price_bucket   |   count |   mean |   median |
|:---------------|--------:|-------:|---------:|
| gratuit        |  62.000 |  0.766 |    0.793 |
| ≤5€            |  61.000 |  0.858 |    0.885 |
| 5-10€          |  63.000 |  0.823 |    0.833 |
| 10-20€         |  74.000 |  0.805 |    0.829 |
| 20-30€         |  14.000 |  0.729 |    0.745 |
| >30€           |  10.000 |  0.826 |    0.871 |

## Receptarea pe genuri
| genres                |   count |   mean |   median |
|:----------------------|--------:|-------:|---------:|
| Massively Multiplayer |  20.000 |  0.648 |    0.706 |
| Early Access          |  38.000 |  0.762 |    0.779 |
| Strategy              |  65.000 |  0.785 |    0.786 |
| Free To Play          |  63.000 |  0.763 |    0.786 |
| Racing                |   9.000 |  0.786 |    0.792 |
| Simulation            |  93.000 |  0.767 |    0.794 |
| Game Development      |   2.000 |  0.808 |    0.808 |
| Action                | 101.000 |  0.811 |    0.818 |
| RPG                   |  75.000 |  0.795 |    0.826 |
| Casual                | 116.000 |  0.828 |    0.854 |
| Indie                 | 195.000 |  0.830 |    0.867 |
| Adventure             | 114.000 |  0.837 |    0.871 |
| Sports                |  20.000 |  0.854 |    0.885 |
| Animation & Modeling  |   1.000 |  0.970 |    0.970 |
| Design & Illustration |   1.000 |  0.970 |    0.970 |

## Receptarea pe tag-uri
| tags         |   count |   mean |   median |
|:-------------|--------:|-------:|---------:|
| Roguelite    |  20.000 |  0.792 |    0.776 |
| Simulation   |  47.000 |  0.758 |    0.794 |
| Early Access |  27.000 |  0.766 |    0.794 |
| RPG          |  44.000 |  0.766 |    0.796 |
| Multiplayer  |  26.000 |  0.775 |    0.801 |
| Strategy     |  49.000 |  0.797 |    0.802 |
| 3D           |  33.000 |  0.779 |    0.812 |
| Action       |  57.000 |  0.812 |    0.827 |
| Exploration  |  39.000 |  0.809 |    0.831 |
| 2D           |  33.000 |  0.824 |    0.834 |
| Horror       |  30.000 |  0.796 |    0.835 |
| First-Person |  20.000 |  0.824 |    0.835 |
| Roguelike    |  22.000 |  0.835 |    0.854 |
| Singleplayer |  42.000 |  0.816 |    0.861 |
| Casual       |  62.000 |  0.841 |    0.872 |
| Adventure    |  53.000 |  0.849 |    0.885 |
| Puzzle       |  32.000 |  0.874 |    0.897 |
| Indie        |  28.000 |  0.863 |    0.905 |
| Cute         |  24.000 |  0.860 |    0.924 |
| Visual Novel |  28.000 |  0.870 |    0.935 |

## Corelații Spearman cu ținta (feature-uri numerice)
|                          |   spearman_rho |
|:-------------------------|---------------:|
| n_languages              |         -0.177 |
| description_length       |         -0.176 |
| has_full_audio_en        |         -0.149 |
| is_free                  |         -0.130 |
| has_website              |         -0.123 |
| short_description_length |         -0.104 |
| is_early_access          |         -0.098 |
| n_genres                 |         -0.070 |
| n_screenshots            |         -0.039 |
| required_age             |         -0.029 |
| price_eur                |         -0.016 |
| n_categories             |         -0.013 |
| dev_prior_rated_games    |         -0.011 |
| dev_has_track_record     |         -0.009 |
| dev_prior_games          |          0.006 |
| n_movies                 |          0.013 |
| n_content_descriptors    |          0.015 |
| n_dlc                    |          0.025 |
| release_month            |          0.029 |
| is_self_published        |          0.050 |
| n_achievements           |          0.055 |
| release_dayofweek        |          0.068 |
| release_year             |          0.101 |
| controller_support       |          0.132 |
| has_mac                  |          0.146 |
| has_linux                |          0.180 |
| dev_prior_mean_score     |          0.312 |

## Ipoteze specifice
**Self-published vs. cu publisher**
|                |   count |   mean |   median |
|:---------------|--------:|-------:|---------:|
| are publisher  |  95.000 |  0.798 |    0.834 |
| self-published | 189.000 |  0.814 |    0.833 |

**Conținut media (screenshot-uri + trailere)**
| media_bucket   |   count |   mean |   median |
|:---------------|--------:|-------:|---------:|
| 6-10           | 163.000 |  0.814 |    0.854 |
| 11-15          |  76.000 |  0.792 |    0.807 |
| 16-20          |  23.000 |  0.828 |    0.870 |
| >20            |  22.000 |  0.807 |    0.796 |

**Early Access**
|                  |   count |   mean |   median |
|:-----------------|--------:|-------:|---------:|
| lansare completă | 246.000 |  0.816 |    0.840 |
| early access     |  38.000 |  0.762 |    0.779 |

**Experiența dezvoltatorului (jocuri lansate anterior pe Steam)**
| dev_bucket   |   count |   mean |   median |
|:-------------|--------:|-------:|---------:|
| primul joc   | 153.000 |  0.800 |    0.849 |
| 1 anterior   |  62.000 |  0.825 |    0.825 |
| 2-3          |  28.000 |  0.834 |    0.861 |
| 4+           |  41.000 |  0.800 |    0.802 |

**Scorul jocurilor anterioare ale dezvoltatorului** (122 jocuri cu istoric): corelația Spearman cu scorul jocului nou = **0.602**
