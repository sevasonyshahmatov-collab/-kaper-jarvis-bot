# -*- coding: utf-8 -*-
"""Instagram: ролики на оставшиеся матчи 19.10 и ночь на 20.10 (владелец 19.10 — «выгрузим всё сегодняшнее, пусть набирает
просмотры»). Прогнозы — как в постах канала (facts_khl.md / facts_nhl.md), шаблоны разные. YouTube выключен (лимит канала
на сегодня исчерпан ночью). Каждый ролик — владельцу в Telegram со ссылкой на Instagram."""
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
import khl_data  # noqa: E402
import make  # noqa: E402
import nhl_data  # noqa: E402

DAY = '2026-10-19'
LEAGUES = {
    'khl': ('KHL', 'КХЛ', khl_data, form.khl, [
        dict(h='Северсталь', a='Торпедо', pick='Тотал матча меньше 4,5', odds=2.07, x1x2=[2.33, 3.61, 2.74], tpl='tape',
             d='2026-10-19 19:00'),
        dict(h='Сочи', a='Шанхайские Драконы', pick='Победа Шанхайских Драконов в основное время', odds=1.94,
             x1x2=[3.42, 3.77, 1.94], tpl='jarvis', d='2026-10-19 19:30')]),
    'nhl': ('NHL', 'НХЛ', nhl_data, form.nhl, [
        dict(h='Рейнджерс', a='Анахайм', pick='Индивидуальный тотал Анахайма меньше 2,5 в основное время', odds=2.04,
             x1x2=[2.15, 4.22, 2.81], tpl='cinema_vampire', d='2026-10-20 02:00'),
        dict(h='Филадельфия', a='Колорадо', pick='Победа Колорадо в основное время', odds=1.71, x1x2=[3.90, 4.60, 1.71],
             tpl='graffiti_demons', d='2026-10-20 02:00'),
        dict(h='Юта', a='Питтсбург', pick='Тотал матча больше 6,5 в основное время', odds=2.07, x1x2=[1.90, 4.43, 3.26],
             tpl='race_cant_say', d='2026-10-20 04:00')]),
}
errors = []
for league, (code, lg, src, stats_fn, ms) in LEAGUES.items():
    games, nxt = src.fetch(DAY)
    names = [t for m in ms for t in (m['h'], m['a'])]
    P = dict(day=DAY, league=league, matches=ms, stats=stats_fn(games, DAY, names),
             all=[dict(d=x['d'], h=x['h'], a=x['a']) for x in sorted(nxt, key=lambda x: x['d'])])
    os.makedirs(make.out_dir(league, DAY), exist_ok=True)
    for i in range(len(ms)):
        try:
            make.one(P, i, league, DAY, code, lg, None)
        except Exception as e:  # noqa: BLE001
            errors.append('%s — %s: %r' % (ms[i]['h'], ms[i]['a'], e))
            print('REELERR', errors[-1], flush=True)
if errors:
    make.tg_text('Instagram, ролики 19.10: не собрались\n' + '\n'.join(errors))
