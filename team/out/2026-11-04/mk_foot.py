# -*- coding: utf-8 -*-
"""Футбол 04.11: «ВЫБОР» нет ни в одном из 10 матчей (данные run 41778513660) → футбольный экспресс 0411-e4."""
import json, os
D = '2026-11-04'
H = os.path.dirname(__file__)
legs = [
    dict(home='АЕК', away='Реал Мадрид', date=D, time='20:45', league='Футбол', kef=1.20, p=0.878,
         bet_short='победа Реал Мадрида', bet_full='победа Реал Мадрида в основное время', src='Pinnacle'),
    dict(home='РБ Лейпциг', away='Манчестер Сити', date=D, time='23:00', league='Футбол', kef=1.55, p=0.679,
         bet_short='победа Манчестер Сити', bet_full='победа Манчестер Сити в основное время', src='Pinnacle'),
]
json.dump({'coupons': [{'size': 2, 'legs': legs, 'kef': 1.86}]}, open(os.path.join(H, 'express_foot_coupons.json'), 'w'),
          ensure_ascii=False, indent=1)
post = """Футбол · 4 ноября · экспресс

1. <b>АЕК — Реал Мадрид</b>, 20:45 МСК
победа Реал Мадрида в основное время · 1,20
2. <b>РБ Лейпциг — Манчестер Сити</b>, 23:00 МСК
победа Манчестер Сити в основное время · 1,55

Общий кэф: <b>1,86</b>

#футбол #экспресс #jarvibet"""
ov = """<b>Футбол — 4 ноября</b>: одиночных ставок от 60 % сегодня нет (10 матчей: 9 — Лига чемпионов, 1 — Лига Европы). Ближе всех: Славия — Арсенал, тотал больше 2,5 (1,64, 59 %).

Вместо них — экспресс из двух событий ниже: Реал Мадрид у АЕК (1,20) + Манчестер Сити в Лейпциге (1,55), общий кэф 1,86. Линии Фонбета на Лигу чемпионов нет — кэфы Pinnacle, у Фонбета могут отличаться.

Под купоном: «Опубликовать» — выйдет в канал сразу; «Редактировать»; «Не надо»."""
X = 'out/express/%s-foot/' % D
msgs = [{'to': 'owner', 'type': 'text', 'html': True, 'text': ov},
        {'to': 'owner', 'type': 'animation', 'html': True, 'files': [X + 'e1_anim.mp4'], 'text': post,
         'buttons': 'post', 'pid': '0411-e4'}]
json.dump({'day': D, 'make': ['team/picks/express_render.py team/out/%s/express_foot_coupons.json %s' % (D, X.rstrip('/'))],
           'messages': msgs}, open(os.path.join(H, 'express_foot.json'), 'w'), ensure_ascii=False, indent=1)
