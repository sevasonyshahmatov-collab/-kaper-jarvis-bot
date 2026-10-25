# Разведка данных для мини-приложения

- ✓ 200 khl_boot https://khl.api.webcaster.pro/api/khl_mobile/data.json | 30338 байт
- КХЛ стадия: 407; ключи data.json: about_khl, alternative_payment_services, android_app_version, balance_payment_services, country, current_customer, current_stage_id, exchange_rate_usd, geo_error, ios_app_version, mastercard_api, mastercard_enabled_stage_ids, mqtt_broker, push_notification_subscriptions, remote_ip, safe_live_shift, selections, server_day, server_time, sms_data, stages, stages_v2, stat_url, teams, teams_for_filter, test_event, transaction_types, transactions, video_types
- ✓ 200 khl_events https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json?order_direction=desc&page=1&stage_id=407 | 24311 байт
- ✓ 200 khl_teams https://khl.api.webcaster.pro/api/khl_mobile/teams_v2.json?stage_id=407 | 7189 байт
- ✓ 200 khl_teams_plain https://khl.api.webcaster.pro/api/khl_mobile/teams.json | 20596 байт
- ✓ 200 khl_team https://khl.api.webcaster.pro/api/khl_mobile/team_v2.json?id=None | 110 байт
- ✓ 200 khl_players https://khl.api.webcaster.pro/api/khl_mobile/players_v2.json?q[team_id_eq]=None | 2 байт
- ✓ 200 khl_players_stage https://khl.api.webcaster.pro/api/khl_mobile/players_v2.json?stage_id=407&team_id=None | 347380 байт
- ✗ 404 khl_player_stats https://khl.api.webcaster.pro/api/khl_mobile/player_stats_v2.json?stage_id=407&team_id=None
- ✗ 404 khl_team_stats https://khl.api.webcaster.pro/api/khl_mobile/team_stats_v2.json?stage_id=407
- ✗ 404 khl_standings https://khl.api.webcaster.pro/api/khl_mobile/tournament_table_v2.json?stage_id=407
- ✗ 404 khl_table https://khl.api.webcaster.pro/api/khl_mobile/table_v2.json?stage_id=407
- ✗ 404 khl_stages https://khl.api.webcaster.pro/api/khl_mobile/stages_v2.json
- ✓ 200 nhl_standings https://api-web.nhle.com/v1/standings/now | 63266 байт
- ✓ 200 nhl_club_stats https://api-web.nhle.com/v1/club-stats/BOS/now | 11659 байт
- ✓ 200 nhl_roster https://api-web.nhle.com/v1/roster/BOS/current | 10817 байт
- ✓ 200 nhl_team_summary https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId=20262027%20and%20gameTypeId=2 | 17901 байт
