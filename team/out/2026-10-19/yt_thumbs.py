# -*- coding: utf-8 -*-
"""Обложки роликам, которые конвейер загрузил ночью 19.10 (владелец 19.10). ID — из логов reels-daily, run 16/17.
Обложки — docs/channel/vk/covers_1910 (render/vk_covers.py). Итог — сообщением владельцу (задание перечитывается)."""
import json
import os
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(DAY)))
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
import youtube  # noqa: E402

C = os.path.join(ROOT, 'docs', 'channel', 'vk', 'covers_1910')
VIDEOS = [('5q85ZKDKnNo', 'Рейнджерс — Анахайм', '05_nhl_Рейнджерс.jpg'),
          ('vRa5Qq5r7DU', 'Филадельфия — Колорадо', '06_nhl_Филадельфия.jpg'),
          ('eJ-6jjJ8Xsw', 'Торонто — Сан-Хосе', '07_nhl_Торонто.jpg'),
          ('7WmzjGaEkJ8', 'Юта — Питтсбург', '08_nhl_Юта.jpg'),
          ('AAFfuRoOpMw', 'Сочи — Шанхайские Драконы', '04_khl_Сочи.jpg')]
lines = []
for vid, name, f in VIDEOS:
    note = youtube.thumbnail('https://youtu.be/' + vid, os.path.join(C, f))
    lines.append('%s %s — %s' % ('✅' if not note else '⚠️', name, note or 'обложка стоит'))
p = os.path.join(DAY, 'yt_thumbs.json')
job = json.load(open(p, encoding='utf-8'))
job['messages'] = [{'to': 'owner', 'type': 'text', 'text': 'Обложки на YouTube (ролики ночи 19.10):\n' + '\n'.join(lines)}]
json.dump(job, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(lines), flush=True)
