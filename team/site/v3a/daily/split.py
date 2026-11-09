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
    hockey/data/lgp_<лига>.json      страница лиги: матчи сезона (хозяева) и итоги игроков без лога
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
# Веса компонентов и масштаб осей (рейтинг = a + b·Z, Z — нормированная по группе ось; медиана по лиге ≈ 74, 95+ — редкость).
# Веса подобраны так, чтобы шкала была похожа на игровую. W[лига][группа F/D][ось][компонент] = вес; S[лига][группа][ось] = (a, b).
_NF = {'Катание': {'bur': .75, 'toi2': 1}, 'Бросок': {'shot': 1, 'shp': .25, 'sog': 1}, 'Руки': {'p60': 1, 'tk': .25},
       'Интеллект': {'a60': .5, 'inv': 1}, 'Оборона': {'blk': 1, 'fo': .25, 'tk': .25, 'toi': 1}}
_ND = {'Катание': {'bur': .75, 'spd': .25, 'toi2': 1}, 'Бросок': {'shot': .5, 'sog': 1}, 'Руки': {'p60': 1},
       'Интеллект': {'a60': .25, 'inv': 1}, 'Оборона': {'blk': 1, 'pm': .25, 'toi': .5}}
_KH = {'Катание': {'spd': 1, 'dist': 1, 'toi': .5}, 'Бросок': {'g': 1}, 'Руки': {'pts': 1},
       'Интеллект': {'a': 1, 'inv': 1}, 'Оборона': {'pm': 1, 'toi': .5, 'fo': 1}}      # КХЛ: веса по смыслу
W = {'nhl': {'F': _NF, 'D': _ND}, 'khl': {'F': _KH, 'D': _KH}}
_AX = ('Катание', 'Бросок', 'Руки', 'Интеллект', 'Оборона')
S = {'nhl': {'F': dict(zip(_AX, [(74, 9), (74, 9), (75, 8), (76, 8), (74, 7)])),
             'D': dict(zip(_AX, [(75, 8), (75, 7), (75, 6), (76, 7), (74, 6)]))},
     'khl': {g: {a: (74, 8) for a in _AX} for g in 'FD'}}


DBG = None          # для подбора весов: словарь, куда складываются z компонентов


def skills(lg, players, tgf=None):
    """Пятиугольник навыков как в играх EA NHL (владелец 07.11): Катание, Бросок, Руки, Интеллект, Оборона
    (Интеллект вместо Силовой — владелец 07.11: «находить передачи, интеллектуальная работа»). Свои рейтинги из
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
        # участие в голах команды: (голы + передачи) / голы команды в его матчах
        tg_ = [tgf(r[1], r[0][:10]) for r in L] if tgf else []
        tgs = sum(x for x in tg_ if x is not None)
        inv = (g + a) / tgs if tgs >= 10 else None
        c = {}                                   # компоненты: ось -> {имя: значение}; веса — таблица W ниже
        if lg == 'nhl':
            e = sk.get(str(pid)) or {}
            gp = e.get('gp') or n
            m60 = (e.get('toi') or toi * 60) * gp / 3600.0 or None      # минуты на льду за сезон / 60
            def r60(k):
                return e[k] / m60 if e.get(k) is not None and m60 else None
            c['Катание'] = {'spd': e.get('spd'), 'bur': e['bur'] / gp if e.get('bur') is not None else None,
                            'toi': toi if e.get('spd') is None else None, 'toi2': toi}   # без EDGE — время на льду
            c['Бросок'] = {'sog': sh / n, 'shp': g / sh if sh >= 5 else None, 'shot': e.get('shot'), 'g60': g / m60 if m60 else None}
            c['Руки'] = {'p60': (g + a) / m60 if m60 else None, 'tk': r60('tk'), 'gv': -r60('gv') if r60('gv') is not None else None}
            c['Интеллект'] = {'a60': a / m60 if m60 else None, 'inv': inv, 'tk': r60('tk'),
                              'gv': -r60('gv') if r60('gv') is not None else None}
            c['Оборона'] = {'blk': r60('blk'), 'tk': r60('tk'), 'pm': e.get('pm'), 'hit': r60('hit'), 'toi': toi,
                            'fo': e.get('fo') if p.get('pos') == 'C' and (e.get('fon') or 0) >= 100 else None}
        else:
            st = p.get('st') or {}
            gp = p.get('gp') or n
            # приложение КХЛ отдаёт: top_speed (км/ч), distance_travelled (км за сезон), fow (выигранные вбрасывания, штуки), pim, pm,
            # sft_avg (средняя смена, с), toi_avg. Силовых приёмов, блок-шотов, бросков, отборов/потерь НЕТ — замены ниже.
            spd = st.get('top_speed') or None; dist = st.get('distance_travelled') or None
            fow = st.get('fow'); pm = st.get('pm')
            c['Катание'] = {'spd': spd, 'dist': dist / gp if dist else None, 'toi': toi}      # скорость + пробег за игру + время
            c['Бросок'] = {'g': g / n}                                            # бросков нет — голы за игру
            c['Руки'] = {'pts': (g + a) / n}                                      # отборов/потерь нет — очки за игру
            c['Интеллект'] = {'a': a / n, 'inv': inv}                             # передачи за игру + участие в голах команды
            c['Оборона'] = {'pm': pm, 'toi': toi if grp == 'D' else None,         # блоков нет — плюс-минус (+ время у защитников)
                            'fo': fow / gp if grp == 'F' and (fow or 0) >= 30 else None}   # позиции C в приложении нет: центр = от 30 выигранных вбрасываний
        raw[pid] = {'grp': grp, 'n': n, 'c': c}
    out = {}
    AX = ('Катание', 'Бросок', 'Руки', 'Интеллект', 'Оборона')
    # Шкала как у рейтингов в играх (владелец 07.11: «у Маккиннона почти всё 100 — непропорционально»): не процентиль, а
    # рейтинг по отклонению от среднего группы: компонент -> z (выбросы обрезаны ±3), ось = взвешенное среднее z,
    # затем ось ещё раз нормируется по группе и переводится в 35–99 по таблице S (медиана ≈ 74). Звёзды — 85–97, слабая сторона видна.
    def zs(vals):
        m = sum(vals) / len(vals)
        sd = (sum((x - m) ** 2 for x in vals) / len(vals)) ** .5 or 1.0
        return m, sd
    for grp in ('D', 'F'):
        pool = {k: v for k, v in raw.items() if v['grp'] == grp and v['n'] >= 5}
        if len(pool) < 10:
            continue
        axz = {}
        for name in AX:
            comp = {}
            for k, v in pool.items():
                for cn, val in v['c'][name].items():
                    w = W[lg][grp][name].get(cn, 0)
                    if val is not None and w > 0:
                        comp.setdefault(cn, []).append((k, val, w))
            acc = {}
            for cn, arr in comp.items():
                if len(arr) < 10:
                    continue
                m, sd = zs([x[1] for x in arr])
                for k, val, w in arr:
                    zc = max(-3.0, min(3.0, (val - m) / sd))
                    acc.setdefault(k, []).append((zc, w))
                    if DBG is not None:
                        DBG.setdefault((lg, grp, name), {}).setdefault(k, {})[cn] = zc
            zz = {k: sum(z * w for z, w in v) / sum(w for _, w in v) for k, v in acc.items()}
            if zz:
                m, sd = zs(list(zz.values()))
                axz[name] = {k: (z - m) / sd for k, z in zz.items()}
        for k, v in raw.items():
            if v['grp'] != grp:
                continue
            row = []
            for name in AX:
                a_ = axz.get(name, {})
                if k not in a_:
                    row = None
                    break
                a0, b0 = S[lg][grp][name]
                row.append([name, int(max(35, min(99, round(a0 + b0 * a_[k]))))])
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
        abbr_of = {v: k for k, v in slug_of.items()}
        GF = {}
        for s_, t_ in d['teams'].items():
            if t_.get('lg') != lg:
                continue
            key_ = abbr_of.get(s_, s_) if lg == 'nhl' else s_
            for gm_ in t_.get('games') or []:
                if gm_.get('gf') is not None:
                    GF[(key_, gm_.get('d', '')[:10])] = gm_['gf']
        SK = skills(lg, j.get('players', []), lambda tm, dt: GF.get((tm, dt)))
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
        for t_, m_ in (j.get('gimg') or {}).items():                  # фото вратарей (лучший вратарь на странице клуба)
            slug = t_ if lg == 'khl' else slug_of.get(t_)
            if slug:
                byteam.setdefault(slug, {}).update(m_)
        lj = {'built': j.get('built'), 'season': j.get('season'), 'next': j.get('next', {}), 'players': out}
        write(os.path.join(hd, 'plite_%s.json' % lg), jd(lj))
        for slug, m in byteam.items():
            write(os.path.join(pdir, slug + '.json'), jd(m))
        for slug, m in idteam.items():
            write(os.path.join(iddir, slug + '.json'), jd(m))
        tot += len(out)
    lgp = league_pages()
    return 'хоккей: клубов %d, игроков %d, профилей %d, лиги %s' % (len(d['teams']), tot, ppn, ', '.join(lgp))


def league_pages():
    """hockey/data/lgp_<лига>.json — всё для страницы лиги (hockey/league.html) одним маленьким файлом (09.11):
    матчи сезона только со стороны хозяев (из team/season.json) и итоги игроков без полного лога (из <лига>_players.json)."""
    se = load(os.path.join(V3A, 'team', 'season.json'))
    out = []
    for lg in ('khl', 'nhl'):
        pp = os.path.join(V3A, 'hockey', 'data', lg + '_players.json')
        pl = load(pp) if os.path.exists(pp) else {'players': []}
        ps = []
        for x in pl.get('players') or []:
            lgl = x.get('log') or []
            sm = lambda i: sum((r[i] or 0) for r in lgl if len(r) > i and isinstance(r[i], (int, float)))
            if lg == 'nhl':
                gp = len(lgl)
                t = [r[7] for r in lgl if len(r) > 7 and r[7]]
                toi = round(sum(t) / len(t) / 60, 3) if t else None
            else:
                gp = int(x.get('gp') or 0)
                toi = round(float(x['toi_avg']), 3) if x.get('toi_avg') else None
            st = [sm(4), sm(5), sm(6), sm(8)]
            if not gp and not any(st):
                continue
            ps.append({'n': x.get('n'), 't': x.get('t'), 'img': x.get('img') or '', 'gp': gp, 's': st, 'toi': toi})
        games = {name: {'games': [g for g in (t.get('games') or []) if g.get('h') == 1]} for name, t in (se.get(lg) or {}).items()}
        write(os.path.join(V3A, 'hockey', 'data', 'lgp_' + lg + '.json'),
              jd({'season': pl.get('season'), 'next': pl.get('next'), 'players': ps, 'se': games}))
        out.append('%s %d' % (lg, len(ps)))
    return out


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
