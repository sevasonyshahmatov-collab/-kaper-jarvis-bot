"""Трейлер таблицы прогнозов (владелец 19.10): настоящие матчи КХЛ сезона и линия на 20.10 из приложения КХЛ →
render/sheet_data.build → render/reels/sheet_trailer.py. 2-я версия (владелец 19.10): трек depto (быстрее), ролик на ~30 %
короче, точность — со старта сезона, кликабельная обложка (sheet_trailer.cover).
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
from reels import core as C  # noqa: E402
from reels import owner_tracks  # noqa: E402
from reels.sheet_trailer import SheetTrailer, cover  # noqa: E402

games, nxt = khl_data.fetch('2026-10-20')
data = sheet_data.build(games, nxt)
print('TRAILER ' + json.dumps({k: v for k, v in data.items() if k != 'elo'}, ensure_ascii=False), flush=True)
U, TDROP = 0.621762, 39.219                                  # depto: доля и удар — пробы 19.10 (run 268)
r = SheetTrailer(data, u=U, pre=4, beats=(6, 5, 3, 5, 5, 5), cta=4)
os.makedirs('out/trailer', exist_ok=True)
C.render(r, 'out/trailer/trailer.mp4', track=owner_tracks.wav('depto'), start=TDROP - r.drop,
         extra_out='out/trailer/trailer_clean.mp4')
cover(data).save('out/trailer/trailer_cover.jpg', quality=92)
print('TRAILER готов: %.1f с' % r.dur, flush=True)
