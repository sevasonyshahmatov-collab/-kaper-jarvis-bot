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
    football/data/football-club.js   то же без up — для страницы клуба (football/team.html и копии <лига>/<клуб>/)
    football/data/football-lite.js   JV_FOOT без games / sc / cd / scx / cdx / cx у клубов и без h2h (таблицы, клубы, лиги, up)
    football/data/games.js           games всех клубов без ударов/угловых + личные встречи пар из «ближайших матчей» (футбол, ЛЧ, лиги)
    football/data/games-xy.js        удары, угловые, владение к games.js — грузится при раскрытии матча (foot-index.js)
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
       'Передачи': {'a60': 1, 'inv': .5}, 'Оборона': {'blk': 1, 'fo': .25, 'tk': .25, 'toi': 1}}
_ND = {'Катание': {'bur': .75, 'spd': .25, 'toi2': 1}, 'Бросок': {'shot': .5, 'sog': 1}, 'Руки': {'p60': 1},
       'Передачи': {'a60': 1, 'inv': .5}, 'Оборона': {'blk': 1, 'pm': .25, 'toi': .5}}
_KH = {'Катание': {'spd': 1, 'dist': 1, 'toi': .5}, 'Бросок': {'g': 1}, 'Руки': {'pts': 1},
       'Передачи': {'a': 1, 'inv': .5}, 'Оборона': {'pm': 1, 'toi': .5, 'fo': 1}}      # КХЛ: веса по смыслу
W = {'nhl': {'F': _NF, 'D': _ND}, 'khl': {'F': _KH, 'D': _KH}}
_AX = ('Катание', 'Бросок', 'Руки', 'Передачи', 'Оборона')
S = {'nhl': {'F': dict(zip(_AX, [(74, 9), (74, 9), (75, 8), (76, 8), (74, 7)])),
             'D': dict(zip(_AX, [(75, 8), (75, 7), (75, 6), (76, 7), (74, 6)]))},
     'khl': {g: {a: (74, 8) for a in _AX} for g in 'FD'}}


DBG = None          # для подбора весов: словарь, куда складываются z компонентов


def skills(lg, players, tgf=None):
    """Пятиугольник навыков как в играх EA NHL (владелец 07.11): Катание, Бросок, Руки, Передачи, Оборона
    (07.11 — «Интеллект» вместо Силовой, 18.11 — «Передачи» вместо «Интеллекта» — владелец 07.11: «находить передачи, интеллектуальная работа»). Свои рейтинги из
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
            c['Передачи'] = {'a60': a / m60 if m60 else None, 'inv': inv, 'tk': r60('tk'),
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
            c['Передачи'] = {'a': a / n, 'inv': inv}                             # передачи за игру + участие в голах команды
            c['Оборона'] = {'pm': pm, 'toi': toi if grp == 'D' else None,         # блоков нет — плюс-минус (+ время у защитников)
                            'fo': fow / gp if grp == 'F' and (fow or 0) >= 30 else None}   # позиции C в приложении нет: центр = от 30 выигранных вбрасываний
        raw[pid] = {'grp': grp, 'n': n, 'c': c}
    out = {}
    AXZ = {}
    AX = ('Катание', 'Бросок', 'Руки', 'Передачи', 'Оборона')
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
        AXZ[grp] = axz
    # Пересчёт 15.11 (владелец: «у многих 90+, так не бывает; 99 — это катание Макдэвида, интеллект Кучерова, бросок Капризова»):
    # рейтинг — по МЕСТУ в лиге, а не по отклонению от среднего. Ось нормирована внутри своей группы (нападающие / защитники),
    # места — внутри своей группы; у кого мало матчей — оценка поджимается к середине (n / (n + 8)).
    # Шкала (до 17.11): 1-е место в лиге — 99, 2-е — 97, 3-е — 95; остальные — по доле игроков ниже: 99-й процентиль ≈ 90,
    # 95-й ≈ 85, 80-й ≈ 78, медиана ≈ 70, худшие ≈ 45. Итог: 90+ — около 1 % лиги (6–7 игроков на ось в НХЛ), 99 — один.
    # 17.11 (владелец: «у многих не очень сильных игроков завышенные показатели; 99 — один на лигу»): шкала строже —
    # медиана 60, 80-й процентиль 70, 95-й 79, 99-й 87; места 1–3 — 99 / 96 / 93, остальные не выше 91.
    CURVE = ((0.0, 40), (0.5, 60), (0.8, 70), (0.95, 79), (0.99, 87), (1.0, 91))
    def curve(q):
        for (q0, r0), (q1, r1) in zip(CURVE, CURVE[1:]):
            if q <= q1:
                return r0 + (r1 - r0) * (q - q0) / (q1 - q0 or 1)
        return CURVE[-1][1]
    # 99 по атакующим навыкам — только у нападающего, по обороне — только у защитника; лучший из «чужой» группы — не выше 95
    # (иначе лучший защитник по очкам обгонял Макдэвида в «Руках»). Места считаются внутри своей группы.
    rat = {}
    for name in AX:
        for grp, axz in AXZ.items():
            sc = sorted(((z * raw[k]['n'] / (raw[k]['n'] + 8.0), k) for k, z in axz.get(name, {}).items()), reverse=True)
            N = len(sc)
            own = (name == 'Оборона') == (grp == 'D')
            top = (99, 96, 93) if own else (93, 90, 87)
            cap = 91 if own else 86
            for r, (_, k) in enumerate(sc):
                val = top[r] if r < 3 and N >= 30 else min(cap, curve(1 - r / max(1, N - 1)))
                rat.setdefault(k, {})[name] = int(round(val))
    # 18.11 владелец: ось «Интеллект» заменена на «Передачи» (в игре — атрибут passing; по статистике — передачи за 60 минут
    # и участие в голах команды).
    # 18.11 (владелец: «возьми рейтинги из NHL 27 и убавь все пункты кроме самых больших на 2, а у самого лучшего аспекта
    # на 1»): у игроков из рейтингов игры EA NHL 27 (300 лучших, hockey/data/nhl_ea.json, собирает hockey/ea_axes.py) оценка —
    # среднее атрибутов игры по оси (округлено); лучший навык игрока — минус 1, остальные — минус 2. Эталоны ниже к ним
    # не применяются. Остальным игрокам — оценка по статистике, не выше 80 (ниже почти всех игроков из рейтингов игры).
    ea_ids = set()
    if lg == 'nhl':
        try:
            ea = load(os.path.join(V3A, 'hockey', 'data', 'nhl_ea.json')).get('p', {})
        except Exception:  # noqa: BLE001
            ea = {}
        if len(ea) >= 100:
            for k, v in rat.items():
                e = ea.get(str(k))
                if e and all(name in e for name in AX):
                    r = {name: int(round(e[name])) for name in AX}
                    best = max(r.values())
                    for name in AX:
                        v[name] = max(40, min(99, r[name] - (1 if r[name] == best else 2)))
                    ea_ids.add(k)
                else:
                    for name in AX:
                        if name in v:
                            v[name] = min(v[name], 80)
    # Эталоны владельца (17.11): «интеллект у Кучерова — самый высокий в хоккее: 99, остальные — относительно него;
    # у Макдэвида — 90». Эталонным игрокам — их оценка; остальные по этой оси — не выше 91, порядок по статистике сохраняется.
    # 18.11: при рейтингах игры (ea_ids) эталоны не применяются — владелец выбрал цифры игры.
    for name, fixed in ({} if ea_ids else ANCHOR.get(lg, {})).items():
        if not any(str(k) in fixed for k in rat):
            continue
        for k, v in rat.items():
            if name not in v:
                continue
            if str(k) in fixed:
                v[name] = fixed[str(k)]
            elif v[name] >= 90:
                v[name] = int(round(88 + (v[name] - 90) * 0.5))
    for k, v in rat.items():
        if len(v) == len(AX):
            out[k] = [[name, v[name]] for name in AX]
    return out


# эталоны владельца по осям навыков: id игрока в лиге -> оценка (НХЛ: 8476453 — Кучеров, 8478402 — Макдэвид)
# 17.11 «скорость 99 — у Макдэвида и Маккиннона, у остальных ниже» (8477492 — Маккиннон)
ANCHOR = {'nhl': {'Передачи': {'8476453': 99, '8478402': 90}, 'Катание': {'8478402': 99, '8477492': 99}}}


def pct_ranks(lg, players):
    """«Лучше, чем у N % игроков того же амплуа» (владелец 16.11, по образцу Opta Analyst / FBref): по каждой цифре —
    доля нападающих (или защитников) своей лиги, у кого она хуже. В выборке — от 5 матчей. Возвращает {id: [[ключ, значение, %]]};
    ключи и подписи — assets/pct.js. У «меньше — лучше» (штраф, потери) процент считается наоборот."""
    sk = {}
    if lg == 'nhl':
        try:
            sk = load(os.path.join(V3A, 'hockey', 'data', 'nhl_skills.json')).get('p', {})
        except Exception:  # noqa: BLE001
            sk = {}
    LOW = {'pim', 'gv'}
    rows, grp = {}, {}
    for p in players:
        L = p.get('log', [])
        n = len(L)
        if n < 5 or p.get('id') is None:
            continue
        g = sum(r[4] or 0 for r in L); a = sum(r[5] or 0 for r in L)
        tv = [r[7] for r in L if r[7]]
        toi = sum(tv) / len(tv) if tv else ((p.get('toi_avg') or 0) * 60 or None)   # секунды за матч
        m60 = toi * n / 3600.0 if toi else None
        v = {'ppg': (g + a) / n, 'gpg': g / n, 'apg': a / n, 'toi': toi, 'p60': (g + a) / m60 if m60 else None}
        if lg == 'nhl':
            e = sk.get(str(p['id'])) or {}
            gp = e.get('gp') or n
            sh = sum(r[6] or 0 for r in L)
            v.update({'spg': sh / n, 'shp': g / sh * 100 if sh >= 15 else None, 'pm': e.get('pm'),
                      'pim': (e['pim'] / gp) if e.get('pim') is not None else sum(r[8] or 0 for r in L) / n,
                      'hit': e['hit'] / gp if e.get('hit') is not None else None,
                      'blk': e['blk'] / gp if e.get('blk') is not None else None,
                      'tk': e['tk'] / gp if e.get('tk') is not None else None,
                      'gv': e['gv'] / gp if e.get('gv') is not None else None,
                      'fo': e['fo'] * (100 if e['fo'] <= 1 else 1) if e.get('fo') is not None and (e.get('fon') or 0) >= 100 else None,
                      'spd': e['spd'] * 1.609 if e.get('spd') else None, 'shot': e['shot'] * 1.609 if e.get('shot') else None})
        else:
            st = p.get('st') or {}
            gp = st.get('gp') or n
            v.update({'pm': st.get('pm'), 'pim': (st['pim'] / gp) if st.get('pim') is not None else None,
                      'spd': st.get('top_speed') or None,
                      'dist': st['distance_travelled'] / gp if st.get('distance_travelled') else None})
        rows[p['id']] = v
        grp[p['id']] = 'D' if p.get('pos') == 'D' else 'F'
    out = {}
    keys = sorted({k for v in rows.values() for k in v})
    for G in ('F', 'D'):
        ids = [i for i in rows if grp[i] == G]
        for k in keys:
            vals = sorted(rows[i][k] for i in ids if rows[i].get(k) is not None)
            if len(vals) < 20:
                continue
            import bisect
            N = len(vals)
            for i in ids:
                x = rows[i].get(k)
                if x is None:
                    continue
                lo = bisect.bisect_left(vals, x); hi = bisect.bisect_right(vals, x)
                worse = (N - hi) if k in LOW else lo                       # у скольких хуже
                pc = int(round((worse + (hi - lo - 1) / 2) / (N - 1) * 100)) if N > 1 else 50
                out.setdefault(i, []).append([k, round(x, 3), max(1, min(99, pc))])
    return out


def write_profile(ppdir, lg, p, slug, sl, nx, tpl, games=None, sk=None, pc=None):
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
    if pc:
        q['pc'] = pc
    write(os.path.join(ppdir, lg, '%s.json' % p['id']), jd(q))
    return 1


# ─────────────── имена КХЛ: по-русски «Имя Фамилия» (владелец 13.11; с 09.11 по 13.11 были латиницей) ───────────────
# Таблица ru → en: hockey/data/khl_names_en.json (официальное написание приложения КХЛ, locale=en: «Фамилия Имя»,
# пополняет hockey/khl_players_fetch.py). На сайте — как у НХЛ: «Имя Фамилия». Кого нет в таблице — транслитерация.
_TR = dict(zip('абвгдезийклмнопрстуфхцчшщыэюя', ['a','b','v','g','d','e','z','i','y','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch','y','e','yu','ya']))
_TR.update({'ж': 'zh', 'ё': 'yo', 'ъ': '', 'ь': ''})


def _translit(w):
    out, prev = [], ''
    for ch in w:
        lo = ch.lower()
        if lo in _TR or lo in 'её':
            r = 'ye' if lo == 'е' and (not prev or prev in 'аеёиоуыэюяьъ') else ('yo' if lo == 'ё' else _TR.get(lo, lo))
            out.append(r.capitalize() if ch.isupper() else r)
        else:
            out.append(ch)
        prev = lo
    return re.sub(r'(iy|yy)$', 'y', ''.join(out))


_EN = None


def en_name(n):
    """«Блажиевский Артём» → «Artyom Blazhiyevsky» (латиница — только для поиска, 13.11)."""
    global _EN
    if not n or not re.search('[А-Яа-яЁё]', n):
        return n
    if _EN is None:
        fp = os.path.join(V3A, 'hockey', 'data', 'khl_names_en.json')
        _EN = load(fp) if os.path.exists(fp) else {}
    e = _EN.get(n) or ' '.join(_translit(w) for w in n.split())
    w = e.split()
    return ' '.join(w[1:] + w[:1]) if len(w) > 1 else e


def ru_name(n):
    """Владелец 13.11: имена КХЛ снова по-русски. «Блажиевский Артём» → «Артём Блажиевский» (имя вперёд, как у НХЛ)."""
    if not n or not re.search('[А-Яа-яЁё]', n):
        return n
    w = n.split()
    return ' '.join(w[1:] + w[:1]) if len(w) > 1 else n


def en_khl_players(j):
    for p in j.get('players') or []:
        p['n'] = ru_name(p.get('n'))
    j['gimg'] = {t: {ru_name(k): v for k, v in m.items()} for t, m in (j.get('gimg') or {}).items()}
    return j


COACH_EN = {'Буше Ги': 'Boucher Guy', 'Гордон Скотт': 'Gordon Scott', 'Лав Митч': 'Love Mitch'}   # тренеры-иностранцы


def en_khl_teams(d):
    for t in d.get('teams', {}).values():
        if t.get('lg') != 'khl':
            continue
        # тренер остаётся по-русски «Фамилия Имя» (13.11) — team.js сам ставит имя вперёд
        for k in ('sk', 'gk'):
            for r in (t.get('pl') or {}).get(k) or []:
                if isinstance(r, dict) and r.get('n'):
                    r['n'] = ru_name(r['n'])
    return d


def hockey():
    d = load(os.path.join(V3A, 'assets', 'data', 'teams.json'))
    en_khl_teams(d)
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
        if lg == 'khl':
            en_khl_players(j)
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
        PC = pct_ranks(lg, j.get('players', []))
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
                ppn += write_profile(ppdir, lg, p, slug, sl, nxt.get(p['t']), d['teams'].get(slug, {}).get('pl'), d['teams'].get(slug, {}).get('games'), SK.get(p.get('id')), PC.get(p.get('id')))
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
        if lg == 'khl':
            en_khl_players(pl)
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
    # страница клуба: то же без «up» (ближайшие матчи всех лиг, ~70 КБ) — клубу не нужно (09.11, скорость)
    write(os.path.join(fd, 'football-club.js'), 'window.JV_FOOT=' + jd({k: v for k, v in lite.items() if k != 'up'}) + ';')
    # games.js — для страниц, где нужны матчи всех клубов; h2h — только для пар из ближайших матчей
    pairs = {'|'.join(sorted([m['h'], m['a']])) for m in d.get('up', [])}
    h2h_up = {k: v for k, v in d.get('h2h', {}).items() if k in pairs}
    # удары, угловые, владение (x — клуб, y — соперник) нужны только в раскрытом матче (foot-index.js) — отдельным файлом (09.11, скорость)
    g = {s: [{k: v for k, v in x.items() if k not in ('x', 'y')} for x in t['games']] for s, t in teams.items() if t.get('games')}
    xy = {s: [[x.get('x'), x.get('y')] for x in t['games']] for s, t in teams.items() if t.get('games')}
    write(os.path.join(fd, 'games.js'),
          '(function(F){var G=%s,H=%s,s;for(s in G)if(F.teams[s])F.teams[s].games=G[s];Object.assign(F.h2h,H)})(window.JV_FOOT);' % (jd(g), jd(h2h_up)))
    write(os.path.join(fd, 'games-xy.js'),
          '(function(F){var X=%s,s,i,g;for(s in X)if(F.teams[s]&&F.teams[s].games)for(i=0;i<X[s].length;i++){g=F.teams[s].games[i];if(g){if(X[s][i][0])g.x=X[s][i][0];if(X[s][i][1])g.y=X[s][i][1]}}window.JV_XY=1})(window.JV_FOOT);' % jd(xy))
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
