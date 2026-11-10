# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-10/picks_khl.json — прогнозы КХЛ на 10.11."""
import json

D = '2026-11-10'
DATE = '10 ноября'
N0 = 13
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1011-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 10 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nДва поста — «ВЫБОР» расчёта: Трактор — Драконы ТБ 4,5 (60,0 %), Динамо Минск 1Х (61,6 %). В Нефтехимик — Салават «ВЫБОР» был «Салават не проиграет в осн. время» (62,3 %, 1,63) — второй двойной шанс за день, поэтому взял ТМ 5,5 (57,8 %, 1,70): ниже порога «ВЫБОР», в посте без пометок. Кэфы — Фонбет; линии Pinnacle сегодня нет ни на один матч (ошибка доступа), вероятность — по модели и линии Фонбета. Трактор — Драконы в 17:00 (пост выйдет в 15:30), остальные — с 17:40.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
