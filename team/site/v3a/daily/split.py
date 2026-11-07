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
def _kst(st, *pats):
    """показатель КХЛ из p['st'] по подстроке имени (приложение отдаёт id вида hits, blocked_shots и т.п.)"""
    for k, v in (st or {}).items():
        kl = str(k).lower()
        if any(x in kl for x in pats) and isinstance(v, (int, float)):
            return float(v)
    return None


def skills(lg, players):
    """Пятиугольник навыков как в играх EA NHL (владелец 07.11): Катание, Бросок, Руки, Силовая, Оборона. Свои рейтинги из
    статистики лиги (рейтинги EA не копируем): процентиль 0–100 среди игроков своей лиги и группы (защитники / нападающие),
    у кого от 5 матчей. Ось = взвешенное среднее процентилей компонентов, затем процентиль итога по группе.
    НХЛ: данные hockey/data/nhl_skills.json (stats API + NHL EDGE). КХЛ: приложение отдаёт только игры, голы, передачи, время
    (+ что окажется в p['st']): недостающие компоненты заменены ближайшими (комментарии ниже)."""
    sk = {}
    if lg == 'nhl':
        try:
            sk = load(os.path.join(V3A, 'hockey', 'data', 'nhl_skills.json')).get('p', {})
        except Exception:  # noqa: BLE001
            sk = {}
    raw = {}
    for p in players:
        L = p.get('log', [])
        n = len(L)
        if not n:
            continue
        pid = p.get('id')
        grp = 'D' if p.get('pos') == 'D' else 'F'
        g = sum(r[4] or 0 for r in L); a = sum(r[5] or 0 for r in L); sh = sum(r[6] or 0 for r in L)
        tv = [r[7] for r in L if r[7]]
        toi = (sum(tv) / len(tv) / 60) if tv else (p.get('toi_avg') or 0)
        c = {}                                   # компоненты: ось -> {имя: (значение, вес)}
        if lg == 'nhl':
            e = sk.get(str(pid)) or {}
            gp = e.get('gp') or n
            m60 = (e.get('toi') or toi * 60) * gp / 3600.0 or None      # минуты на льду за сезон / 60
            def r60(k):
                return e[k] / m60 if e.get(k) is not None and m60 else None
            tg = (e['tk'] - e['gv']) / m60 if e.get('tk') is not None and e.get('gv') is not None and m60 else None
            c['Катание'] = {'spd': (e.get('spd'), 1), 'bur': (e['bur'] / gp if e.get('bur') is not None else None, 1),
                            'toi': (toi if e.get('spd') is None else None, 1)}    # без EDGE — время на льду
            c['Бросок'] = {'sog': (sh / n, 1), 'shp': (g / sh if sh >= 5 else None, 1), 'shot': (e.get('shot'), 1)}
            c['Руки'] = {'a': (a / n, 1), 'tkgv': (tg, 1)}
            c['Силовая'] = {'hit': (r60('hit'), 1), 'pim': (e['pim'] / gp if e.get('pim') is not None else None, .3)}
            c['Оборона'] = {'blk': (r60('blk'), 1), 'tk': (r60('tk'), 1), 'pm': (e.get('pm'), 1),
                            'fo': (e.get('fo') if p.get('pos') == 'C' and (e.get('fon') or 0) >= 100 else None, 1)}
        else:
            st = p.get('st') or {}
            gp = p.get('gp') or n
            hit = _kst(st, 'hit'); blk = _kst(st, 'block', 'blk'); shots = _kst(st, 'shot')
            pim = _kst(st, 'pim', 'penalt'); pm = _kst(st, 'plus', 'pm'); fo = _kst(st, 'faceoff', 'fo_')
            c['Катание'] = {'toi': (toi, 1)}                                     # скорости нет — время на льду
            c['Бросок'] = {'g': (g / n, 1), 'sog': (shots / gp if shots is not None else None, 1)}   # бросков в приложении нет — голы за игру
            c['Руки'] = {'a': (a / n, 1)}
            c['Силовая'] = {'hit': (hit / gp if hit is not None else None, 1), 'pim': (pim / gp if pim is not None else None, .3 if hit is not None else 1)}
            c['Оборона'] = {'blk': (blk / gp if blk is not None else None, 1), 'pm': (pm, 1),
                            'fo': (fo if p.get('pos') == 'C' else None, 1)}
        raw[pid] = {'grp': grp, 'n': n, 'c': c}
    out = {}
    for grp in ('D', 'F'):
        pool = {k: v for k, v in raw.items() if v['grp'] == grp and v['n'] >= 5}
        if len(pool) < 10:
            continue
        ax = {}                                  # ось -> {id: взвешенное среднее процентилей компонентов}
        for name in ('Катание', 'Бросок', 'Руки', 'Силовая', 'Оборона'):
            comp = {}
            for k, v in pool.items():
                for cn, (val, w) in v['c'][name].items():
                    if val is not None:
                        comp.setdefault(cn, []).append((k, val, w))
            sc = {}
            for cn, arr in comp.items():
                if len(arr) < 10:
                    continue
                vals = [x[1] for x in arr]
                for k, val, w in arr:             # процентиль со средним рангом при равенстве (иначе нули у «пустых» показателей)
                    lo = sum(1 for x in vals if x < val); eq = sum(1 for x in vals if x == val)
                    sc.setdefault(k, []).append((100.0 * (lo + (eq - 1) / 2.0) / (len(vals) - 1), w))
            ax[name] = {k: sum(p * w for p, w in v) / sum(w for _, w in v) for k, v in sc.items()}
        for k, v in raw.items():
            if v['grp'] != grp:
                continue
            row = []
            for name in ('Катание', 'Бросок', 'Руки', 'Силовая', 'Оборона'):
                a_ = ax.get(name, {})
                if k not in a_:
                    row = None
                    break
                allv = list(a_.values())
                row.append([name, round(100 * sum(1 for x in allv if x < a_[k]) / len(allv))])
            if row:
                out[k] = row
    return out


def write_profile(ppdir, lg, p, slug, sl, nx, tpl, games=None, sk=None):
    """Профиль одного игрока: hockey/data/pp/<лига>/<id>.json.
    log: [дата, соперник(slug), дома, г, п, броски, toi сек, штраф, (счёт [свои, чужие, ОТ/Б])]; итоги +/-, штраф, броски — из таблицы клуба (teams.json pl.sk),
    если игрок там найден по имени (иначе считаются по логу, +/- тогда нет)."""
    log = [[r[0][:10], sl(r[2]), r[3], r[4], r[5], r[6], r[7], r[8] if len(r) > 8 else 0] for r in p.get('log', [])]
    # счёт матча клуба (владелец 07.11: «результат матча слева и справа»): [забил клуб, пропустил, 'ОТ'/'Б'/''] по дате и сопернику
    gm = {}
    for g in games or []:
        gm.setdefault((g.get('d', '')[:10], g.get('o')), g)
    for r in log:
        g = gm.get((r[0], r[1]))
        if g and g.get('gf') is not None and g.get('ga') is not None:
            r.append([g['gf'], g['ga'], g.get('x') or ''])
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
    if sk:
        q['sk'] = sk
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
        SK = skills(lg, j.get('players', []))
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
                ppn += write_profile(ppdir, lg, p, slug, sl, nxt.get(p['t']), d['teams'].get(slug, {}).get('pl'), d['teams'].get(slug, {}).get('games'), SK.get(p.get('id')))
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
