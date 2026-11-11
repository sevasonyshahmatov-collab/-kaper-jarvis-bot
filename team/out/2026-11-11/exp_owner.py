"""Экспресс владельца 11.11 (скрин BetBoom, 00:20 по Красноярску = 20:20 МСК) → 1111-e8. Кэфы BetBoom, время МСК."""
import json, math
D = 'team/out/2026-11-11'
LEGS = [  # хозяева, гости, время МСК, ставка полностью, коротко, кэф, вид
    ('Калгари', 'Рейнджерс', '03:30', 'фора Рейнджерс +1,5', 'фора Рейнджерс +1,5', 1.25, 'fora'),
    ('Сан-Хосе', 'Питтсбург', '06:00', 'тотал матча больше 4,5 в основное время', 'тотал больше 4,5', 1.21, 'total'),
    ('Анахайм', 'Нэшвилл', '06:00', 'индивидуальный тотал Нэшвилла больше 2 в основное время',
     'инд. тотал Нэшвилла больше 2', 1.26, 'it'),
]
legs = [dict(home=h, away=a, date='2026-11-12', time=t, league='НХЛ', p=None, bet=s, kef=k, src='BetBoom (скрин владельца)',
             cat=c, bet_full=b, bet_short=s) for h, a, t, b, s, k, c in LEGS]
K = round(math.prod(l['kef'] for l in legs), 2)
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'купоны e1–e7 раньше'}] * 7 + [{'size': 3, 'legs': legs, 'kef': K, 'in_target': True}]}
json.dump(cp, open(D + '/express_owner_coupons.json', 'w'), ensure_ascii=False, indent=1)
ks = ('%.2f' % K).replace('.', ',')
lines = ['НХЛ · 12 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>%s</b>' % ks, '', '#нхл #экспресс #jarvibet']
msgs = {'day': '2026-11-11', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-11-owner/e8_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '1111-e8'}]}
json.dump(msgs, open(D + '/express_owner_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
