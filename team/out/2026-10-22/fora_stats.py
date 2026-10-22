"""Как заходят наши опубликованные прогнозы по видам ставок (владелец 22.10: «почему так часто фора +1,5 — по ощущениям
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


t0 = datetime(2026, 10, 1, tzinfo=data.MSK)
t1 = data.now_msk()
picks, chan = channel.posts(t0, t1)
print('FORA постов-прогнозов: %d (страниц %s)' % (len(picks), chan.get('pages')), flush=True)
found, errs = data.games_for(picks)
rows, pending, bad = morning.settle_rows(picks, found)
print('FORA с итогом: %d, без итога: %d, не разобрано: %d' % (len(rows), len(pending), len(bad)), flush=True)
st = defaultdict(lambda: dict(n=0, w=0, l=0, p=0, k=[], profit=0.0))
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
    g = r['g']
    line = '%s %s | %s — %s %s:%s%s | %s | кэф %s | %s' % (r['league'], r['start'].strftime('%d.%m'), r['home'], r['away'],
                                                        g.get('hg'), g.get('ag'), (' ' + g['end']) if g.get('end') else '',
                                                        r['bet'], k or '—', r['res'])
    print('FORAROW', c, '|', line, flush=True)
    if c == 'фора +1,5':
        fora.append(line)
lines = ['Как заходят наши прогнозы в канале с 1 октября — по видам ставок (ровная ставка 1):']
for c, s in sorted(st.items(), key=lambda kv: -kv[1]['n']):
    dec = s['w'] + s['l']
    lines.append('%s: %d — зашло %d, минус %d%s, %d%%, средний кэф %s, итог %+.2f' % (
        c, s['n'], s['w'], s['l'], (', возврат %d' % s['p']) if s['p'] else '', round(100 * s['w'] / dec) if dec else 0,
        ('%.2f' % (sum(s['k']) / len(s['k']))) if s['k'] else '—', s['profit']))
for ln in lines:
    print('FORASUM', ln, flush=True)
for ln in fora:
    print('FORA15', ln, flush=True)
