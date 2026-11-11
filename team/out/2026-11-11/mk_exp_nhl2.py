"""Просьба владельца 11.11 ~18:40 МСК: варианты экспрессов НХЛ на ночь 12.11, общий кэф 1,90-2,10, самые вероятные
по модели (brief run 1191, кэфы Фонбет). Купоны делят не больше одной ноги; не больше одной форы."""
import json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
D = 'team/out/2026-11-11'
by = ex.candidates(ex.parse_brief('out/picks/nhl-2026-11-11/brief.md', 'НХЛ'))
leg = {x['bet']: x for v in by.values() for x in v}
leg.update({x['bet'] + '@' + x['home']: x for v in by.values() for x in v})
PICK = [['ТБ 4,5 в осн. время@Сан-Хосе', 'ИТБ 1,5 Юта в осн. время', 'Ф2(+1,5) Тампа-Бэй'],
        ['ТБ 4,5 в осн. время@Сан-Хосе', 'ТБ 4,5 в осн. время@Вегас', 'ТБ 4,5 в осн. время@Анахайм'],
        ['ИТБ 1,5 Юта в осн. время', 'ТБ 4,5 в осн. время@Анахайм', 'ТБ 4,5 в осн. время@Баффало'],
        ['ТБ 4,5 в осн. время@Сан-Хосе', 'Ф2(+2,5) Нэшвилл', 'ИТБ 1,5 Калгари в осн. время']]
cs, msgs = [], []
for i, bets in enumerate(PICK, 1):
    L = []
    for x in sorted((leg[b] for b in bets), key=lambda x: (x['date'], x['time'])):
        full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
        L.append(dict(x, bet_full=full, bet_short=short))
    k = round(math.prod(x['kef'] for x in L), 2); p = math.prod(x['p'] for x in L)
    cs.append(dict(size=3, legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4)))
    t = ['НХЛ · 12 ноября · экспресс', '']
    for j, l in enumerate(L, 1):
        t += ['%d. <b>%s — %s</b>, %s МСК' % (j, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
    t += ['', 'Общий кэф: <b>%s</b>' % ('%.2f' % k).replace('.', ','), '', '#нхл #экспресс #jarvibet']
    msgs.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/express/2026-11-11-nhl2/e%d_anim.mp4' % i],
                 'text': '\n'.join(t), 'buttons': 'post', 'pid': '1111-e%d' % (3 + i)})
    print(k, '%.1f%%' % (p * 100)); print('\n'.join(t)); print('---')
json.dump({'coupons': cs}, open(D + '/express_nhl2_coupons.json', 'w'), ensure_ascii=False, indent=1)
json.dump({'day': '2026-11-11', 'make': ['team/picks/express_render.py team/out/2026-11-11/express_nhl2_coupons.json out/express/2026-11-11-nhl2'],
           'messages': msgs}, open(D + '/express_nhl2.json', 'w'), ensure_ascii=False, indent=1)
