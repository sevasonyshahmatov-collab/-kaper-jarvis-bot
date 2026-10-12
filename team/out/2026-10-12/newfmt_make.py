# -*- coding: utf-8 -*-
"""Три новых формата роликов 12.10: «Взвешивание» (tape), «Терминал JARVIS» (jarvis), «Коллекционная карточка» (card).
Драматургия: команда 1 (последние 3 игры, очки) → команда 2 → прогноз ровно на дроп трека владельца.
Запуск из корня: PYTHONPATH=render python team/out/2026-10-12/newfmt_make.py [tape|jarvis|card ...] [--frames 0.5,3,...]
Треки — render/reels/owner_tracks.py (TRACKS_DIR локально или секрет TRACKS_KEY). Цифры клубов — team_stats.json
(готовит аналитик; путь можно заменить переменной STATS). Результат: team/out/2026-10-12/reels2/<имя>.mp4 (с треком),
<имя>_clean.mp4 (без музыки), <имя>_cover.jpg, tracks.txt."""
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
from reels.run import TRACKS  # noqa: E402


def stats():
    with open(os.environ.get('STATS') or os.path.join(DAY, 'team_stats.json'), encoding='utf-8') as f:
        return json.load(f)


def club(S, name):
    """Запись клуба: по ключу poster.TEAMS или по короткому имени."""
    import poster
    for k in (name, poster.SHORT.get(name, name)):
        if k in S:
            return S[k]
    for k, v in S.items():
        if poster.SHORT.get(k, k) == poster.SHORT.get(name, name):
            return v
    return {}


def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0, файл)."""
    S = stats()
    if name == 'tape':
        from reels import tape
        u, d = TRACKS['depto']
        drop = 16 * u
        r = tape.Tape('Барыс', 'Сибирь', 'KHL', 'ПН 12.10 · 17:30 МСК', 'Победа Барыса в основное время', 2.16,
                      club(S, 'Барыс'), club(S, 'Сибирь'), u=u, drop=drop)
        return r, 'depto', d - drop, 'tape_barys'
    if name == 'jarvis':
        from reels import jarvis
        u, d = TRACKS['quantum']
        drop = 8 * u
        r = jarvis.Jarvis('Баффало', 'Флорида', 'NHL', 'ПН 12.10 · 20:00 МСК', 'Победа Флориды в основное время', 2.43,
                          club(S, 'Баффало'), club(S, 'Флорида'), u=u, drop=drop)
        return r, 'quantum', d - drop, 'jarvis_florida'
    if name == 'card':
        from reels import card
        u, d = TRACKS['kilo']
        drop = d - 0.05
        r = card.Card('Миннесота', 'Вегас', 'NHL', 'ВТ 13.10 · 03:00 МСК', 'Победа Миннесоты в основное время', 2.43,
                      club(S, 'Миннесота'), club(S, 'Вегас'), u=u, drop=drop)
        return r, 'kilo', d - drop, 'card_wild'
    raise SystemExit('нет формата: %s' % name)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = None
    if '--frames' in sys.argv:
        frames = sys.argv[sys.argv.index('--frames') + 1]
        args = [a for a in args if a != frames]
    os.makedirs(OUT, exist_ok=True)
    lines = []
    for name in args or ['tape', 'jarvis', 'card']:
        t0 = time.time()
        reel, key, start, fn = make(name)
        base = os.path.join(OUT, fn)
        if frames:
            base = os.path.join(os.environ.get('FRAMES_DIR') or OUT, fn)
            print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        from reels import owner_tracks
        wav = owner_tracks.wav(key)
        C.render(reel, base + '.mp4', track=wav, start=start, extra_out=base + '_clean.mp4')
        lines.append('%s: трек %s, старт %.2f с, дроп на %.2f с ролика; ролик %.1f с' % (fn, key, start, reel.drop, reel.dur))
        print(lines[-1], '· сборка %.0f с' % (time.time() - t0), flush=True)
    if lines and not args:
        with open(os.path.join(OUT, 'tracks.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
