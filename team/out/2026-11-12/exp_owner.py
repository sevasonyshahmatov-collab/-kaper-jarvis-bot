"""Экспресс владельца 12.11 (скрин BetBoom, ставка 01:15 по Красноярску = 21:15 МСК, матчи 07:00 Крс = 03:00 МСК) → 1211-e4. Кэфы BetBoom, время МСК."""
import json, math
D = 'team/out/2026-11-12'
LEGS = [  # хозяева, гости, время МСК, ставка полностью, коротко, кэф, вид
    ('Торонто', 'Миннесота', '03:00', 'фора Миннесоты +1,5 в основное время', 'фора Миннесоты +1,5', 1.21, 'fora'),
    ('Бостон', 'Монреаль', '03:00', 'индивидуальный тотал Бостона больше 1,5 в основное время', 'инд. тотал Бостона больше 1,5', 1.16, 'it'),
    ('Оттава', 'Колорадо', '03:00', 'тотал матча больше 4,5 в основное время', 'тотал больше 4,5', 1.30, 'total'),
]
legs = [dict(home=h, away=a, date='2026-11-13', time=t, league='НХЛ', p=None, bet=s, kef=k, src='BetBoom (скрин владельца)',
             cat=c, bet_full=b, bet_short=s) for h, a, t, b, s, k, c in LEGS]
K = round(math.prod(l['kef'] for l in legs), 2)
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'купоны e1–e3 раньше'}] * 3 + [{'size': 3, 'legs': legs, 'kef': K, 'in_target': True}]}
json.dump(cp, open(D + '/express_owner_coupons.json', 'w'), ensure_ascii=False, indent=1)
ks = ('%.2f' % K).replace('.', ',')
lines = ['НХЛ · 13 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>%s</b>' % ks, '', '#нхл #экспресс #jarvibet']
msgs = {'day': '2026-11-12', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-12-owner/e4_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '1211-e4'}]}
json.dump(msgs, open(D + '/express_owner_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
