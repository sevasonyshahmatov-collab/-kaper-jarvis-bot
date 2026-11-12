# -*- coding: utf-8 -*-
"""Собирает team/out/2026-11-12/picks_nhl.json — прогнозы НХЛ, игровой день 12.11 (ночь на 13.11), данные run 1227."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from posts_nhl import P

D = '2026-11-12'
N0 = 6
posts, summary = [], []
for i, (h, a, dt, t, bet, k, pr, odds, q, end) in enumerate(P):
    text = ('НХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#нхл #прогноз #jarvibet') % (dt, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/nhl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': '1211-%d' % (N0 + i),
                  'vs': {'league': 'NHL', 'home': h, 'away': a, 'date': dt, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы НХЛ на 12 ноября</b> — 11 матчей (первый сегодня в 20:00 в Хельсинки, остальные ночью)\n\n' + '\n'.join(summary) +
        '\n\nПод каждым постом: «Опубликовать» — выйдет в канал за 4 часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nПорог «ВЫБОР» НХЛ прошли два: ИТБ Бостона 2,5 (60,9 %) и ИТБ Колорадо 2,5 (60,2 %) — кэфы 1,61 Pinnacle, у Фонбета инд. тоталов нет. '
        'Остальные 9 ниже порога (52–63 %): самая вероятная ставка с кэфом от 1,6 по Фонбету. '
        'Замены ради разных ставок: Флорида — Детройт ТБ 5,5 1,75 (57,5 %) вместо итоговой Флориды 1,60 (57,8 %); '
        'Чикаго 1Х 1,68 (57,4 %) вместо ТМ 6,5 1,65 (59,6 %). '
        'Даллас — Виннипег: итоговая Далласа 1,58 ниже 1,6, взял ИТМ Виннипега 2,5 1,77 (52,4 %, Pinnacle) — самый слабый пост дня. '
        'У Pinnacle нет линии на Коламбус — Тампа, Чикаго — Баффало, Юта — Сент-Луис: вероятность без смеси с линией, кэф Фонбета. '
        'Подтверждён только вратарь Монреаля (Фаулер), остальных стартерами не называю. '
        'Сиэтл — Каролина в 20:00 — пост выйдет в 16:00, если нажать до этого.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_nhl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    for i, p in enumerate(posts):
        print(p['pid'], len(p['text']), len(P[i][8]))
