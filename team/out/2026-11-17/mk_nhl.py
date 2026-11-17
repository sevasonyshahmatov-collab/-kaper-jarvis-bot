# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-17/picks_nhl.json — прогнозы НХЛ на 15.11 (игровой день)."""
import json

D = '2026-11-17'
DATE = '18 ноября'
N0 = 6
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1711-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 18 ноября</b> — 11 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nВажно: ни одна ставка дня не прошла порог «ВЫБОР» НХЛ (65 %, инд. тотал и фора — 60 %) — все 11 постов ниже порога, '
        'взята самая вероятная ставка с кэфом от 1,6 (Флорида — Эдмонтон — соседняя по вероятности, ради разных видов ставок). '
        'Вероятности: Бостон итоговая 57,5 %, Флорида — Эдмонтон ТБ 5,5 56,1 %, ИТБ 2,5 Айлендерс 59,4 %, 1Х Филадельфия 60,9 %, ИТБ 2,5 Оттавы 59,9 %, '
        'Тампа итоговая 58,4 %, Чикаго — Торонто ТМ 6,5 58,4 %, Сент-Луис — Анахайм ТБ 5,5 63,0 %, Нэшвилл Ф+1,5 59,4 %, Даллас Х2 57,6 %, ИТБ 2,5 Сан-Хосе 59,4 %. '
        'Кэфы — Фонбет; инд. тоталов у Фонбета нет — у Айлендерс, Оттавы и Сан-Хосе кэф Pinnacle. Стартовые вратари не подтверждены — в постах никто не назван стартером.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
