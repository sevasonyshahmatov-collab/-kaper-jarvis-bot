"""Итог Амур — Барыс 5:2 (владелец 19.10: ставил на Амур) — анимированный «Итог матча» → out/pa/."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
import postmatch_styles as pm  # noqa: E402

banners.ensure_ffmpeg()
print(pm.render('Амур', 'Барыс', 5, 2, 'out/pa/amur_barys.mp4', league='KHL', date='понедельник, 19 октября',
                pick='итоговая победа Амура', kef=1.73, hit=True, style='verdict_anim'))
