# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-19/picks_nhl.json — прогнозы НХЛ на 19.11 (игровой день)."""
import json

D = '2026-11-19'
DATE = '20 ноября'
N0 = 4
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '1911-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на ночь на 20 ноября</b> — 12 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошли три поста: ИТБ 2,5 Лос-Анджелеса (60,1 %), фора Филадельфии +1,5 (62,3 %), ИТБ 2,5 Баффало (60,2 %). '
        'Остальные девять — ниже порога, самая вероятная ставка с кэфом от 1,6 (55–62 %). '
        'Питтсбург — Сент-Луис: «ВЫБОР» был ИТБ 2,5 Сент-Луиса (60,4 %), взял ТБ 5,5 (59,5 %) — иначе три инд. тотала за ночь, а у Фонбета их нет. '
        'Чикаго 1Х (55,2 %) вместо итоговой Коламбуса (56,4 %), Калгари — Миннесота П2 за 1,80 (56,8 %) вместо ТБ 5,5 (57,1 %), Колорадо — Анахайм Х2 (55,3 %) вместо итоговой Колорадо (55,8 %) — ради разных видов ставок. '
        'Кэф инд. тоталов — Pinnacle (у Фонбета нет). У Каролины — Монреаля и Колорадо — Анахайма нет линии Pinnacle: вероятность по модели и Фонбету. '
        'Монреаль и Колорадо играют второй вечер подряд; у Монреаля подтверждён Добеш (85,2 % отражённых).')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
        print(i + 1, len(q), len(posts[i]['text']))
