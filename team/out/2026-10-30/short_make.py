# -*- coding: utf-8 -*-
"""Проба коротких роликов (владелец 30.10, core.Short): 2 ролика разных шаблонов с карточками «Протокол» и «Отправь тому…»
и для сравнения тот же матч прежним роликом ~23 с. Без YouTube / Instagram — только файлы для отправки владельцу.
Данные клубов — team/out/2026-10-13/team_stats_1014.json (образец формата, не прогноз дня)."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily')):
    sys.path.insert(0, p)

import make  # noqa: E402
from reels import core as C, intro, owner_tracks  # noqa: E402
import nhl  # noqa: E402

nhl.register()
OUT = os.path.join(ROOT, 'out', 'short_3010')
os.makedirs(OUT, exist_ok=True)
stats = json.load(open(os.path.join(ROOT, 'team', 'out', '2026-10-13', 'team_stats_1014.json'), encoding='utf-8'))
M = [(0, dict(d='2026-10-31 19:30', h='Детройт', a='Коламбус', pick='Победа Коламбуса в основное время', odds=1.95, tpl='card')),
     (3, dict(d='2026-11-01 03:00', h='Нью-Джерси', a='Детройт', pick='Тотал матча меньше 5,5', odds=1.8, tpl='radar_quantum'))]


def dur(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout.strip() or 0)


def build(i, m, short, name):
    r, key, start = make.reel(m, stats, 'NHL')
    make.SHORT, make.AB_DUR = short, (1.2 if short else 1.5)
    if short:
        d0 = r.drop
        r = C.Short(r, make.card(i), make.short_head(m, 'НХЛ'), m['pick'], *make.short_fav(m, 'NHL'),
                    cta=make.short_cta(m, i, 'NHL'))
        start += d0 - r.drop
    r = intro.wrap(r, m['h'], m['a'], 'NHL', *make.ab_lines(m, i))
    start -= r.intro
    r = C.Loop(r) if short else r
    p = os.path.join(OUT, name + '.mp4')
    C.render(r, p, track=owner_tracks.wav(key), start=start)
    print('SHORT %s: %.2f с, дроп на %.2f с, трек %s с %.2f с, %.1f МБ' % (name, dur(p), r.drop, key, start,
                                                                     os.path.getsize(p) / 1e6), flush=True)
    return p


build(0, M[0][1], False, 'before_card')
for i, m in M:
    build(i, m, True, 'after_%s' % m['tpl'])
