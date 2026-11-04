# -*- coding: utf-8 -*-
"""Нарезка тяжёлых данных макета v3a на лёгкие файлы (владелец 04.11: «ускорить сайт, особенно на телефоне»).
Запуск: python team/site/v3a/daily/split.py   (без сети; входы — teams.json, football.json, players.js, *_players.json;
в конвейере — шаг `split` в run.py, последним перед `search`).

Что получается (страницы грузят только нужное; полные файлы остаются для сборщиков и поиска):
  Хоккей
    assets/data/teams-lite.js        JV_TEAMS без pl / h2h / picks (таблица, названия, цвета, оси, матчи сезона) — для всех страниц
    assets/data/club/<slug>.js       pl / h2h / picks одного клуба: дописывает их в JV_TEAMS.teams[slug] (страница клуба)
    hockey/data/plite_khl.json, plite_nhl.json   игроки для hockey/players*.html и трендов: короткий лог [дата, соперник, дома, г, п, б, toi]
    hockey/data/players/<slug>.json  {имя: фото} игроков клуба (плашка «Игроки» на странице клуба)
    hockey/data/pid/<slug>.json      {имя: id} игроков клуба (ссылки на профиль из таблицы клуба)
    hockey/data/pp/<лига>/<id>.json  профиль одного игрока (hockey/player.html, 1–4 КБ): шапка, итоги, полный лог сезона, следующий матч
  Футбол
    football/data/football-lite.js   JV_FOOT без games / sc / cd / scx / cdx / cx у клубов и без h2h (таблицы, клубы, лиги, up)
    football/data/games.js           games всех клубов + личные встречи только для пар из «ближайших матчей» (главная, ЦЛ, лиги)
    football/data/club/<id>.js       games / sc / cd / scx / cdx / cx клуба + games / cx соперников ближайших матчей + h2h клуба
    football/data/pl/<лига>.js       JV_PLAYERS.players: топ-15 бомбардиров и топ-10 по карточкам лиги (league.html)
    football/data/pl/trends.js       JV_PLAYERS.players: только то, что нужно трендам (t, n, f, sg)
  Раздел «Игроки» футбола (players.js, players.html) не трогаем — скрыт владельцем.
"""
import json, os, re, shutil, sys

V3A = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SEP = (',', ':')


def jd(o):
    return json.dumps(o, ensure_ascii=False, separators=SEP)


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def write(p, s):
    # имена файлов берутся из данных (slug клуба и т. п.): выйти из папки макета нельзя (защита от ../ во внешних данных)
    if os.path.commonpath([V3A, os.path.abspath(p)]) != V3A:
        raise ValueError('запись вне папки макета: %r' % p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)


def fresh(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)


def nhl_abbr(slug):
    return {'minnesota': 'MIN', 'dallas': 'DAL'}.get(slug, slug.replace('nhl_', '').upper())


# ───────────────────────────── хоккей ─────────────────────────────
def write_profile(ppdir, lg, p, slug, sl, nx, tpl):
    """Профиль одного игрока: hockey/data/pp/<лига>/<id>.json.
    log: [дата, соперник(slug), дома, г, п, броски, toi сек, штраф]; итоги +/-, штраф, броски — из таблицы клуба (teams.json pl.sk),
    если игрок там найден по имени (иначе считаются по логу, +/- тогда нет)."""
    log = [[r[0][:10], sl(r[2]), r[3], r[4], r[5], r[6], r[7], r[8] if len(r) > 8 else 0] for r in p.get('log', [])]
    q = {'n': p['n'], 't': slug, 'pos': p.get('pos'), 'log': log}
    for k in ('no', 'img', 'gp'):
        if p.get(k) not in (None, ''):
            q[k] = p[k]
    if p.get('toi_avg') is not None:
        q['ts'] = int(round(p['toi_avg'] * 60))
    for x in (tpl or {}).get('sk', []):
        if x.get('n') == p['n']:
            for k in ('pm', 'pim', 'sog'):
                if x.get(k) is not None:
                    q['s' + k] = x[k]
            if x.get('gp') is not None:
                q['sgp'] = x['gp']
            break
    if nx:
        q['nx'] = {'o': sl(nx['o']), 'h': nx['h'], 'd': nx['d'][:16]}
    write(os.path.join(ppdir, lg, '%s.json' % p['id']), jd(q))
    return 1


def hockey():
    d = load(os.path.join(V3A, 'assets', 'data', 'teams.json'))
    heavy = ('pl', 'h2h', 'picks')
    lite = dict(d)
    lite['teams'] = {s: {k: v for k, v in t.items() if k not in heavy} for s, t in d['teams'].items()}
    write(os.path.join(V3A, 'assets', 'data', 'teams-lite.js'), 'window.JV_TEAMS=' + jd(lite) + ';')
    cdir = os.path.join(V3A, 'assets', 'data', 'club')
    fresh(cdir)
    for s, t in d['teams'].items():
        part = {k: t[k] for k in heavy if k in t}
        write(os.path.join(cdir, s + '.js'),
              'Object.assign(window.JV_TEAMS.teams[%s],%s);' % (jd(s), jd(part)))
    # игроки
    hd = os.path.join(V3A, 'hockey', 'data')
    slug_of = {}
    for s, t in d['teams'].items():
        if t.get('lg') == 'nhl':
            slug_of[nhl_abbr(s)] = s
    pdir = os.path.join(hd, 'players')
    fresh(pdir)
    iddir = os.path.join(hd, 'pid')
    fresh(iddir)
    ppdir = os.path.join(hd, 'pp')
    fresh(ppdir)
    ppn = 0
    tot = 0
    for lg in ('khl', 'nhl'):
        src = os.path.join(hd, lg + '_players.json')
        if not os.path.exists(src):
            continue
        j = load(src)
        out, byteam, idteam = [], {}, {}
        sl = (lambda a: slug_of.get(a, a)) if lg == 'nhl' else (lambda a: a)
        nxt = j.get('next', {})
        for p in j.get('players', []):
            log = [[r[0][:10], r[2], r[3], r[4], r[5], r[6], r[7]] for r in p.get('log', [])]
            q = {'n': p['n'], 't': p['t'], 'pos': p.get('pos'), 'log': log}
            if p.get('id') is not None:
                q['id'] = p['id']
            for k in ('no', 'img', 'gp'):
                if p.get(k) not in (None, ''):
                    q[k] = p[k]
            if p.get('toi_avg') is not None:
                q['ts'] = int(round(p['toi_avg'] * 60))          # среднее время на льду, секунды (страница рисует мм:сс)
            out.append(q)
            slug = p['t'] if lg == 'khl' else slug_of.get(p['t'])
            if slug and p.get('img'):
                byteam.setdefault(slug, {})[p['n']] = p['img']
            if slug and p.get('id') is not None:
                idteam.setdefault(slug, {})[p['n']] = p['id']
                ppn += write_profile(ppdir, lg, p, slug, sl, nxt.get(p['t']), d['teams'].get(slug, {}).get('pl'))
        lj = {'built': j.get('built'), 'season': j.get('season'), 'next': j.get('next', {}), 'players': out}
        write(os.path.join(hd, 'plite_%s.json' % lg), jd(lj))
        for slug, m in byteam.items():
            write(os.path.join(pdir, slug + '.json'), jd(m))
        for slug, m in idteam.items():
            write(os.path.join(iddir, slug + '.json'), jd(m))
        tot += len(out)
    return 'хоккей: клубов %d, игроков %d, профилей %d' % (len(d['teams']), tot, ppn)


# ───────────────────────────── футбол ─────────────────────────────
HEAVY_F = ('games', 'sc', 'cd', 'scx', 'cdx', 'cx')


def football():
    fd = os.path.join(V3A, 'football', 'data')
    d = load(os.path.join(fd, 'football.json'))
    teams = d['teams']
    lite = {k: v for k, v in d.items() if k not in ('teams', 'h2h')}
    lite['teams'] = {s: {k: v for k, v in t.items() if k not in HEAVY_F} for s, t in teams.items()}
    lite['h2h'] = {}
    write(os.path.join(fd, 'football-lite.js'), 'window.JV_FOOT=' + jd(lite) + ';')
    # games.js — для страниц, где нужны матчи всех клубов; h2h — только для пар из ближайших матчей
    pairs = {'|'.join(sorted([m['h'], m['a']])) for m in d.get('up', [])}
    h2h_up = {k: v for k, v in d.get('h2h', {}).items() if k in pairs}
    g = {s: t['games'] for s, t in teams.items() if t.get('games')}
    write(os.path.join(fd, 'games.js'),
          '(function(F){var G=%s,H=%s,s;for(s in G)if(F.teams[s])F.teams[s].games=G[s];Object.assign(F.h2h,H)})(window.JV_FOOT);' % (jd(g), jd(h2h_up)))
    # club/<id>.js
    cdir = os.path.join(fd, 'club')
    fresh(cdir)
    for s, t in teams.items():
        mine = {k: t[k] for k in HEAVY_F if k in t}
        opp = []
        fut = sorted([x for x in t.get('games', []) if x.get('gf') is None], key=lambda x: x['d'])
        seen = {}
        for x in fut:                                   # соперники ближайших матчей каждого турнира (лига / кубки)
            c = x.get('c') or ''
            seen.setdefault(c, [])
            if len(seen[c]) < 4 and x['o'] not in seen[c]:
                seen[c].append(x['o'])
        for c in seen.values():
            for o in c:
                if o not in opp and o != s and o in teams:
                    opp.append(o)
        for x in fut[:6]:
            if x['o'] not in opp and x['o'] != s and x['o'] in teams:
                opp.append(x['o'])
        om = {o: {k: teams[o][k] for k in ('games', 'cx') if k in teams[o]} for o in opp}
        hh = {k: v for k, v in d.get('h2h', {}).items() if s in k.split('|')}
        write(os.path.join(cdir, s + '.js'),
              '(function(F){var M=%s,O=%s,H=%s,s;Object.assign(F.teams[%s],M);for(s in O)if(F.teams[s])Object.assign(F.teams[s],O[s]);Object.assign(F.h2h,H)})(window.JV_FOOT);'
              % (jd(mine), jd(om), jd(hh), jd(s)))
    # игроки: по лигам (бомбардиры/карточки) и для трендов
    pj = os.path.join(fd, 'players.js')
    n = 0
    if os.path.exists(pj):
        s = open(pj, encoding='utf-8').read()
        P = json.loads(s[s.index('=') + 1:].strip().rstrip(';'))
        pdir = os.path.join(fd, 'pl')
        fresh(pdir)
        pl = P.get('players', [])
        keys = ('id', 'n', 't', 'lg', 'G', 'pen', 'y', 'r', 'sg')
        for lg in d['leagues']:
            a = [p for p in pl if p.get('lg') == lg]
            sc = sorted([p for p in a if (p.get('G') or 0) > 0], key=lambda p: (-(p['G'] or 0), p.get('pen') or 0, p['n']))[:15]
            cd = sorted([p for p in a if (p.get('y') or 0) + (p.get('r') or 0) > 0],
                        key=lambda p: (-((p.get('y') or 0) + (p.get('r') or 0) * 2), -(p.get('r') or 0), p['n']))[:10]
            pick, ids = [], set()
            for p in sc + cd:
                if p['id'] not in ids:
                    ids.add(p['id'])
                    pick.append({k: p[k] for k in keys if k in p})
            write(os.path.join(pdir, lg + '.js'), 'window.JV_PLAYERS={players:%s};' % jd(pick))
        tr = [{k: p[k] for k in ('t', 'n', 'f', 'sg') if k in p} for p in pl if p.get('f')]
        write(os.path.join(pdir, 'trends.js'), 'window.JV_PLAYERS={players:%s};' % jd(tr))
        n = len(pl)
    return 'футбол: клубов %d, игроков в исходнике %d' % (len(teams), n)


def main():
    out = []
    for fn in (hockey, football):
        try:
            out.append(fn())
        except Exception as e:  # noqa: BLE001
            out.append('ОШИБКА %s: %s' % (fn.__name__, e))
            raise
    return '; '.join(out)


if __name__ == '__main__':
    print(main())
