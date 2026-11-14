# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-14/picks_nhl.json — прогнозы НХЛ, игровой день 14.11 (ночь на 15.11), данные run 1287."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-14'
N0 = 6
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '1411-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 14 ноября</b> — 14 матчей (ночь на 15.11; Каролина — Сиэтл в Хельсинки — сегодня в 21:00)\n\n'
        + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКэфы — Фонбет; инд. тоталы (Миннесота, Колорадо, Нью-Джерси, Калгари) — Pinnacle, у Фонбета их нет. '
        'Порог «ВЫБОР» НХЛ прошла одна ставка: ИТБ 2,5 Колорадо (60,4 %). Остальные 13 — ниже порога, взята самая вероятная '
        'с кэфом от 1,6 (55–62 %; Анахайм — Айлендерс и Лос-Анджелес — Калгари слабее всего, ~52 %). '
        'Ради разных видов ставок заменил: Тампа-Бэй — Детройт фора Детройта +1,5 вместо ТБ 5,5 (57,2 против 57,9 %), Питтсбург — Оттава ТМ 6,5 вместо ТБ 5,5 (57,8 против 60,2 %), '
        'Сент-Луис — Флорида ТБ 5,5 вместо ИТБ Флориды (55,9 против 57,2 %), Анахайм — Айлендерс ТМ 6,5 вместо итоговой Анахайма '
        '(51,8 против 52,1 %). Вашингтон — Нью-Джерси: ИТБ Нью-Джерси 62,5 % — выше порога инд. тотала, но расчёт не пометил «ВЫБОР» (кэф ровно 1,60). '
        'Вратари без статуса — стартерами никого не называю.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(p['pid'], len(p['text']), len(P[i][8]))
