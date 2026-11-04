# Ежедневный конвейер данных макета v3a

Запуск: `.github/workflows/site-v3a-daily.yml` (workflow_dispatch / правка `daily/run.txt` на ветке `claude/team-dev-*`),
по расписанию — `gh workflow run` из `site-v3a-daily-cron.yml` (ветка `claude/site-v3a-daily-cron` → main): 06:23 и 23:47 МСК.
Сеть к ESPN / НХЛ / КХЛ / Фонбету / Pinnacle есть только в Actions. Живой сайт не трогаем, публикации нет — коммит в ветку макета.

## Что делает `run.py` (шаги, каждый независим; итог — `data/daily_log.json`)
| шаг | источник | результат |
|---|---|---|
| teamcode | ветка команды `claude/project-migration-old-account-6e31vz` (`git archive` в /tmp/teamcode) | код `team/picks`, `team_season.py` |
| live | клон живого сайта (app/data.json — таблицы, оси силы, наши итоги) | /tmp/live |
| hockey_season | приложение КХЛ, api-web.nhle.com (`team_season.py`) + расписание КХЛ на 3 недели | `team/season.json` |
| foot_raw / foot_build | ESPN (site.api.espn.com) | `football/data/raw.json.gz`, `football.json/js` |
| foot_lineups / foot_photos / foot_players / foot_trends | ESPN summary (только новые матчи) | `lineups.json.gz`, `players.js`, `trends.js` |
| nhl_players / khl_players | api-web.nhle.com, приложение КХЛ | `hockey/data/*_players.json` |
| lines_model | см. ниже | `data/lines.json`, `data/model.json`, `data/today.json` (+ `.js`) |
| teams_build | `team/build_data.py` | `assets/data/teams.json/js` — без примеров (`s:1`), где есть настоящие матчи сезона |
| split | `daily/split.py` (без сети) | лёгкие файлы для страниц: `assets/data/teams-lite.js` + `club/<slug>.js`, `football/data/football-lite.js` + `games.js` + `club/<id>.js` + `pl/*.js`, `hockey/data/plite_{khl,nhl}.json` + `players/<slug>.json`. Последний шаг перед `search`; полные файлы остаются (их читают сборщики и поиск), страницы грузят только лёгкие |

Если новый файл заметно меньше прежнего (источник вернул пусто) — прежний возвращается, шаг помечается ошибкой в `daily_log.json`.

## Ключ матча (одинаков во всех файлах)
`лига|дата МСК|хозяева slug|гости slug`, например `khl|2026-11-05|ska|cska`, `nhl|2026-11-05|boston|toronto`,
`epl|2026-11-08|arsenal|chelsea`. Лига: `khl nhl epl laliga seriea bundesliga ligue1 rpl ucl uel`. Дата — день **начала матча по Москве**
(ночные матчи НХЛ — следующее число). Slug хоккея — ключи `names` в `assets/data/teams.json`, футбола — `id` клубов в `football.json`.

## data/lines.json — линии (коэффициенты), окно: сегодня и завтра по Москве
`{ключ: {src, t, start, p1, x, p2, tot, over, under, tot_src, fin1?, fin2?, alt?}}`
- `src`: `fonbet` (линия Фонбета, основное время; по ней ставит владелец) | `khl-app` (приложение КХЛ, поле bets, только П1/Х/П2) | `pinnacle` | `espn` (линия ESPN, футбол);
  порядок приоритета: Фонбет → приложение КХЛ → Pinnacle → ESPN.
- `t` — когда снято (UTC, `2026-11-04T10:30Z`), `start` — начало матча `ГГГГ-ММ-ДД ЧЧ:ММ` МСК.
- `p1 x p2` — десятичные кэфы П1/Х/П2 за основное время (в хоккее `x` — ничья в основное время; у КХЛ-app может не быть).
- `tot over under` — основная линия тотала (где кэфы ближе всего), кэф «больше» и «меньше»; `tot_src` — откуда тотал (может отличаться от `src`).
- `fin1 fin2` — итоговая победа с ОТ/буллитами (хоккей, Фонбет). `alt` — те же `p1 x p2` из других источников для сверки.

## data/model.json — вероятности модели (доли 0–1)
`{ключ: {p1, x, p2, tot, over, btts?, w1?, w2?, totals?, lam, src:'model', ver, t}}`
- хоккей `ver: jarvis-hockey-v2` — `team/picks/calc.match()` с новым рейтингом `khl_live`/`nhl_live` (xG/броски, вратарь, два дня подряд),
  вероятность = ½ модель счёта + ½ частота у самих команд (без смеси с линией); `jarvis-hockey-v1` — то же без нового рейтинга;
  `p1 x p2` — основное время, `w1 w2` — итоговая победа с ОТ/Б, `totals` — {линия: P(больше)}, `tot/over` — линия тотала линии или 5.5.
- футбол `ver: jarvis-foot-fd (football_day.py)` — рейтинг Дикси-Коулса + смесь с линией Pinnacle (как в прогнозах команды), `btts` — «обе забьют»;
  `ver: poisson-v1` — запасная прозрачная модель Пуассона по голам сезона (football/build_data.py, атака/оборона, прошлый сезон с весом 0,35);
  `over` — P(тотал больше 2,5).

## data/today.json
`{built, days, matches:[{key, lg, t, h, a, hn, an, arena?, line?, model?}]}` — матчи окна с реальным временем МСК (`t`), названиями и
источником линии/версией модели. Хоккейные блоки главной (`__HTODAY` на hockey/index.html) можно собирать из него + lines/model по `key`.

## Контракт для страниц
Страницы читают `lines.json`/`model.json` по ключу; в `teams.json` у будущих матчей клуба `k` — линия `[победа клуба, ничья, победа соперника]`
(`ksrc` — источник; `ks:1` — линии нет, оценка-пример), `pm` — вероятности модели в том же порядке.
