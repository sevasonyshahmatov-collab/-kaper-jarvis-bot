# -*- coding: utf-8 -*-
"""Шесть новых форматов роликов 14.10 (ночь НХЛ 13→14 октября), по два на каждый новый трек владельца —
разные участки трека (свой дроп у каждого ролика):
  horses (76 BPM): race «Скачки» — дроп трека 37,92 с; polaroid «Полароиды» — дроп 104,23 с;
  bats   (73 BPM): radar «Радар» — дроп 39,46 с;     dossier «Досье» — дроп 118,36 с;
  packs  (71 BPM): broadcast «Эфир» — дроп 29,59 с;  kinetic «Кинетика» — дроп 97,20 с.
Драматургия как у утверждённых lineup / tape / jarvis / card: матч и линия П1 · Х · П2 → команда 1 (последние 3 игры,
очки, место) → команда 2 → прогноз ровно на дроп (только выбранная команда) → плашка Telegram.
Матчи, время и линия — данные таблицы (событие «sides» 13.10); цифры клубов — официальный API НХЛ
(team_stats_1014.json, собирает nhl_fetch.py в Actions). Прогноз в образцах — фаворит линии в основное время.
Параметры сцен формата (доли до дропа и прочее) — reels_cfg/<формат>.json, его ведёт автор формата.
Запуск из корня: PYTHONPATH=render python team/out/2026-10-13/reels_make.py [race polaroid …] [--frames 0.5,3,…]
Треки — render/reels/owner_tracks.py: TRACKS_DIR с horses.wav, bats.wav, packs.wav (в репозиторий треки не кладём).
Результат — OUT (по умолчанию team/out/2026-10-13/reels, mp4 в git не попадают): <имя>.mp4 (с треком),
<имя>_clean.mp4 (без музыки), <имя>_cover.jpg, tracks.txt."""
import importlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
DAY = os.path.join(ROOT, 'team', 'out', '2026-10-13')
OUT = os.environ.get('OUT') or os.path.join(DAY, 'reels')

if not shutil.which('ffmpeg'):                                   # на раннере ubuntu ffmpeg может не быть
    pre = [] if os.geteuid() == 0 else ['sudo']
    subprocess.run(pre + ['apt-get', 'update', '-qq'], check=True)
    subprocess.run(pre + ['apt-get', 'install', '-y', '-qq', 'ffmpeg'], check=True)

import nhl  # noqa: E402
nhl.register()
from reels import core as C  # noqa: E402

# формат: (модуль, класс, хозяева, гости, время МСК, прогноз, кэф, линия П1/Х/П2, трек, доля трека (с), дроп трека (с), файл)
REELS = {
    'race': ('race', 'Race', 'Каролина', 'Вашингтон', 'СР 14.10 · 01:45 МСК', 'Победа Каролины в основное время', 2.01,
             (2.01, 4.26, 3.07), 'horses', 60 / 76, 37.92, 'race_carolina'),
    'polaroid': ('polaroid', 'Polaroid', 'Анахайм', 'Калгари', 'СР 14.10 · 04:45 МСК', 'Победа Анахайма в основное время', 1.82,
                 (1.82, 4.43, 3.56), 'horses', 60 / 76, 104.23, 'polaroid_anaheim'),
    'radar': ('radar', 'Radar', 'Даллас', 'Колорадо', 'СР 14.10 · 03:30 МСК', 'Победа Колорадо в основное время', 2.37,
              (2.55, 4.13, 2.37), 'bats', 60 / 73, 39.46, 'radar_colorado'),
    'dossier': ('dossier', 'Dossier', 'Нэшвилл', 'Вегас', 'СР 14.10 · 03:45 МСК', 'Победа Вегаса в основное время', 2.20,
                (2.75, 4.17, 2.20), 'bats', 60 / 73, 118.36, 'dossier_vegas'),
    'broadcast': ('broadcast', 'Broadcast', 'Рейнджерс', 'Тампа-Бэй', 'СР 14.10 · 02:15 МСК', 'Победа Тампы в основное время',
                  2.00, (3.13, 4.19, 2.00), 'packs', 60 / 71, 29.59, 'broadcast_tampa'),
    'kinetic': ('kinetic', 'Kinetic', 'Лос-Анджелес', 'Эдмонтон', 'СР 14.10 · 05:30 МСК', 'Победа Эдмонтона в основное время',
                2.24, (2.69, 4.17, 2.24), 'packs', 60 / 71, 97.20, 'kinetic_edmonton'),
}


def stats():
    with open(os.environ.get('STATS') or os.path.join(DAY, 'team_stats_1014.json'), encoding='utf-8') as f:
        return json.load(f)


def cfg(name):
    """Параметры сцен формата: {"drop_beats": доли до дропа в ролике, "kw": {…аргументы класса…}}."""
    p = os.path.join(DAY, 'reels_cfg', name + '.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return {'drop_beats': 20, 'kw': {}}


def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0, файл)."""
    mod, cls, home, away, when, pick, coef, line, key, u, tdrop, fn = REELS[name]
    S, c = stats(), cfg(name)
    drop = c.get('drop_beats', 20) * u
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    r = Cls(home, away, 'NHL', when, pick, coef, S.get(home, {}), S.get(away, {}), u=u, drop=drop, line=line, **c.get('kw', {}))
    return r, key, tdrop - drop, fn


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = None
    if '--frames' in sys.argv:
        frames = sys.argv[sys.argv.index('--frames') + 1]
        args = [a for a in args if a != frames]
    bad = [a for a in args if a not in REELS]
    if bad:
        raise SystemExit('нет формата: %s (есть: %s)' % (', '.join(bad), ' '.join(REELS)))
    os.makedirs(OUT, exist_ok=True)
    lines = []
    for name in args or list(REELS):
        t0 = time.time()
        reel, key, start, fn = make(name)
        assert start >= 0, (name, start)
        base = os.path.join(OUT, fn)
        if frames:
            base = os.path.join(os.environ.get('FRAMES_DIR') or OUT, fn)
            print(C.render(reel, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        from reels import owner_tracks
        C.render(reel, base + '.mp4', track=owner_tracks.wav(key), start=start, extra_out=base + '_clean.mp4')
        lines.append('%s: трек %s, старт %.2f с, дроп на %.2f с ролика; ролик %.1f с' % (fn, key, start, reel.drop, reel.dur))
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
