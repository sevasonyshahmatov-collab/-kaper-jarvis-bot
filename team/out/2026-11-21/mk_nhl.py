# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-21/picks_nhl.json — прогнозы НХЛ, игровой день 21.11 (ночь на 22.11 МСК)."""
import json
import os
import sys

D = '2026-11-21'
N0 = 6
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posts_nhl import P

posts, summary = [], []
for i, (h, a, date, t, bet, k, src, pr, odds, q, end, move) in enumerate(P):
    pid = '2111-%d' % (N0 + i)
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (date, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': date, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 21–22 ноября</b> — 14 матчей\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nКаролина — Эдмонтон дневной: начало сегодня в 21:00 МСК, выход поста — в 17:00. '
        'Порог «ВЫБОР» НХЛ прошёл один пост — ИТБ 2,5 Анахайма (61,6 %). Остальные 13 — ниже порога, самая вероятная '
        'ставка с кэфом от 1,6 (53–64 %; Миннесота П2 — 64,0 %, Коламбус Х2 — 61,0 %). '
        'Замены ради разных видов ставок: Бостон — Вашингтон ТМ 6,5 (55,7 %) вместо ИТБ 2,5 Вашингтона (58,4 %); '
        'Монреаль — Филадельфия Х2 за 1,75 (56,0 %) вместо итоговой Монреаля 1,62 (56,6 %; дома Монреаль 5 побед из 11, '
        'Филадельфия в прошлом сезоне выиграла у него 3 из 3); Сент-Луис — Нью-Джерси 1Х (57,2 %) вместо ИТБ 2,5 '
        'Нью-Джерси 1,60 (60,2 %); Сан-Хосе — Сиэтл ТМ 6,5 (58,3 %) вместо ИТБ 2,5 Сиэтла (59,0 %) — иначе пять инд. '
        'тоталов за ночь, а у Фонбета их нет. '
        'Кэф инд. тоталов (Питтсбург, Айлендерс, Анахайм) — Pinnacle, у Фонбета этих ставок нет. '
        'Подтверждены вратари: Суэйман (Бостон), Гибсон (Детройт) — оба упомянуты в постах; остальные стартеры не объявлены, в постах их нет.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'picks_nhl.json'), 'w'),
          ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(P):
        print(i + 1, len(p[9]), len(posts[i]['text']))
