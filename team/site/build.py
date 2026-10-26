# -*- coding: utf-8 -*-
"""Сайт прогнозов для поиска (владелец 22.10: «пробный запуск поиска»): лендинг + страница на каждый матч с прогнозом.
Без Claude, в GitHub Actions (.github/workflows/site.yml). Сайт — отдельный открытый репозиторий с GitHub Pages
(закрытый основной репозиторий Pages бесплатно не публикует). README рядом.

Что делает один запуск:
  1. кладёт прогнозы дня из plan.json конвейера (team/reels_daily/make.py plan) в <сайт>/data/<лига>-<день>.json;
  2. у матчей, которые уже сыграны, дописывает счёт и итог прогноза (как утренние итоги: team/daily/morning.settle_rows);
  3. собирает страницы: /prognozy/<день>-<хозяева>-<гости>.html, /prognozy/ (все прогнозы и честный итог за 30 дней),
     главную (лендинг team/site/landing.html с сегодняшними матчами), sitemap.xml, robots.txt;
  4. пишет в <сайт>/.changed список изменившихся адресов — их задание отправляет в Яндекс (IndexNow).

    python team/site/build.py <папка сайта> [plan.json …]       # SITE_URL — адрес сайта (https://…github.io/<репо>)
    python team/site/build.py <папка сайта> --no-settle …       # без загрузки счёта (проверка без сети)
"""
import glob
import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in ('render', 'team/daily', 'team/picks', 'team/reels_daily'):
    sys.path.insert(0, os.path.join(ROOT, p))

from compose import MONTHS, WD, kef_s, plural  # noqa: E402
from data import MSK  # noqa: E402
from settle import gen  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TG = 'https://t.me/jarvibet'
YT = 'https://www.youtube.com/@jarvibet'          # владелец 25.10: ссылки в шапке рядом с Telegram
IG = 'https://www.instagram.com/jarvisbet_/'
LG = {'khl': 'КХЛ', 'nhl': 'НХЛ'}
KEEP_DAYS = 45            # страницы старше — не пересобираем (файлы остаются), в списке — последние 30 дней
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n',
                                                    'o', 'p', 'r', 's', 't', 'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y',
                                                    '', 'e', 'yu', 'ya']))


def today():
    """Сегодня по Москве (раннер GitHub живёт по UTC)."""
    return datetime.now(MSK).date()


def esc(s):
    return html.escape(str(s), quote=True)


def slug(s):
    s = ''.join(TR.get(ch, ch) for ch in s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def page_name(m):
    return '%s-%s-%s.html' % (m['d'][:10], slug(m['h']), slug(m['a']))


def pct(x):
    return '%.0f%%' % (100 * x)


def lower1(s):
    return s if ' не проиграет ' in s else s[0].lower() + s[1:]


def dt_of(m):
    return datetime.strptime(m['d'][:16], '%Y-%m-%d %H:%M')


def nice_day(d):
    return '%s, %d %s' % (WD[d.weekday()], d.day, MONTHS[d.month - 1])


# ---------------------------------------------------------------- данные

def keep(P):
    """Из plan.json — только то, что нужно странице (без кривых симуляции и истории игр)."""
    out = []
    for m in P['matches']:
        x = {k: m.get(k) for k in ('h', 'a', 'd', 'arena', 'x1x2', 'pick', 'odds', 'p')}
        if m.get('sim'):
            x['sim'] = dict(n=m['sim']['n'], hits=m['sim']['hits'], top=m['sim']['top'])
        if m.get('fact'):
            x['fact'] = {k: m['fact'][k] for k in ('team', 'k', 'n')}
        x['form'] = {t: P['stats'].get(t) for t in (m['h'], m['a'])}
        out.append(x)
    return dict(day=P['day'], league=P['league'], skipped=P.get('skipped', 0), matches=out, all=P.get('all') or [],
                yday=P.get('yday') or [])


def store(site, plans):
    os.makedirs(os.path.join(site, 'data'), exist_ok=True)
    for path in plans:
        with open(path, encoding='utf-8') as f:
            P = keep(json.load(f))
        dst = os.path.join(site, 'data', '%s-%s.json' % (P['league'], P['day']))
        old = load(dst)
        if old:                                    # повторный запуск дня: итоги уже сыгранных не теряем
            res = {(m['h'], m['a']): m for m in old['matches'] if m.get('res')}
            for m in P['matches']:
                if (m['h'], m['a']) in res:
                    m.update({k: res[(m['h'], m['a'])][k] for k in ('res', 'score')})
            have = {(m['h'], m['a']) for m in P['matches']}
            P['matches'] += [m for m in old['matches'] if (m['h'], m['a']) not in have]   # ночной запуск без начавшихся
            P['matches'].sort(key=lambda m: m['d'])
            for k in ('all', 'yday'):              # ночной запуск видит меньше матчей дня — полный список не теряем
                if len(old.get(k) or []) > len(P[k]):
                    P[k] = old[k]
        save(dst, P)


def load(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def days(site):
    lim = (today() - timedelta(days=KEEP_DAYS)).isoformat()
    out = []
    for path in sorted(glob.glob(os.path.join(site, 'data', '*.json'))):
        P = load(path)
        if P and P['day'] >= lim:
            P['_path'] = path
            out.append(P)
    return out


def settle_all(D):
    """Счёт и итог прогноза у матчей, начавшихся больше 3 ч назад и ещё без итога."""
    import data
    import morning
    now = datetime.now(MSK)
    todo = []
    for P in D:
        for m in P['matches']:
            st = dt_of(m).replace(tzinfo=MSK)
            if not m.get('res') and st < now - timedelta(hours=3):
                todo.append((P, m, dict(league=P['league'].upper(), home=m['h'], away=m['a'], start=st, bet=m['pick'],
                                        kef=m.get('odds'))))
    if not todo:
        return
    found, errs = data.games_for([p for *_, p in todo])
    for e in errs:
        print('SITEERR %s' % e, flush=True)
    rows, pending, bad = morning.settle_rows([p for *_, p in todo], found)
    by = {(r['home'], r['away'], r['start']): r for r in rows}
    import compose
    touched = set()
    for P, m, p in todo:
        r = by.get((p['home'], p['away'], p['start']))
        if r:
            m['res'], m['score'] = r['res'], compose.score_s(r['g'])
            touched.add(P['_path'])
            print('SITESETTLE %s — %s %s %s' % (m['h'], m['a'], m['score'], m['res']), flush=True)
    for p, why in pending + bad:
        print('SITEWAIT %s — %s: %s' % (p['home'], p['away'], why), flush=True)
    for P in D:
        if P['_path'] in touched:
            save(P['_path'], {k: v for k, v in P.items() if k != '_path'})


# ---------------------------------------------------------------- страницы

def emblem_files(site, teams):
    """Эмблемы клубов render/emblems → <сайт>/img/<slug>.webp (128 px). → {клуб: адрес от корня}."""
    from PIL import Image
    import nhl
    from poster import TEAMS, EMB
    nhl.register()                                  # клубы НХЛ в poster.TEAMS (эмблемы emblems/nhl_*.png)
    alias = {'Рейнджерс': 'Нью-Йорк Рейнджерс', 'Айлендерс': 'Нью-Йорк Айлендерс'}   # так их называет nhl_data
    os.makedirs(os.path.join(site, 'img'), exist_ok=True)
    out = {}
    for t in teams:
        s = TEAMS.get(alias.get(t, t), (None,))[0]
        src = os.path.join(EMB, '%s.png' % s) if s else None
        if not src or not os.path.exists(src):
            continue
        dst = os.path.join(site, 'img', s + '.webp')
        if not os.path.exists(dst):
            im = Image.open(src).convert('RGBA')
            im = im.crop(im.getbbox())
            im.thumbnail((128, 128), Image.LANCZOS)
            im.save(dst, 'WEBP', quality=88, method=6)
        out[t] = 'img/%s.webp' % s
    return out


def head(title, desc, url, base, extra=''):
    return '''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta property="og:url" content="%s">
<meta name="theme-color" content="#071225">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;800&family=Manrope:wght@400;600;800&family=JetBrains+Mono:wght@500;700&display=swap">
<link rel="stylesheet" href="%sassets/site.css">
%s</head>
<body>
<header class="top"><div class="wrap bar"><a class="logo" href="%s">JAR<b>V</b>IS</a>
<nav><a class="navlink" href="%srazbor/">Разборы</a><a class="navlink" href="%sapp/#table">Команды</a><a class="soc yt" href="%s" target="_blank" rel="noopener" aria-label="YouTube" title="YouTube"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.6 15.6V8.4l6.2 3.6-6.2 3.6z"/></svg></a><a class="soc ig" href="%s" target="_blank" rel="noopener" aria-label="Instagram" title="Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.2c3.2 0 3.6 0 4.8.1 3.3.1 4.8 1.7 4.9 4.9.1 1.3.1 1.6.1 4.8s0 3.6-.1 4.8c-.1 3.2-1.7 4.8-4.9 4.9-1.3.1-1.6.1-4.8.1s-3.6 0-4.8-.1c-3.3-.1-4.8-1.7-4.9-4.9C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.8C2.4 3.9 3.9 2.4 7.2 2.3 8.4 2.2 8.8 2.2 12 2.2zM12 0C8.7 0 8.3 0 7.1.1 2.7.3.3 2.7.1 7.1 0 8.3 0 8.7 0 12s0 3.7.1 4.9c.2 4.4 2.6 6.8 7 7 1.2.1 1.6.1 4.9.1s3.7 0 4.9-.1c4.4-.2 6.8-2.6 7-7 .1-1.2.1-1.6.1-4.9s0-3.7-.1-4.9c-.2-4.4-2.6-6.8-7-7C15.7 0 15.3 0 12 0zm0 5.8a6.2 6.2 0 1 0 0 12.4 6.2 6.2 0 0 0 0-12.4zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.4-11.8a1.4 1.4 0 1 0 0 2.9 1.4 1.4 0 0 0 0-2.9z"/></svg></a><a class="tg" href="%s" target="_blank" rel="noopener">Telegram</a></nav></div></header>
''' % (esc(title), esc(desc), esc(url), esc(title), esc(desc), esc(url), base, extra, base, base, base, YT, IG, TG)


FOOT = '''<section class="cta"><div class="wrap"><h2>Прогнозы на каждый матч — в Telegram</h2>
<p>Посты на все матчи КХЛ и НХЛ, ролики и честные итоги каждое утро.</p>
<a class="btn" href="%s" target="_blank" rel="noopener">Подписаться на @jarvibet</a></div></section>
<footer><div class="wrap"><span>© JARVIS · @jarvibet</span><span>18+. Материалы сайта — аналитика, а не призыв делать ставки. Выигрыш не гарантируется.</span></div></footer>
</body>
</html>
''' % TG

MARK = {'win': ('win', 'Прогноз зашёл'), 'loss': ('loss', 'Прогноз не зашёл'), 'push': ('push', 'Возврат')}


def form_html(team, st, logo, base):
    if not st:
        return ''
    rows = ''.join('<li class="%s"><b>%s</b><span>%s</span><span>%s — %s</span><span class="sc">%s</span></li>' % (
        'w' if g['res'] == 'В' else 'l', g['res'], esc(g['date']), 'дома' if g['home'] else 'в гостях', esc(g['opp']),
        esc(g['score'])) for g in st.get('last3') or [])
    gd = st.get('gd', 0)
    return '''<div class="team">
<div class="th">%s<h3>%s</h3></div>
<p class="meta">%s · %s за %s · разница шайб %s%d</p>
<ul class="last">%s</ul></div>''' % (
        '<img src="%s%s" alt="%s" width="48" height="48">' % (base, logo, esc(team)) if logo else '', esc(team),
        esc(st.get('place') or ''), plural(st.get('points', 0), 'очко', 'очка', 'очков'),
        plural(st.get('games', 0), 'матч', 'матча', 'матчей'), '+' if gd > 0 else '−' if gd < 0 else '', abs(gd), rows)


def match_page(P, m, logos, base, siblings):
    rel = '../'                                   # ссылки и картинки — относительные, адрес сайта — только в canonical
    lg = LG[P['league']]
    d = dt_of(m)
    title = '%s — %s: прогноз на матч %d %s %d | %s' % (m['h'], m['a'], d.day, MONTHS[d.month - 1], d.year, lg)
    desc = '%s — %s, %s, %s МСК. Прогноз JARVIS: %s%s. Форма команд и линия на матч.' % (
        m['h'], m['a'], nice_day(d.date()), m['d'][11:16], lower1(m['pick']), (', кэф ' + kef_s(m['odds'])) if m.get('odds') else '')
    url = base + 'prognozy/' + page_name(m)
    ld = [{
        '@context': 'https://schema.org', '@type': 'SportsEvent', 'name': '%s — %s' % (m['h'], m['a']), 'sport': 'Ice hockey',
        'startDate': d.strftime('%Y-%m-%dT%H:%M:00+03:00'), 'eventStatus': 'https://schema.org/EventScheduled',
        'homeTeam': {'@type': 'SportsTeam', 'name': m['h']}, 'awayTeam': {'@type': 'SportsTeam', 'name': m['a']},
        'location': {'@type': 'Place', 'name': m.get('arena') or lg}, 'organizer': {'@type': 'SportsOrganization', 'name': lg}},
        {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': base},
            {'@type': 'ListItem', 'position': 2, 'name': 'Прогнозы', 'item': base + 'prognozy/'},
            {'@type': 'ListItem', 'position': 3, 'name': '%s — %s' % (m['h'], m['a']), 'item': url}]}]
    extra = '<script type="application/ld+json">%s</script>\n' % json.dumps(ld, ensure_ascii=False)
    x = m.get('x1x2') or []
    line = ''
    if len(x) >= 3 and all(x[:3]):
        line = '<div class="line">%s</div>' % ''.join('<div><small>%s</small><b>%s</b></div>' % (k, kef_s(v))
                                                       for k, v in zip(('П1', 'Х', 'П2'), x[:3]))
    res = ''
    if m.get('res'):
        cls, txt = MARK.get(m['res'], ('push', ''))
        res = '<div class="res %s"><b>%s</b><span>Счёт %s</span></div>' % (cls, txt, esc(m.get('score') or ''))
    sim = ''
    if m.get('sim'):
        s = m['sim']
        sim = '''<p>Модель разыграла матч %s раз: прогноз сыграл в <b>%s</b> розыгрышей.</p>
<div class="scores">%s</div>''' % ('{:,}'.format(s['n']).replace(',', ' '), pct(s['hits'] / s['n']),
                                   ''.join('<span><b>%d:%d</b><small>%s раз</small></span>' % (h, a, '{:,}'.format(c).replace(',', ' '))
                                           for h, a, c in s['top']))
    fact = ''
    if m.get('fact') and m['fact'].get('n'):
        f = m['fact']
        fact = '<p class="fact">Цифра матча: у %s такое событие было в <b>%d из %d</b> игр сезона.</p>' % (esc(gen(f['team'])), f['k'], f['n'])
    sib = ''.join('<a href="%s">%s — %s<small>%s</small></a>' % (page_name(o), esc(o['h']), esc(o['a']), esc(o['d'][11:16]))
                  for o in siblings if o is not m)
    emb = lambda t: ('<img src="%s%s" alt="%s" width="72" height="72">' % (rel, logos[t], esc(t))) if t in logos else ''  # noqa: E731
    body = '''<main class="wrap page">
<nav class="crumbs"><a href="%s">Главная</a> › <a href="%sprognozy/">Прогнозы</a> › %s</nav>
<h1>%s — %s: прогноз на матч %d %s %d</h1>
<p class="when">%s · %s · %s МСК%s</p>
<div class="vs"><div>%s<b>%s</b></div><span>—</span><div>%s<b>%s</b></div></div>
%s
<section class="pick"><small>Прогноз</small><h2>%s</h2><div class="k">%s</div>%s</section>
%s
%s
%s
%s
</main>
''' % (rel, rel, esc('%s — %s' % (m['h'], m['a'])), esc(m['h']), esc(m['a']), d.day, MONTHS[d.month - 1], d.year,
       lg, nice_day(d.date()), m['d'][11:16], (' · ' + esc(m['arena'])) if m.get('arena') else '',
       emb(m['h']), esc(m['h']), emb(m['a']), esc(m['a']), res, esc(m['pick']), kef_s(m['odds']) if m.get('odds') else '',
       ('<div class="prob"><span>Вероятность по модели</span><b>%s</b></div><div class="meter"><i style="width:%s"></i></div>' % (pct(m['p']), pct(m['p']))) if m.get('p') else '',
       ('<section><h2>Линия на основное время</h2>%s</section>' % line) if line else '',
       (lambda fh, fa: ('<section><h2>Форма команд</h2><div class="teams">%s%s</div></section>' % (fh, fa)) if (fh or fa) else '')(
           form_html(m['h'], (m.get('form') or {}).get(m['h']), logos.get(m['h']), rel),
           form_html(m['a'], (m.get('form') or {}).get(m['a']), logos.get(m['a']), rel)),
       ('<section><h2>Что говорит модель</h2>%s%s</section>' % (sim, fact)) if (sim or fact) else '',
       ('<section><h2>Другие матчи дня</h2><div class="sib">%s</div></section>' % sib) if sib else '')
    return head(title, desc, url, '../', extra) + body + FOOT


def list_page(D, base, logos=None):
    """/prognozy/: ближайшие матчи сверху, ниже сыгранные с итогом; честный счёт за 30 дней."""
    lim = (today() - timedelta(days=30)).isoformat()
    allm = [(P, m) for P in D for m in P['matches']]
    done = [m for P, m in allm if m.get('res') in ('win', 'loss') and P['day'] >= lim]
    w = sum(m['res'] == 'win' for m in done)
    days_ = {}
    for P, m in sorted(allm, key=lambda pm: pm[1]['d'], reverse=True):
        days_.setdefault((P['day'], P['league']), []).append(m)
    logos = logos or {}
    icon = lambda t: ('<img src="../%s" alt="" width="26" height="26">' % logos[t]) if t in logos else '<i></i>'  # noqa: E731
    blocks = []
    for (dy, lg), ms in days_.items():
        d = date.fromisoformat(dy)
        rows = ''.join('''<a class="row" href="%s"><time>%s</time><span class="m">%s<span>%s — %s</span>%s</span><span class="p">%s · %s</span>%s</a>''' % (
            page_name(m), m['d'][11:16], icon(m['h']), esc(m['h']), esc(m['a']), icon(m['a']), esc(m['pick']), kef_s(m['odds']) if m.get('odds') else '—',
            '<b class="mk %s">%s %s</b>' % (m['res'], {'win': '✓', 'loss': '✕'}.get(m['res'], '↩'), esc(m.get('score') or ''))
            if m.get('res') else '<b class="mk soon">ждём</b>') for m in sorted(ms, key=lambda m: m['d']))
        blocks.append('<section><h2>%s · %s</h2><div class="rows">%s</div></section>' % (
            LG[lg], ('ночь на %d %s' % (d.day, MONTHS[d.month - 1])) if lg == 'nhl' else nice_day(d), rows))
    title = 'Прогнозы на хоккей сегодня: КХЛ и НХЛ — все матчи с итогами'
    desc = 'Прогнозы на каждый матч КХЛ и НХЛ от собственной модели: форма команд, вероятность, кэф. Итоги всех прогнозов, и зашедших, и нет.'
    tally = ('<p class="tally">За 30 дней: зашло <b>%d из %d</b> прогнозов. Показываем все, без удалений.</p>' % (w, len(done))) if done else ''
    body = '''<main class="wrap page"><nav class="crumbs"><a href="%s">Главная</a> › Прогнозы</nav>
<h1>Прогнозы на хоккей: КХЛ и НХЛ</h1>
<p class="when">Прогнозы, выложенные в Telegram-канале @jarvibet. После матча — счёт и итог.</p>
%s%s</main>
''' % ('../', tally, ''.join(blocks))
    return head(title, desc, base + 'prognozy/', '../') + body + FOOT


APP_TEAMS = os.path.join(ROOT, 'out', 'app_data', 'teams.json')


def app_team_names():
    try:
        with open(APP_TEAMS, encoding='utf-8') as f:
            T = json.load(f)
        return {r['name'] for rows in T['leagues'].values() for r in rows}
    except (OSError, ValueError, KeyError):
        return set()


def app_data(D, site, logos):
    """<сайт>/app/data.json для мини-приложения: команды (out/app_data/teams.json, team/site/app_data/build.py), матчи дня
    с прогнозами и итоги прогнозов с сайта. Нет свежих данных о командах — берём прежние из data.json (не стираем)."""
    dst = os.path.join(site, 'app', 'data.json')
    old = load(dst) or {}
    teams_ = load(APP_TEAMS) or {k: old.get(k) for k in ('leagues', 'axes', 'updated') if old.get(k)}
    td = today().isoformat()
    soon = sorted([(P, m) for P in D for m in P['matches'] if m['d'][:10] >= td and not m.get('res')], key=lambda pm: pm[1]['d'])
    games = []
    for P, m in soon:
        games.append(dict(lg=P['league'], d=m['d'], h=m['h'], a=m['a'], pick=m['pick'], k=kef_s(m['odds']) if m.get('odds') else '—', x=m.get('x1x2'), p=round(m['p'] or 0, 3),
                          u='../prognozy/' + page_name(m)))
    sched = []
    for P in D:
        if P['day'] == td:
            sched += [dict(lg=P['league'], d=x['d'], h=x['h'], a=x['a']) for x in P.get('all') or []]
    res = [dict(lg=P['league'], d=m['d'], h=m['h'], a=m['a'], pick=m['pick'], k=kef_s(m['odds']) if m.get('odds') else '—', sc=m.get('score'), r=m['res'])
           for P in D for m in P['matches'] if m.get('res') in ('win', 'loss', 'push')]
    res.sort(key=lambda r: r['d'], reverse=True)
    out = dict(teams_, built=datetime.now(MSK).strftime('%Y-%m-%d %H:%M'), games=games, schedule=sorted(sched, key=lambda x: x['d']),
               results=res[:40], logos=logos)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    save(dst, out)
    print('SITE приложение: команд %d, матчей с прогнозом %d, итогов %d' % (
        sum(len(v) for v in (out.get('leagues') or {}).values()), len(games), len(out['results'])), flush=True)


def calendar(D, td):
    """Слайд «Расписание» (владелец 25.10: настоящее расписание вместо примера): матчи дня КХЛ (нет — НХЛ) и вчерашние
    со счётом. Нет расписания на сегодня — None, на слайде остаётся пример."""
    for lg in ('khl', 'nhl'):
        P = next((P for P in D if P['league'] == lg and P['day'] == td and P.get('all')), None)
        if P:
            return dict(day=td, lg=lg.upper(), today=[dict(t=x['d'][11:16], h=x['h'], a=x['a']) for x in P['all']][:4],
                        yday=[dict(sc=x['sc'], h=x['h'], a=x['a']) for x in P.get('yday') or []][-3:])
    return None


def landing(D, logos, base, site=None):
    """Главная: лендинг с сегодняшними матчами вместо примеров (window.__TODAY, __TL, __RES — их читает скрипт лендинга);
    __MONTHS — статистика постов канала по месяцам из stats/months.json (team/site/months.py), нет файла — блока нет."""
    with open(os.path.join(HERE, 'landing.html'), encoding='utf-8') as f:
        src = f.read()
    td = today().isoformat()
    soon = sorted([(P, m) for P in D for m in P['matches'] if m['d'][:10] >= td and not m.get('res')], key=lambda pm: pm[1]['d'])
    tod = {'khl': [], 'nhl': []}
    for P, m in soon:
        d = dt_of(m).date()
        when = 'Сегодня' if d.isoformat() == td else 'Ночь на %d %s' % (d.day, MONTHS[d.month - 1]) if P['league'] == 'nhl' and d.isoformat() > td else '%d %s' % (d.day, MONTHS[d.month - 1])
        f = m.get('fact') or {}
        tod[P['league']].append(dict(w='%s · %s МСК' % (when, m['d'][11:16]), a=m['h'], b=m['a'], p=m['pick'], k=kef_s(m['odds']) if m.get('odds') else '—',
                                     y=('У %s такое было в %d из %d игр' % (gen(f['team']), f['k'], f['n'])) if f.get('n') else
                                     ('Вероятность по модели %s' % pct(m['p'])) if m.get('p') else 'Прогноз из канала @jarvibet',
                                     u='prognozy/' + page_name(m), x=m.get('x1x2'), pr=round(m['p'] or 0, 3)))
    tod = {k: v[:6] for k, v in tod.items() if v}
    res = [dict(t='%s — %s' % (m['h'], m['a']), b=m['pick'], ok=m['res'] == 'win')
           for P in D for m in P['matches'] if m.get('res') in ('win', 'loss')][-14:]
    lim = (today() - timedelta(days=30)).isoformat()
    done = [m for P in D if P['day'] >= lim for m in P['matches'] if m.get('res') in ('win', 'loss')]
    tally = dict(w=sum(m['res'] == 'win' for m in done), l=sum(m['res'] == 'loss' for m in done), n=len(done))
    cal = calendar(D, td)
    months = None
    mp = os.path.join(site, 'stats', 'months.json') if site else ''
    if mp and os.path.exists(mp):
        try:
            with open(mp, encoding='utf-8') as f:
                months = json.load(f) or None
        except ValueError as e:
            print('SITEERR months.json не прочитан: %r' % e, flush=True)
    inject = '<script>window.__SITE=1;window.__TODAY=%s;window.__TL=%s;window.__RES=%s;window.__TALLY=%s;window.__MONTHS=%s;window.__CAL=%s;</script>\n' % (
        json.dumps(tod or None, ensure_ascii=False), json.dumps(logos, ensure_ascii=False), json.dumps(res or None, ensure_ascii=False),
        json.dumps(tally), json.dumps(months, ensure_ascii=False).replace('</', '<\\/'),
        json.dumps(cal, ensure_ascii=False))
    title = 'JARVIS — прогнозы на хоккей КХЛ и НХЛ по модели'
    desc = 'Прогноз на каждый матч КХЛ и НХЛ от собственной модели: форма команд, вероятность и кэф. Честные итоги каждое утро в Telegram.'
    m = re.search(r'<title>.*?</title>', src)
    src = src.replace(m.group(0), '') if m else src
    return '''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta name="theme-color" content="#071225">
%s<style>body{margin:0}</style>
%s</head>
<body>
%s
</body>
</html>
''' % (esc(title), esc(desc), esc(base), esc(title), esc(desc), esc(base), verify(), inject, src)


def verify():
    """Мета-теги подтверждения прав: Яндекс Вебмастер (код владельца 23.10) и Google Search Console (переменная
    GOOGLE_VERIFICATION, когда владелец её задаст)."""
    out = ''
    for name, code in (('yandex-verification', os.environ.get('YANDEX_VERIFICATION') or '590b1cfd6efbb89d'),
                       ('google-site-verification', os.environ.get('GOOGLE_VERIFICATION'))):
        if code:
            out += '<meta name="%s" content="%s">\n' % (name, esc(code))
    return out


def sitemap(base, pages):
    items = ''.join('<url><loc>%s</loc><lastmod>%s</lastmod></url>' % (esc(base + p), lm) for p, lm in pages)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % items


def write(site, rel, text, changed):
    path = os.path.join(site, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = None
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            old = f.read()
    if old != text:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        changed.append(rel)


def _norm(t):
    t = str(t or '').lower().replace('ё', 'е').replace('в осн. время', 'в основное время')
    return re.sub(r'[^0-9a-zа-я+,.]+', ' ', t).strip()


def channel_view(site, D):
    """Владелец 25.10: на сайте и в приложении — только прогнозы, выложенные в канал @jarvibet (site/stats/published.json —
    team/site/months.py). Ставка и кэф — из поста; итог — по посту (months), у ещё не сыгранных — без итога. Совпала ставка с
    моделью — оставляем вероятность и розыгрыши модели, нет — убираем (они о другой ставке). Матча нет в прогнозах модели,
    но он есть в расписании дня — показываем по посту, без данных модели. Нет файла — прогнозов на сайте нет."""
    pub = load(os.path.join(site, 'stats', 'published.json')) or []
    key = lambda lg, h, a, d: (lg, _norm(h), _norm(a), d[:10])  # noqa: E731
    posts = {key(x['lg'], x['h'], x['a'], x['d']): x for x in pub}
    out, used = [], set()
    for P in D:
        ms = []
        for m in P['matches']:
            k = key(P['league'], m['h'], m['a'], m['d'])
            x = posts.get(k)
            if not x:
                continue
            used.add(k)
            same = _norm(x['bet']) == _norm(m['pick'])
            m2 = dict(m, pick=x['bet'], odds=x.get('kef') or (m['odds'] if same else None), post=x['id'])
            if not same:
                m2.update(p=None, sim=None, fact=None)
            if x.get('r'):
                m2.update(res=x['r'], score=x.get('sc'))
            elif not same:
                m2.pop('res', None), m2.pop('score', None)
            ms.append(m2)
        for y in P.get('all') or []:                    # пост есть, у модели прогноза на матч не было
            k = key(P['league'], y['h'], y['a'], y['d'])
            x = posts.get(k)
            if x and k not in used:
                used.add(k)
                m2 = dict(h=y['h'], a=y['a'], d=y['d'], pick=x['bet'], odds=x.get('kef'), p=None, post=x['id'], form={})
                if x.get('r'):
                    m2.update(res=x['r'], score=x.get('sc'))
                ms.append(m2)
        out.append(dict(P, matches=sorted(ms, key=lambda m: m['d'])))
    print('SITE прогнозы из канала: постов %d, на сайте %d' % (len(pub), sum(len(P['matches']) for P in out)), flush=True)
    return out


def build(site, plans, do_settle=True):
    base = (os.environ.get('SITE_URL') or 'https://example.github.io/jarvis').rstrip('/') + '/'
    store(site, plans)
    D = days(site)
    if do_settle:
        try:
            settle_all(D)
        except Exception as e:  # noqa: BLE001 — без счёта страницы всё равно собираем
            print('SITEERR итоги не посчитаны: %r' % e, flush=True)
    D = channel_view(site, D)                      # дальше — только то, что выложено в канал
    app_teams = app_team_names()
    logos = emblem_files(site, sorted({t for P in D for m in P['matches'] + P.get('all', []) + P.get('yday', [])
                                       for t in (m['h'], m['a'])} | app_teams))
    os.makedirs(os.path.join(site, 'assets'), exist_ok=True)
    shutil.copy(os.path.join(HERE, 'site.css'), os.path.join(site, 'assets', 'site.css'))
    # мини-приложение Telegram (прототип, владелец 25.10): team/site/app → <сайт>/app/, данные → <сайт>/app/data.json
    shutil.copytree(os.path.join(HERE, 'app'), os.path.join(site, 'app'), dirs_exist_ok=True)
    app_data(D, site, logos)
    changed = []
    for P in D:
        ms = sorted(P['matches'], key=lambda m: m['d'])
        for m in ms:
            write(site, 'prognozy/' + page_name(m), match_page(P, m, logos, base, ms), changed)
    keep_pages = {page_name(m) for P in D for m in P['matches']}
    gone = [p for p in glob.glob(os.path.join(site, 'prognozy', '20*.html')) if os.path.basename(p) not in keep_pages]
    for p in gone:                                 # прогноз не выкладывался в канал — страницы на сайте нет
        os.remove(p)
    if gone:
        print('SITE убрано страниц без поста в канале: %d' % len(gone), flush=True)
    write(site, 'prognozy/index.html', list_page(D, base, logos), changed)
    write(site, 'index.html', landing(D, logos, base, site), changed)
    # разборы всех сыгранных матчей (владелец 26.10): данные — team/site/razbor.py, страницы — razbor_pages.py
    import razbor_pages
    rz = razbor_pages.pages(site, base, logos, changed)
    # sitemap — по всем страницам матчей, что лежат на сайте (и старше KEEP_DAYS)
    pages = [('', today().isoformat()), ('prognozy/', today().isoformat())] + rz
    for path in sorted(glob.glob(os.path.join(site, 'prognozy', '20*.html'))):
        pages.append(('prognozy/' + os.path.basename(path), datetime.fromtimestamp(os.path.getmtime(path)).date().isoformat()))
    write(site, 'sitemap.xml', sitemap(base, pages), [])
    write(site, 'robots.txt', 'User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % base, [])
    key = os.environ.get('INDEXNOW_KEY') or hashlib.sha1(base.encode()).hexdigest()[:32]
    write(site, key + '.txt', key, [])
    write(site, '.nojekyll', '', [])
    with open(os.path.join(site, '.changed'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(base + ('' if c == 'index.html' else c.replace('index.html', '')) for c in changed))
    print('SITE страниц изменилось: %d (ключ IndexNow %s)' % (len(changed), key), flush=True)
    return changed


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    do_settle = '--no-settle' not in a
    a = [x for x in a if x != '--no-settle']
    build(a[0], a[1:], do_settle)
    return 0


if __name__ == '__main__':
    sys.exit(main())
