# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-07/picks_nhl.json — прогнозы НХЛ, игровой день 07.11 (данные: run 1014)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-07'
N0 = 7
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '0711-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 7–8 ноября</b> — 12 матчей (два дневных 7 ноября, остальные ночью)\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ (65 %, у инд. тотала и форы +1,5 — 60 %) прошли два: инд. тотал Вашингтона (63,7 %) и инд. тотал Оттавы (60,6 %), '
        'у обоих кэф Pinnacle — у Фонбета инд. тоталов нет. Остальные десять ниже порога (54–62 %): взял самую вероятную ставку с кэфом от 1,6 по Фонбету, '
        'где-то соседнюю, чтобы виды не повторялись. Монреаль — итоговая 1,87 (54,2 %) вместо ИТБ Торонто 1,62 (59,8 %). '
        'Первый матч в 20:30 — пост выйдет в 16:30, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(i + 1, len(p['text']))
