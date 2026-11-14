"""Экспресс владельца 14.11 (скрин BetBoom 17:23 Крс = 13:23 МСК; КХЛ 14.11) → 1411-e1. Кэфы BetBoom, общий кэф со скрина."""
import json
D = 'team/out/2026-11-14'
LEGS = [
    ('Автомобилист', 'Ак Барс', '14:30', 'тотал больше 4 в основное время', 'тотал больше 4', 1.40, 'total'),
    ('Спартак', 'Адмирал', '16:30', 'индивидуальный тотал Спартака больше 2 в основное время', 'инд. тотал Спартака больше 2', 1.19, 'it'),
    ('Локомотив', 'Шанхайские Драконы', '17:00', 'тотал меньше 6,5 в основное время', 'тотал меньше 6,5', 1.26, 'total'),
]
legs = [dict(home=h, away=a, date='2026-11-14', time=t, league='КХЛ', p=None, bet=s, kef=k, src='BetBoom (скрин владельца)',
             cat=c, bet_full=b, bet_short=s) for h, a, t, b, s, k, c in LEGS]
K = 2.09  # как на скрине BetBoom (1,26 × 1,19 × 1,40 = 2,099)
cp = {'coupons': [{'size': 3, 'legs': legs, 'kef': K, 'in_target': True}]}
json.dump(cp, open(D + '/express_bb_coupons.json', 'w'), ensure_ascii=False, indent=1)
lines = ['КХЛ · 14 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>2,09</b>', '', '#кхл #экспресс #jarvibet']
msgs = {'day': '2026-11-14', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-14-bb/e1_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '1411-e1'}]}
json.dump(msgs, open(D + '/express_bb_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
