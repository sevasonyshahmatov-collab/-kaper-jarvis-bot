# -*- coding: utf-8 -*-
"""Линия Pinnacle на матчи КХЛ дня — тот же источник, что лист «Коэффициенты» таблицы КХЛ (guest.api.arcadia.pinnacle.com,
лига 1484). Нужна для кэфов к прогнозам 15.10 по рынкам, которых нет в рассылке таблицы (тоталы, форы, индивидуальные тоталы,
победа с ОТ). Облачная сессия до API не достаёт, Actions — достаёт: печатает «PIN …» в лог; ничего не рисует и не шлёт.
period 0 — с овертаймом и буллитами, period 6 — основное время (как в таблице).
Запуск: python team/out/2026-10-15/pin_fetch.py [слова-команды через запятую, по умолчанию lada,ska,severstal,lokomotiv]"""
import sys

import requests

API = 'https://guest.api.arcadia.pinnacle.com/0.1'
LEAGUE = 1484
WORDS = (sys.argv[1] if len(sys.argv) > 1 else 'lada,ska,severstal,lokomotiv').split(',')
H = {'Accept': 'application/json',
     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}


def dec(a):
    a = float(a)
    return round(1 + a / 100, 3) if a > 0 else round(1 + 100 / abs(a), 3)


mu = requests.get('%s/leagues/%d/matchups' % (API, LEAGUE), headers=H, timeout=30)
mk = requests.get('%s/leagues/%d/markets/straight' % (API, LEAGUE), headers=H, timeout=30)
print('PIN статус', mu.status_code, mk.status_code, flush=True)
mu.raise_for_status()
mk.raise_for_status()
names = {}
ms = mu.json()
for m in ms:
    if not m.get('parentId'):
        nm = ' — '.join('%s(%s)' % (p.get('name'), p.get('alignment')) for p in m.get('participants') or [])
        names[m['id']] = (nm, 'start=%s units=%s' % (m.get('startTime'), m.get('units')))
for m in ms:
    if m.get('parentId'):
        par = m['parentId']
        own = ' / '.join(str(p.get('name')) for p in m.get('participants') or [])
        names[m['id']] = (names.get(par, ('?', ''))[0], 'child of %s units=%s type=%s special=%s parts=%s' % (
            par, m.get('units'), m.get('type'), (m.get('special') or {}).get('description'), own))
for mid, (nm, info) in names.items():
    if any(w in nm.lower() for w in WORDS):
        print('PINMATCH', mid, nm, info, flush=True)
want = {mid for mid, (nm, _) in names.items() if any(w in nm.lower() for w in WORDS)}
for x in mk.json():
    if x.get('matchupId') not in want:
        continue
    prices = ' | '.join('%s%s %.3f' % (p.get('designation') or p.get('participantId'),
                                       '' if p.get('points') is None else ' %+g' % p['points'] if x.get('type') == 'spread' else ' %g' % p['points'],
                                       dec(p['price'])) for p in x.get('prices') or [])
    print('PIN %s | %s | type=%s period=%s side=%s alt=%s status=%s | %s' % (
        x.get('matchupId'), names[x['matchupId']][0][:60], x.get('type'), x.get('period'), x.get('side'), x.get('isAlternate'),
        x.get('status'), prices), flush=True)
