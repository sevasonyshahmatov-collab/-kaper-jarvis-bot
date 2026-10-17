# -*- coding: utf-8 -*-
"""Шортсы КХЛ 17.10 на прогнозы владельца — утверждённые шаблоны 14.10 («Кино», «Эфир»), данные заменены на матчи дня.
Форма клубов — khl_stats_1017.json (официальное приложение КХЛ, run khl_stats.json), линия и кэф — facts_khl.md (Pinnacle).

    TRACKS_DIR=<папка с треками> PYTHONPATH=render python team/out/2026-10-17/khl_reels_make.py [имя …] [--frames 1,5,…]
"""
import importlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
DAY = os.path.join(ROOT, 'team', 'out', '2026-10-17')
CFG = os.path.join(ROOT, 'team', 'out', '2026-10-13', 'reels_cfg')
OUT = os.environ.get('OUT') or os.path.join(DAY, 'reels_khl')

from reels import core as C  # noqa: E402

# имя: (модуль, класс, хозяева, гости, время, прогноз, кэф, линия П1/Х/П2 осн. время, трек, доля, дроп трека, файл)
REELS = {
    'barys': ('cinema', 'Cinema', 'Сибирь', 'Барыс', 'СБ 17.10 · 13:30 МСК', 'Итоговая победа Барыса', 1.83,
              (2.60, 3.70, 2.40), 'withyou', 60 / 73, 52.11, 'kino_sibir_barys'),
    'loko': ('broadcast', 'Broadcast', 'Сочи', 'Локомотив', 'СБ 17.10 · 17:00 МСК', 'Тотал матча меньше 5,5', 1.62,
             (6.80, 4.70, 1.41), 'packs', 60 / 71, 29.59, 'efir_sochi_loko'),
}


def make(name):
    mod, cls, home, away, when, pick, coef, line, key, u, tdrop, fn = REELS[name]
    with open(os.path.join(DAY, 'khl_stats_1017.json'), encoding='utf-8') as f:
        S = json.load(f)
    p = os.path.join(CFG, mod + '.json')
    c = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'drop_beats': 20, 'kw': {}}
    drop = c.get('drop_beats', 20) * u
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    r = Cls(home, away, 'KHL', when, pick, coef, S.get(home, {}), S.get(away, {}), u=u, drop=drop, line=line, **c.get('kw', {}))
    return r, key, tdrop - drop, fn


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = sys.argv[sys.argv.index('--frames') + 1] if '--frames' in sys.argv else None
    args = [a for a in args if a != frames]
    os.makedirs(OUT, exist_ok=True)
    for name in args or list(REELS):
        t0 = time.time()
        reel, key, start, fn = make(name)
        base = os.path.join(OUT, fn)
        if frames:
            print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        C.render(reel, base + '.mp4', track=os.path.join(os.environ['TRACKS_DIR'], key + '.wav'), start=start,
                 extra_out=base + '_clean.mp4')
        print('%s: трек %s, старт %.2f с, дроп на %.2f с; ролик %.1f с · %.0f с' % (fn, key, start, reel.drop, reel.dur,
                                                                                 time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
