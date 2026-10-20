# Stabilitatea scorului după lansare

Eșantion: 103 jocuri lansate între 2024-01 și 2025-09 (≥ 1 an de istoric).
Pentru fiecare vârstă se iau doar jocurile cu ≥ 10 recenzii la acea vârstă.

- `diferenta_mediana` / `diferenta_p90`: |scor la ziua d − scor actual| (0.05 = 5 puncte procentuale)
- `peste_5pp`: ce parte din jocuri au scorul la ziua d mai departe de 5 pp de cel actual
- `fractie_recenzii_mediana`: ce parte din recenziile de azi existau deja la ziua d

|   age_days |   jocuri |   diferenta_mediana |   diferenta_p90 |   peste_5pp |   fractie_recenzii_mediana |
|-----------:|---------:|--------------------:|----------------:|------------:|---------------------------:|
|          7 |   70.000 |               0.042 |           0.158 |       0.386 |                      0.250 |
|         14 |   78.000 |               0.038 |           0.123 |       0.397 |                      0.337 |
|         30 |   84.000 |               0.028 |           0.107 |       0.369 |                      0.417 |
|         60 |   91.000 |               0.029 |           0.105 |       0.330 |                      0.493 |
|         90 |   94.000 |               0.026 |           0.086 |       0.266 |                      0.552 |
|        120 |   96.000 |               0.024 |           0.080 |       0.208 |                      0.591 |
|        180 |   98.000 |               0.023 |           0.071 |       0.224 |                      0.678 |
|        365 |  101.000 |               0.014 |           0.049 |       0.099 |                      0.819 |
