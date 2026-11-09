# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-09/picks_nhl.json — прогнозы НХЛ, игровой день 09.11 (ночь на 10.11), данные run 1125."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-09'
N0 = 5
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '0911-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 10 ноября</b> — 3 матча\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ сегодня не прошёл ни один матч (лучшие с кэфом от 1,6 — 56–60 %): везде самая вероятная ставка '
        'с кэфом от 1,6 по Фонбету, виды разные. Эдмонтон — итоговая 1,65 (57,2 %) вместо ТМ 6,5 1,73 (58,5 %): '
        'дома у Эдмонтона 7,4 шайбы за игру, меньше 6,5 туда не верю. '
        'Ванкувер — Филадельфия: Ванкувер не проиграет 1,63 (56,3 %), Филадельфия играет второй вечер подряд. '
        'Первый матч в 04:00 — пост выйдет в 00:00, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(i + 1, len(p['text']), len(P[i][8]))
