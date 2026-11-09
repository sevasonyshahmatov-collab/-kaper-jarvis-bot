# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-09/picks_khl.json — прогнозы КХЛ на 08.11 (данные: run 1097)."""
import json

D = '2026-11-09'
DATE = '9 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '0911-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 9 ноября</b> — 4 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nТри поста — «ВЫБОР» расчёта: Торпедо Х2 (63,8 %), Северсталь П1 (61,1 %), ЦСКА — Сибирь ТМ 5,5 (66,2 %). В СКА — Спартак «ВЫБОР» был «Спартак не проиграет в осн. время» (63,6 %, 1,60) — второй Х2 за день, поэтому взял ТБ 4,5 (58,3 %, 1,62): ниже порога «ВЫБОР», в посте без пометок. Кэфы — Фонбет (Pinnacle 1,50 · 1,60 · — · 1,70; на ТМ 5,5 в ЦСКА у Pinnacle нет). Все матчи в 19:00–19:30 — посты выйдут с 17:30.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
