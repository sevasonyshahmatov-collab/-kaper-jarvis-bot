# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-20/picks_khl.json — прогнозы КХЛ на 19.11."""
import json

D = '2026-11-20'
DATE = '20 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '2011-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 20 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет, у всех пяти матчей есть линии Фонбета и Pinnacle. Все ставки — «ВЫБОР» расчёта или равные ему по вероятности, ниже порога — 0. Вероятности: итоговая Автомобилиста — 57,4 % (Pinnacle 1,66); фора Барыса +1,5 — 64,7 % (Pinnacle 1,60); Торпедо 1Х — 58,8 % (Pinnacle 1,72); Амур Х2 — 55,3 % (Pinnacle 1,71); ТМ 5,5 Шанхай — ЦСКА — 64,0 % (Pinnacle 1,57). Сибирь — Автомобилист: «ВЫБОР» был ТБ 4,5 за 1,68 (57,4 %), взял итоговую Автомобилиста 1,65 — та же вероятность, модель за неё увереннее (56,9 против 52,5 %), и вид ставки не повторяет ТМ в Шанхае. Два двойных шанса (Торпедо на хозяев, Амур на гостей) — ставки другого вида там на 4 п. п. ниже (ТМ 4,5 за 2,00 и 1,95), оставил «ВЫБОР». Самые уверенные — фора Барыса и ТМ 5,5 в матче Шанхай — ЦСКА. Вратари КХЛ не подтверждены — в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
