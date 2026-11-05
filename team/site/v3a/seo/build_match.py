# -*- coding: utf-8 -*-
"""Страницы матчей и понятные адреса клубов (идеи 44, 46, 47; «Поиск Яндекса и Google»). Запускается из seo/build_seo.py.

Что строит:
  1. /<лига>/<ГГГГ-ММ-ДД>-<хозяева>-<гости>/index.html  (например khl/2026-11-05-avangard-cska/) — страница каждого матча окна данных:
     3 дня назад … 7 дней вперёд. Только реальные поля из data/*.json, assets/data/teams.json, football/data/football.json.
     Чего нет в данных (арена, кэфы, личные встречи, расчёт модели) — блока на странице нет.
  2. /<лига>/<клуб>/index.html (khl/ska, nhl/edmonton, epl/arsenal …) — страница клуба по понятному адресу: копия team/index.html
     (хоккей) или football/team.html (футбол) с <base> на папку исходной страницы и вшитым id клуба. Старые адреса ?id= работают,
     у них canonical на новый (seo/build_seo.py, canon_map).
  3. data/matchlinks.js — ключ матча → адрес страницы (для колоды matches.html).
  4. Удаляет страницы матчей старше 30 дней и страницы окна, которых в данных больше нет.

ТЕКСТЫ ПРЕВЬЮ (idea 46): собираются из данных по шаблонам (preview_text). ДО ЗАПУСКА (до открытия индексации) их читает человек —
владелец или редактор: проверить грамматику на 10–15 матчах разных лиг. Оценок «точно выиграет» и обещаний в шаблонах быть не должно.
Кэфы показываются без названия букмекера/источника (решение владельца 05.11)."""
import datetime
import html as H
import json
import os
import re
import shutil
import zlib

B = None  # модуль build_seo (передаётся в init)
CLUBS = {}      # (sport, id) -> 'khl/ska'
CLUB_INFO = {}  # 'khl/ska' -> dict
MATCHES = {}    # key -> dict
PAST_DAYS, AHEAD_DAYS, KEEP_DAYS = 3, 7, 30

NHL_EN = {'nhl_car': 'carolina', 'nhl_edm': 'edmonton', 'minnesota': 'minnesota', 'nhl_bos': 'boston', 'nhl_vgk': 'vegas', 'nhl_mtl': 'montreal',
          'nhl_tbl': 'tampa-bay', 'nhl_njd': 'new-jersey', 'nhl_uta': 'utah', 'dallas': 'dallas', 'nhl_col': 'colorado', 'nhl_ott': 'ottawa',
          'nhl_fla': 'florida', 'nhl_tor': 'toronto', 'nhl_sea': 'seattle', 'nhl_buf': 'buffalo', 'nhl_nsh': 'nashville', 'nhl_nyr': 'rangers',
          'nhl_det': 'detroit', 'nhl_wsh': 'washington', 'nhl_nyi': 'islanders', 'nhl_stl': 'st-louis', 'nhl_ana': 'anaheim', 'nhl_sjs': 'san-jose',
          'nhl_cgy': 'calgary', 'nhl_wpg': 'winnipeg', 'nhl_cbj': 'columbus', 'nhl_pit': 'pittsburgh', 'nhl_phi': 'philadelphia',
          'nhl_lak': 'los-angeles', 'nhl_chi': 'chicago', 'nhl_van': 'vancouver'}


def slug_of(sport, tid, lg=None):
    if sport == 'hockey' and (lg == 'nhl' or tid in NHL_EN):
        return NHL_EN.get(tid) or re.sub(r'^nhl_', '', tid).replace('_', '-')
    return tid.replace('_', '-')


def club_dir(sport, tid):
    return CLUBS.get((sport, tid))


def match_rel(key):
    m = MATCHES.get(key)
    return m['rel'] if m else None


def canon_map(sport):
    return {tid: d + '/' for (sp, tid), d in CLUBS.items() if sp == sport}


def sitemap_paths():
    return sorted(d + '/' for d in CLUB_INFO) + sorted(m['rel'][:-len('index.html')] for m in MATCHES.values())


# ───────────────────────── инициализация: клубы и матчи окна ─────────────────────────
def init(b):
    global B
    B = b
    CLUBS.clear(); CLUB_INFO.clear(); MATCHES.clear()
    for tid, t in B.TEAMS['teams'].items():
        lg = t.get('lg') or 'khl'
        d = '%s/%s' % (lg, slug_of('hockey', tid, lg))
        CLUBS[('hockey', tid)] = d
        CLUB_INFO[d] = {'sport': 'hockey', 'id': tid, 'lg': lg, 'name': t['name'], 't': t}
    for tid, t in B.FOOT['teams'].items():
        lg = t.get('lg') or 'epl'
        d = '%s/%s' % (lg, slug_of('football', tid, lg))
        CLUBS[('football', tid)] = d
        CLUB_INFO[d] = {'sport': 'football', 'id': tid, 'lg': lg, 'name': t.get('n', tid), 't': t}
    collect()


def collect():
    today = datetime.datetime.strptime(B.BUILT_DAY, '%Y-%m-%d').date()
    lo = (today - datetime.timedelta(days=PAST_DAYS)).isoformat()
    hi = (today + datetime.timedelta(days=AHEAD_DAYS)).isoformat()
    arenas = {m['key']: m.get('arena') for m in B.TODAY.get('matches', [])}

    def add(sport, lg, t, h, a, res, md_game, xg=None):
        d = t[:10]
        if not (lo <= d <= hi):
            return
        key = '%s|%s|%s|%s' % (lg, d, h, a)
        if key in MATCHES:
            return
        md = B.MODEL.get(key)
        if not md and md_game:
            md = md_game
        names = B.TEAMS['names'] if sport == 'hockey' else {k: v.get('n', k) for k, v in B.FOOT['teams'].items()}
        hs, as_ = slug_of(sport, h, lg if sport == 'hockey' else None), slug_of(sport, a, lg if sport == 'hockey' else None)
        rel = '%s/%s-%s-%s/index.html' % (lg, d, hs, as_)
        ar = arenas.get(key)
        MATCHES[key] = {'key': key, 'sport': sport, 'lg': lg, 't': t, 'h': h, 'a': a, 'hn': names.get(h, h), 'an': names.get(a, a),
                        'md': md, 'res': res, 'rel': rel, 'arena': ar if isinstance(ar, dict) else None,
                        'arena_s': ar if isinstance(ar, str) else None}

    for tid, t in B.TEAMS['teams'].items():
        lg = t.get('lg') or 'khl'
        for g in t.get('games', []):
            if g.get('h') != 1:
                continue
            res = (g['gf'], g['ga'], g.get('x') or '') if 'gf' in g else None
            md = None
            if g.get('pm'):
                p = g['pm']
                md = {'p1': p[0], 'x': p[1], 'p2': p[2]}
            add('hockey', lg, g['d'], tid, g['o'], res, md)
    for u in B.FOOT['up']:
        md = None
        if u.get('pr'):
            md = {'p1': u['pr'][0], 'x': u['pr'][1], 'p2': u['pr'][2], 'tot': 2.5, 'over': u.get('ov'), 'lam': u.get('xg'), 'btts': u.get('bt')}
        add('football', u['lg'], u['t'], u['h'], u['a'], None, md)
    for tid, t in B.FOOT['teams'].items():
        for g in t.get('games', []):
            if g.get('h') != 1:
                continue
            lg = g.get('c') or t.get('lg')
            res = (g['gf'], g['ga'], '') if 'gf' in g else None
            md = None
            if g.get('pr'):
                md = {'p1': g['pr'][0], 'x': g['pr'][1], 'p2': g['pr'][2], 'tot': 2.5, 'over': g.get('ov'), 'btts': g.get('bt')}
            add('football', lg, g['d'], tid, g['o'], res, md)
    # приоритет данных: результат известен, если у хозяев в играх есть счёт (повторный проход не нужен: add берёт первый)


# ───────────────────────── мелкие помощники ─────────────────────────
esc = lambda s: H.escape(str(s), quote=True)  # noqa: E731
f1 = lambda v: ('%.1f' % v).replace('.', ',')  # noqa: E731
f2 = lambda v: ('%.2f' % v).replace('.', ',')  # noqa: E731


def pl(n, forms):
    n = abs(int(n)) % 100
    a = n % 10
    return forms[2] if 10 < n < 20 else forms[1] if 1 < a < 5 else forms[0] if a == 1 else forms[2]


def pick(key, slot, options):
    """Детерминированный выбор шаблона: один и тот же матч всегда даёт один и тот же текст, разные матчи — разные формулировки."""
    return options[zlib.crc32(('%s|%s' % (key, slot)).encode('utf-8')) % len(options)]


def date_ru(t):
    dm, wd = B.ru_date(t[:10])
    return dm, wd, t[:4]


def lg_name(lg):
    return B.LG_NAME.get(lg, lg)


def lg_link(m, from_dir):
    pre = '../' * B.depth(from_dir)
    if m['sport'] == 'hockey':
        return pre + 'hockey/league.html?lg=' + m['lg']
    return pre + ('football/ucl.html' if m['lg'] == 'ucl' else 'football/league.html?lg=' + m['lg'])


# ───────────────────────── данные для блоков ─────────────────────────
def team_games(m, tid):
    """Сыгранные матчи клуба (со счётом) до даты матча, свежие последними."""
    t = B.TEAMS['teams'].get(tid) if m['sport'] == 'hockey' else B.FOOT['teams'].get(tid)
    if not t:
        return []
    out = [g for g in t.get('games', []) if 'gf' in g and g['d'] < m['t'][:10] + ' 00:00']
    out.sort(key=lambda g: g['d'])
    return out


def form5(m, tid):
    gs = team_games(m, tid)[-5:]
    return gs


def outcome(g):
    return 'w' if g['gf'] > g['ga'] else 'l' if g['gf'] < g['ga'] else 'd'


def h2h_rows(m):
    """Личные встречи с точки зрения хозяев: [(дата, дома?, голы_хозяев_клуба, голы_гостей_клуба, доп, сезон)]."""
    out = []
    if m['sport'] == 'hockey':
        t = B.TEAMS['teams'].get(m['h']) or {}
        for r in (t.get('h2h') or {}).get(m['a'], []):
            out.append({'d': r[0], 'home': r[1], 'gf': r[2], 'ga': r[3], 'x': r[4] if len(r) > 4 else ''})
    else:
        for k in (m['h'] + '|' + m['a'], m['a'] + '|' + m['h']):
            for r in B.FOOT['h2h'].get(k, []):
                hs, as_ = r['hs'], r['as']
                mine = (hs, as_) if r['h'] == m['h'] else (as_, hs)
                out.append({'d': r['d'], 'home': 1 if r['h'] == m['h'] else 0, 'gf': mine[0], 'ga': mine[1], 'x': ''})
    out = [r for r in out if r['d'] < m['t'][:10]]
    out.sort(key=lambda r: r['d'], reverse=True)
    return out


def standing(m, tid):
    """Строка таблицы клуба из данных: place, gp, pts, w, l, (d), gf, ga. Для еврокубков — строка таблицы турнира, если она есть."""
    if m['sport'] == 'hockey':
        t = B.TEAMS['teams'].get(tid)
        if t and t.get('place') is not None:
            return {'place': t['place'], 'gp': t['gp'], 'pts': t['pts'], 'w': t['w'], 'l': t['l'], 'gf': t['gf'], 'ga': t['ga'], 'sub': t.get('conf') or ''}
        return None
    if m['lg'] in ('ucl', 'uel'):
        for r in B.FOOT['tables'].get(m['lg'], []):
            if r['id'] == tid:
                return {'place': r['place'], 'gp': r['gp'], 'pts': r['pts'], 'w': r['w'], 'd': r['d'], 'l': r['l'], 'gf': r['gf'], 'ga': r['ga'], 'sub': ''}
        return None
    t = B.FOOT['teams'].get(tid)
    if t and t.get('place') is not None and t.get('lg') == m['lg']:
        return {'place': t['place'], 'gp': t['gp'], 'pts': t['pts'], 'w': t['w'], 'd': t.get('d'), 'l': t['l'], 'gf': t['gf'], 'ga': t['ga'], 'sub': ''}
    return None


def lines_for(key):
    ln = LINES.get(key)
    if not ln or not ln.get('p1') or not ln.get('p2'):
        return None
    return ln


# ───────────────────────── превью (идея 46) ─────────────────────────
def summ(gs, sport):
    w = sum(1 for g in gs if outcome(g) == 'w')
    d = sum(1 for g in gs if outcome(g) == 'd')
    l = sum(1 for g in gs if outcome(g) == 'l')  # noqa: E741
    parts = []
    if w:
        parts.append('%d %s' % (w, pl(w, ('победа', 'победы', 'побед'))))
    if d:
        parts.append('%d %s' % (d, pl(d, ('ничья', 'ничьи', 'ничьих'))))
    if l:
        parts.append('%d %s' % (l, pl(l, ('поражение', 'поражения', 'поражений'))))
    return ', '.join(parts) or 'без матчей'


def preview_text(m):
    """3–6 предложений из данных. Шаблоны выбираются по ключу матча (разные матчи — разные формулировки).
    Названия клубов стоят только в именительном падеже (через тире и двоеточие), чтобы не склонять их.
    ТЕКСТЫ ПЕРЕД ЗАПУСКОМ САЙТА СМОТРИТ ЧЕЛОВЕК: прочитать 10–15 страниц разных лиг, поправить шаблоны."""
    k, h, a = m['key'], m['hn'], m['an']
    s = []
    if m['res'] is not None:
        r = m['res']
        s.append(pick(k, 'rs', [
            'Матч сыгран: {h} — {a}, итог {x}:{y}{ot}.',
            'Итог встречи: {h} — {a} {x}:{y}{ot}.',
        ]).format(h=h, a=a, x=r[0], y=r[1], ot=(' (%s)' % r[2]) if r[2] else ''))
    sh, sa = standing(m, m['h']), standing(m, m['a'])
    if sh and sa:
        o = lambda n: pl(n, ('очко', 'очка', 'очков'))  # noqa: E731
        g = lambda n: pl(n, ('матч', 'матча', 'матчей'))  # noqa: E731
        s.append(pick(k, 'st', [
            '{h} идёт на {ph}-м месте в таблице: {pth} {oh} после {gph} {mh}. {a} — {pa}-е место, {pta} {oa}.',
            'Таблица: {h} — {ph}-е место ({pth} {oh}), {a} — {pa}-е ({pta} {oa}).',
            'По таблице: {h} — {ph}-е место, {pth} {oh} за {gph} {mh}; {a} — {pa}-е место, {pta} {oa} за {gpa} {ma}.',
        ]).format(h=h, a=a, ph=sh['place'], pa=sa['place'], pth=sh['pts'], pta=sa['pts'], gph=sh['gp'], gpa=sa['gp'],
                  oh=o(sh['pts']), oa=o(sa['pts']), mh=g(sh['gp']), ma=g(sa['gp'])))
    fh, fa = form5(m, m['h']), form5(m, m['a'])
    n = min(len(fh), len(fa))
    if n >= 3:
        fh, fa = fh[-n:], fa[-n:]
        s.append(pick(k, 'fm', [
            'Форма в последних {n} матчах: {h} — {sh}; {a} — {sa}.',
            'В последних {n} матчах: {h} — {sh}, {a} — {sa}.',
            'Недавние результаты (матчей: {n}): {h} — {sh}; {a} — {sa}.',
        ]).format(h=h, a=a, n=n, sh=summ(fh, m['sport']), sa=summ(fa, m['sport'])))
    md = m.get('md')
    has_md = bool(md and md.get('p1') is not None and md.get('p2') is not None)
    if has_md:
        p1, p2, x = round(md['p1'] * 100), round(md['p2'] * 100), round((md.get('x') or 0) * 100)
        gap = abs(md['p1'] - md['p2'])
        if gap < 0.06:
            t = pick(k, 'md', [
                'Модель оценивает встречу как равную: {h} — {p1} %, {a} — {p2} %',
                'Расчёт JARVIS почти не разделяет команды: {h} — {p1} %, {a} — {p2} %',
                'Шансы по модели близки: {h} — {p1} %, {a} — {p2} %',
            ])
        else:
            t = pick(k, 'md', [
                'По расчёту модели шансы выше у фаворита — {l}: {lp} % против {op} %',
                'Модель видит {w}: {l} — {lp} %, соперник — {op} %',
                'Расчёт JARVIS: {l} — {lp} %, соперник — {op} %',
            ])
        lead, lp, op = (h, p1, p2) if md['p1'] >= md['p2'] else (a, p2, p1)
        t = t.format(h=h, a=a, p1=p1, p2=p2, l=lead, lp=lp, op=op, w='заметное преимущество' if gap >= 0.2 else 'небольшое преимущество')
        s.append(t + ('; ничья — %d %%.' % x if x and m['sport'] == 'football' else '.'))
        lam = md.get('lam')
        if lam and len(lam) == 2:
            s.append(pick(k, 'xg', [
                'Ожидаемые голы по модели: {a1} : {a2}, всего около {t}.',
                'Модель ждёт около {t} гола в матче: {a1} у хозяев и {a2} у гостей.',
                'Ожидаемый счёт по голам — {a1} : {a2}, суммарно около {t}.',
            ]).format(a1=f1(lam[0]), a2=f1(lam[1]), t=f1(lam[0] + lam[1])))
    hr = h2h_rows(m)
    if len(hr) >= 3:
        hw = sum(1 for r in hr if r['gf'] > r['ga'])
        aw = sum(1 for r in hr if r['gf'] < r['ga'])
        dr = len(hr) - hw - aw
        tail = ', ничьих — %d' % dr if dr else ''
        s.append(pick(k, 'hh', [
            'Личные встречи ({n} в данных): {h} — {hw} {pw}, {a} — {aw} {pa}{t}.',
            'Очные встречи из данных ({n}): {h} — {hw} {pw}, {a} — {aw} {pa}{t}.',
        ]).format(h=h, a=a, n=len(hr), hw=hw, aw=aw, t=tail, pw=pl(hw, ('победа', 'победы', 'побед')), pa=pl(aw, ('победа', 'победы', 'побед'))))
    if not s:
        return ''
    if has_md:
        s.append('Это оценка вероятностей по данным, а не обещание исхода.')
    return ' '.join(s)


# ───────────────────────── блоки страницы матча ─────────────────────────
def team_link(m, side, from_dir):
    tid, name = (m['h'], m['hn']) if side == 'h' else (m['a'], m['an'])
    em = B.emblem(m['sport'], tid, from_dir)
    img = '<img src="%s" alt="" width="40" height="40" loading="lazy">' % esc(em) if em else ''
    return '<a class="mt-tm" href="%s">%s<span>%s</span></a>' % (esc(B.club_href(m['sport'], tid, from_dir)), img, esc(name))


def form_block(m, from_dir):
    cols = []
    for side in ('h', 'a'):
        tid, name = (m['h'], m['hn']) if side == 'h' else (m['a'], m['an'])
        gs = form5(m, tid)
        if not gs:
            continue
        names = B.TEAMS['names'] if m['sport'] == 'hockey' else {k: v.get('n', k) for k, v in B.FOOT['teams'].items()}
        items = []
        for g in gs:
            o = outcome(g)
            ot = (' (%s)' % g['x']) if isinstance(g.get('x'), str) and g['x'] else ''
            items.append('<li class="r-%s"><b aria-label="%s">%s</b><span class="mt-fd">%s</span><span class="mt-fo">%s %s</span><span class="mt-fs">%d:%d%s</span></li>'
                         % (o, {'w': 'победа', 'd': 'ничья', 'l': 'поражение'}[o], {'w': 'В', 'd': 'Н', 'l': 'П'}[o], esc(g['d'][8:10] + '.' + g['d'][5:7]),
                            'дома' if g.get('h') else 'в гостях', esc(names.get(g['o'], g['o'])), g['gf'], g['ga'], esc(ot)))
        cols.append('<div class="mt-col"><h3>%s</h3><ol class="mt-form" aria-label="Последние матчи, свежие внизу">%s</ol></div>' % (esc(name), ''.join(items)))
    if not cols:
        return ''
    return ('<section class="fc-sec" aria-labelledby="mt-form"><div class="wrap"><h2 id="mt-form">Форма команд: последние %d матчей</h2>'
            '<div class="mt-cols">%s</div></div></section>' % (max(len(form5(m, m['h'])), len(form5(m, m['a']))), ''.join(cols)))


def h2h_block(m):
    rows = h2h_rows(m)[:8]
    if not rows:
        return ''
    trs = []
    for r in rows:
        home, away = (m['hn'], m['an']) if r['home'] else (m['an'], m['hn'])
        sc = '%d:%d' % ((r['gf'], r['ga']) if r['home'] else (r['ga'], r['gf']))
        trs.append('<tr><td>%s.%s.%s</td><td>%s</td><td class="mt-sc">%s%s</td><td>%s</td></tr>'
                   % (r['d'][8:10], r['d'][5:7], r['d'][:4], esc(home), sc, esc((' ' + r['x']) if r['x'] else ''), esc(away)))
    return ('<section class="fc-sec" aria-labelledby="mt-h2h"><div class="wrap"><h2 id="mt-h2h">Личные встречи</h2>'
            '<div class="mt-tw"><table class="mt-tab"><thead><tr><th scope="col">Дата</th><th scope="col">Хозяева</th><th scope="col">Счёт</th><th scope="col">Гости</th></tr></thead>'
            '<tbody>%s</tbody></table></div><p class="mt-note">Последние встречи из данных сайта; ОТ и Б — овертайм и буллиты.</p></div></section>' % ''.join(trs)) \
        if m['sport'] == 'hockey' else \
        ('<section class="fc-sec" aria-labelledby="mt-h2h"><div class="wrap"><h2 id="mt-h2h">Личные встречи</h2>'
         '<div class="mt-tw"><table class="mt-tab"><thead><tr><th scope="col">Дата</th><th scope="col">Хозяева</th><th scope="col">Счёт</th><th scope="col">Гости</th></tr></thead>'
         '<tbody>%s</tbody></table></div><p class="mt-note">Последние встречи из данных сайта.</p></div></section>' % ''.join(trs))


def table_block(m):
    sh, sa = standing(m, m['h']), standing(m, m['a'])
    if not (sh and sa):
        return ''
    hock = m['sport'] == 'hockey'

    def row(name, s):
        cells = [s['place'], s['gp'], s['w']] + ([] if hock else [s['d']]) + [s['l'], '%d:%d' % (s['gf'], s['ga']), s['pts']]
        return '<tr><th scope="row">%s</th>%s</tr>' % (esc(name), ''.join('<td>%s</td>' % esc(c) for c in cells))
    head = ['Место', 'И', 'В'] + ([] if hock else ['Н']) + ['П', 'Голы', 'Очки']
    return ('<section class="fc-sec" aria-labelledby="mt-tbl"><div class="wrap"><h2 id="mt-tbl">Положение в таблице</h2>'
            '<div class="mt-tw"><table class="mt-tab"><thead><tr><th scope="col">Команда</th>%s</tr></thead><tbody>%s%s</tbody></table></div>'
            '<p class="mt-note">%s</p></div></section>'
            % (''.join('<th scope="col">%s</th>' % c for c in head), row(m['hn'], sh), row(m['an'], sa),
               'И — игры, В — победы, ' + ('' if hock else 'Н — ничьи, ') + 'П — поражения' + (' (в основное и дополнительное время)' if hock else '') + '.'))


def odds_block(m):
    ln = LINES.get(m['key'])
    if not ln or m['res'] or not ln.get('p1') or not ln.get('p2'):
        return ''
    cells = [('П1', ln['p1'])] + ([('Х', ln['x'])] if ln.get('x') else []) + [('П2', ln['p2'])]
    s = '<ul class="fc-nums mt-odds">%s</ul>' % ''.join('<li><small>%s</small><b>%s</b></li>' % (c, f2(v)) for c, v in cells)
    if ln.get('tot') is not None and ln.get('over') and ln.get('under'):
        s += '<p class="fc-ext">Тотал %s: больше <b>%s</b>, меньше <b>%s</b></p>' % (f1(ln['tot']), f2(ln['over']), f2(ln['under']))
    return ('<div class="mt-odds-wrap"><h3>Кэфы на матч</h3>%s<p class="mt-note">Основное время; кэфы на момент последнего обновления данных, до матча они меняются. '
            'Это справка, не рекомендация.</p></div>' % s)


def other_matches(m, from_dir):
    same = [x for x in MATCHES.values() if x['lg'] == m['lg'] and x['t'][:10] == m['t'][:10] and x['key'] != m['key']]
    same.sort(key=lambda x: (x['t'], x['key']))
    if not same:
        return ''
    pre = '../' * B.depth(from_dir)
    lis = ''.join('<li><a href="%s"><b>%s — %s</b><small>%s МСК</small></a></li>' % (esc(pre + x['rel']), esc(x['hn']), esc(x['an']), esc(x['t'][11:16])) for x in same[:8])
    return ('<section class="fc-sec" aria-labelledby="mt-oth"><div class="wrap"><h2 id="mt-oth">Другие матчи %s в этот день</h2><ul class="fc-hub mt-oth">%s</ul></div></section>'
            % (esc(lg_name(m['lg'])), lis))


def match_page(m):
    rel = m['rel']
    from_dir = os.path.dirname(rel)
    pre = '../' * B.depth(from_dir)
    sport, lg = m['sport'], m['lg']
    dm, wd, yr = date_ru(m['t'])
    fin = m['res'] is not None
    name = '%s — %s' % (m['hn'], m['an'])
    md = m.get('md')
    ar = m.get('arena')
    ar_txt = ''
    if ar and ar.get('name'):
        ar_txt = ar['name'] + ((', ' + ar['city']) if ar.get('city') else '')
    elif m.get('arena_s'):
        ar_txt = m['arena_s']
    if fin:
        title = '%s: итог матча %s %s, %s' % (name, dm, yr, lg_name(lg))
        h1b = 'итог матча %s' % dm
        res_txt = '%d:%d%s' % (m['res'][0], m['res'][1], (' (%s)' % m['res'][2]) if m['res'][2] else '')
    else:
        title = '%s: прогноз на матч %s %s, %s' % (name, dm, yr, lg_name(lg))
        h1b = 'прогноз на матч %s' % dm
    if md and md.get('p1') is not None:
        pr = [round(md['p1'] * 100), round((md.get('x') or 0) * 100), round(md['p2'] * 100)]
        desc = '%s, %s, %s %s, %s МСК%s. Вероятности по модели: победа хозяев %d %%, ничья %d %%, гостей %d %%. Форма команд и личные встречи.' % (
            name, lg_name(lg), dm, wd, m['t'][11:16], (', ' + ar_txt) if ar_txt else '', pr[0], pr[1], pr[2])
        if fin:
            desc = '%s, %s, %s: итог %s. Расчёт модели до матча, форма команд и личные встречи.' % (name, lg_name(lg), dm, res_txt)
    else:
        desc = '%s, %s, %s %s, %s МСК%s. Форма команд, положение в таблице, личные встречи.' % (name, lg_name(lg), dm, wd, m['t'][11:16], (', ' + ar_txt) if ar_txt else '')
        if fin:
            desc = '%s, %s, %s: итог %s. Форма команд, положение в таблице, личные встречи.' % (name, lg_name(lg), dm, res_txt)
    sp_dir = 'hockey' if sport == 'hockey' else 'football'
    crumbs = [B.HOME, (B.SPORT_RU[sport], sp_dir + '/index.html'), ('Прогноз на сегодня: ' + lg_name(lg), B.fc_rel(lg)), (name, rel)]
    facts = ['<li><small>Когда</small><b>%s, %s</b><span>%s МСК</span></li>' % (esc(dm), esc(wd), esc(m['t'][11:16]))]
    if ar_txt:
        extra = ''
        if ar and ar.get('capacity'):
            extra = '<span>вместимость %s</span>' % esc('{:,}'.format(ar['capacity']).replace(',', ' '))
        facts.append('<li><small>Арена</small><b>%s</b>%s</li>' % (esc(ar_txt), extra))
    facts.append('<li><small>Турнир</small><b><a href="%s">%s</a></b></li>' % (esc(lg_link(m, from_dir)), esc(lg_name(lg))))
    if fin:
        facts.insert(0, '<li class="mt-res"><small>Итог матча</small><b>%s</b></li>' % esc(res_txt))
    top = ('<section class="fc-top"><div class="wrap">\n%s\n<h1>%s<br><span>%s</span></h1>\n'
           '<div class="mt-teams">%s<span class="mt-vs" aria-hidden="true">—</span>%s</div>\n<ul class="mt-facts">%s</ul>\n'
           '<p class="fc-upd"><time datetime="%s">%s</time></p>\n</div></section>\n'
           % (B.crumbs_html(crumbs, rel), esc(name), esc(h1b), team_link(m, 'h', from_dir), team_link(m, 'a', from_dir), ''.join(facts),
              esc(B.BUILT.replace(' ', 'T') + ':00+03:00'), esc(B.upd_text())))
    # расчёт и кэфы
    mdl = ''
    if md and md.get('p1') is not None:
        mdl = ('<section class="fc-sec" aria-labelledby="mt-md"><div class="wrap"><h2 id="mt-md">%s</h2>\n<div class="mt-md">%s%s</div>\n'
               '<p class="mt-note">Цифры считает модель по данным сайта, а не эксперт. Это вероятности, а не гарантия исхода. '
               '<a href="%smodel.html?s=%s">Как считает модель</a> · <a href="%sglossary.html">словарь терминов</a>.</p></div></section>\n'
               % ('Расчёт модели до матча' if fin else 'Расчёт модели: вероятности и тотал', B.mdl_block(m, sport), odds_block(m), pre, 'h' if sport == 'hockey' else 'f', pre))
    else:
        o = odds_block(m)
        if o:
            mdl = '<section class="fc-sec"><div class="wrap"><div class="mt-md">%s</div></div></section>\n' % o
    pv = preview_text(m)
    prev = ('<section class="fc-sec" aria-labelledby="mt-pv"><div class="wrap"><h2 id="mt-pv">Коротко о матче</h2>'
            '<!-- превью собрано по шаблонам из данных (seo/build_match.py, preview_text); до запуска сайта тексты читает человек -->'
            '<p class="mt-prev">%s</p></div></section>\n' % esc(pv)) if pv else ''
    cl = []
    for tid, nm in ((m['h'], m['hn']), (m['a'], m['an'])):
        cl.append('<a href="%s">Страница клуба: %s</a>' % (esc(B.club_href(sport, tid, from_dir)), esc(nm)))
    links = ('<section class="fc-sec fc-how"><div class="wrap"><p class="fc-links">%s · <a href="%s">Лига: %s</a> · <a href="%s">Прогноз на сегодня: %s</a> · '
             '<a href="%s">Все матчи дня колодой</a></p>\n'
             '<p class="mt-cta"><a class="btn btn-tg" href="%s" target="_blank" rel="noopener">%s<span>Все прогнозы дня — в Telegram</span></a></p>\n'
             '<p class="fc-legal">Материалы носят информационный характер и не гарантируют результат. Реклама букмекеров на сайте не размещается. Сайт только для совершеннолетних (18+).</p>'
             '</div></section>' % (' · '.join(cl), esc(lg_link(m, from_dir)), esc(lg_name(lg)), esc(pre + B.fc_rel(lg)), esc(lg_name(lg)),
                                   esc(pre + 'matches.html?s=' + ('h' if sport == 'hockey' else 'f')), B.CFG.TELEGRAM, B.TGSVG))
    body = top + mdl + prev + form_block(m, from_dir) + h2h_block(m) + table_block(m) + other_matches(m, from_dir) + links
    js = '<script>window.JV_ACT=%s;</script>\n' % json.dumps('khl' if lg == 'khl' else 'nhl' if lg == 'nhl' else 'ucl' if lg == 'ucl' else '' if sport == 'hockey' else 'lg')
    text = B.shell(rel, sport, body, extra_css='match.css', head_js=js)
    # JSON-LD SportsEvent
    ev = {'@type': 'SportsEvent', 'name': name, 'startDate': m['t'].replace(' ', 'T') + ':00+03:00',
          'sport': 'Ice hockey' if sport == 'hockey' else 'Association football', 'description': desc,
          'homeTeam': {'@type': 'SportsTeam', 'name': m['hn'], 'url': B.url(club_dir(sport, m['h']) + '/') if club_dir(sport, m['h']) else B.url(rel)},
          'awayTeam': {'@type': 'SportsTeam', 'name': m['an'], 'url': B.url(club_dir(sport, m['a']) + '/') if club_dir(sport, m['a']) else B.url(rel)},
          'url': B.url(rel[:-len('index.html')]), 'inLanguage': 'ru'}
    if not fin:
        ev['eventStatus'] = 'https://schema.org/EventScheduled'
    if ar and ar.get('name'):
        pl_ = {'@type': 'Place', 'name': ar['name']}
        if ar.get('address'):
            pl_['address'] = ar['address']
        ev['location'] = pl_
    P = dict(title=title, desc=desc, og='assets/og/og-%s.png' % ('khl' if lg == 'khl' else 'nhl' if lg == 'nhl' else sport),
             crumbs=[(n, p if p != rel else rel[:-len('index.html')]) for n, p in crumbs], page_path=rel[:-len('index.html')])
    return text, P, [ev]


# ───────────────────────── клубы по понятным адресам ─────────────────────────
ANCHOR_JS = ('<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest(\'a[href^="#"]\');if(!a)return;'
             'var id=decodeURIComponent(a.getAttribute("href").slice(1)),t=id&&document.getElementById(id);if(!t)return;e.preventDefault();'
             't.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion:reduce)").matches?"auto":"smooth"});'
             'try{history.replaceState(null,"",location.pathname+location.search+"#"+id)}catch(x){}},true);</script>')


def club_page(d, info):
    sport, tid, lg = info['sport'], info['id'], info['lg']
    src_rel = 'team/index.html' if sport == 'hockey' else 'football/team.html'
    src = B.rd(src_rel)
    src = re.sub(re.escape(B.BEGIN) + r'.*?' + re.escape(B.END) + r'\n?', '', src, flags=re.S)
    base = '../../team/' if sport == 'hockey' else '../../football/'
    head = ('<base href="%s">\n<script>window.JV_TEAM_ID=%s;window.JV_TEAM_KIND=%s;window.JV_ACT=%s;</script>\n%s\n'
            % (base, json.dumps(tid), json.dumps('h' if sport == 'hockey' else 'f'),
               json.dumps(lg if lg in ('khl', 'nhl') else 'ucl' if lg in ('ucl', 'uel') else 'lg' if sport == 'football' else 'khl'), ANCHOR_JS))
    src = re.sub(r'(<meta name="viewport"[^>]*>\s*)', lambda mo: mo.group(1) + head, src, count=1)
    src = src.replace('/[?&]id=([a-z0-9_]+)/i.exec(location.search)', '[0,%s]' % json.dumps(tid))
    t = info['t']
    nm = info['name']
    lgn = lg_name(lg)
    if sport == 'hockey':
        bits = ['%s-е место' % t['place']] if t.get('place') is not None else []
        if t.get('conf'):
            bits[:] = ['%s-е место в конференции «%s»' % (t['place'], t['conf'])] if t.get('place') is not None else []
        if t.get('pts') is not None and t.get('gp'):
            bits.append('%d %s за %d %s' % (t['pts'], pl(t['pts'], ('очко', 'очка', 'очков')), t['gp'], pl(t['gp'], ('матч', 'матча', 'матчей'))))
    else:
        bits = []
        if t.get('place') is not None and lg not in ('ucl', 'uel') and t.get('gp'):
            bits.append('%s-е место' % t['place'])
            bits.append('%d %s за %d %s' % (t['pts'], pl(t['pts'], ('очко', 'очка', 'очков')), t['gp'], pl(t['gp'], ('матч', 'матча', 'матчей'))))
    title = '%s: матчи, таблица и прогнозы модели, %s' % (nm, lgn)
    desc = '%s (%s): %sМатчи сезона, форма, сила команды и расчёт модели на ближайшие игры.' % (nm, lgn, (', '.join(bits) + '. ') if bits else '')
    sp_dir = 'hockey' if sport == 'hockey' else 'football'
    crumbs = [B.HOME, (B.SPORT_RU[sport], sp_dir + '/index.html'), (lgn, 'hockey/league.html?lg=' + lg if sport == 'hockey' else ('football/ucl.html' if lg == 'ucl' else 'football/league.html?lg=' + lg)), (nm, d + '/')]
    P = dict(title=title, desc=desc, og='assets/og/og-%s.png' % ('khl' if lg == 'khl' else 'nhl' if lg == 'nhl' else sport), crumbs=crumbs, page_path=d + '/')
    team = {'@type': 'SportsTeam', 'name': nm, 'sport': 'Ice hockey' if sport == 'hockey' else 'Association football', 'url': B.url(d + '/')}
    return src, P, [team]


def finish(rel, text, P, ld):
    """Заголовок/canonical/JSON-LD через общий head_block build_seo (тот же блок, что у остальных страниц)."""
    P = dict(P)
    page_path = P.pop('page_path')
    # head_block строит адрес из rel: для страниц-папок canonical = адрес папки без index.html
    orig_url = B.url
    B.url = lambda r, _o=orig_url: _o(r[:-len('index.html')]) if r == rel else _o(r)
    try:
        out = B.patch_text(text, rel, P, ld)
    finally:
        B.url = orig_url
    return out


# ───────────────────────── запуск ─────────────────────────
def run():
    global LINES
    LINES = B.jload('data', 'lines.json')
    made = set()
    nm = nc = 0
    for m in MATCHES.values():
        text, P, ld = match_page(m)
        B.wr(m['rel'], finish(m['rel'], text, P, ld))
        made.add(os.path.dirname(m['rel']))
        nm += 1
    for d, info in CLUB_INFO.items():
        text, P, ld = club_page(d, info)
        rel = d + '/index.html'
        B.wr(rel, finish(rel, text, P, ld))
        nc += 1
    # ссылки для колоды
    links = {k: m['rel'] for k, m in MATCHES.items()}
    B.wr('data/matchlinks.js', '/* страницы матчей по понятным адресам; генерирует seo/build_match.py */\nwindow.JV_MATCHLINKS=%s;\n'
         % json.dumps(links, ensure_ascii=False, separators=(',', ':'), sort_keys=True))
    # уборка: страницы матчей старше KEEP_DAYS и страницы окна, которых в данных больше нет
    today = datetime.datetime.strptime(B.BUILT_DAY, '%Y-%m-%d').date()
    cut_old = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    cut_win = (today - datetime.timedelta(days=PAST_DAYS)).isoformat()
    removed = 0
    for lg in B.LG_ALL:
        base = os.path.join(B.ROOT, lg)
        if not os.path.isdir(base):
            continue
        for e in os.listdir(base):
            mo = re.match(r'^(\d{4}-\d\d-\d\d)-', e)
            if not mo or not os.path.isdir(os.path.join(base, e)):
                continue
            rel = '%s/%s' % (lg, e)
            if rel in made:
                continue
            if mo.group(1) < cut_old or mo.group(1) >= cut_win:
                shutil.rmtree(os.path.join(base, e))
                removed += 1
    return 'матчей %d, клубов %d, удалено старых %d' % (nm, nc, removed)
