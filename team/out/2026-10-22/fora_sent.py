"""То же по ВСЕМ прогнозам, которые я предлагал владельцу в бота (team/picks/SENT.md), опубликованы они или нет; плюс
вероятность модели против того, как вышло. Было: как заходят наши опубликованные прогнозы по видам ставок (владелец 22.10: «почему так часто фора +1,5 — по ощущениям
она часто не заходит»). Источник — посты-прогнозы канала с 1 октября (channel.posts, последняя версия поста на матч), итог —
по данным лиг (как утренние итоги, morning.settle_rows). По виду ставки: сколько, зашло / минус / возврат, средний кэф,
прибыль ровной ставкой 1. Отдельно — все прогнозы на фору +1,5 с счётом. Владельцу — сводка текстом."""
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
import channel  # noqa: E402
import data  # noqa: E402
import morning  # noqa: E402
import settle  # noqa: E402

channel.MAX_PAGES = 60


def kind(bet):
    b = bet.lower().replace('ё', 'е')
    if re.search(r'фор\w*[^,;]*\+\s*1[,.]5|\(\+1[,.]5\)', b):
        return 'фора +1,5'
    if 'фор' in b:
        return 'другая фора'
    if ' и ' in b or '+ тотал' in b or re.search(r'\b[12]x|x[12]\b', b) and 'тотал' in b:
        return 'комбинация'
    if 'не проиграет' in b or re.search(r'\b(1x|x2|2x)\b', b):
        return 'двойной шанс'
    if 'индивидуальн' in b or 'итб' in b or 'итм' in b:
        return 'инд. тотал'
    if 'тотал' in b or re.search(r'\bт[бм]\b', b):
        return 'тотал'
    if 'основное время' in b or 'осн. время' in b:
        return 'победа в осн. время'
    if 'победа' in b or re.search(r'\bп[12]\b', b):
        return 'победа с ОТ'
    return 'другое'


import ledger  # noqa: E402
sent = ledger.parse_sent(open(os.path.join(ROOT, 'team', 'picks', 'SENT.md'), encoding='utf-8').read(), data.now_msk())
pm = {}
for line in open(os.path.join(ROOT, 'team', 'picks', 'SENT.md'), encoding='utf-8'):
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    m = re.search(r'(\d+)[,.](\d)\s*%', c[5]) if len(c) > 5 else None
    if m and c[0] in sent:
        pm[c[0]] = float(m.group(1) + '.' + m.group(2)) / 100
picks = [p for p in sent.values() if p['start'] < data.now_msk()]
print('FORA предложений с прошедшими матчами: %d' % len(picks), flush=True)
found, errs = data.games_for(picks)
rows, pending, bad = morning.settle_rows(picks, found)
print('FORA с итогом: %d, без итога: %d, не разобрано: %d' % (len(rows), len(pending), len(bad)), flush=True)
st = defaultdict(lambda: dict(n=0, w=0, l=0, p=0, k=[], profit=0.0, pm=[]))
fora = []
for r in rows:
    c = kind(r['bet'])
    s = st[c]
    s['n'] += 1
    k = r.get('kef')
    if r['res'] == settle.WIN:
        s['w'] += 1
        s['profit'] += (k - 1) if k else 0
    elif r['res'] == settle.LOSS:
        s['l'] += 1
        s['profit'] -= 1 if k else 0
    else:
        s['p'] += 1
    if k:
        s['k'].append(k)
    if r['pid'] in pm:
        s['pm'].append(pm[r['pid']])
    g = r['g']
    line = '%s %s %s | %s — %s %s:%s%s | %s | кэф %s | %s' % (r['pid'], r['league'], r['start'].strftime('%d.%m'), r['home'], r['away'],
                                                        g.get('hg'), g.get('ag'), (' ' + g['end']) if g.get('end') else '',
                                                        r['bet'], k or '—', r['res'])
    print('FORAROW', c, '|', line, flush=True)
    if c == 'фора +1,5':
        fora.append(line)
lines = ['Все мои предложения в бота (опубликованные и нет) — по видам ставок (ровная ставка 1):']
for c, s in sorted(st.items(), key=lambda kv: -kv[1]['n']):
    dec = s['w'] + s['l']
    lines.append('%s: %d — зашло %d, минус %d%s, %d%% (модель обещала %s), средний кэф %s, итог %+.2f' % (
        c, s['n'], s['w'], s['l'], (', возврат %d' % s['p']) if s['p'] else '', round(100 * s['w'] / dec) if dec else 0,
        ('%d%%' % round(100 * sum(s['pm']) / len(s['pm']))) if s['pm'] else '—',
        ('%.2f' % (sum(s['k']) / len(s['k']))) if s['k'] else '—', s['profit']))
for ln in lines:
    print('FORASUM', ln, flush=True)
for ln in fora:
    print('FORA15', ln, flush=True)
