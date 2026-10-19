# -*- coding: utf-8 -*-
"""Пробная загрузка в Instagram Reels (владелец 19.10): Торонто — Сан-Хосе, ночь на 20.10, прогноз как в посте 1910-7
(Х2 Сан-Хосе 1,74, facts_nhl.md). Шаблон «Карточка». Только Instagram и Telegram — YouTube в этом запуске выключен
(ролик матча уже загружен ночью конвейером)."""
import os
import shutil
import subprocess
import sys

for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN'):
    os.environ.pop(k, None)
if not shutil.which('ffmpeg'):
    subprocess.run('sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg >/dev/null', shell=True, check=True)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import form  # noqa: E402
import make  # noqa: E402
import nhl_data  # noqa: E402

DAY = '2026-10-19'
M = [dict(h='Торонто', a='Сан-Хосе', pick='Сан-Хосе не проиграет в основное время', odds=1.74,
          x1x2=[2.15, 4.27, 2.79], tpl='card', d='2026-10-20 02:30')]
games, nxt = nhl_data.fetch(DAY)
P = dict(day=DAY, league='nhl', matches=M, stats=form.nhl(games, DAY, ['Торонто', 'Сан-Хосе']),
         all=[dict(d=x['d'], h=x['h'], a=x['a']) for x in sorted(nxt, key=lambda x: x['d'])])
os.makedirs(make.out_dir('nhl', DAY), exist_ok=True)
make.one(P, 0, 'nhl', DAY, 'NHL', 'НХЛ', None)
