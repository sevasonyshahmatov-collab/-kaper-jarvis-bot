# Проверка источников живого счёта

Запуск: 2026-11-05 05:53 UTC, Origin: `https://raw.githack.com`

| Лига | Источник | HTTP | ACAO | Preflight (код / ACAO / methods) | Cache-Control | Размер | Задержка | CORS для GET |
|---|---|---|---|---|---|---|---|---|
| НХЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=6 | 94461 | 69 мс | да |
| АПЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=2 | 15386 | 53 мс | да |
| Ла Лига | ESPN scoreboard | 200 | * | 403 / None / None | max-age=9 | 15402 | 46 мс | да |
| Серия А | ESPN scoreboard | 200 | * | 403 / None / None | max-age=4 | 15158 | 39 мс | да |
| Бундеслига | ESPN scoreboard | 200 | * | 403 / None / None | max-age=3 | 11404 | 49 мс | да |
| Лига 1 | ESPN scoreboard | 200 | * | 403 / None / None | max-age=2 | 14889 | 61 мс | да |
| РПЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=8 | 9472 | 79 мс | да |
| Лига чемпионов | ESPN scoreboard | 200 | * | 403 / None / None | max-age=8 | 111862 | 47 мс | да |
| Лига Европы | ESPN scoreboard | 200 | * | 403 / None / None | max-age=3 | 9572 | 45 мс | да |
| НХЛ | api-web score/now | 200 | None | 200 / None / None | no-transform, max-age=9, s-maxage=9 | 29077 | 287 мс | нет |
| НХЛ | api-web gamecenter landing | 200 | None | 200 / None / None | no-transform, max-age=9, s-maxage=9 | 7510 | 323 мс | нет |
| НХЛ | api-web schedule/now | 200 | None | 200 / None / None | no-transform, max-age=14, s-maxage=14 | 89624 | 212 мс | нет |
| НХЛ | api.nhle.com stats team summary | 200 | None | 200 / None / None | None | 1063 | 141 мс | нет |
| КХЛ | khl.api.webcaster.pro data.json | 403 | None | 403 / None / None | no-cache | 1 | 1228 мс | нет |
| КХЛ | khl.api.webcaster.pro events_v2 | 200 | https://raw.githack.com | 403 / None / None | max-age=0, private, must-revalidate | 170 | 1230 мс | да |
| КХЛ | khl.ru (сайт) | 200 | None | 405 / None / None | no-store, no-cache, must-revalidate | 97506 | 991 мс | нет |

## Поля счёта (пример)

- **НХЛ / ESPN scoreboard**: `{"events": 4, "sample": [{"id": "401892644", "date": "2026-11-05T00:30Z", "teams": ["BUF", "OTT"], "score": ["1", "2"], "period": 3, "clock": "0:00", "state": "post", "detail": "Final"}, {"id": "401892645", "date": "2026-11-05T00:30Z", "teams": ["FLA", "CHI"], "score": ["5", "3"], "period": 3, "clock": "0:00", "state": "post", "detail": "Final"}, {"id": "401892646", "date": "2026-11-05T03:00Z", "teams": ["LA", "SJ"], "score": ["7", "2"], "period": 3, "clock": "0:00", "state": "post", "detail": "Final"}]}`
- **АПЛ / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401879242", "date": "2026-11-06T20:00Z", "teams": ["EVE", "COV"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **Ла Лига / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401882809", "date": "2026-11-06T20:00Z", "teams": ["SEV", "ALA"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **Серия А / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401874815", "date": "2026-11-06T19:45Z", "teams": ["VEN", "UDI"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **Бундеслига / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401884739", "date": "2026-11-06T19:30Z", "teams": ["HSV", "BMG"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **Лига 1 / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401876405", "date": "2026-11-06T19:45Z", "teams": ["TOU", "STR"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **РПЛ / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401879812", "date": "2026-11-06T16:30Z", "teams": ["LMO", "RUB"], "score": ["0", "0"], "period": null, "clock": "0'", "state": "pre", "detail": "Scheduled"}]}`
- **Лига чемпионов / ESPN scoreboard**: `{"events": 9, "sample": [{"id": "401915383", "date": "2026-11-04T17:45Z", "teams": ["AEK", "RMA"], "score": ["2", "3"], "period": 2, "clock": "90'+4'", "state": "post", "detail": "FT"}, {"id": "401915382", "date": "2026-11-04T17:45Z", "teams": ["FEN", "LIV"], "score": ["3", "2"], "period": 2, "clock": "90'+3'", "state": "post", "detail": "FT"}, {"id": "401915304", "date": "2026-11-04T20:00Z", "teams": ["DOR", "BET"], "score": ["2", "1"], "period": 2, "clock": "90'+4'", "state": "post", "detail": "FT"}]}`
- **Лига Европы / ESPN scoreboard**: `{"events": 1, "sample": [{"id": "401915551", "date": "2026-11-04T15:30Z", "teams": ["REN", "OLY"], "score": ["0", "0"], "period": 2, "clock": "90'+4'", "state": "post", "detail": "FT"}]}`
- **НХЛ / api-web score/now**: `{"games": 4, "sample": [{"id": 2026020247, "start": "2026-11-05T00:30:00Z", "state": "OFF", "home": "BUF", "away": "OTT", "score": [1, 2], "period": 3, "clock": {"timeRemaining": "00:00", "secondsRemaining": 0, "running": false, "inIntermission": false}}, {"id": 2026020248, "start": "2026-11-05T00:30:00Z", "state": "OFF", "home": "FLA", "away": "CHI", "score": [5, 3], "period": 3, "clock": {"timeRemaining": "00:00", "secondsRemaining": 0, "running": false, "inIntermission": false}}, {"id": 2026020249, "start": "2026-11-05T03:00:00Z", "state": "FINAL", "home": "LAK", "away": "SJS", "score": [7,`
- **НХЛ / api-web gamecenter landing**: `{"id": 2026020247, "state": "OFF", "period": 3, "clock": {"timeRemaining": "00:00", "secondsRemaining": 0, "running": false, "inIntermission": false}, "home": 1, "away": 2}`
- **НХЛ / api-web schedule/now**: `{"keys": ["nextStartDate", "previousStartDate", "gameWeek", "oddsPartners", "preSeasonStartDate", "regularSeasonStartDate", "regularSeasonEndDate", "playoffEndDate"]}`
- **НХЛ / api.nhle.com stats team summary**: `{"keys": ["data", "total"]}`
- **КХЛ / khl.api.webcaster.pro data.json**: `{"stage": null}`
- **КХЛ / khl.api.webcaster.pro events_v2**: `{"events": 0, "sample": []}`
- **КХЛ / khl.ru (сайт)**: `{}`
