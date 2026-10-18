# -*- coding: utf-8 -*-
"""Пробная загрузка на YouTube (владелец 18.10): ролик нового вида (поля, бегущая строка, плашка в конце) —
yt_test/kino_calgary_carolina.mp4 из yt_test_make.py. Загрузка — team/reels_daily/youtube.py (как у конвейера),
результат — сообщением владельцу (задание yt_test.json переписывается, team_job перечитывает его после make)."""
import json
import os
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DAY, '..', '..', 'reels_daily'))
import youtube  # noqa: E402
import yt_texts  # noqa: E402

m = dict(d='2026-10-19 03:00', h='Калгари', a='Каролина', pick='Победа Каролины в основное время', odds=1.79)
y = yt_texts.youtube(m, 'НХЛ')
link, note = youtube.upload(os.path.join(DAY, 'yt_test', 'kino_calgary_carolina.mp4'), y['title'], y['description'], y['tags'])
text = ('Пробный ролик нового вида на YouTube: %s — %s\n\nПосмотрите с телефона: поля по краям, бегущая строка внизу, '
        'плашка Telegram только в конце.' % (link, note) if link else
        'Пробный ролик на YouTube не загрузился: %s' % (note or 'нет секретов YT_* в запуске'))
print('YTTEST', link, note, flush=True)
p = os.path.join(DAY, 'yt_test.json')
job = json.load(open(p, encoding='utf-8'))
job['messages'] = [{'to': 'owner', 'type': 'text', 'text': text}]
json.dump(job, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
