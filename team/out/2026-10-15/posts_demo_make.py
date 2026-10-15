"""Картинки к примерам оформления постов (team/POSTS.md) — владельцу в личку, 15.10.

Матч — прогноз владельца «победа Бостона с учётом ОТ» 1,84 (team/PICKS.md, ночь на 14.10):
- Versus «до матча»: Сан-Хосе — Бостон, 14 октября 06:00 МСК (23:00 ET 13.10 — NESN, Boston Globe, TickPick);
- «вердикт» после матча: 3:6 — официальный API НХЛ и табло ESPN (как в render/make_picks_1410.py).
Запуск из корня репозитория: PYTHONPATH=render python team/out/2026-10-15/posts_demo_make.py [папка] (по умолчанию out/1510)
"""
import os
import sys

import ice_more2 as im2
import nhl
import versus

nhl.register()
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/1510'
os.makedirs(OUT, exist_ok=True)

print(versus.render('Сан-Хосе', 'Бостон', OUT + '/demo_vs_sjs_bos.jpg', date='14 октября', time='06:00', league='NHL'))
m = dict(home='Сан-Хосе', away='Бостон', sh=3, sa=6, mark='', date='среда, 14 октября', tag='НХЛ',
         pick=dict(text='ПОБЕДА БОСТОНА С УЧЁТОМ ОТ', odds=1.84, hit=True, checks=[('БОСТОН ВЫИГРАЛ 6:3', True)]))
path = OUT + '/demo_verdict_sjs_bos.jpg'
im2.single(m, path, style='verdict', league='NHL')
print(path)
