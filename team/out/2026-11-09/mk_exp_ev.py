"""Просьба владельца 09.11 ~18:30 МСК: варианты экспрессов отдельно НХЛ (ночь на 10.11) и КХЛ (вечер 09.11), общий кэф 1,85–2,20.
Купон — 2–3 события из разных матчей, нога не повторяется между купонами лиги, одна фора на купон, по убыванию шанса модели."""
import itertools, json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
D = 'team/out/2026-11-09'
def build(brief, lg, n_coupons=3):
    by = ex.candidates(ex.parse_brief(brief, lg))
    def combos(n):
        out = []
        for ms in itertools.combinations(list(by), n):
            for ls in itertools.product(*(by[m] for m in ms)):
                if sum(x['cat'] == 'fora' for x in ls) > 1:
                    continue
                k = round(math.prod(x['kef'] for x in ls), 2)
                if 1.85 <= k <= 2.20:
                    out.append((math.prod(x['p'] for x in ls), k, ls))
        return sorted(out, key=lambda t: -t[0])
    pool = sorted(combos(3) + combos(2), key=lambda t: -t[0])
    used, res = set(), []
    for p, k, ls in pool:
        if len(res) >= n_coupons:
            break
        if any((x['home'], x['bet']) in used for x in ls):
            continue
        used |= {(x['home'], x['bet']) for x in ls}
        L = []
        for x in sorted(ls, key=lambda x: (x['date'], x['time'])):
            full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
            L.append(dict(x, bet_full=full, bet_short=short))
        res.append(dict(size=len(L), legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4)))
        print(lg, '%.2f  %.1f%% / %.1f%%' % (k, p * 100, 100 / k), ' | '.join('%s %s—%s %s %.2f (%.1f%%)' % (x['time'], x['home'], x['away'], x['bet'], x['kef'], x['p'] * 100) for x in L))
    return res
khl = build('out/picks/khl-2026-11-09/brief.md', 'КХЛ')
nhl = build('out/picks/nhl-2026-11-09/brief.md', 'НХЛ')
cs = khl + nhl
json.dump({'coupons': cs}, open(D + '/express_ev_coupons.json', 'w'), ensure_ascii=False, indent=1)
RU = {11: 'ноября'}
msgs = []
for i, c in enumerate(cs, 1):
    lg = c['legs'][0]['league']
    d = max(l['date'] for l in c['legs'])
    t = ['%s · %d %s · экспресс' % (lg, int(d[8:]), RU[int(d[5:7])]), '']
    for j, l in enumerate(c['legs'], 1):
        t += ['%d. <b>%s — %s</b>, %s МСК' % (j, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
    t += ['', 'Общий кэф: <b>%s</b>' % ('%.2f' % c['kef']).replace('.', ','), '', '#%s #экспресс #jarvibet' % ('кхл' if lg == 'КХЛ' else 'нхл')]
    msgs.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/express/2026-11-09-ev/e%d_anim.mp4' % i],
                 'text': '\n'.join(t), 'buttons': 'post', 'pid': '0911-e%d' % (2 + i)})
note = 'Экспрессы, кэф 1,85–2,20: КХЛ — %d (матчи 19:00–19:30, публиковать сразу), НХЛ на ночь — %d. Кэфы Фонбета утренние, сверь.' % (len(khl), len(nhl))
json.dump({'day': '2026-11-09', 'make': ['team/picks/express_render.py team/out/2026-11-09/express_ev_coupons.json out/express/2026-11-09-ev'],
           'messages': [{'to': 'owner', 'type': 'text', 'text': note}] + msgs}, open(D + '/express_ev.json', 'w'), ensure_ascii=False, indent=1)
