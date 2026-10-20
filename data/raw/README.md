# Date brute

Fișierele din acest folder **nu sunt în repo**: au zeci de MB și se pot regenera oricând cu
scripturile din `extraction/` (vezi `README.md` din rădăcină și `docs/PASI_REALIZARE.md`).

| Fișier | Generat de | Conținut |
|---|---|---|
| `search_index.jsonl` | `get_app_list.py` | toate jocurile lansate din 2024 (appid, dată, sumar recenzii, tag-uri) |
| `tag_names.json` | `get_app_list.py` | tagid -> nume |
| `appdetails.jsonl` | `crawl_steam.py --stage details` | metadatele Store API |
| `reviews.jsonl` | `crawl_steam.py --stage reviews` | sumarul recenziilor (ținta) |
| `steamspy.jsonl` | `crawl_steam.py --stage steamspy` | tag-uri SteamSpy (acoperire slabă) |
| `developers.jsonl` | `crawl_steam.py --stage developers` | istoricul jocurilor fiecărui dezvoltator |
| `review_timelines.jsonl` | `crawl_review_timelines.py` | data + verdictul fiecărei recenzii, pentru eșantionul de stabilitate |

Setul de date final, rezultat din acestea, este în repo: `data/final/steam_clean.csv`.
