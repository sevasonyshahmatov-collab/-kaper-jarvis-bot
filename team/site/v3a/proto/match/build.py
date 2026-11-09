# -*- coding: utf-8 -*-
"""Образец страницы матча, вид 2 (09.11): собирает матчи в proto/match-<n>/index.html тем же кодом, что и сайт
(seo/build_match.py, V2=True). Остальные страницы матчей не трогает. Запуск: python3 team/site/v3a/proto/match/build.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SEO = os.path.normpath(os.path.join(HERE, '..', '..', 'seo'))
sys.path.insert(0, SEO)
import build_seo as B  # noqa: E402
import build_match as BM  # noqa: E402

BM.init(B)
B._wire_canon()
BM.LINES = B.jload('data', 'lines.json')
BM.V2 = True
ms = sorted(BM.MATCHES.values(), key=lambda m: m['t'])
fut_h = [m for m in ms if m['sport'] == 'hockey' and m['res'] is None and (m.get('md') or {}).get('p1') is not None]
fin_f = [m for m in ms if m['sport'] == 'football' and m['res'] is not None]
fut_f = [m for m in ms if m['sport'] == 'football' and m['res'] is None and (m.get('md') or {}).get('p1') is not None]
pick = [x for x in (fut_h[:1] + fin_f[-1:] + fut_f[:1]) if x]
for want in sys.argv[1:]:   # ещё матчи по части адреса, например dortmund
    pick += [m for m in ms if want in m['rel']][:1]
for n, m in enumerate(pick, 1):
    text, P, ld = BM.match_page(m)
    html = BM.finish(m['rel'], text, P, ld)
    out = os.path.join(HERE, '..', 'match-%d' % n, 'index.html')   # та же глубина, что <лига>/<матч>/
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html.replace('<meta name="robots"', '<meta name="robots" content="noindex"><meta name="x-proto"', 1))
    print(n, m['rel'])
