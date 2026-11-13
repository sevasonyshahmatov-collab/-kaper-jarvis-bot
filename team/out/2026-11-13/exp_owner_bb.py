"""Экспресс владельца 13.11 (скрин BetBoom 02:22 Крс; матчи 09:00/10:00 Крс = 05:00/06:00 МСК 14.11) → 1311-e5. Кэфы BetBoom, общий кэф со скрина."""
import json
D = 'team/out/2026-11-13'
LEGS = [
    ('Ванкувер', 'Рейнджерс', '05:00', 'победа Рейнджерс в основное время', 'победа Рейнджерс в осн. время', 1.78, 'win'),
    ('Вегас', 'Нэшвилл', '06:00', 'индивидуальный тотал Нэшвилла больше 1,5 в основное время', 'инд. тотал Нэшвилла больше 1,5', 1.25, 'it'),
]
legs = [dict(home=h, away=a, date='2026-11-14', time=t, league='НХЛ', p=None, bet=s, kef=k, src='BetBoom (скрин владельца)',
             cat=c, bet_full=b, bet_short=s) for h, a, t, b, s, k, c in LEGS]
K = 2.22  # как на скрине BetBoom (1,78 × 1,25 = 2,225)
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'раньше'}] * 4 + [{'size': 2, 'legs': legs, 'kef': K, 'in_target': True}]}
json.dump(cp, open(D + '/express_bb_coupons.json', 'w'), ensure_ascii=False, indent=1)
lines = ['НХЛ · 14 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>2,22</b>', '', '#нхл #экспресс #jarvibet']
msgs = {'day': '2026-11-13', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-13-bb/e5_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '1311-e5'}]}
json.dump(msgs, open(D + '/express_bb_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
