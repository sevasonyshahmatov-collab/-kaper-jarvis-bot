# -*- coding: utf-8 -*-
"""Ролики «Состав» 12.10: две команды по очереди, прогноз — на дроп трека владельца.
Запуск из корня: PYTHONPATH=render python team/out/2026-10-12/lineup_make.py [akbars metallurg devils] [--frames 0,3.5,…]
Треки — render/reels/owner_tracks.py (TRACKS_DIR локально или секрет TRACKS_KEY в Actions).
Результат: team/out/2026-10-12/reels2/lineup_<имя>.mp4 (со звуком), lineup_<имя>_clean.mp4 (без музыки), *_cover.jpg, tracks.txt."""
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
DAY = os.path.join(ROOT, 'team', 'out', '2026-10-12')
OUT = os.path.join(DAY, 'reels2')

if not shutil.which('ffmpeg'):                                   # на раннере ubuntu ffmpeg может не быть
    pre = [] if os.geteuid() == 0 else ['sudo']
    subprocess.run(pre + ['apt-get', 'update', '-qq'], check=True)
    subprocess.run(pre + ['apt-get', 'install', '-y', '-qq', 'ffmpeg'], check=True)

import nhl  # noqa: E402
nhl.register()
from reels import core as C  # noqa: E402
from reels import lineup  # noqa: E402
from reels.run import TRACKS  # noqa: E402

with open(os.path.join(DAY, 'team_stats.json'), encoding='utf-8') as f:
    STATS = json.load(f)

# имя: (хозяева, гости, лига, прогноз, кэф, время, за кого, трек, ni, nt, nv)
JOBS = {
    'akbars': ('Ак Барс', 'Сочи', 'KHL', 'Победа Ак Барса в основное время', 1.46, 'ПН 12.10 · 19:00 МСК', 'h', 'rotten', 1, 6, 2),
    'metallurg': ('Торпедо', 'Металлург', 'KHL', 'Победа Металлурга в основное время', 2.06, 'ПН 12.10 · 19:30 МСК', 'a', 'jefe',
                  1, 6, 2),
    'devils': ('Нью-Джерси', 'Оттава', 'NHL', 'Победа Нью-Джерси в основное время', 2.23, 'ВТ 13.10 · 02:00 МСК', 'h', 'north',
               1, 6, 2),
}


def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0 ролика). Дроп ролика ложится на дроп трека: start = d − drop."""
    h, a, lg, pick, k, when, side, key, ni, nt, nv = JOBS[name]
    u, d = TRACKS[key]
    r = lineup.Lineup(h, a, lg, pick, k, when, STATS, side=side, u=u, ni=ni, nt=nt, nv=nv)
    start = d - r.drop
    assert start >= 0, (name, start)
    return r, key, start


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    frames = None
    if '--frames' in sys.argv:
        frames = sys.argv[sys.argv.index('--frames') + 1]
        args = [x for x in args if x != frames]
    os.makedirs(OUT, exist_ok=True)
    lines = []
    for name in args or list(JOBS):
        t0 = time.time()
        reel, key, start = make(name)
        base = os.path.join(OUT, 'lineup_' + name)
        if frames:
            print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        from reels import owner_tracks
        C.render(reel, base + '.mp4', track=owner_tracks.wav(key), start=start, extra_out=base + '_clean.mp4')
        lines.append('lineup_%s: трек %s, старт %.2f с, дроп в ролике %.2f с; ролик %.1f с' % (name, key, start, reel.drop, reel.dur))
        print(lines[-1], '· сборка %.0f с' % (time.time() - t0), flush=True)
    if lines and not args:
        with open(os.path.join(OUT, 'tracks.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
