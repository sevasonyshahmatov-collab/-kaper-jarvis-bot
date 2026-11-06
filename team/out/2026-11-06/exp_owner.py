"""Экспресс владельца 06.11 (скрин BetBoom, 01:54 по Красноярску = 21:54 МСК) → 0611-e7. Кэфы BetBoom, время МСК
(на скрине — красноярское, +4 ч)."""
import json
D = 'team/out/2026-11-06'
LEGS = [  # хозяева, гости, время МСК, ставка полностью, коротко, кэф, вид
    ('Баффало', 'Коламбус', '03:00', 'фора Баффало +1,5', 'Ф1(+1,5) Баффало', 1.21, 'fora'),
    ('Калгари', 'Анахайм', '04:00', 'фора Анахайма +2,5', 'Ф2(+2,5) Анахайм', 1.25, 'fora'),
    ('Миннесота', 'Сан-Хосе', '04:00', 'индивидуальный тотал Миннесоты больше 2,5 в основное время',
     'ИТБ 2,5 Миннесота в осн. время', 1.29, 'it'),
]
legs = [dict(home=h, away=a, date='2026-11-07', time=t, league='НХЛ', p=None, bet=s, kef=k, src='BetBoom (скрин владельца)',
             cat=c, bet_full=b, bet_short=b if c == 'fora' else 'инд. тотал Миннесоты больше 2,5')
        for h, a, t, b, s, k, c in LEGS]
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'купоны e1–e6 раньше'}] * 6 + [{'size': 3, 'legs': legs, 'kef': 1.95, 'in_target': True}]}
json.dump(cp, open(D + '/express_owner_coupons.json', 'w'), ensure_ascii=False, indent=1)
lines = ['НХЛ · 7 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>1,95</b>', '', '#нхл #экспресс #jarvibet']
msgs = {'day': '2026-11-06', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-06-owner/e7_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '0611-e7'}]}
json.dump(msgs, open(D + '/express_owner_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
