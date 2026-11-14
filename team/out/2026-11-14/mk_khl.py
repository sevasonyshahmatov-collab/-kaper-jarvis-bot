# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-14/picks_khl.json — прогнозы КХЛ на 14.11."""
import json

D = '2026-11-14'
DATE = '14 ноября'
N0 = 1
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_khl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1411-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 14 ноября</b> — 5 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет. «ВЫБОР» расчёта: Нефтехимик 1Х (56,7 %), Амур итоговая (58,2 %), Локомотив П1 (60,8 %). Спартак — Адмирал: «ВАРИАНТ» фора Адмирала +1,5, 1,85 (57,7 %, кэф выше; «ВЫБОР» был ТБ 4,5, 1,60, 59,7 %). Автомобилист — Ак Барс — замена ради разных видов ставок: «ВЫБОР» там Ак Барс не проиграет в осн. время, 1,65 (56,9 %) — тот же вид, что у Нефтехимика; взял ТБ 4,5, 1,70 (53,8 %) — ниже порога «ВЫБОР» только этот пост. Хотите по расчёту — поправьте 1411-2 на Х2 Ак Барс 1,65. Pinnacle: 1Х Нефтехимик 1,71; ТБ 4,5 — 1,77; Адмирал +1,5 — 1,79; Амур итоговая 1,64; Локомотив П1 1,60. Вратари КХЛ не подтверждены — в постах их нет. Запуск поздний: Нефтехимик (14:00) и Автомобилист (14:30) по кнопке выйдут сразу, остальные — за полтора часа до матча.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
