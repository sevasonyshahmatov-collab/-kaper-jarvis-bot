# -*- coding: utf-8 -*-
"""Ролики 12.10 со звуком (треки владельца) + без музыки (clean) + обложки.
Треки — render/reels/owner_tracks.py (TRACKS_DIR локально или секрет TRACKS_KEY в Actions). Запуск из корня: PYTHONPATH=render python team/out/2026-10-12/shorts.py
Результат: team/out/2026-10-12/shorts/{chat,top3,notify}_clean.mp4, *_cover.jpg, tracks.txt (трек и секунда старта для редактора)."""
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
OUT = os.path.join(ROOT, 'team', 'out', '2026-10-12', 'shorts')

if not shutil.which('ffmpeg'):                                   # на раннере ubuntu ffmpeg может не быть
    pre = [] if os.geteuid() == 0 else ['sudo']
    subprocess.run(pre + ['apt-get', 'update', '-qq'], check=True)
    subprocess.run(pre + ['apt-get', 'install', '-y', '-qq', 'ffmpeg'], check=True)

import nhl  # noqa: E402
nhl.register()
from reels import core as C  # noqa: E402
from reels.run import TRACKS  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402


def track_wav(key):
    from reels import owner_tracks
    return owner_tracks.wav(key)

def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0) — как в reels/run.py::make."""
    if name == 'coupon':
        from reels import coupon
        u, d = TRACKS['slx']
        legs = [('Барыс', 'Сибирь', 'П1', 'победа Барыса', 2.16, '17:30'),
                ('Ак Барс', 'Сочи', 'П1', 'победа Ак Барса', 1.46, '19:00'),
                ('Торпедо', 'Металлург', 'П2', 'победа Металлурга', 2.06, '19:30')]
        start = d - 4 * u
        r = coupon.Coupon(legs, '12.10.2026', 'KHL', u=u, drop=d - start, stop=12.40 - start, hit2=15.18 - start)
        return r, 'slx', start
    if name == 'top3':
        from reels import top3
        u, d = TRACKS['kizaru']
        drop = 2 * u
        picks = [('Ак Барс', 'Сочи', 'KHL', 'Победа Ак Барса в осн. время', 1.46, 'ПН 12.10 · 19:00 МСК', 'h', 76),
                 ('Торпедо', 'Металлург', 'KHL', 'Победа Металлурга в осн. время', 2.06, 'ПН 12.10 · 19:30 МСК', 'a', 53),
                 ('Миннесота', 'Вегас', 'NHL', 'Победа Миннесоты в осн. время', 2.43, 'ВТ 13.10 · 03:00 МСК', 'h', 60)]
        r = top3.Top3('ТОП-3|ПРОГНОЗА|НА ПОНЕДЕЛЬНИК', picks, u=u, drop=drop)
        return r, 'kizaru', d - drop
    if name == 'notify':
        from reels import notify
        u, d = TRACKS['vace']
        drop = 3 * u
        r = notify.Notify('Нью-Джерси', 'Оттава', 'NHL', 'h', 'Победа Нью-Джерси в осн. время', 2.23, (2.23, 4.13, 2.72), 54,
                          'вторник, 13 октября', '01:59', '02:00', u=u, drop=drop)
        return r, 'vace', d - drop
    raise SystemExit(name)


def main():
    os.makedirs(OUT, exist_ok=True)
    lines = []
    for name in sys.argv[1:] or ['coupon', 'top3', 'notify']:
        t0 = time.time()
        reel, key, start = make(name)
        wav = track_wav(key)                                            # трек владельца
        C.render(reel, os.path.join(OUT, name + '.mp4'), track=wav, start=start,
                 extra_out=os.path.join(OUT, name + '_clean.mp4'))      # со звуком + без музыки, обложка *_cover.jpg
        lines.append('%s: трек %s, старт %.2f с; ролик %.1f с' % (name, key, start, reel.dur))
        print('%s: %.1f с ролика, %.0f с сборки' % (name, reel.dur, time.time() - t0), flush=True)
    if not sys.argv[1:]:
        with open(os.path.join(OUT, 'tracks.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
