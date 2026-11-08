"""Итоги экспрессов 07.11 (по просьбе владельца 08.11): НХЛ 0711-e20 (пост №1485) и футбол 0711-e13 (пост №1476).
«Опубликовать» выпускает итог ответом на пост купона (pid ДДММ-eNr<номер поста>). Счёт футбола — ESPN, 90 минут."""
import json, os, sys, requests
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, p) for p in ('team/picks', 'render', 'team/daily')]
import express_result as xr
import express_card as ec
JOB = os.path.join(ROOT, 'team/out/2026-11-08/exres_0711.json')
job = json.load(open(JOB, encoding='utf-8'))
os.environ['EXPRESS_FORCE_LIVE'] = '0'
# НХЛ
c, legs, res, st = xr.compute('team/out/2026-11-07/express_nhl3_coupons.json', '1', 'out/express/2026-11-07-nhl3')
if st == 'pending':
    sys.exit('NHL pending')
job['messages'].append({'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': ['out/express/2026-11-07-nhl3/e1_result.jpg'],
                        'text': xr.result_text(c, legs, st), 'buttons': 'post', 'pid': '0711-e20r1485'})
# Футбол
LEGS = [('Майнц', 'Бавария', 'ger.1', 'mainz', lambda h, a: a >= 2, 'тотал Баварии больше 1,5', 1.18),
        ('Рома', 'Сассуоло', 'ita.1', 'roma', lambda h, a: h >= 2, 'тотал Ромы больше 1,5', 1.30),
        ('Валенсия', 'Реал Мадрид', 'esp.1', 'valencia', lambda h, a: a >= 2, 'тотал Реал Мадрида больше 1,5', 1.31)]
fl = []
for home, away, lg, key, f, bet, kef in LEGS:
    r = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=20261107' % lg,
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).json()
    g = None
    for e in r.get('events', []):
        cc = e['competitions'][0]['competitors']
        h = [x for x in cc if x['homeAway'] == 'home'][0]
        if key in h['team']['displayName'].lower() or key in h['team'].get('slug', ''):
            a = [x for x in cc if x['homeAway'] == 'away'][0]
            g = (int(h['score']), int(a['score']), e['status']['type'].get('completed'))
    if not g or not g[2]:
        sys.exit('FOOT нет финала %s' % home)
    w = f(g[0], g[1])
    print('EXRES FOOT', home, away, '%d:%d' % g[:2], bet, w, flush=True)
    fl.append(dict(home=home, away=away, time='%d:%d' % g[:2], bet=bet, kef=kef, league='Футбол', mark='win' if w else 'loss', score='%d:%d' % g[:2]))
win = all(l['mark'] == 'win' for l in fl)
img = 'out/express/2026-11-07-ownerfoot/e1_result.jpg'
os.makedirs(os.path.join(ROOT, os.path.dirname(img)), exist_ok=True)
ec.render(fl, os.path.join(ROOT, img), fmt='feed', title='ИТОГ ЭКСПРЕССА', date_title='7 ноября', total=2.01)
sign = {'win': '✅', 'loss': '❌'}
txt = ['🏆 <b>Итог экспресса %s</b>' % ('✅ Зашёл!' if win else '❌ Не зашёл'), '', 'Футбол · 7 ноября', '']
txt += ['%d. <b>%s — %s</b> %s · %s %s' % (i, l['home'], l['away'], l['score'], l['bet'], sign[l['mark']]) for i, l in enumerate(fl, 1)]
txt += ['', 'Общий кэф: <b>2,01</b>' if win else 'Одна нога не дошла — бывает. Идём дальше.', '', '#футбол #экспресс #jarvibet']
job['messages'].append({'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': [img], 'text': '\n'.join(txt),
                        'buttons': 'post', 'pid': '0711-e13r1476'})
json.dump(job, open(JOB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('EXRES SENT nhl', st, 'foot', win, flush=True)
