"""Просьба владельца 06.11 ~14:45 МСК: экспрессы только НХЛ на ночь 07.11. В линии 3 матча — в купоне по ноге с каждого,
нога не повторяется между купонами, одна фора на купон, купоны: 3 события 1,75–2,05; 3 события до 2,30; 2 события 1,75–2,05 — по убыванию шанса модели."""
import itertools, json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
by = ex.candidates(ex.parse_brief('out/picks/nhl-2026-11-06/brief.md', 'НХЛ'))
def combos(n, lo, hi):
    out = []
    for ms in itertools.combinations(list(by), n):
        for ls in itertools.product(*(by[m] for m in ms)):
            if sum(x['cat'] == 'fora' for x in ls) > 1:
                continue
            k = round(math.prod(x['kef'] for x in ls), 2)
            if lo <= k <= hi:
                out.append((math.prod(x['p'] for x in ls), k, ls))
    return sorted(out, key=lambda t: (-(1.80 <= t[1] <= 2.00), -t[0]))


lid = lambda x: (x['home'], x['bet'])
used, chosen = set(), []
# 1) 3 события 1,75–2,05; 2) 3 события до 2,30 (вилка владельца 05.11); 3) 2 события 1,75–2,05
for n, lo, hi in ((3, 1.75, 2.05), (3, 1.75, 2.30), (2, 1.75, 2.05)):
    for p, k, ls in combos(n, lo, hi):
        if any(lid(x) in used for x in ls):
            continue
        chosen.append((p, k, ls)); used |= {lid(x) for x in ls}
        break
src = json.load(open('team/out/2026-11-06/express_coupons.json'))
cs = src['coupons'][:3]
for p, k, ls in chosen:
    L = []
    for x in sorted(ls, key=lambda x: (x['date'], x['time'])):
        full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
        L.append(dict(x, bet_full=full, bet_short=short))
    cs.append(dict(size=len(L), legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4), in_target=1.80 <= k <= 2.00))
    print('%.2f  %.1f%% / %.1f%%' % (k, p * 100, 100 / k), ' | '.join('%s—%s %s %.2f (%.1f%%)' % (x['home'], x['away'], x['bet'], x['kef'], x['p'] * 100) for x in L))
src['coupons'] = cs
json.dump(src, open('team/out/2026-11-06/express_coupons.json', 'w'), ensure_ascii=False, indent=1)
