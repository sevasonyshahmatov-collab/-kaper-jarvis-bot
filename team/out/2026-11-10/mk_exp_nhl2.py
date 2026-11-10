"""Просьба владельца 10.11 ~14:30 МСК: экспрессы на ночные матчи НХЛ 11.11 (brief run 1168). Ноги не повторяют
утренние купоны 1011-e1/e2 и друг друга; не больше одной форы в купоне."""
import json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
D = 'team/out/2026-11-10'
by = ex.candidates(ex.parse_brief('out/picks/nhl-2026-11-10/brief.md', 'НХЛ'))
leg = {x['bet']: x for v in by.values() for x in v}
leg.update({x['bet'] + '@' + x['home']: x for v in by.values() for x in v})
PICK = [['ИТБ 1,5 Торонто в осн. время', 'ИТБ 1,5 Коламбус в осн. время', 'Ф2(+1,5) Нью-Джерси'],
        ['ТБ 4,5 в осн. время@Оттава', 'ИТБ 1,5 Детройт в осн. время', 'Ф2(+2,5) Нэшвилл']]
cs, msgs = [], []
for i, bets in enumerate(PICK, 1):
    L = []
    for x in sorted((leg[b] for b in bets), key=lambda x: (x['date'], x['time'])):
        full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
        L.append(dict(x, bet_full=full, bet_short=short))
    k = round(math.prod(x['kef'] for x in L), 2); p = math.prod(x['p'] for x in L)
    cs.append(dict(size=3, legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4)))
    t = ['НХЛ · 11 ноября · экспресс', '']
    for j, l in enumerate(L, 1):
        t += ['%d. <b>%s — %s</b>, %s МСК' % (j, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
    t += ['', 'Общий кэф: <b>%s</b>' % ('%.2f' % k).replace('.', ','), '', '#нхл #экспресс #jarvibet']
    msgs.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/express/2026-11-10-nhl2/e%d_anim.mp4' % i],
                 'text': '\n'.join(t), 'buttons': 'post', 'pid': '1011-e%d' % (2 + i)})
    print(k, '%.1f%%' % (p * 100)); print('\n'.join(t)); print('---')
json.dump({'coupons': cs}, open(D + '/express_nhl2_coupons.json', 'w'), ensure_ascii=False, indent=1)
json.dump({'day': '2026-11-10', 'make': ['team/picks/express_render.py team/out/2026-11-10/express_nhl2_coupons.json out/express/2026-11-10-nhl2'],
           'messages': msgs}, open(D + '/express_nhl2.json', 'w'), ensure_ascii=False, indent=1)
