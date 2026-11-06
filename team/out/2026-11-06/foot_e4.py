"""Итог футбольного экспресса 0511-e4 (Лига конференций, 05.11): счёт 90 минут из ESPN → баннер и сообщение владельцу.
Дописывает в team/out/2026-11-06/exres_both.json; без счёта хоть одной ноги — только печатает FOOTE4 и ничего не шлёт."""
import json, os, sys, requests
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')]
import express_card as ec
JOB = os.path.join(ROOT, 'team/out/2026-11-06/exres_both.json')
# (дома, в гостях, ключи ESPN дома/гостей, ставка: функция, подпись, кэф)
LEGS = [('Хетафе', 'Брайтон', 'getafe', 'brighton', lambda h, a: a > h, 'П2 Брайтон', 1.53),
        ('Спарта Прага', 'Борнмут', 'sparta', 'bournemouth', lambda h, a: a > h, 'П2 Борнмут', 1.54),
        ('Бенфика', 'Лех', 'benfica', 'psv', lambda h, a: h - a >= 2, 'Ф1(−1,5) Бенфика', 1.31)]
ev = []
for lg in ('uefa.europa.conf', 'uefa.europa', 'uefa.champions'):
    try:
        r = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=20261105' % lg,
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).json()
        ev += r.get('events', [])
    except Exception as e:
        print('FOOTE4 ERR', lg, e, flush=True)
games = []
for e in ev:
    c = e['competitions'][0]['competitors']
    h = [x for x in c if x['homeAway'] == 'home'][0]; a = [x for x in c if x['homeAway'] == 'away'][0]
    st = e['status']['type']
    print('FOOTE4 GAME', h['team']['displayName'], h['score'], a['team']['displayName'], a['score'], st.get('name'), flush=True)
    games.append((h['team']['displayName'].lower(), a['team']['displayName'].lower(), int(h['score'] or 0), int(a['score'] or 0), st.get('completed')))
legs, ok = [], True
for home, away, kh, ka, f, bet, kef in LEGS:
    g = [x for x in games if kh in x[0] and ka[:4] in x[1]] or [x for x in games if kh in x[0]]
    if not g or not g[0][4]:
        print('FOOTE4 нет финала', home, away, flush=True); ok = False; continue
    h, a = g[0][2], g[0][3]; w = f(h, a)
    print('FOOTE4', home, away, '%d:%d' % (h, a), bet, 'win' if w else 'loss', flush=True)
    legs.append(dict(home=home, away=away, time='%d:%d' % (h, a), bet=bet, kef=kef, league='Футбол', mark='win' if w else 'loss', score='%d:%d' % (h, a)))
if not ok:
    sys.exit(1)
win = all(l['mark'] == 'win' for l in legs)
img = ec.render(legs, os.path.join(ROOT, 'out/express/2026-11-05/e4_result.jpg'), fmt='feed', title='ИТОГ ЭКСПРЕССА', date_title='5 ноября', total=3.08)
os.makedirs(os.path.dirname(img), exist_ok=True)
sign = {'win': '✅', 'loss': '❌'}
txt = ['🏆 <b>Итог экспресса %s</b>' % ('✅ Зашёл!' if win else '❌ Не зашёл'), '', 'Футбол · Лига конференций · 5 ноября', '']
txt += ['%s <b>%s — %s</b> %s · %s' % (sign[l['mark']], l['home'], l['away'], l['score'], l['bet']) for l in legs]
txt += ['', 'Общий кэф %s — экспресс %s' % ('3,08', 'зашёл ✅' if win else 'не зашёл ❌'), '', '#лигаконференций #экспресс #jarvibet']
job = json.load(open(JOB, encoding='utf-8'))
job['messages'].append({'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': [img], 'text': '\n'.join(txt), 'buttons': 'post', 'pid': '0511-e4r'})
json.dump(job, open(JOB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('FOOTE4 SENT', 'win' if win else 'loss', flush=True)
