# -*- coding: utf-8 -*-
"""Серия 4 (17.10): новые шаблоны под треки владельца, драматургия утверждённых 12.10 / 14.10 (render/reels/s4.py).
Образцы — на матчах НХЛ ночи 13→14.10 (данные клубов team_stats_1014.json, линия П1/Х/П2 — как в reels_make.py).

    PYTHONPATH=render python team/out/2026-10-17/reels4_make.py [storm …] [--frames 1,5,…]

Треки — TRACKS_DIR с <ключ>.wav (в репозиторий треки не кладём). Результат — OUT (по умолчанию team/out/2026-10-17/reels4):
<имя>.mp4 (с треком), <имя>_clean.mp4 (без музыки), <имя>_cover.jpg; затем сжатая копия — в videos/архив (tools/video_archive.py)."""
import importlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
DAY = os.path.join(ROOT, 'team', 'out', '2026-10-17')
OUT = os.environ.get('OUT') or os.path.join(DAY, 'reels4')
STATS = os.path.join(ROOT, 'team', 'out', '2026-10-13', 'team_stats_1014.json')

import nhl  # noqa: E402
nhl.register()
from reels import core as C  # noqa: E402
from reels import s4  # noqa: E402

# шаблон: (модуль, класс, хозяева, гости, время МСК, прогноз, кэф, линия, трек, доля трека (с), дроп трека (с), файл)
REELS = {
    'storm': ('s4_storm', 'Storm', 'Нэшвилл', 'Вегас', 'СР 14.10 · 03:45 МСК', 'Победа Вегаса в основное время', 2.20,
              (2.75, 4.17, 2.20), 'doomsday', 0.4444, 43.181, 'storm_vegas'),
}


def make(name):
    mod, cls, home, away, when, pick, coef, line, key, u, tdrop, fn = REELS[name]
    with open(STATS, encoding='utf-8') as f:
        S = json.load(f)
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    r = Cls(home, away, 'NHL', when, pick, coef, S.get(home, {}), S.get(away, {}), u=u, line=line)
    return r, key, tdrop - r.drop, fn


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = None
    if '--frames' in sys.argv:
        frames = sys.argv[sys.argv.index('--frames') + 1]
        args = [a for a in args if a != frames]
    os.makedirs(OUT, exist_ok=True)
    for name in args or list(REELS):
        t0 = time.time()
        reel, key, start, fn = make(name)
        assert start >= 0, (name, start)
        base = os.path.join(OUT, fn)
        if frames:
            ts = [float(x) for x in frames.split(',')] if frames != 'auto' else \
                [1.0, reel.t1 + 0.4, reel.t1 + 3.5, reel.t2 + 3.5, reel.drop - 0.4, reel.drop + 0.2, reel.drop + 1.6, reel.dur - 0.8]
            print(C.render(reel, base + '.mp4', frames=[int(round(x * C.FPS)) for x in ts]))
            continue
        track = os.path.join(os.environ['TRACKS_DIR'], key + '.wav')
        C.render(reel, base + '.mp4', track=track, start=start, extra_out=base + '_clean.mp4')
        print('%s: трек %s, старт %.2f с, дроп на %.2f с ролика; ролик %.1f с · сборка %.0f с'
              % (fn, key, start, reel.drop, reel.dur, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
