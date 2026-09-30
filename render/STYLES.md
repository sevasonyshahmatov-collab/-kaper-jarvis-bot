# Форматы «Итоги дня»

Вызов для любого формата:

```python
import nhl, results_styles as rs, results_styles2 as rs2
nhl.register()                      # нужно для НХЛ (эмблемы и названия клубов)
rs2.render(items, 'itogi.jpg', style='ice_logo', league='KHL', date_title='понедельник, 28 сентября')
# items = [dict(home='Ак Барс', away='Барыс', sh=3, sa=2, mark='')]   # mark: '' | 'ОТ' | 'Б'
```

## ⭐ Выбранные (30.09.2026)

| style | модуль | что это |
|---|---|---|
| `ice_logo` | results_styles2 | «Лёд»: плашки в цветах клубов, эмблемы вплавлены в плашку тон-в-тон |
| `ice_frost_logo` | results_styles2 | то же + иней по краям картинки |
| `ice_logo_over` | results_styles2 | «Лёд»: плашки в цветах клубов, эмблемы поверх плашки — в цвете, с обводкой-наклейкой и тенью |
| `ice_frost_logo_over` | results_styles2 | то же + иней по краям |

## Все остальные форматы

| style | модуль | что это |
|---|---|---|
| `board` | results_styles | ТАБЛО: «хозяева 4 : 1 гости» в строку, графитовый фон |
| `tiles` | results_styles | ПЛИТКИ: сетка в 2 колонки, фон бордо / тёмный лёд |
| `ticker` | results_styles | СВЕТЛЫЙ: табло трансляции, команда на строку |
| `arena` | results_styles2 | АРЕНА: строки в клубных цветах, Oswald |
| `digital` | results_styles2 | ЦИФРОВОЕ ТАБЛО: сетка, светящиеся цифры, Tektur |
| `gazeta` | results_styles2 | СПОРТ-ГАЗЕТА: косые плашки, Russo One + Golos |
| `minimal` | results_styles2 | МИНИМАЛИЗМ: без карточек, Unbounded + Onest |
| `ice` | results_styles2 | ЛЁД: светлый, разметка площадки, счёт в «шайбах», Exo 2 Italic |
| `ice_frost` | results_styles2 | ЛЁД + иней по краям |
| `ice_color` | results_styles2 | ЛЁД + плашки в цветах клубов (эмблемы в кружках) |
| `ice_frost_color` | results_styles2 | ЛЁД + цветные плашки + иней |

Исходный формат из набора — `recap.render_results_day` (КХЛ) и `nhl_kit.results_day` (НХЛ).
Логотип лиги на фоне — `league_mark.on('KHL' | 'NHL')`.
