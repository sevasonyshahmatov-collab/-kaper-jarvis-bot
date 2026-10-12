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

with open(os.path.join(DAY, 'team_stats.json'), encoding='utf-8') as f:
    STATS = json.load(f)

# имя: (хозяева, гости, лига, прогноз, кэф, время, за кого, трек, дроп трека (с), доля трека u (с), ni, nt, nv, nh, nf,
#       линия основного времени П1 / Х / П2)
# Поправки владельца 12.10: темп на 10–20 % быстрее (ролик ~21–24 с, команда ~5,5–6,5 с, прогноз ~4 с, плашка ~2–2,5 с),
# новые треки: slx, kizaru, vace (TRACKS в run.py не трогаем — доля и дроп заданы здесь). Дропы — удар по громкости окнами
# 10 мс: slx 35,11 (35,00 — короткий щелчок-подводка), kizaru 30,57 (16,07 — раньше дропа ролика), vace 36,08 (12,07 — рано).
JOBS = {
    'akbars': ('Ак Барс', 'Сочи', 'KHL', 'Победа Ак Барса в основное время', 1.46, 'ПН 12.10 · 19:00 МСК', 'h', 'slx', 35.11,
               60 / 95, 4, 9, 3, 6, 4, (1.46, 4.58, 5.98)),
    'metallurg': ('Торпедо', 'Металлург', 'KHL', 'Победа Металлурга в основное время', 2.06, 'ПН 12.10 · 19:30 МСК', 'a',
                  'kizaru', 30.57, 60 / 60, 3, 6, 2, 4, 2, (3.16, 3.72, 2.06)),
    'devils': ('Нью-Джерси', 'Оттава', 'NHL', 'Победа Нью-Джерси в основное время', 2.23, 'ВТ 13.10 · 02:00 МСК', 'h', 'vace',
               36.08, 60 / 64, 3, 6, 2, 4, 3, (2.23, 4.13, 2.72)),
}


def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0 ролика). Дроп ролика ложится на дроп трека: start = d − drop."""
    h, a, lg, pick, k, when, side, key, d, u, ni, nt, nv, nh, nf, line = JOBS[name]
    r = lineup.Lineup(h, a, lg, pick, k, when, STATS, side=side, u=u, ni=ni, nt=nt, nv=nv, nh=nh, nf=nf, line=line)
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
    bad = [x for x in args if x not in JOBS]
    if bad:
        raise SystemExit('нет ролика: %s (есть: %s)' % (', '.join(bad), ' '.join(JOBS)))
    for name in args or list(JOBS):
        t0 = time.time()
        reel, key, start = make(name)
        base = os.path.join(OUT, 'lineup_' + name)
        if frames:
            print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        from reels import owner_tracks
        C.render(reel, base + '.mp4', track=owner_tracks.wav(key), start=start, extra_out=base + '_clean.mp4')
        lines.append('lineup_%s: трек %s, старт %.2f с, дроп в ролике %.2f с (трек %.2f с); ролик %.1f с'
                     % (name, key, start, reel.drop, start + reel.drop, reel.dur))
        print(lines[-1], '· сборка %.0f с' % (time.time() - t0), flush=True)
    if lines:                                        # ролики могут собираться по одному — заменяем только свои строки
        fn = os.path.join(OUT, 'tracks.txt')
        keep = []
        if os.path.exists(fn):
            with open(fn, encoding='utf-8') as f:
                done = {x.split(':')[0] for x in lines}
                keep = [x.rstrip('\n') for x in f if x.strip() and x.split(':')[0] not in done]
        with open(fn, 'w', encoding='utf-8') as f:
            f.write('\n'.join(keep + lines) + '\n')


if __name__ == '__main__':
    main()
