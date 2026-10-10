"""Образец шаблона «МАТЧ ДНЯ» (match_day.py) на матче Ак Барс — Северсталь.

Дата, время, линия и текст — ОБРАЗЕЦ для проверки вёрстки, не реальный матч. Фото игроков: положите файлы
в render/photos/ и укажите их в home_photo / away_photo (focus — где лицо: доли ширины и высоты кадра).
Запуск из папки render: python make_match_day_demo.py → out/match_day/akbars_severstal.jpg
"""
import os

import match_day

OUT = 'out/match_day'
os.makedirs(OUT, exist_ok=True)
PH = 'photos'
M = dict(
    home='Ак Барс', away='Северсталь', home_abbr='АКБ', away_abbr='СЕВ',
    arena='«Татнефть Арена» · Казань',
    date='среда, 7 октября', time='19:30',
    odds=(2.05, 4.10, 3.30),
    text='«Ак Барс» дома принимает «Северсталь». Казань на своём льду играет первым номером и давит броском, '
         'Череповец силён в обороне и ловит соперника на контратаках. Кто навяжет свой темп, тот и заберёт матч.',
    home_photo=os.path.join(PH, 'akbars.jpg') if os.path.exists(os.path.join(PH, 'akbars.jpg')) else None, home_focus=(0.58, 0.36),
    away_photo=os.path.join(PH, 'severstal.jpg') if os.path.exists(os.path.join(PH, 'severstal.jpg')) else None, away_focus=(0.49, 0.25),
    home_city='Казань', away_city='Череповец',
)
print(match_day.render(M, OUT + '/akbars_severstal.jpg', league='KHL'))
