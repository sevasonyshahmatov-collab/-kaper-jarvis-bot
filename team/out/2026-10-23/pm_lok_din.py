"""Итог 2310-4 вручную (владелец 23.10: автозадание зависло на хронике): Локомотив — Динамо Москва 2:1 ОТ, ТМ 5,5 → out/pm/."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
import postmatch_styles as pm  # noqa: E402

banners.ensure_ffmpeg()
print(pm.render('Локомотив', 'Динамо Москва', 2, 1, 'out/pm/lok_din.mp4', mark='ОТ', league='KHL',
                date='пятница, 23 октября', pick='тотал матча меньше 5,5', kef=1.61, hit=True, style='verdict_anim'))
