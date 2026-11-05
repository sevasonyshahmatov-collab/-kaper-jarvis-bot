"""Просьба владельца 05.11 ~20:00 МСК: 5 «уверенных» экспрессов НХЛ (матчи ночью 06.11) по 3 события, кэф 1,80–2,30.
В НХЛ дня 11 матчей, на 15 ног матчи повторяются: одна и та же нога — не больше одного раза, матч — не больше чем в 2 купонах,
у двух купонов общий — не больше одного матча; в купоне одна фора. Среди подходящих — наибольшее произведение вероятностей."""
import itertools, json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
legs = ex.parse_brief('out/picks/nhl-2026-11-05/brief.md', 'НХЛ')
by = ex.candidates(legs)
allc = []
for ms in itertools.combinations(list(by), 3):
    for ls in itertools.product(*(by[k] for k in ms)):
        if sum(x['cat'] == 'fora' for x in ls) > 1:
            continue
        k = round(math.prod(x['kef'] for x in ls), 2)
        if 1.80 <= k <= 2.30:
            allc.append((math.prod(x['p'] for x in ls), k, ls))
allc.sort(key=lambda t: -t[0])
lid = lambda x: (x['home'], x['bet'])
used_leg, mcount, chosen = set(), {}, []
for p, k, ls in allc:
    ms = {(x['home'], x['away']) for x in ls}
    if any(lid(x) in used_leg for x in ls) or any(mcount.get(m, 0) >= 2 for m in ms):
        continue
    if any(len(ms & c[3]) > 1 for c in chosen):
        continue
    chosen.append((p, k, ls, ms))
    used_leg |= {lid(x) for x in ls}
    for m in ms:
        mcount[m] = mcount.get(m, 0) + 1
    if len(chosen) == 5:
        break
src = json.load(open('team/out/2026-11-05/express_coupons.json'))
cs = src['coupons'][:3]
own = json.load(open('team/out/2026-11-05/express_owner_coupons.json'))['coupons'][3]
cs.append(own)
for p, k, ls, _ in chosen:
    L = []
    for x in sorted(ls, key=lambda x: (x['date'], x['time'])):
        full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
        L.append(dict(x, bet_full=full, bet_short=short))
    cs.append(dict(size=3, legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4), in_target=True))
    print('%.2f  %.1f%% / %.1f%%' % (k, p * 100, 100 / k), ' | '.join('%s—%s %s %.2f (%.1f%%)' % (x['home'], x['away'], x['bet'], x['kef'], x['p'] * 100) for x in L))
src['coupons'] = cs
json.dump(src, open('team/out/2026-11-05/express_coupons.json', 'w'), ensure_ascii=False, indent=1)
