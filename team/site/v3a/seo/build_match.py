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
import sys
import zlib

import og_match  # картинка-превью матча og.jpg (09.11)

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


def pct3(md):
    """Три вероятности в целых процентах с суммой ровно 100 (аудит 09.11b, п. 9): остаток округления — на самый вероятный исход."""
    v = [md['p1'], md.get('x') or 0, md['p2']]
    p = [round(x * 100) for x in v]
    if abs(sum(v) - 1) < .02 and sum(p) != 100:
        p[v.index(max(v))] += 100 - sum(p)
    return p


def lg_crumb(m):
    """Крошка лиги (от корня сайта) — для сыгранных матчей вместо «Прогноз на сегодня» (аудит 09.11b, п. 9)."""
    lg = m['lg']
    if m['sport'] == 'hockey':
        return lg_name(lg), 'hockey/league.html?lg=' + lg
    return lg_name(lg), ('football/ucl.html' if lg == 'ucl' else 'football/league.html?lg=' + lg)


def has_md(m):
    return (m.get('md') or {}).get('p1') is not None


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


LG_GEN = {'laliga': 'Ла Лиги', 'seriea': 'Серии А', 'bundesliga': 'Бундеслиги', 'ligue1': 'Лиги 1', 'ucl': 'Лиги чемпионов', 'uel': 'Лиги Европы'}


def lg_gen(lg):   # «Другие матчи Лиги чемпионов» — родительный падеж (аудит 09.11b)
    return LG_GEN.get(lg, lg_name(lg))


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
            '<tbody>%s</tbody></table></div></div></section>' % ''.join(trs)) \
        if m['sport'] == 'hockey' else \
        ('<section class="fc-sec" aria-labelledby="mt-h2h"><div class="wrap"><h2 id="mt-h2h">Личные встречи</h2>'
         '<div class="mt-tw"><table class="mt-tab"><thead><tr><th scope="col">Дата</th><th scope="col">Хозяева</th><th scope="col">Счёт</th><th scope="col">Гости</th></tr></thead>'
         '<tbody>%s</tbody></table></div></div></section>' % ''.join(trs))


def table_block(m, from_dir=''):
    sh, sa = standing(m, m['h']), standing(m, m['a'])
    if not (sh and sa):
        return ''
    hock = m['sport'] == 'hockey'

    def row(name, s, tid):
        cells = [s['place'], s['gp'], s['w']] + ([] if hock else [s['d']]) + [s['l'], '%d:%d' % (s['gf'], s['ga']), s['pts']]
        return '<tr><th scope="row">%s%s</th>%s</tr>' % (crest(m, tid, from_dir, 26) if from_dir else '', esc(name), ''.join('<td>%s</td>' % esc(c) for c in cells))
    head = ['Место', 'И', 'В'] + ([] if hock else ['Н']) + ['П', 'Голы', 'Очки']
    return ('<section class="fc-sec" aria-labelledby="mt-tbl"><div class="wrap"><h2 id="mt-tbl">Положение в таблице</h2>'
            '<div class="mt-tw"><table class="mt-tab"><thead><tr><th scope="col">Команда</th>%s</tr></thead><tbody>%s%s</tbody></table></div></div></section>'
            % (''.join('<th scope="col">%s</th>' % c for c in head), row(m['hn'], sh, m['h']), row(m['an'], sa, m['a'])))


def odds_block(m):
    ln = LINES.get(m['key'])
    if not ln or m['res'] or not ln.get('p1') or not ln.get('p2'):
        return ''
    cells = [('П1', ln['p1'])] + ([('Х', ln['x'])] if ln.get('x') else []) + [('П2', ln['p2'])]
    s = '<ul class="fc-nums mt-odds">%s</ul>' % ''.join('<li><small>%s</small><b>%s</b></li>' % (c, f2(v)) for c, v in cells)
    if ln.get('tot') is not None and ln.get('over') and ln.get('under'):
        s += '<p class="fc-ext">Тотал %s: больше <b>%s</b>, меньше <b>%s</b></p>' % (f1(ln['tot']), f2(ln['over']), f2(ln['under']))
        mt = (m.get('md') or {}).get('tot')
        if mt is not None and abs(mt - ln['tot']) > .01:   # модель считает другую линию — подписать, чтобы цифры не спорили
            s += '<p class="mt-note mt-totn">Линия тотала в кэфах — %s, модель считает вероятность для %s: цифры относятся к разным линиям.</p>' % (f1(ln['tot']), f1(mt))
    return ('<div class="mt-odds-wrap"><h3>Кэфы на матч</h3>%s<p class="mt-note">Это справка, не рекомендация.</p></div>' % s)


def other_matches(m, from_dir):
    same = [x for x in MATCHES.values() if x['lg'] == m['lg'] and x['t'][:10] == m['t'][:10] and x['key'] != m['key']]
    same.sort(key=lambda x: (x['t'], x['key']))
    if not same:
        return ''
    pre = '../' * B.depth(from_dir)
    def em(tid, nm):   # эмблемы клубов в «Других матчах» (владелец 09.11)
        e = B.emblem(m['sport'], tid, from_dir)
        return ('<img src="%s" alt="" width="36" height="36" loading="lazy">' % esc(e)) if e else '<i class="mt-oe0">%s</i>' % esc(nm[:2])
    lis = ''.join('<li><a href="%s"><span class="mt-oe">%s%s</span><b><span>%s</span> — <span>%s</span></b><small>%s МСК</small></a></li>'
                  % (esc(pre + x['rel']), em(x['h'], x['hn']), em(x['a'], x['an']), esc(x['hn']), esc(x['an']), esc(x['t'][11:16])) for x in same[:8])
    return ('<section class="fc-sec" aria-labelledby="mt-oth"><div class="wrap"><h2 id="mt-oth">Другие матчи %s в этот день</h2><ul class="fc-hub mt-oth">%s</ul></div></section>'
            % (esc(lg_gen(m['lg'])), lis))


def remind_block(m, name, sport):
    """«Напомнить о матче» (владелец 09.11): событие в календарь телефона (.ics, сигнал за 15 мин), Google Календарь, Telegram."""
    from urllib.parse import quote
    st = datetime.datetime.strptime(m['t'][:16], '%Y-%m-%d %H:%M') - datetime.timedelta(hours=3)   # МСК → UTC
    en = st + datetime.timedelta(minutes=150 if sport == 'hockey' else 120)
    f = lambda d: d.strftime('%Y%m%dT%H%M%SZ')
    title = '%s — %s' % (name, lg_name(m['lg']))
    det = 'Расчёт модели — на сайте JARVIS. Прогнозы дня — в Telegram @jarvibet.'
    uid = re.sub(r'[^a-z0-9-]', '', (m['t'][:10] + '-' + str(m['h']) + '-' + str(m['a'])).lower().replace('_', '-'))
    ics = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//JARVIS//match//RU\r\nBEGIN:VEVENT\r\nUID:%s@jarvis\r\nDTSTAMP:%s\r\n'
           'DTSTART:%s\r\nDTEND:%s\r\nSUMMARY:%s\r\nDESCRIPTION:%s\r\nBEGIN:VALARM\r\nTRIGGER:-PT15M\r\nACTION:DISPLAY\r\n'
           'DESCRIPTION:%s\r\nEND:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n') % (uid, f(st), f(st), f(en), title, det, title)
    g = 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=%s&dates=%s/%s&details=%s' % (quote(title), f(st), f(en), quote(det))
    bell = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>')
    return ('<div class="mt-rem">'
            '<a class="btn mt-rem-b" href="data:text/calendar;charset=utf-8,%s" download="%s.ics">%s<span>Напомнить о матче</span></a>'
            '<a class="mt-rem-l" href="%s" target="_blank" rel="noopener">Google Календарь</a>'
            '<a class="mt-rem-l" href="%s" target="_blank" rel="noopener">Прогнозы дня — в Telegram</a>'
            '<small>Событие в календаре телефона, напоминание за 15 минут до начала.</small></div>\n') % (
        esc(quote(ics, safe='')), esc(uid), bell, esc(g), esc(B.CFG.TELEGRAM))


# ───────────────────────── страница матча, вид 2 (09.11, образец; включается V2=True) ─────────────────────────
# Двухцветное поле в цвета клубов с крупными эмблемами, вероятности модели полосой в тех же цветах,
# форма — кружками, личные встречи — карточками. Стили — assets/matchx.css.
V2 = True
import colorsys  # noqa: E402


def _hex(c):
    c = str(c or '').lstrip('#')
    return c if re.match(r'^[0-9a-fA-F]{6}$', c) else None


def club_cols(sport, tid):
    if sport == 'hockey':
        cs = (B.TEAMS['teams'].get(tid) or {}).get('colors') or []
    else:
        cs = (B.FOOT['teams'].get(tid) or {}).get('c') or []
    return [x for x in (_hex(c) for c in cs) if x]


def _hls(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def _lum(c):
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return .2126 * r + .7152 * g + .0722 * b


def _tone(h):
    """Цвет клуба для поля: тёмные и насыщенные — в среднюю яркость с белыми буквами; светлые (жёлтый, золото) остаются
    яркими, буквы на них тёмные. Возвращает (цвет, цвет букв)."""
    hh, ll, ss = _hls(h)
    if _lum(h) > .42 and ss > .25:
        ll, ink, ss = min(max(ll, .46), .56), '#141a24', min(ss, .82)
    else:
        ll, ink = min(max(ll, .16 if ss < .12 else .28), .44), '#ffffff'
        ss = max(ss, .45) if ss > .12 else ss
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255)), ink


def pair_cols(m):
    """Цвета хозяев и гостей: первый цвет клуба (не белый); если у гостей он похож на цвет хозяев — следующий цвет гостей."""
    def pick(cs, skip=None):
        good = [c for c in cs if .04 < _hls(c)[1] < .93] or cs
        for c in good:
            if skip is None or abs(_hls(c)[0] - _hls(skip)[0]) > .07 or abs(_hls(c)[1] - _hls(skip)[1]) > .22:
                return c
        return good[0] if good else None
    h = pick(club_cols(m['sport'], m['h'])) or '2b4a8a'
    a = pick(club_cols(m['sport'], m['a']), h) or '6b2b3a'
    (hc, hi), (ac, ai) = _tone(h), _tone(a)
    return hc, ac, hi, ai


# фон поля — тот же, что у баннеров Telegram и в «Матчах дня» (daily/deck_bg.py: перелив цветов клубов + холст), полосой под первый экран
BG_SIZES = {'bg': (2560, 800), 'bg-m': (1170, 1000)}   # чётко на экранах высокой плотности — не хуже «Матчей дня» (владелец 09.11)
BG_Q = {'bg': 84, 'bg-m': 78}
BG_VER = 2   # сменить число — фоны перерисуются
_DBG = None


def _deck():
    global _DBG
    if _DBG is None:
        try:
            sys.path.insert(0, os.path.join(og_match.V3A, 'daily'))
            import deck_bg as D
            fb = (D.jload_js(os.path.join(og_match.V3A, 'football', 'data', 'football-lite.js')) or {}).get('teams', {})
            try:
                tl = D.jload_js(os.path.join(og_match.V3A, 'assets', 'data', 'teams-lite.js')).get('teams', {})
            except Exception:  # noqa: BLE001
                tl = {}
            _DBG = (D, D._maps(), fb, tl)
        except Exception as e:  # noqa: BLE001
            print('фон матча: deck_bg недоступен — %r' % e)
            _DBG = False
    return _DBG


def v2_bg(m, from_dir):
    """Рисует <матч>/bg.webp и bg-m.webp, если их ещё нет (рисунок стабилен от ключа матча). Возвращает ((c1, c2) hex) или None."""
    dk = _deck()
    if not dk:
        return None
    D, HM, FB, TL = dk
    try:
        c1, c2 = D.colors_for(m, HM, FB, TL)
        seed = zlib.crc32(m['key'].encode()) % 997
        for name, (W, H) in BG_SIZES.items():
            f = os.path.join(og_match.V3A, from_dir, name + '.webp')
            mark = os.path.join(og_match.V3A, from_dir, '.bgv')
            fresh = os.path.exists(f) and os.path.exists(mark) and open(mark).read().strip() == str(BG_VER)
            if not fresh:
                D.render(c1, c2, seed, W, H).save(f, 'WEBP', quality=BG_Q[name], method=6)
        open(os.path.join(og_match.V3A, from_dir, '.bgv'), 'w').write(str(BG_VER))
        return '#%02x%02x%02x' % tuple(c1), '#%02x%02x%02x' % tuple(c2)
    except Exception as e:  # noqa: BLE001
        print('фон матча не нарисован %s: %r' % (m['key'], e))
        return None


def v2_top(m, from_dir, fin, name, h1b, dm, wd, ar_txt, crumbs, rel, cols):
    sport = m['sport']
    hc, ac, hi, ai = cols
    bg = v2_bg(m, from_dir)
    fld = ' has-bg' if bg else ''
    fxl = ('<i class="mx-fx mx-fd" aria-hidden="true" style="background-image:url(bg.webp)"></i>'
           '<i class="mx-fx mx-fm" aria-hidden="true" style="background-image:url(bg-m.webp)"></i>') if bg else '<i class="mx-fx" aria-hidden="true"></i>'

    def team(side):
        tid, nm = (m['h'], m['hn']) if side == 'h' else (m['a'], m['an'])
        em = B.emblem(sport, tid, from_dir)
        st = standing(m, tid)
        sub = ('дома' if side == 'h' else 'в гостях') + ((', %d-е место' % st['place']) if st and st.get('place') else '')
        img = '<img src="%s" alt="" width="160" height="160">' % esc(em) if em else ''
        return ('<a class="mx-team mx-%s" href="%s"><span class="mx-crest">%s</span><b>%s</b><small>%s</small></a>'
                % (side, esc(B.club_href(sport, tid, from_dir)), img, esc(nm), esc(sub)))
    if fin:
        r = m['res']
        mid = ('<div class="mx-mid"><span class="mx-score">%d<i>:</i>%d</span><span class="mx-when">%s%s</span></div>'
               % (r[0], r[1], 'итог матча' + ((', ' + r[2]) if r[2] else ''), ''))
    else:
        mid = ('<div class="mx-mid"><span class="mx-time">%s</span><span class="mx-when">%s, %s · МСК</span>'
               '<span class="mx-cd" data-t="%s"></span><div class="lv-box"%s></div></div>'
               % (esc(m['t'][11:16]), esc(dm), esc(wd), esc(m['t'][:16]), B.lv_attrs(m)))
    facts = []
    if ar_txt:
        facts.append('<li><small>Арена</small><b>%s</b></li>' % esc(ar_txt))
    facts.append('<li><small>Турнир</small><b><a href="%s">%s</a></b></li>' % (esc(lg_link(m, from_dir)), esc(lg_name(m['lg']))))
    rem = '' if fin else remind_block(m, name, sport)
    # расчёт модели — сразу под полем и заголовком; арена, напоминание и «обновлено» — отдельным блоком ниже (владелец 10.11);
    # «Когда» убрано: дата и время уже стоят на поле и в заголовке
    info = ('<section class="fc-sec mx-info" aria-label="О матче"><div class="wrap"><ul class="mx-facts">%s</ul>\n%s'
            '<p class="fc-upd"><time datetime="%s">%s</time></p></div></section>\n'
            % (''.join(facts), rem, esc(B.BUILT.replace(' ', 'T') + ':00+03:00'), esc(B.upd_text())))
    return ('<section class="mx-hero" style="--hc:%s;--ac:%s;--hi:%s;--ai:%s" aria-label="%s">\n'
            '<div class="wrap mx-crumbs">%s</div>\n'
            '<div class="mx-field%s">%s<i class="mx-sheen" aria-hidden="true"></i><i class="mx-seam" aria-hidden="true"></i><div class="wrap mx-stage">%s%s%s</div></div>\n'
            '<div class="wrap mx-head"><h1 class="mx-h1">%s <span>%s</span></h1></div>\n</section>\n'
            % (hc, ac, hi, ai, esc(name), B.crumbs_html(crumbs, rel), fld, fxl, team('h'), mid, team('a'), esc(name), esc(h1b))), info


def model_stub(m, pre, odds=''):
    """Будущий матч без расчёта (аудит 09.11b, п. 3): честная заглушка — когда появится расчёт и что есть уже сейчас."""
    return ('<section class="fc-sec mx-model mx-wait" aria-labelledby="mt-md"><div class="wrap"><h2 id="mt-md">Расчёт модели</h2>\n'
            '<div class="mx-stub"><b>Расчёт появится примерно за 1,5 суток до матча</b>'
            '<p>Модель считает вероятности, когда известны свежие результаты команд. До этого на странице — форма, личные встречи и таблица.</p></div>%s\n'
            '<p class="mt-note"><a href="%smodel.html?s=%s">Как считает модель</a> · <a href="%sglossary.html">словарь терминов</a>.</p></div></section>\n'
            % (odds, pre, 'h' if m['sport'] == 'hockey' else 'f', pre))


def crest(m, tid, from_dir, px=28):
    """Эмблема клуба рядом с названием (правило владельца 11.11: логотип у названия команды — везде, где рядом он ещё не стоит)."""
    em = B.emblem(m['sport'], tid, from_dir)
    return ('<img class="mx-em" src="%s" alt="" width="%d" height="%d" loading="lazy">' % (esc(em), px, px)) if em else ''


_MST = None


def mstats(m):
    """Статистика сыгранного матча (владелец 11.11): hockey/data/khl_mstats.json и nhl_mstats.json — их пишут загрузчики игроков
    (приложение КХЛ, api-web.nhle.com) для матчей с 11.11. → {'h': {...}, 'a': {...}} или None."""
    global _MST
    if _MST is None:
        _MST = {}
        hk = os.path.join(og_match.V3A, 'hockey', 'data')
        try:
            _MST.update(json.load(open(os.path.join(hk, 'khl_mstats.json'), encoding='utf-8')))
        except (OSError, ValueError):
            pass
        try:                                             # НХЛ: ключ с сокращениями лиги (TOR) → slug сайта (nhl_tor)
            src = open(os.path.join(og_match.V3A, 'search', 'build_index.py'), encoding='utf-8').read()
            ab = dict(re.findall(r"'([A-Z]{3})': \('([a-z_]+)'", src))
            for k, v in json.load(open(os.path.join(hk, 'nhl_mstats.json'), encoding='utf-8')).items():
                lg, d, h, a = k.split('|')
                if h in ab and a in ab:
                    _MST['%s|%s|%s|%s' % (lg, d, ab[h], ab[a])] = v
        except (OSError, ValueError):
            pass
    return _MST.get(m['key'])


def v2_mstats(m, fin, from_dir=''):
    """«Статистика матча» под счётом: пары цифр хозяева — гости с полосой в цветах клубов. Только то, что отдал источник."""
    st = mstats(m) if fin and m['sport'] == 'hockey' else None
    if not st:
        return ''
    h, a = st.get('h') or {}, st.get('a') or {}
    num = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else None  # noqa: E731
    rows = []

    def row(label, hv, av, show=None, less=False, note=''):
        hv, av = num(hv), num(av)
        if hv is None or av is None or (hv == 0 and av == 0 and not show):
            return
        fmt = show or (lambda v: ('%d' % v) if float(v).is_integer() else f1(v))
        lead = 0 if hv == av else (1 if (hv > av) != less else 2)
        rows.append((label, fmt(hv), fmt(av), hv, av, lead, note))

    row('Броски в створ', h.get('shots', h.get('sog')), a.get('shots', a.get('sog')))
    pp = lambda t: (t.get('ppg'), t.get('ppc'))  # noqa: E731
    for t in (h, a):                                     # НХЛ: «1/4» из сводки лиги
        if isinstance(t.get('pp'), str) and re.match(r'^\d+/\d+$', t['pp']):
            t['ppg'], t['ppc'] = [int(x) for x in t['pp'].split('/')]
    if num(h.get('ppc')) is not None and num(a.get('ppc')) is not None and (h['ppc'] or a['ppc']):
        hv, av = h.get('ppg') or 0, a.get('ppg') or 0
        rows.append(('Голы в большинстве', '%d из %d' % (hv, h['ppc']), '%d из %d' % (av, a['ppc']), hv, av, 0 if hv == av else (1 if hv > av else 2), ''))
    elif num(h.get('ppg')) is not None and num(a.get('ppg')) is not None:
        row('Голы в большинстве', h['ppg'], a['ppg'], show=lambda v: '%d' % v)
    row('Голы в меньшинстве', h.get('shg'), a.get('shg'))
    row('Штрафные минуты', h.get('pim'), a.get('pim'), less=True)
    if st.get('pn'):
        row('Удаления', st['pn'][0], st['pn'][1], less=True)
    if num(h.get('vbr')) is not None and num(a.get('vbr')) is not None and h['vbr'] + a['vbr'] > 0:
        row('Выигранные вбрасывания', h['vbr'], a['vbr'])
    elif num(h.get('fo')) is not None and num(a.get('fo')) is not None:
        k = 100 if max(h['fo'], a['fo']) <= 1 else 1
        row('Выигранные вбрасывания', h['fo'] * k, a['fo'] * k, show=lambda v: '%d %%' % round(v))
    row('Силовые приёмы', h.get('hit'), a.get('hit'))
    row('Блокированные броски', h.get('blk'), a.get('blk'))
    row('Отборы', h.get('tk'), a.get('tk'))
    row('Потери', h.get('gv'), a.get('gv'), less=True)
    ch, ca = num(h.get('total_puck_control_time')), num(a.get('total_puck_control_time'))
    if ch and ca:
        row('Владение шайбой', 100.0 * ch / (ch + ca), 100.0 * ca / (ch + ca), show=lambda v: '%d %%' % round(v))
    row('Входы в зону атаки', h.get('offensive_blue_line_crossings_count'), a.get('offensive_blue_line_crossings_count'))
    if not rows:
        return ''
    lis = ''
    for label, hs, as_, hv, av, lead, note in rows:
        tot = (hv + av) or 1
        lis += ('<li><b class="%s">%s</b><span>%s</span><b class="%s">%s</b>'
                '<i aria-hidden="true"><u style="flex:%.3f"></u><u style="flex:%.3f"></u></i></li>'
                % ('on' if lead == 1 else '', esc(hs), esc(label), 'on' if lead == 2 else '', esc(as_), max(hv / tot, .02), max(av / tot, .02)))
    return ('<section class="fc-sec mx-ms" aria-labelledby="mt-ms"><div class="wrap"><h2 id="mt-ms">Статистика матча</h2>\n'
            '<div class="mx-msb"><div class="mx-msh"><b>%s%s</b><b>%s%s</b></div><ul class="mx-msl">%s</ul></div>'
            '<p class="mt-note">Данные лиги.</p></div></section>\n' % (crest(m, m['h'], from_dir), esc(m['hn']), esc(m['an']), crest(m, m['a'], from_dir), lis))


def v2_model(m, fin, pre, cols):
    md = m.get('md') or {}
    if md.get('p1') is None:
        o = odds_block(m)
        if fin:
            return ('<section class="fc-sec"><div class="wrap"><div class="mt-md">%s</div></div></section>\n' % o) if o else ''
        return model_stub(m, pre, o)
    sport = m['sport']
    p = pct3(md)
    lab = [m['hn'], 'ничья' + (' в осн. время' if sport == 'hockey' else ''), m['an']]
    mx = max(p)
    seg = ''.join('<i class="mx-s%s%s" style="flex:%d"><b>%d %%</b><small>%s</small></i>'
                  % (k, ' on' if v == mx else '', max(v, 1), v, esc(t)) for k, v, t in zip(('h', 'x', 'a'), p, lab))
    f1_ = lambda v: ('%.1f' % v).replace('.', ',')  # noqa: E731
    stats = []
    if md.get('lam'):
        stats.append('<li><b>%s : %s</b><span>ожидаемые голы</span></li>' % (f1_(md['lam'][0]), f1_(md['lam'][1])))
    if md.get('tot') is not None and md.get('over') is not None:
        stats.append('<li><b>%d %%</b><span>тотал больше %s</span></li>' % (round(md['over'] * 100), f1_(md['tot'])))
    if md.get('btts') is not None:
        stats.append('<li><b>%d %%</b><span>обе забьют</span></li>' % round(md['btts'] * 100))
    return ('<section class="fc-sec mx-model" style="--hc:%s;--ac:%s;--hi:%s;--ai:%s" aria-labelledby="mt-md"><div class="wrap"><h2 id="mt-md">%s</h2>\n'
            '<div class="mx-bar" role="img" aria-label="Победа %s %d %%, %s %d %%, победа %s %d %%">%s</div>\n'
            '<ul class="mx-stats">%s</ul>%s\n'
            '<p class="mt-note">Цифры считает модель по данным сайта, а не эксперт. Это вероятности, а не гарантия исхода. '
            '<a href="%smodel.html?s=%s">Как считает модель</a> · <a href="%sglossary.html">словарь терминов</a>.</p></div></section>\n'
            % (cols[0], cols[1], cols[2], cols[3], 'Расчёт модели до матча' if fin else 'Расчёт модели', esc(m['hn']), p[0], esc(lab[1]), p[1], esc(m['an']), p[2], seg,
               ''.join(stats), odds_block(m), pre, 'h' if sport == 'hockey' else 'f', pre))


def v2_form(m, from_dir):
    names = B.TEAMS['names'] if m['sport'] == 'hockey' else {k: v.get('n', k) for k, v in B.FOOT['teams'].items()}
    cols = []
    for side in ('h', 'a'):
        tid, nm = (m['h'], m['hn']) if side == 'h' else (m['a'], m['an'])
        gs = form5(m, tid)
        if not gs:
            continue
        lis = []
        for g in gs:
            o = outcome(g)
            ot = (' ' + g['x']) if isinstance(g.get('x'), str) and g['x'] else ''
            em = B.emblem(m['sport'], g['o'], from_dir)
            on = names.get(g['o'], g['o'])
            pic = ('<img src="%s" alt="" width="34" height="34" loading="lazy">' % esc(em)) if em else '<i>%s</i>' % esc(on[:2])
            lis.append('<li class="r-%s" title="%s, %s, %s: %d:%d%s"><b aria-label="%s, соперник %s">%s<em>%s</em></b><span>%d:%d</span></li>'
                       % (o, g['d'][8:10] + '.' + g['d'][5:7], 'дома' if g.get('h') else 'в гостях', on, g['gf'], g['ga'], ot,
                          {'w': 'победа', 'd': 'ничья', 'l': 'поражение'}[o], esc(on), pic, {'w': 'В', 'd': 'Н', 'l': 'П'}[o], g['gf'], g['ga']))
        w = sum(1 for g in gs if outcome(g) == 'w')
        cols.append('<div class="mx-fc"><h3>%s%s <small>%d %s из %d</small></h3><ol class="mx-dots" aria-label="Последние матчи, свежие справа">%s</ol></div>'
                    % (crest(m, tid, from_dir, 32), esc(nm), w, 'победа' if w == 1 else 'победы' if 2 <= w <= 4 else 'побед', len(gs), ''.join(lis)))
    if not cols:
        return ''
    return ('<section class="fc-sec" aria-labelledby="mt-form"><div class="wrap"><h2 id="mt-form">Форма: последние матчи</h2>'
            '<div class="mx-form">%s</div></div></section>' % ''.join(cols))


def v2_h2h(m, from_dir):
    rows = h2h_rows(m)[:6]
    if not rows:
        return ''
    cards = []
    for r in rows:
        home, away = (m['hn'], m['an']) if r['home'] else (m['an'], m['hn'])
        hg, ag = (r['gf'], r['ga']) if r['home'] else (r['ga'], r['gf'])
        win = 'h' if hg > ag else 'a' if ag > hg else ''
        cards.append('<li><time>%s.%s.%s</time><span class="%s">%s</span><b>%d:%d%s</b><span class="%s">%s</span></li>'
                     % (r['d'][8:10], r['d'][5:7], r['d'][2:4], 'w' if win == 'h' else '', esc(home), hg, ag,
                        ('<small>%s</small>' % esc(r['x'])) if r['x'] else '', 'w' if win == 'a' else '', esc(away)))
    return ('<section class="fc-sec" aria-labelledby="mt-h2h"><div class="wrap"><h2 id="mt-h2h">Личные встречи</h2>'
            '<ul class="mx-h2h">%s</ul></div></section>' % ''.join(cards))


def v2_summary(m):
    """«Коротко о матче», вид 2 (владелец 09.11): не перечень мест в таблице, а сводка — о чём матч. Из данных:
    серии, голы за и против в последних матчах, дом и выезд, частота тотала, последняя очная встреча, расчёт модели.
    Названия клубов — только в именительном (через двоеточие и тире), без склонений."""
    k, h, a, sp = m['key'], m['hn'], m['an'], m['sport']
    line = 5.5 if sp == 'hockey' else 2.5
    fw = lambda n: '%d %s' % (n, pl(n, ('победа', 'победы', 'побед')))  # noqa: E731
    fl = lambda n: '%d %s' % (n, pl(n, ('поражение', 'поражения', 'поражений')))  # noqa: E731
    gh, ga = team_games(m, m['h']), team_games(m, m['a'])
    s = []
    if m['res'] is not None:
        r = m['res']
        md = m.get('md') or {}
        res = 'h' if r[0] > r[1] else 'a' if r[1] > r[0] else 'd'
        s.append('Итог: %s — %s %d:%d%s.' % (h, a, r[0], r[1], (' (%s)' % r[2]) if r[2] else ''))
        if md.get('p1') is not None:
            pr = {'h': md['p1'], 'd': md.get('x') or 0, 'a': md['p2']}
            fav = max(pr, key=pr.get)
            s.append('Модель до матча считала самым вероятным исходом %s (%d %%) — %s.'
                     % ({'h': 'победу хозяев', 'a': 'победу гостей', 'd': 'ничью'}[fav], round(pr[fav] * 100),
                        'так и вышло' if fav == res else 'вышло иначе'))
        else:
            s.append('Расчёт модели до матча не сохранился.')
        gh, ga = [g for g in gh if g['d'][:10] < m['t'][:10]], [g for g in ga if g['d'][:10] < m['t'][:10]]

    def streak(gs):
        if not gs:
            return 0, ''
        o = outcome(gs[-1])
        n = 0
        for g in reversed(gs):
            if outcome(g) != o:
                break
            n += 1
        return n, o

    # 1) главное по форме: длинная серия или контраст
    f5h, f5a = gh[-5:], ga[-5:]
    wh, wa = sum(outcome(g) == 'w' for g in f5h), sum(outcome(g) == 'w' for g in f5a)
    sh_, sa_ = streak(gh), streak(ga)
    form = []
    for nm, (n, o) in ((h, sh_), (a, sa_)):
        if n >= 3 and o in ('w', 'l'):
            form.append('%s: %s подряд' % (nm, fw(n) if o == 'w' else fl(n)))
    if form:
        s.append(pick(k, 'v2f', ['Серии перед матчем — %s.', 'Обе команды подходят с серией: %s.' if len(form) == 2 else 'Перед матчем серия — %s.']) % '; '.join(form))
    elif len(f5h) >= 4 and len(f5a) >= 4 and abs(wh - wa) >= 2:
        hi, lo = ((h, wh), (a, wa)) if wh > wa else ((a, wa), (h, wh))
        s.append('По форме разница заметна: %s — %s в последних 5, %s — %s.' % (hi[0], fw(hi[1]), lo[0], fw(lo[1])))
    elif len(f5h) >= 4 and len(f5a) >= 4:
        s.append('По форме команды близки: %s — %s в последних 5, %s — %s.' % (h, fw(wh), a, fw(wa)))

    # 2) голы: атака одних против обороны других
    def avg(gs, key):
        return sum(g[key] for g in gs) / len(gs) if gs else None
    if len(f5h) >= 4 and len(f5a) >= 4:
        hf, ha_, af, aa = avg(f5h, 'gf'), avg(f5h, 'ga'), avg(f5a, 'gf'), avg(f5a, 'ga')
        if max(hf, af) - min(ha_, aa) > 0 and (ha_ >= (2.9 if sp == 'hockey' else 1.6) or aa >= (2.9 if sp == 'hockey' else 1.6)):
            leak = (h, ha_) if ha_ >= aa else (a, aa)
            s.append(('Пропущено за игру в последних 5 перед матчем — %s: %s.' if m['res'] is not None   # сыгран — без будущего времени и без рода глагола
                      else '%s в последних 5 матчах пропускает %s за игру — у соперника будут моменты.') % (leak[0], f1(leak[1])))
        else:
            s.append('Голы за игру в последних 5: %s — %s забито и %s пропущено, %s — %s и %s.' % (h, f1(hf), f1(ha_), a, f1(af), f1(aa)))
        # тотал: как часто в их матчах больше линии
        last = gh[-8:] + ga[-8:]
        if len(last) >= 10:
            ov = sum(1 for g in last if g['gf'] + g['ga'] > line)
            share = ov / len(last)
            if share >= .65:
                s.append('Обе команды играют результативно: больше %s голов было в %d из %d их последних матчей.' % (f1(line), ov, len(last)))
            elif share <= .35:
                s.append('Матчи этих команд обычно скупые: больше %s голов — лишь в %d из %d последних.' % (f1(line), ov, len(last)))

    # 3) дом и выезд
    hh = [g for g in gh if g.get('h')][-10:]
    aw = [g for g in ga if not g.get('h')][-10:]
    if len(hh) >= 4 and len(aw) >= 4:
        hw_, aw_ = sum(outcome(g) == 'w' for g in hh), sum(outcome(g) == 'w' for g in aw)
        if hw_ / len(hh) >= .65 or aw_ / len(aw) <= .3 or hw_ / len(hh) <= .3 or aw_ / len(aw) >= .65:
            s.append('Дома %s: %s в %d матчах; в гостях %s: %s в %d.' % (h, fw(hw_), len(hh), a, fw(aw_), len(aw)))

    # 4) последняя очная встреча
    hr = h2h_rows(m)
    if hr:
        r = sorted(hr, key=lambda x: x['d'])[-1]
        hg, ag = (r['gf'], r['ga']) if r['home'] else (r['ga'], r['gf'])
        home, away = (h, a) if r['home'] else (a, h)
        s.append('Последняя очная встреча — %s.%s.%s: %s — %s %d:%d%s.' % (r['d'][8:10], r['d'][5:7], r['d'][:4], home, away, hg, ag, (' ' + r['x']) if r['x'] else ''))

    # 5) модель (до матча)
    md = m.get('md') or {}
    if m['res'] is None and md.get('p1') is not None:
        p1, p2 = md['p1'], md['p2']
        gap = abs(p1 - p2)
        lead, lp = (h, p1) if p1 >= p2 else (a, p2)
        if gap < .06:
            s.append('Модель не видит фаворита: шансы почти равны.')
        else:
            s.append('Модель чуть выше оценивает: %s — %d %%.' % (lead, round(lp * 100)) if gap < .15 else 'Фаворит по модели: %s — %d %%.' % (lead, round(lp * 100)))
        s[-1] += ' Это оценка по данным, а не обещание исхода.'
    return s


CD_JS = ('<script>/* отсчёт до начала (вид 2) */(function(){var e=document.querySelector(".mx-cd");if(!e)return;function f(){var t=Date.parse(e.dataset.t.replace(" ","T")+":00+03:00"),'
         's=Math.round((t-Date.now())/1000);if(s<=0){e.textContent=s>-3*3600?"идёт сейчас":"";return}var m=Math.floor(s/60),d=Math.floor(m/1440),h=Math.floor(m%1440/60),mi=m%60;'
         'e.textContent="через "+(d?d+" дн "+h+" ч":h?h+" ч "+mi+" мин":mi+" мин")}f();setInterval(f,30000)})();</script>\n')


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
        kind = 'прогноз на матч' if has_md(m) else 'превью матча'   # без расчёта модели слово «прогноз» не пишем (аудит 09.11b, п. 3)
        title = '%s: %s %s %s, %s' % (name, kind, dm, yr, lg_name(lg))
        h1b = '%s %s' % (kind, dm)
    if md and md.get('p1') is not None:
        pr = pct3(md)
        desc = '%s, %s, %s %s, %s МСК%s. Вероятности по модели: победа хозяев %d %%, ничья %d %%, гостей %d %%. Форма команд и личные встречи.' % (
            name, lg_name(lg), dm, wd, m['t'][11:16], (', ' + ar_txt) if ar_txt else '', pr[0], pr[1], pr[2])
        if fin:
            desc = '%s, %s, %s: итог %s. Расчёт модели до матча, форма команд и личные встречи.' % (name, lg_name(lg), dm, res_txt)
    else:
        desc = '%s, %s, %s %s, %s МСК%s. Форма команд, положение в таблице, личные встречи. Расчёт модели появится примерно за 1,5 суток до матча.' % (name, lg_name(lg), dm, wd, m['t'][11:16], (', ' + ar_txt) if ar_txt else '')
        if fin:
            desc = '%s, %s, %s: итог %s. Форма команд, положение в таблице, личные встречи.' % (name, lg_name(lg), dm, res_txt)
    sp_dir = 'hockey' if sport == 'hockey' else 'football'
    crumbs = [B.HOME, (B.SPORT_RU[sport], sp_dir + '/index.html'), lg_crumb(m) if fin else ('Прогноз на сегодня: ' + lg_name(lg), B.fc_rel(lg)), (name, rel)]
    facts = ['<li><small>Когда</small><b>%s, %s</b><span>%s МСК</span></li>' % (esc(dm), esc(wd), esc(m['t'][11:16]))]
    if ar_txt:
        extra = ''
        if ar and ar.get('capacity'):
            extra = '<span>вместимость %s</span>' % esc('{:,}'.format(ar['capacity']).replace(',', ' '))
        facts.append('<li><small>Арена</small><b>%s</b>%s</li>' % (esc(ar_txt), extra))
    facts.append('<li><small>Турнир</small><b><a href="%s">%s</a></b></li>' % (esc(lg_link(m, from_dir)), esc(lg_name(lg))))
    if fin:
        facts.insert(0, '<li class="mt-res"><small>Итог матча</small><b>%s</b></li>' % esc(res_txt))
    lv_box = '' if fin else '<div class="lv-box"%s></div>\n' % B.lv_attrs(m)
    rem = '' if fin else remind_block(m, name, sport)
    top = ('<section class="fc-top"><div class="wrap">\n%s\n<h1>%s<br><span>%s</span></h1>\n'
           '<div class="mt-teams">%s<span class="mt-vs" aria-hidden="true">—</span>%s</div>\n%s<ul class="mt-facts">%s</ul>\n%s'
           '<p class="fc-upd"><time datetime="%s">%s</time></p>\n</div></section>\n'
           % (B.crumbs_html(crumbs, rel), esc(name), esc(h1b), team_link(m, 'h', from_dir), team_link(m, 'a', from_dir), lv_box, ''.join(facts), rem,
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
        if not fin:
            mdl = model_stub(m, pre, o)
        elif o:
            mdl = '<section class="fc-sec"><div class="wrap"><div class="mt-md">%s</div></div></section>\n' % o
    pv = v2_summary(m) if V2 else preview_text(m)
    if isinstance(pv, list):   # вид 2: «Коротко о матче» — списком, по одной мысли в строке (владелец 10.11)
        prev = ('<section class="fc-sec" aria-labelledby="mt-pv"><div class="wrap"><h2 id="mt-pv">Коротко о матче</h2>'
                '<ul class="mx-sum">%s</ul></div></section>\n' % ''.join('<li>%s</li>' % esc(x) for x in pv)) if pv else ''
    else:
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
    if V2:
        cols = pair_cols(m)
        bgc = v2_bg(m, from_dir)
        if bgc:   # цвета баннера Telegram — и для полосы вероятностей; буквы тёмные только на очень светлом
            ink = lambda c: '#141a24' if _lum(c.lstrip('#')) > .55 else '#ffffff'  # noqa: E731
            cols = (bgc[0], bgc[1], ink(bgc[0]), ink(bgc[1]))
        top, info = v2_top(m, from_dir, fin, name, h1b, dm, wd, ar_txt, crumbs, rel, cols)
        body = top + v2_model(m, fin, pre, cols) + v2_mstats(m, fin, from_dir) + info + prev + v2_form(m, from_dir) + v2_h2h(m, from_dir) + table_block(m, from_dir) + other_matches(m, from_dir) + links
    else:
        body = top + mdl + prev + form_block(m, from_dir) + h2h_block(m) + table_block(m) + other_matches(m, from_dir) + links
    js = '<script>window.JV_ACT=%s;</script>\n' % json.dumps('khl' if lg == 'khl' else 'nhl' if lg == 'nhl' else 'ucl' if lg == 'ucl' else '' if sport == 'hockey' else 'lg')
    if V2:
        js += '<link rel="stylesheet" href="%sassets/matchx.css">\n' % pre
        body += CD_JS
    text = B.shell(rel, sport, body, extra_css='match.css', head_js=js,
                   extra_scripts='' if fin else '<script src="%sassets/live.js" defer></script>\n' % pre)
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
    og_rel = from_dir + '/og.jpg'
    try:
        og_match.draw(m, os.path.join(og_match.V3A, og_rel), lg_name(lg), '%s, %s · %s МСК' % (dm, wd, m['t'][11:16]))
    except Exception as e:  # noqa: BLE001
        print('og.jpg не нарисован %s: %r' % (rel, e))
        og_rel = 'assets/og/og-%s.png' % ('khl' if lg == 'khl' else 'nhl' if lg == 'nhl' else sport)
    P = dict(title=title, desc=desc, og=og_rel,
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
