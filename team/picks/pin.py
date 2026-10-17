# -*- coding: utf-8 -*-
"""Линия Pinnacle на матчи дня — тот же источник, что лист «Коэффициенты» таблиц (guest.api.arcadia.pinnacle.com):
КХЛ — лига 1484, НХЛ — 1456. period 0 — с овертаймом и буллитами, period 6 — основное время (как в таблице).
Облачная сессия до API не достаёт, Actions — достаёт. Печатает PINMATCH (матч, начало) и PIN (рынки периодов 0 и 6).
День: КХЛ — дата начала по Москве, НХЛ — игровой день НХЛ (дата по Нью-Йорку, как в расписании лиги).
Отдельно: python team/picks/pin.py khl 2026-10-16"""
import sys
from datetime import datetime, timedelta, timezone

import requests

import teams

API = 'https://guest.api.arcadia.pinnacle.com/0.1'
LEAGUES = {'khl': 1484, 'nhl': 1456}
HDR = {'Accept': 'application/json',
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
MSK = timezone(timedelta(hours=3))


def dec(a):
    a = float(a)
    return round(1 + a / 100, 3) if a > 0 else round(1 + 100 / abs(a), 3)


def local_day(iso, league):
    dt = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
    if league == 'nhl':
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    return dt.astimezone(MSK).strftime('%Y-%m-%d')


def _flip(m):
    """Pinnacle поставил хозяев и гостей наоборот — меняем стороны."""
    sw = {'home': 'away', 'away': 'home'}
    m = dict(m, side=sw.get(m.get('side'), m.get('side')))
    m['prices'] = [dict(p, designation=sw.get(p['designation'], p['designation'])) for p in m['prices']]
    return m


def fetch(league, day, want=None):
    """→ ({(хозяева, гости): [рынки]}, {(хозяева, гости): начало ISO}). want — пары из расписания лиги (для сверки сторон)."""
    lg = LEAGUES[league]
    mu = requests.get('%s/leagues/%d/matchups' % (API, lg), headers=HDR, timeout=30)
    mk = requests.get('%s/leagues/%d/markets/straight' % (API, lg), headers=HDR, timeout=30)
    print('PIN статус', mu.status_code, mk.status_code, flush=True)
    mu.raise_for_status()
    mk.raise_for_status()
    pairs, starts, flips = {}, {}, set()
    want = set(want or [])
    for m in mu.json():
        if m.get('parentId') or m.get('units') not in (None, 'Regular'):
            continue
        st = m.get('startTime')
        if not st or local_day(st, league) != day:
            continue
        side = {p.get('alignment'): p.get('name') for p in m.get('participants') or []}
        h, a = teams.pin_team(side.get('home'), league), teams.pin_team(side.get('away'), league)
        print('PINMATCH %s | %s (home) — %s (away) | %s → %s — %s' % (m['id'], side.get('home'), side.get('away'), st, h, a), flush=True)
        if not h or not a:
            continue
        if want and (h, a) not in want and (a, h) in want:
            h, a = a, h
            flips.add(m['id'])
        pairs[m['id']] = (h, a)
        starts[(h, a)] = st
    res = {}
    for x in mk.json():
        mid = x.get('matchupId')
        if mid not in pairs or x.get('period') not in (0, 6) or x.get('status') not in (None, 'open'):
            continue
        prices = [dict(designation=p.get('designation'), points=p.get('points'), price=dec(p['price'])) for p in x.get('prices') or []
                  if p.get('price') is not None]
        m = dict(type=x.get('type'), period=x.get('period'), side=x.get('side'), alt=bool(x.get('isAlternate')), prices=prices)
        if mid in flips:
            m = _flip(m)
        res.setdefault(pairs[mid], []).append(m)
        print('PIN %s—%s | %s p%s%s%s | %s' % (pairs[mid][0], pairs[mid][1], m['type'], m['period'], ' ' + m['side'] if m['side'] else '',
                                              ' alt' if m['alt'] else '',
                                              ' | '.join('%s%s %.3f' % (p['designation'], '' if p['points'] is None else ' %+g' % p['points']
                                                                        if m['type'] == 'spread' else ' %g' % p['points'], p['price'])
                                                         for p in prices)), flush=True)
    return res, starts


if __name__ == '__main__':
    fetch(sys.argv[1], sys.argv[2])
