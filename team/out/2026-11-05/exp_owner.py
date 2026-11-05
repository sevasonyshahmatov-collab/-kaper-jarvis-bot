"""Экспресс владельца 05.11 (скрин BetBoom 19:46 МСК, Лига конференций) → 0511-e4.
Время матчей — ESPN (uefa.europa.conf), не нашлось — 20:45/23:00 по умолчанию не ставим, пишем без времени."""
import json, os, urllib.request, datetime
D = 'team/out/2026-11-05'
LEGS = [  # (хозяева, гости, ключ ESPN, ставка, кэф)
    ('Хетафе', 'Брайтон', 'getafe', 'победа Брайтона', 'П2 Брайтон', 1.53, 'win'),
    ('Спарта Прага', 'Борнмут', 'sparta', 'победа Борнмута', 'П2 Борнмут', 1.54, 'win'),
    ('Бенфика', 'Лех', 'benfica', 'фора Бенфики (−1,5)', 'Ф1(−1,5) Бенфика', 1.31, 'fora'),
]
times = {}
try:
    req = urllib.request.Request('https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa.conf/scoreboard?dates=20261105',
                                 headers={'User-Agent': 'jarvis-bot'})
    ev = json.load(urllib.request.urlopen(req, timeout=20)).get('events', [])
    for e in ev:
        t = datetime.datetime.strptime(e['date'], '%Y-%m-%dT%H:%MZ') + datetime.timedelta(hours=3)
        for *_, key, _b, _s, _k, _c in [(*l[:2], l[2], *l[3:]) for l in LEGS]:
            if key in e['name'].lower():
                times[key] = t.strftime('%H:%M')
    print('EXPOWN times', times, 'events', len(ev))
except Exception as ex:
    print('EXPOWN espn error', ex)
legs = [dict(home=h, away=a, date='2026-11-05', time=times.get(k, ''), league='Футбол', p=None, bet=s, kef=kf,
             src='BetBoom (скрин владельца)', cat=c, bet_full=b, bet_short=s) for h, a, k, b, s, kf, c in LEGS]
cp = {'coupons': [{'size': 3, 'legs': [], 'note': 'хоккей утром'}] * 3 + [{'size': 3, 'legs': legs, 'kef': 3.08, 'in_target': False}]}
json.dump(cp, open(D + '/express_owner_coupons.json', 'w'), ensure_ascii=False, indent=1)
lines = ['Футбол · 5 ноября · экспресс', '']
for i, l in enumerate(legs, 1):
    tm = ', %s МСК' % l['time'] if l['time'] else ''
    lines += ['%d. <b>%s — %s</b>%s' % (i, l['home'], l['away'], tm), '%s · %s' % (l['bet_full'], ('%.2f' % l['kef']).replace('.', ','))]
lines += ['', 'Общий кэф: <b>3,08</b>', '', '#футбол #лигаконференций #экспресс #jarvibet']
msgs = {'day': '2026-11-05', 'messages': [{'to': 'owner', 'type': 'animation', 'html': True,
        'files': ['out/express/2026-11-05-owner/e4_anim.mp4'], 'text': '\n'.join(lines), 'buttons': 'post', 'pid': '0511-e4'}]}
json.dump(msgs, open(D + '/express_owner_msgs.json', 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
