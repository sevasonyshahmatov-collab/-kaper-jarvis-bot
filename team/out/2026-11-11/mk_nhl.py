# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-11/picks_nhl.json — прогнозы НХЛ, игровой день 11.11 (ночь на 12.11), данные run 1191."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-11'
N0 = 4
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '1111-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 12 ноября</b> — 6 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошли два матча: Филадельфия фора +1,5 (60,2 %, 1,65) и Сан-Хосе ИТБ 2,5 (60,6 %, 1,62 — Pinnacle, у Фонбета инд. тоталов нет). '
        'Остальные 4 ниже порога (56–61 %): самая вероятная ставка с кэфом от 1,6 по Фонбету. '
        'Баффало — Тампа: ТМ 6,5 1,73 (57,1 %) вместо ИТБ Баффало 1,65 (57,7 %, только Pinnacle). '
        'Анахайм — Нэшвилл: у Pinnacle линии нет — вероятность без смеси с линией, кэф Фонбета; инд. тотала Нэшвилла (как вы правили вчера) в линии нет. '
        'Вратари всех шести матчей пока не подтверждены — в постах стартерами никого не называю. '
        'Первый матч в 03:00 — пост выйдет в 23:00, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(i + 1, len(p['text']), len(P[i][8]))
