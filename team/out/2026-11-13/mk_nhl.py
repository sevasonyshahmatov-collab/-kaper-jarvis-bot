# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-13/picks_nhl.json — прогнозы НХЛ, игровой день 13.11 (ночь на 14.11), данные run 1268."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-13'
N0 = 4
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '1311-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 13 ноября</b> — 2 матча (ночь на 14.11, в линии только два)\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошла одна ставка: фора Нэшвилла +1,5 (62,1 %, 1,60; Pinnacle 1,61). '
        'Ванкувер — Рейнджерс ниже порога: самая вероятная с кэфом от 1,6 — ТМ 6,5 1,67 (58,0 %), но у Ванкувера в среднем 7 шайб за матч, '
        'взял П2 Рейнджерс в осн. время 1,77 (56,1 %; Pinnacle 1,75) — все 11 побед Рейнджерс в основное время. '
        'Вратари без статуса, стартерами никого не называю.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(p['pid'], len(p['text']), len(P[i][8]))
