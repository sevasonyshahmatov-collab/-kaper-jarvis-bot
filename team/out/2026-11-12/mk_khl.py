# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-12/picks_khl.json — прогнозы КХЛ на 12.11."""
import json

D = '2026-11-12'
DATE = '12 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1211-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 12 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВсе пять — «ВЫБОР» расчёта (от 56,5 до 65,3 %), ниже порога нет. Кэфы — Фонбет (Pinnacle: Металлург ТБ 4,5 — 1,64; Автомобилист — 1,59; Ак Барс Х2 — 1,69; Барыс — 1,53; Амур +1,5 — 1,53). Две итоговые победы хозяев (Автомобилист, Барыс): в Барыс — Адмирал другой ставки того же уровня с кэфом от 1,6 не было, запасной вариант — Адмирал не проиграет в осн. время, 1,80 (54,7 %). Вратари КХЛ заранее не подтверждены — в постах их нет. Выход: три матча в 17:00 — посты в 15:30, Барыс в 17:30 — в 16:00, Спартак в 19:30 — в 18:00.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
