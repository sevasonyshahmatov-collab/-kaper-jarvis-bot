# -*- coding: utf-8 -*-
"""Пробный шортс для первой загрузки на YouTube (владелец 18.10): «Кино», Калгари — Каролина, ночь на 19.10.
Новое: поле 94% по краям и подвал Telegram только в конце (core.inset / core.footer), бегущая строка «Матчи дня» (core.ticker).
Форма — reel_stats_1018.json (team/reels_daily/stats.py, Actions run 228), линия и кэф — facts_nhl.md (Pinnacle, run 225).

    TRACKS_DIR=<папка с треками> PYTHONPATH=render python team/out/2026-10-18/yt_test_make.py [--frames 1,5,…]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
DAY = os.path.join(ROOT, 'team', 'out', '2026-10-18')
CFG = os.path.join(ROOT, 'team', 'out', '2026-10-13', 'reels_cfg')
OUT = os.environ.get('OUT') or os.path.join(DAY, 'yt_test')

from reels import core as C  # noqa: E402
from reels.cinema import Cinema  # noqa: E402

HOME, AWAY = 'Калгари', 'Каролина'
TICKER = ['НХЛ · время МСК', 'Миннесота — Коламбус 01:00', 'Калгари — Каролина 03:00']
U, TDROP, KEY, FN = 60 / 73, 52.11, 'withyou', 'kino_calgary_carolina'


def make():
    S = json.load(open(os.path.join(DAY, 'reel_stats_1018.json'), encoding='utf-8'))
    c = json.load(open(os.path.join(CFG, 'cinema.json'), encoding='utf-8'))
    drop = c.get('drop_beats', 20) * U
    r = Cinema(HOME, AWAY, 'NHL', 'ПН 19.10 · 03:00 МСК', 'Победа Каролины в основное время', 1.79, S[HOME], S[AWAY],
               u=U, drop=drop, line=(3.64, 4.43, 1.79), **c.get('kw', {}))
    r.ticker, r.ticker_tag = TICKER, 'МАТЧИ ДНЯ · 19.10'
    return r, TDROP - drop


def main():
    os.makedirs(OUT, exist_ok=True)
    reel, start = make()
    base = os.path.join(OUT, FN)
    if '--frames' in sys.argv:
        fr = sys.argv[sys.argv.index('--frames') + 1]
        print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in fr.split(',')]))
        return
    C.render(reel, base + '.mp4', track=os.path.join(os.environ['TRACKS_DIR'], KEY + '.wav'), start=start,
             extra_out=base + '_clean.mp4')
    print('%s: %.1f с' % (base, reel.dur))


if __name__ == '__main__':
    main()
