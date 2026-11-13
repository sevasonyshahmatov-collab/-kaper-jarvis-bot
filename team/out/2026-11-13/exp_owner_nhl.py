"""Экспресс из двух событий НХЛ по просьбе владельца 13.11 (каждая нога — кэф выше 1,70), ночь на 14.11. Кэфы Фонбета, осн. время; данные — brief run 43491256434."""
import json, math
D = 'team/out/2026-11-13'
LEGS = [  # хозяева, гости, время МСК, ставка полностью, коротко, кэф, вероятность модели «Что заходит», вид
    ('Ванкувер', 'Рейнджерс', '05:00', 'победа Рейнджерс в основное время', 'победа Рейнджерс в осн. время', 1.77, 0.559, 'win'),
    ('Вегас', 'Нэшвилл', '06:00', 'Нэшвилл не проиграет в основное время', 'Нэшвилл не проиграет в осн. время', 1.75, 0.541, 'dc'),
]
legs = [dict(home=h, away=a, date='2026-11-14', time=t, league='НХЛ', p=p, bet=s, kef=k, src='Фонбет, осн. время',
             cat=c, bet_full=b, bet_short=s) for h, a, t, b, s, k, p, c in LEGS]
K = round(math.prod(l['kef'] for l in legs), 2)
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'купоны e1–e3 раньше'}] * 3 + [{'size': 2, 'legs': legs, 'kef': K, 'in_target': True}]}
json.dump(cp, open(D + '/express_nhl_owner_coupons.json', 'w'), ensure_ascii=False, indent=1)
ks = ('%.2f' % K).replace('.', ',')
lines = ['НХЛ · 14 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    lines += ['%d. <b>%s — %s</b>, %s МСК' % (i, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>%s</b>' % ks, '', '#нхл #экспресс #jarvibet']
msgs = {'day': '2026-11-13', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-13-owner/e4_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '1311-e4'}]}
json.dump(msgs, open(D + '/express_nhl_owner_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
