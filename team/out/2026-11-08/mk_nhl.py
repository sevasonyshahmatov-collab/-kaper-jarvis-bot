# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-08/picks_nhl.json — прогнозы НХЛ, игровой день 07.11 (данные: run 1065)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-08'
N0 = 10
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '0811-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 8–9 ноября</b> — 6 матчей (два вечером 8 ноября, остальные ночью)\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ сегодня не прошёл ни один матч (лучшие 55–61 %): везде взял самую вероятную ставку с кэфом от 1,6 по Фонбету, '
        'Бостон — итоговая 1,72 (59,1 %) вместо ТМ 6,5 1,60 (61,3 %), чтобы не было трёх «меньше 6,5». '
        'Калгари — Филадельфия: ИТБ 2,5 Калгари 1,77 (52,0 %, кэф Pinnacle — у Фонбета инд. тоталов нет) вместо ИТБ Филадельфии 1,71 (54,2 %): '
        'Филадельфия в гостях забивает 1,62, Калгари дома 3,22. '
        'Первый матч в 21:00 — пост выйдет в 17:00, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(i + 1, len(p['text']))
