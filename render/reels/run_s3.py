# -*- coding: utf-8 -*-
"""Серия 3 (render/reels/s3_*.py): восемь роликов на «настоящих» предметах под восемь треков владельца.

Треки — у владельца / в скретчпаде сессии, в репозиторий не кладём. Ролик начинается за ~4,5 с до дропа трека.

    python -m reels.run_s3 <папка треков> <папка вывода> [ролик …] [--frames]   (запуск из render/)
"""
import importlib
import os
import sys

from reels import core as C
from reels.run_premium import MATCHES

# ролик: (модуль.класс, трек, дроп в треке, доля, матч)
PLAN = {
    'coin': ('s3_coin.Coin', 'twofaced', 33.871, 0.4839, 'adm'),
    'board': ('s3_board.Board', 'demons', 86.296, 0.6522, 'col'),
    'arena': ('s3_arena.Arena', 'say', 49.161, 0.3871, 'avg'),
    'case': ('s3_case.Case', 'militant', 8.060, 0.4762, 'sha'),
}


def build(name):
    cls, track, drop_t, u, mk = PLAN[name]
    mod, kl = cls.split('.')
    pre = max(1, round(4.5 / u)) * u
    reel = getattr(importlib.import_module('reels.' + mod), kl)(MATCHES[mk], u, pre)
    return reel, track, drop_t - pre


def main():
    tracks, out = sys.argv[1], sys.argv[2]
    names = [a for a in sys.argv[3:] if not a.startswith('--')] or list(PLAN)
    os.makedirs(out, exist_ok=True)
    for nm in names:
        reel, track, start = build(nm)
        base = os.path.join(out, 's3_%02d_%s_%s' % (list(PLAN).index(nm) + 1, nm, track))
        if '--frames' in sys.argv:
            D = reel.drop
            ts = [1.0, D - 0.5, D + 0.3, getattr(reel, 't_kef', D + 3) + 0.7, reel.dur - 1.2]
            print(C.render(reel, base + '.mp4', frames=[int(t * C.FPS) for t in ts]))
            continue
        C.render(reel, base + '_preview.mp4', track=os.path.join(tracks, track + '.m4a'), start=start,
                 extra_out=base + '_clean.mp4')
        print(base, '%.1f с' % reel.dur, flush=True)


if __name__ == '__main__':
    main()
