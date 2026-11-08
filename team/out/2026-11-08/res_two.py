"""Итог «ставки на два матча» владельца 0811-e5 (пост №1498): счёт КХЛ из приложения (data.games_for), расчёт по основному
времени; вторая нога — две части (Х2 и тотал больше 3,5), проходит, если прошли обе. Баннер + сообщение владельцу, pid 0811-e5r1498."""
import json, os, sys
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, p) for p in ('team/picks', 'render', 'team/daily')]
import data, settle, express_card as ec
JOB = os.path.join(ROOT, 'team/out/2026-11-08/res_two.json')
LEGS = [('Трактор', 'Автомобилист', ['тотал матча меньше 6,5 в основное время'], 'тотал меньше 6,5', 1.25),
        ('Нефтехимик', 'Локомотив', ['Локомотив не проиграет в основное время', 'тотал матча больше 3,5 в основное время'],
         'Х2 и тотал больше 3,5', 1.64)]
st = datetime(2026, 11, 8, 14, 0, tzinfo=data.MSK)
picks = [dict(league='KHL', home=settle.canon(h), away=settle.canon(a), start=st, bet=b[0]) for h, a, b, _, _ in LEGS]
found, errs = data.games_for(picks)
print('RESTWO errs', errs, flush=True)
legs = []
for (h, a, bets, short, kef), p in zip(LEGS, picks):
    g = data.match_game(found, p)
    if not g or g['state'] != 'final' or g.get('hg') is None:
        sys.exit('RESTWO нет финала %s — %s (%s)' % (h, a, g and g['state']))
    rs = [settle.settle(b, p['home'], p['away'], g)[0] for b in bets]
    mark = 'loss' if settle.LOSS in rs else 'win' if all(r == settle.WIN for r in rs) else 'push'
    sc = '%s:%s%s' % (g['hg'], g['ag'], {'ot': ' ОТ', 'so': ' Б'}.get(str(g.get('end') or '').lower(), ''))
    print('RESTWO', h, a, sc, bets, rs, mark, flush=True)
    legs.append(dict(home=h, away=a, time=sc, bet=short, kef=kef, league='КХЛ', mark=mark, score=sc))
win = all(l['mark'] == 'win' for l in legs)
loss = any(l['mark'] == 'loss' for l in legs)
img = 'out/express/2026-11-08-owner/two_result.jpg'
ec.render(legs, os.path.join(ROOT, img), fmt='feed', title='ИТОГ СТАВКИ', date_title='8 ноября · два матча', total=2.05)
sign = {'win': '✅', 'loss': '❌', 'push': '↩️'}
head = '✅ Зашла!' if win else '❌ Не зашла' if loss else '↩️ Возврат по одной из ставок'
txt = ['Итог ставки на два матча %s' % head, '', 'КХЛ · 8 ноября', '']
txt += ['%d. <b>%s — %s</b> %s · %s %s' % (i, l['home'], l['away'], l['score'], l['bet'], sign[l['mark']]) for i, l in enumerate(legs, 1)]
txt += ['', 'Общий кэф: <b>2,05</b>' if win else 'Одна из ставок не прошла — бывает. Идём дальше.' if loss else 'Кэф пересчитывается.', '', '#кхл #jarvibet']
job = json.load(open(JOB, encoding='utf-8'))
job['messages'].append({'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': [img], 'text': '\n'.join(txt),
                        'buttons': 'post', 'pid': '0811-e5r1498'})
json.dump(job, open(JOB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('RESTWO SENT', win, loss, flush=True)
