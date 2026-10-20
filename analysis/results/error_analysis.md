# Analiza erorilor: Ridge

MAE total pe test: **0.1245**, bias mediu: +0.0113

## Eroarea pe interval de preț
`bias` > 0 înseamnă că modelul supraestimează receptarea.
| price_bucket   |       n |    MAE |    bias |
|:---------------|--------:|-------:|--------:|
| gratuit        | 14.0000 | 0.1127 | -0.0211 |
| ≤5€            | 11.0000 | 0.1469 |  0.0173 |
| 5-10€          | 16.0000 | 0.0980 |  0.0064 |
| 10-20€         | 15.0000 | 0.1410 |  0.0282 |
| >30€           |  1.0000 | 0.2219 |  0.2219 |

## Eroarea pe număr de recenzii
`bias` > 0 înseamnă că modelul supraestimează receptarea.
| reviews_bucket   |       n |    MAE |    bias |
|:-----------------|--------:|-------:|--------:|
| 20-50            | 13.0000 | 0.1612 |  0.0393 |
| 51-100           | 17.0000 | 0.1241 | -0.0191 |
| 101-500          | 16.0000 | 0.1323 |  0.0357 |
| 501-2000         |  7.0000 | 0.0663 | -0.0383 |
| >2000            |  4.0000 | 0.0779 |  0.0378 |

## Eroarea pe valoarea reală a țintei
`bias` > 0 înseamnă că modelul supraestimează receptarea.
| target_bucket   |       n |    MAE |    bias |
|:----------------|--------:|-------:|--------:|
| <50%            |  4.0000 | 0.4219 |  0.4219 |
| 50-70%          | 12.0000 | 0.1518 |  0.1518 |
| 70-80%          |  7.0000 | 0.0448 |  0.0443 |
| 80-90%          | 17.0000 | 0.0748 | -0.0690 |
| 90-100%         | 17.0000 | 0.1179 | -0.1179 |

## Eroarea pe gen (genuri cu ≥ 20 jocuri în test)
| genre     |       n |    MAE |   bias |
|:----------|--------:|-------:|-------:|
| Adventure | 22.0000 | 0.1254 | 0.0036 |
| Action    | 25.0000 | 0.1247 | 0.0045 |
| Indie     | 37.0000 | 0.1126 | 0.0003 |

## Cele mai mari supraestimări (modelul credea că va fi bine primit)
| name                         | genres                                                 |   price_eur |   total_reviews |   positive_ratio |   pred_ratio |   err |
|:-----------------------------|:-------------------------------------------------------|------------:|----------------:|-----------------:|-------------:|------:|
| Legacy of Kain: Ascendance   | Action|Adventure                                       |      19.990 |             473 |            0.288 |        0.874 | 0.586 |
| Web Host Simulator           | Indie|Simulation|Strategy|Early Access                 |      17.750 |              81 |            0.333 |        0.763 | 0.430 |
| Everfall: Idle Dungeon RPG   | Casual|Indie|Massively Multiplayer|RPG|Simulation      |       4.990 |              31 |            0.323 |        0.725 | 0.402 |
| The Last Guild               | Adventure|Indie|Massively Multiplayer|RPG|Free To Play |       0.000 |              49 |            0.469 |        0.739 | 0.269 |
| EvilPunk                     | Action|Indie                                           |       4.990 |              26 |            0.615 |        0.883 | 0.268 |
| SKUF BACKROOMS               | Simulation                                             |       0.990 |              99 |            0.556 |        0.784 | 0.229 |
| Surviving Mars: Relaunched   | Simulation|Strategy                                    |      39.990 |            2556 |            0.564 |        0.786 | 0.222 |
| Only Way is Down             | Action|Adventure|Casual|Indie|Simulation               |       9.750 |             211 |            0.682 |        0.899 | 0.217 |
| Re:Lord – Tales of Adventure | RPG|Strategy                                           |       7.790 |             133 |            0.624 |        0.785 | 0.161 |
| Plantastic                   | Casual|Free To Play                                    |       0.000 |              24 |            0.625 |        0.773 | 0.148 |

## Cele mai mari subestimări (modelul credea că va fi slab primit)
| name                          | genres                                                                                               |   price_eur |   total_reviews |   positive_ratio |   pred_ratio |    err |
|:------------------------------|:-----------------------------------------------------------------------------------------------------|------------:|----------------:|-----------------:|-------------:|-------:|
| Dusty Derby                   | Action|Casual|Indie|Massively Multiplayer|Sports|Early Access                                        |       9.750 |              66 |            1.000 |        0.752 | -0.248 |
| Ruarua                        | Casual|Massively Multiplayer|Free To Play                                                            |       0.000 |              50 |            0.880 |        0.639 | -0.241 |
| Threads of War                | Action|Indie|RPG                                                                                     |       4.990 |              49 |            0.980 |        0.745 | -0.234 |
| Pixel Art Academy: Learn Mode | Casual|Simulation|Animation & Modeling|Design & Illustration|Education|Game Development|Early Access |      13.000 |             435 |            0.970 |        0.788 | -0.182 |
| Split Times                   | Strategy|Free To Play                                                                                |       0.000 |              23 |            0.957 |        0.782 | -0.174 |
| Hyper Team Recon              | Action|Adventure|Indie                                                                               |      19.500 |              81 |            1.000 |        0.830 | -0.170 |
| Kingdom of Night              | Action|Adventure|RPG                                                                                 |      19.500 |             427 |            0.881 |        0.725 | -0.155 |
| Beetle Ninja                  | Action|Adventure|RPG|Free To Play                                                                    |       0.000 |              84 |            0.964 |        0.814 | -0.151 |
| Go Outside Simulator          | Casual|Indie|Simulation                                                                              |       1.990 |              74 |            0.959 |        0.826 | -0.134 |
| Daemonologie                  | Adventure|Indie                                                                                      |       2.990 |             778 |            0.891 |        0.769 | -0.122 |

## Importanța feature-urilor (media |SHAP|), top 20
|                             |   mean_abs_shap |
|:----------------------------|----------------:|
| is_self_published           |          0.0080 |
| dev_prior_mean_score        |          0.0077 |
| short_description_length    |          0.0074 |
| genre_indie                 |          0.0068 |
| is_free                     |          0.0068 |
| tag_immersive_sim           |          0.0067 |
| n_achievements              |          0.0064 |
| genre_free_to_play          |          0.0063 |
| genre_massively_multiplayer |          0.0062 |
| tag_adventure               |          0.0061 |
| description_length          |          0.0061 |
| cat_multi_player            |          0.0060 |
| has_linux                   |          0.0058 |
| tag_action                  |          0.0055 |
| tag_pixel_graphics          |          0.0055 |
| cat_full_controller_support |          0.0051 |
| controller_support          |          0.0051 |
| cat_stereo_sound            |          0.0048 |
| cat_co_op                   |          0.0047 |
| genre_simulation            |          0.0047 |
