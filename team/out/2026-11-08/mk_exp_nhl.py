"""Просьба владельца 08.11 ~20:15 МСК: экспрессы только НХЛ на ночь 09.11 (по образцу 2026-11-06/mk_exp_nhl.py) + купон владельца.
Бостон — Флорида (21:00) не берём: не успеть опубликовать. Нога не повторяется между купонами, одна фора на купон."""
import itertools, json, math, sys
sys.path.insert(0, 'team/picks')
import express as ex
D = 'team/out/2026-11-08'
by = {m: v for m, v in ex.candidates(ex.parse_brief('out/picks/nhl-2026-11-08/brief.md', 'НХЛ')).items() if m[0] != 'Бостон'}
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
for n, lo, hi in ((3, 1.75, 2.05), (3, 1.75, 2.05), (3, 1.75, 2.30)):
    for p, k, ls in combos(n, lo, hi):
        if any(lid(x) in used for x in ls):
            continue
        chosen.append((p, k, ls)); used |= {lid(x) for x in ls}
        break
cs = []
for p, k, ls in chosen:
    L = []
    for x in sorted(ls, key=lambda x: (x['date'], x['time'])):
        full, short = ex.human(x['bet'], x['home'], x['away'], x['league'])
        L.append(dict(x, bet_full=full, bet_short=short))
    cs.append(dict(size=len(L), legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4), in_target=1.80 <= k <= 2.00))
    print('%.2f  %.1f%% / %.1f%%' % (k, p * 100, 100 / k), ' | '.join('%s—%s %s %s %.2f (%.1f%%)' % (x['home'], x['away'], x['time'], x['bet'], x['kef'], x['p'] * 100) for x in L))
# купон владельца
json.dump({'coupons': cs}, open(D + '/express_nhl_coupons.json', 'w'), ensure_ascii=False, indent=1)
OWN = [('Виннипег', 'Тампа-Бэй', '02:00', 'Ф2(+1,5) Тампа-Бэй', 1.25), ('Калгари', 'Филадельфия', '03:00', 'Ф1(+2,5) Калгари', 1.16),
       ('Анахайм', 'Питтсбург', '04:00', 'ТБ 4,5 в осн. время', 1.19)]       # кэфы Фонбета из brief.md
L = []
for h, a, t, b, k in OWN:
    full, short = ex.human(b, h, a, 'НХЛ')
    L.append(dict(home=h, away=a, date='2026-11-09', time=t, league='НХЛ', bet=b, kef=k, cat='own', bet_full=full, bet_short=short))
cs.append(dict(size=3, legs=L, kef=round(math.prod(x['kef'] for x in L), 2), note='купон владельца'))
json.dump({'coupons': cs}, open(D + '/express_nhl_coupons.json', 'w'), ensure_ascii=False, indent=1)
msgs = []
for i, c in enumerate(cs, 1):
    t = ['НХЛ · 9 ноября · экспресс', '']
    for j, l in enumerate(c['legs'], 1):
        t += ['%d. <b>%s — %s</b>, %s МСК' % (j, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
    t += ['', 'Общий кэф: <b>%s</b>' % ('%.2f' % c['kef']).replace('.', ','), '', '#нхл #экспресс #jarvibet']
    msgs.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/express/2026-11-08-nhl/e%d_anim.mp4' % i],
                 'text': '\n'.join(t), 'buttons': 'post', 'pid': '0811-e%d' % (5 + i)})
    print('\n'.join(t)); print('---')
json.dump({'day': '2026-11-08', 'make': ['team/picks/express_render.py team/out/2026-11-08/express_nhl_coupons.json out/express/2026-11-08-nhl'],
           'messages': [{'to': 'owner', 'type': 'text', 'text': 'Экспрессы НХЛ на ночь 9 ноября: три купона по модели (Бостон — Флорида не брал, старт в 21:00) и последний — твой: Тампа +1,5, Калгари +2,5, Анахайм — Питтсбург тотал больше 4,5. Кэфы Фонбета.'}] + msgs},
          open(D + '/express_nhl.json', 'w'), ensure_ascii=False, indent=1)
