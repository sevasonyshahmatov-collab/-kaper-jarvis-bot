"""Пример: нынешний «Итог матча» (шёлк), анимированный (гифка) → out/pa/."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
import postmatch_styles as pm  # noqa: E402

banners.ensure_ffmpeg()
print(pm.render('Адмирал', 'Спартак', 1, 5, 'out/pa/admiral_spartak.mp4', league='KHL', date='четверг, 16 октября',
                pick='победа Спартака в основное время', kef=1.95, hit=True, style='verdict_anim'))
