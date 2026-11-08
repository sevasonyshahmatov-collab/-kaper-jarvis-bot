"""Просьба владельца 08.11 ~20:30 МСК: футбольные экспрессы на матчи, которые ещё не начались (Хоффенхайм 21:30, Фиорентина и Ланс
22:45, Атлетико 23:00). Ноги — самые вероятные исходы модели (FDPROB, run 42450362675), кэф — Фонбет (FDFON утром), купон 2 события от 1,80."""
import json, math
D = 'team/out/2026-11-08'
def leg(h, a, t, short, full, k, p):
    return dict(home=h, away=a, date='2026-11-08', time=t, league='Футбол', kef=k, p=p, bet_short=short, bet_full=full)
ATL = ('Атлетико', 'Барселона', '23:00'); FIO = ('Фиорентина', 'Ювентус', '22:45')
HOF = ('Хоффенхайм', 'Шальке', '21:30'); LEN = ('Ланс', 'Марсель', '22:45')
CS = [[leg(*HOF, 'тотал больше 2,5', 'тотал матча больше 2,5', 1.53, .648), leg(*FIO, 'Х2', 'двойной шанс Х2 (Ювентус не проиграет)', 1.32, .725)],
      [leg(*FIO, 'тотал меньше 3,5', 'тотал матча меньше 3,5', 1.40, .710), leg(*ATL, 'тотал больше 2,5', 'тотал матча больше 2,5', 1.35, .737)],
      [leg(*LEN, '1Х', 'двойной шанс 1Х (Ланс не проиграет)', 1.42, .659), leg(*ATL, 'Х2', 'двойной шанс Х2 (Барселона не проиграет)', 1.35, .712)]]
cs, msgs = [], []
for i, L in enumerate(CS, 1):
    k = round(math.prod(x['kef'] for x in L), 2)
    cs.append(dict(size=len(L), legs=L, kef=k, p=round(math.prod(x['p'] for x in L), 4)))
    t = ['Футбол · 8 ноября · экспресс', '']
    for j, l in enumerate(L, 1):
        t += ['%d. <b>%s — %s</b>, %s МСК' % (j, l['home'], l['away'], l['time']), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
    t += ['', 'Общий кэф: <b>%s</b>' % ('%.2f' % k).replace('.', ','), '', '#футбол #экспресс #jarvibet']
    msgs.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/express/2026-11-08-foot/e%d_anim.mp4' % i],
                 'text': '\n'.join(t), 'buttons': 'post', 'pid': '0811-e%d' % (9 + i)})
    print(k, '%.1f%%' % (cs[-1]['p'] * 100), ' | '.join('%s—%s %s %.2f' % (l['home'], l['away'], l['bet_short'], l['kef']) for l in L))
json.dump({'coupons': cs}, open(D + '/express_foot_coupons.json', 'w'), ensure_ascii=False, indent=1)
note = ('Футбольные экспрессы на матчи, которые ещё не начались (Хоффенхайм — Шальке 21:30, Фиорентина — Ювентус и Ланс — Марсель 22:45, '
        'Атлетико — Барселона 23:00). Кэфы Фонбета на утро — сверь перед публикацией, мог сдвинуться. Первый — с Хоффенхаймом, публиковать до 21:30.')
json.dump({'day': '2026-11-08', 'make': ['team/picks/express_render.py team/out/2026-11-08/express_foot_coupons.json out/express/2026-11-08-foot'],
           'messages': [{'to': 'owner', 'type': 'text', 'text': note}] + msgs}, open(D + '/express_foot.json', 'w'), ensure_ascii=False, indent=1)
