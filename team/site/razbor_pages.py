# -*- coding: utf-8 -*-
"""Страницы разборов матчей (данные — <сайт>/razbor/data/<день>.json, их пишет team/site/razbor.py):
  /razbor/<день>-<хозяева>-<гости>.html — разбор матча: счёт, рассказ, «для ставок», тренды команд, наш прогноз, что дальше;
  /razbor/ — разборы последних дней по лигам;
  /app/razbory.json — список разборов за 30 дней для мини-приложения (текст приложение берёт из razbor/data/<день>.json).
Вызывает team/site/build.py → pages(...). → [(адрес страницы, дата)] для sitemap.
"""
import glob
import json
import os
from datetime import date, timedelta

import build as B

SHOW_DAYS = 30
END = {'ОТ': ' ОТ', 'Б': ' Б'}


def page_name(r):
    return '%s-%s-%s.html' % (r['d'][:10], B.slug(r['h']), B.slug(r['a']))


def load_all(site):
    lim = (B.today() - timedelta(days=SHOW_DAYS)).isoformat()
    out = []
    for p in sorted(glob.glob(os.path.join(site, 'razbor', 'data', '20*.json'))):
        if os.path.basename(p)[:10] < lim:
            continue
        for k, r in (B.load(p) or {}).items():
            out.append(dict(r, key=k, day=os.path.basename(p)[:10]))
    return sorted(out, key=lambda r: r['d'], reverse=True)


def score(r):
    return '%d:%d%s' % (r['hg'], r['ag'], END.get(r.get('end'), ''))


def trend_card(team, x, logo, n):
    if not x:
        return ''
    chips = ''.join('<b class="%s">%s</b>' % ('w' if c == 'В' else 'l', c) for c in x['form'])
    nx = ''
    if n:
        d = date.fromisoformat(n['d'][:10])
        nx = '<p class="nx">Дальше: %s %s · %d %s, %s МСК</p>' % (
            'дома против' if n['home'] else 'в гостях у', B.esc(B.gen(n['opp'])), d.day, B.MONTHS[d.month - 1], n['d'][11:16])
    return '''<div class="team">
<div class="th">%s<h3>%s</h3></div>
<div class="frm">%s<span>%s</span></div>
<ul class="kv"><li><span>Тотал больше 5,5</span><b>%s</b></li><li><span>Забивает / пропускает</span><b>%s / %s</b></li>
<li><span>Дома / в гостях</span><b>%s / %s</b></li></ul>%s
<a class="more" href="../app/#team/%s">Страница команды →</a></div>''' % (
        '<img src="../%s" alt="" width="48" height="48">' % logo if logo else '', B.esc(team), chips, B.esc(x['streak']),
        B.esc(x['over']), str(x['gf10']).replace('.', ','), str(x['ga10']).replace('.', ','), x['home'], x['away'], nx,
        B.esc(team))


def match_page(r, logos, base, same_day, site):
    lg = B.LG[r['lg']]
    d = B.dt_of(r)
    title = '%s — %s %s: разбор матча %d %s | %s' % (r['h'], r['a'], score(r), d.day, B.MONTHS[d.month - 1], lg)
    lead = (r.get('story') or [''])[0]
    desc = (lead[:150].rsplit(' ', 1)[0] + '…') if len(lead) > 150 else lead
    url = base + 'razbor/' + page_name(r)
    ld = [{'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': r['title'][:110],
           'datePublished': (r.get('built') or r['d']).replace(' ', 'T') + ':00+03:00', 'inLanguage': 'ru',
           'author': {'@type': 'Organization', 'name': 'JARVIS'}, 'about': {
               '@type': 'SportsEvent', 'name': '%s — %s' % (r['h'], r['a']), 'sport': 'Ice hockey',
               'startDate': d.strftime('%Y-%m-%dT%H:%M:00+03:00'),
               'homeTeam': {'@type': 'SportsTeam', 'name': r['h']}, 'awayTeam': {'@type': 'SportsTeam', 'name': r['a']}}},
          {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
              {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': base},
              {'@type': 'ListItem', 'position': 2, 'name': 'Разборы', 'item': base + 'razbor/'},
              {'@type': 'ListItem', 'position': 3, 'name': '%s — %s' % (r['h'], r['a']), 'item': url}]}]
    extra = '<script type="application/ld+json">%s</script>\n' % json.dumps(ld, ensure_ascii=False)
    emb = lambda t: ('<img src="../%s" alt="%s" width="72" height="72">' % (logos[t], B.esc(t))) if t in logos else ''  # noqa: E731
    story = ''.join('<p>%s</p>' % B.esc(p) for p in r.get('story') or [])
    chips = ''.join('<div><small>%s</small><b>%s</b></div>' % (B.esc(x['t']), B.esc(x['v'])) for x in r.get('bets_t') or [])
    bets = ''
    if r.get('bets') or chips:
        bets = '<section class="rz-bets"><h2>Что это значит для ставок</h2>%s<div class="bt">%s</div></section>' % (
            ('<p>%s</p>' % B.esc(r['bets'])) if r.get('bets') else '', chips)
    pk = ''
    if r.get('pick'):
        p = r['pick']
        cls, txt = B.MARK.get(p.get('r'), ('push', 'Ждём итог'))
        pk = '''<section class="pick"><small>Наш прогноз в канале</small><h2>%s</h2><div class="k">%s</div>
<div class="res %s" style="margin-top:12px"><b>%s</b><span>Счёт %s</span></div></section>''' % (
            B.esc(p['bet']), (B.kef_s(p['kef']) if isinstance(p.get('kef'), (int, float)) else B.esc(p.get('kef') or '')), cls, txt, score(r))
    tr, nx = r.get('tr') or {}, r.get('nx') or {}
    cards = trend_card(r['h'], tr.get(r['h']), logos.get(r['h']), nx.get(r['h'])) + \
        trend_card(r['a'], tr.get(r['a']), logos.get(r['a']), nx.get(r['a']))
    # следующий матч с нашим прогнозом — ссылка на его страницу
    nxt = []
    for t in (r['h'], r['a']):
        n = nx.get(t)
        if not n:
            continue
        h, a = (t, n['opp']) if n['home'] else (n['opp'], t)
        pn = '%s-%s-%s.html' % (n['d'][:10], B.slug(h), B.slug(a))
        if os.path.exists(os.path.join(site, 'prognozy', pn)) and pn not in [x[0] for x in nxt]:
            nxt.append((pn, '%s — %s' % (h, a)))
    nxt_html = ''.join('<a class="btn" href="../prognozy/%s">Прогноз: %s</a>' % (pn, B.esc(t)) for pn, t in nxt)
    sib = ''.join('<a href="%s">%s — %s<small>%s</small></a>' % (page_name(o), B.esc(o['h']), B.esc(o['a']), score(o))
                  for o in same_day if o is not r)
    body = '''<main class="wrap page rz">
<nav class="crumbs"><a href="../">Главная</a> › <a href="./">Разборы</a> › %s</nav>
<h1>%s</h1>
<p class="when">%s · %s · %s МСК</p>
<div class="vs"><div>%s<b>%s</b></div><span class="sc">%s</span><div>%s<b>%s</b></div></div>
<section class="story">%s</section>
%s
%s
<section><h2>Тренды команд</h2><p class="hint">Последние 10 матчей, с учётом этого.</p><div class="teams">%s</div>
<p class="cmp"><a href="../app/#team/%s/vs/%s">Сравнить команды по шестиугольнику силы →</a></p>%s</section>
%s
</main>
''' % (B.esc('%s — %s' % (r['h'], r['a'])), B.esc(r['title']), lg, B.nice_day(d.date()), r['d'][11:16],
       emb(r['h']), B.esc(r['h']), score(r), emb(r['a']), B.esc(r['a']), story, bets, pk, cards,
       B.esc(r['h']), B.esc(r['a']), ('<div class="acts">%s</div>' % nxt_html) if nxt_html else '',
       ('<section><h2>Другие разборы дня</h2><div class="sib">%s</div></section>' % sib) if sib else '')
    return B.head(title, desc, url, '../', extra) + body + B.FOOT


def list_page(R, base, logos):
    by = {}
    for r in R:
        by.setdefault((r['day'], r['lg']), []).append(r)
    icon = lambda t: ('<img src="../%s" alt="" width="26" height="26">' % logos[t]) if t in logos else '<i></i>'  # noqa: E731
    blocks = []
    for (dy, lg), rs in sorted(by.items(), key=lambda x: (x[0][0], x[0][1] == 'khl'), reverse=True)[:14]:
        rows = ''.join('''<a class="row rzr" href="%s"><time>%s</time><span class="m">%s<span>%s — %s</span>%s</span><span class="p">%s</span><b class="mk">%s</b></a>''' % (
            page_name(r), r['d'][11:16], icon(r['h']), B.esc(r['h']), B.esc(r['a']), icon(r['a']), B.esc(r['title']), score(r))
            for r in sorted(rs, key=lambda r: r['d']))
        blocks.append('<section><h2>%s · %s</h2><div class="rows">%s</div></section>' % (
            B.LG[lg], B.nice_day(date.fromisoformat(dy)), rows))
    title = 'Разборы матчей КХЛ и НХЛ: как сыграли и что это значит для ставок'
    desc = 'Разбор каждого матча КХЛ и НХЛ: как прошла игра, тренды команд, тоталы и формы — что это значит для следующих матчей.'
    body = '''<main class="wrap page"><nav class="crumbs"><a href="../">Главная</a> › Разборы</nav>
<h1>Разборы матчей</h1>
<p class="when">Каждый сыгранный матч КХЛ и НХЛ: как прошла игра, тренды команд и что это значит для ставок. Обновляется утром и ночью.</p>
%s</main>
''' % (''.join(blocks) or '<p>Разборы появятся после ближайших матчей.</p>')
    return B.head(title, desc, base + 'razbor/', '../') + body + B.FOOT


def pages(site, base, logos, changed):
    R = load_all(site)
    if not R:
        return []
    same = {}
    for r in R:
        same.setdefault((r['day'], r['lg']), []).append(r)
    out = []
    for r in R:
        B.write(site, 'razbor/' + page_name(r), match_page(r, logos, base, same[(r['day'], r['lg'])], site), changed)
        out.append(('razbor/' + page_name(r), (r.get('built') or r['d'])[:10]))
    B.write(site, 'razbor/index.html', list_page(R, base, logos), changed)
    app = [dict(k=r['key'], day=r['day'], u=page_name(r), lg=r['lg'], d=r['d'], h=r['h'], a=r['a'], sc=score(r),
                t=r['title'], p=bool(r.get('pick'))) for r in R]
    B.write(site, 'app/razbory.json', json.dumps(app, ensure_ascii=False, separators=(',', ':')), [])
    print('SITE разборов: %d (за %d дней)' % (len(R), SHOW_DAYS), flush=True)
    return [('razbor/', B.today().isoformat())] + out
