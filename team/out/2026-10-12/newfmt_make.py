# -*- coding: utf-8 -*-
"""Три формата роликов 12.10: tape (tale of the tape), jarvis (терминал), card (коллекционная карточка).
Драматургия: матч → команда 1 (последние 3 игры, очки) → команда 2 → прогноз ровно на дроп трека владельца.
Правила владельца 12.10: без заголовков-рубрик; темп — ролик ~21–24 с (tape ~18–19 с), команда ~5,5–6,5 с, прогноз ~4 с,
плашка Telegram ~2–2,5 с; в начале — линия кэфов П1 / Х / П2; на прогнозе — только выбранная команда.
Треки (поправка 12.10): tape — rotten, jarvis — north, card — jefe. Доля и дроп трека заданы здесь явно (TRACKS в run.py
не трогаем); дроп — удар по громкости окнами 10 мс; старт трека = дроп трека − дроп ролика (≥ 0).
Запуск из корня: PYTHONPATH=render python team/out/2026-10-12/newfmt_make.py [tape|jarvis|card ...] [--frames 0.5,3,...]
Треки — render/reels/owner_tracks.py (TRACKS_DIR локально или секрет TRACKS_KEY). Цифры клубов — team_stats.json
(готовит аналитик; путь можно заменить переменной STATS). Результат: team/out/2026-10-12/reels2/<имя>.mp4 (с треком),
<имя>_clean.mp4 (без музыки), <имя>_cover.jpg, newfmt_tracks.txt."""
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
    if name == 'tape':                       # 25–30 % быстрее версии 25,5 с: ~18,8 с; трек rotten (72 BPM)
        from reels import tape
        u, d = 60 / 72, 28.20                # удар rotten 28,20 (по громкости окнами 10 мс)
        per, pre, n = 1, 1.5, 6              # строка на долю; 6 строк на команду (3 игры + очки, место, шайбы)
        drop = (2.5 + 2 * n * per + pre) * u
        r = tape.Tape('Барыс', 'Сибирь', 'KHL', 'ПН 12.10 · 17:30 МСК', 'Победа Барыса в основное время', 2.16,
                      club(S, 'Барыс'), club(S, 'Сибирь'), u=u, drop=drop, per=per, pre=pre, hold=4, cta=2.5,
                      line=(2.16, 3.70, 2.96))
        return r, 'rotten', d - drop, 'tape_barys'
    if name == 'jarvis':                     # трек north (71 BPM, сцена — 2 доли = 0,845 с)
        from reels import jarvis
        u, d = 120 / 142, 57.50              # удар north 57,50 (57,30 — подводка)
        drop = 19 * u
        r = jarvis.Jarvis('Баффало', 'Флорида', 'NHL', 'ПН 12.10 · 20:00 МСК', 'Победа Флориды в основное время', 2.43,
                          club(S, 'Баффало'), club(S, 'Флорида'), u=u, drop=drop, team=7, pre=2, hold=5, cta=2.5,
                          line=(2.47, 4.16, 2.43))
        return r, 'north', d - drop, 'jarvis_florida'
    if name == 'card':                       # трек jefe (81 BPM)
        from reels import card
        u, d = 60 / 81, 20.80                # удар jefe 20,80
        drop = 21 * u
        r = card.Card('Миннесота', 'Вегас', 'NHL', 'ВТ 13.10 · 03:00 МСК', 'Победа Миннесоты в основное время', 2.43,
                      club(S, 'Миннесота'), club(S, 'Вегас'), u=u, drop=drop, team=8, rush=2, hold=5.5, cta=3,
                      line=(2.43, 4.12, 2.48))
        return r, 'jefe', d - drop, 'card_wild'
    raise SystemExit('нет формата: %s' % name)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = None
    if '--frames' in sys.argv:
        frames = sys.argv[sys.argv.index('--frames') + 1]
        args = [a for a in args if a != frames]
    os.makedirs(OUT, exist_ok=True)
    lines = []
    bad = [a for a in args if a not in ('tape', 'jarvis', 'card')]
    if bad:
        raise SystemExit('нет формата: %s (есть: tape jarvis card)' % ', '.join(bad))
    for name in args or ['tape', 'jarvis', 'card']:
        t0 = time.time()
        reel, key, start, fn = make(name)
        assert start >= 0, (name, start)
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
    if lines:                                        # ролики могут собираться по одному — заменяем только свои строки
        fn = os.path.join(OUT, 'newfmt_tracks.txt')
        keep = []
        if os.path.exists(fn):
            with open(fn, encoding='utf-8') as f:
                done = {x.split(':')[0] for x in lines}
                keep = [x.rstrip('\n') for x in f if x.strip() and x.split(':')[0] not in done]
        with open(fn, 'w', encoding='utf-8') as f:
            f.write('\n'.join(keep + lines) + '\n')


if __name__ == '__main__':
    main()
