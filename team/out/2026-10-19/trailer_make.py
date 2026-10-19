"""Трейлер таблицы прогнозов (владелец 19.10): настоящие матчи КХЛ сезона и линия на 20.10 из приложения КХЛ →
render/sheet_data.build → render/reels/sheet_trailer.py, трек north (как у «Джарвиса»): дроп трека 57,50 с, доля 120/142.
→ out/trailer/trailer.mp4 (с музыкой), trailer_clean.mp4 (без), trailer_cover.jpg. Данные — строкой TRAILER в лог."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
import khl_data  # noqa: E402
import sheet_data  # noqa: E402
from PIL import Image  # noqa: E402
from reels import core as C  # noqa: E402
from reels import owner_tracks  # noqa: E402
from reels.sheet_trailer import SheetTrailer  # noqa: E402

games, nxt = khl_data.fetch('2026-10-20')
data = sheet_data.build(games, nxt)
print('TRAILER ' + json.dumps({k: v for k, v in data.items() if k != 'elo'}, ensure_ascii=False), flush=True)
U, TDROP = 120 / 142, 57.50
r = SheetTrailer(data, u=U, pre=4)
os.makedirs('out/trailer', exist_ok=True)
C.render(r, 'out/trailer/trailer.mp4', track=owner_tracks.wav('north'), start=TDROP - r.drop,
         extra_out='out/trailer/trailer_clean.mp4')
f = C.render(r, 'out/trailer/c.mp4', frames=[int(r.cover_t * C.FPS)])[0]
Image.open(f).save('out/trailer/trailer_cover.jpg', quality=92)
print('TRAILER готов: %.1f с' % r.dur, flush=True)
