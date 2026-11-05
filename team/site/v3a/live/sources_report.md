# Проверка источников живого счёта

Запуск: 2026-11-05 05:55 UTC, Origin: `https://raw.githack.com`

| Лига | Источник | HTTP | ACAO | Preflight (код / ACAO / methods) | Cache-Control | Размер | Задержка | CORS для GET |
|---|---|---|---|---|---|---|---|---|
| НХЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=2 | 95995 | 102 мс | да |
| АПЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=1 | 15386 | 51 мс | да |
| Ла Лига | ESPN scoreboard | 200 | * | 403 / None / None | max-age=3 | 15402 | 54 мс | да |
| Серия А | ESPN scoreboard | 200 | * | 403 / None / None | max-age=4 | 15158 | 86 мс | да |
| Бундеслига | ESPN scoreboard | 200 | * | 403 / None / None | max-age=3 | 11404 | 53 мс | да |
| Лига 1 | ESPN scoreboard | 200 | * | 403 / None / None | max-age=8 | 14889 | 60 мс | да |
| РПЛ | ESPN scoreboard | 200 | * | 403 / None / None | max-age=1 | 9472 | 130 мс | да |
| Лига чемпионов | ESPN scoreboard | 200 | * | 403 / None / None | max-age=8 | 111862 | 48 мс | да |
| Лига Европы | ESPN scoreboard | 200 | * | 403 / None / None | max-age=5 | 9572 | 56 мс | да |
| НХЛ | api-web score/now | 200 | None | 200 / None / None | no-transform, max-age=14, s-maxage=14 | 29077 | 277 мс | нет |
| НХЛ | api-web gamecenter landing | 200 | None | 200 / None / None | no-transform, max-age=13, s-maxage=13 | 7510 | 411 мс | нет |
| НХЛ | api-web schedule/now | 200 | None | 200 / None / None | no-transform, max-age=12, s-maxage=12 | 89624 | 322 мс | нет |
| НХЛ | api.nhle.com stats team summary | 200 | None | 200 / None / None | None | 1063 | 121 мс | нет |
| КХЛ | khl.api.webcaster.pro data.json | 403 | None | 403 / None / None | no-cache | 1 | 1386 мс | нет |
| КХЛ | khl.api.webcaster.pro events_v2 | 200 | https://raw.githack.com | 403 / None / None | max-age=0, private, must-revalidate | 170 | 787 мс | да |
| КХЛ | khl.ru (сайт) | 200 | None | 405 / None / None | no-store, no-cache, must-revalidate | 97506 | 1127 мс | нет |

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

## КХЛ data.json: варианты заголовков

- UA Mozilla/5.0 без Origin: {"code": 200, "acao": "*", "bytes": 29947, "head": "{\"safe_live_shift\":0,\"stages_v2\":[{\"id\":407,\"khl_id\":1436,\"title\":\"Регулярный чемпионат\",\"type\":\"regular\",\"season\":\"2026"}
- UA Chrome без Origin: {"code": 200, "acao": "*", "bytes": 29947, "head": "{\"safe_live_shift\":0,\"stages_v2\":[{\"id\":407,\"khl_id\":1436,\"title\":\"Регулярный чемпионат\",\"type\":\"regular\",\"season\":\"2026"}
- UA Chrome + Origin: {"code": 403, "acao": null, "bytes": 1, "head": " "}
- UA Mozilla/5.0 + Origin: {"code": 403, "acao": null, "bytes": 1, "head": " "}
- UA Chrome + Origin + Referer: {"code": 403, "acao": null, "bytes": 1, "head": " "}

## КХЛ: с Origin и без

- `{"what": "events_v2", "origin": false, "code": 200, "acao": "*", "ms": 1117, "n": 15}`
- `{"what": "events_v2", "origin": true, "code": 200, "acao": "https://raw.githack.com", "ms": 763, "n": 15}`
- `{"what": "event_v2", "origin": false, "code": 200, "acao": "*", "ms": 1041, "keys": ["announce", "arena", "audio_tracks", "balancer_type", "bets", "commentator", "commentators_names", "condensed_game", "end_at", "event_or_quote_type_name", "event_start_at", "feed_url", "free", "game_state_key", "geo_error", "goals", "has_video", "hd", "highlight", "id", "iframe_code", "iframe_url", "image_big", "infographics", "infographics_enabled", "is_vertical_video", "khl_id", "likes_enabled", "location", "lref1", "lref2", "m3u8_url", "match_id", "mref1", "mref2", "name", "not_regular", "other_events_with_both_teams", "outer_stage_id", "outer_url", "parent_id", "period", "quotes", "score", "scores", "season", "social_tags", "sscore", "stage_id", "stage_name", "stage_type", "start_at", "start_at_day", "team_a", "team_b", "text_events", "this_pair_stat", "tickets", "transaction_types", "transactions", `
- `{"what": "event_v2", "origin": true, "code": 403, "acao": null, "ms": 758, "keys": null, "state": null, "score": null}`
- пример события: `{"id": 3001043, "start_at": 1793775600000, "game_state_key": "finished", "score": "4:0", "scores": {"first_period": "1:0", "second_period": "2:0", "third_period": "1:0", "overtime": null, "bullitt": null}, "period": -1}`
- ключи события: `['balancer_type', 'commentator', 'condensed_game_id', 'end_at', 'event_or_quote_type_name', 'event_start_at', 'feed_url', 'free', 'game_state_key', 'has_video', 'hd', 'highlight_id', 'id', 'iframe_code', 'iframe_url', 'image', 'infographics', 'infographics_enabled', 'is_vertical_video', 'khl_id', 'likes_enabled', 'location', 'm3u8_url', 'match_id', 'name', 'not_regular', 'outer_stage_id', 'period', 'previews', 'score', 'scores', 'sscore', 'stage_id', 'stage_name', 'start_at', 'start_at_day', 'team_a', 'team_b', 'tickets', 'type_id', 'yandex_id', 'yandex_rights']`
