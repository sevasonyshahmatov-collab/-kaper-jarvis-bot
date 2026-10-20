"""Проверка запасной линии НХЛ (team/picks/espn.py) на матчах дня 20.10: какие рынки DraftKings пришли и какой прогноз
выбрал бы конвейер, если бы у Pinnacle матчей не было (все матчи — как запасные). Ничего не шлёт."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import espn  # noqa: E402
import nhl_data  # noqa: E402
import pick  # noqa: E402

games, nxt = nhl_data.fetch('2026-10-20')
mk = espn.fetch('2026-10-20', nxt)
ms = pick.day_picks(games, nxt, mk, {}, 'nhl', backup=set(mk))
print('ESPNCHECK матчей %d, с линией ESPN %d, прогнозов %d' % (len(nxt), len(mk), len(ms)), flush=True)
