# -*- coding: utf-8 -*-
"""История футбола для рейтинга (ТЗ docs/handoff/FOOTBALL_BRIEF.md, этап 1; лиги — решение владельца 30.10).

Лиги — football-data.co.uk (CSV сезона: счёт, удары, удары в створ, кэфы Pinnacle на открытии и закрытии, тотал 2,5;
у текущего сезона Pinnacle в CSV нет — только средняя линия рынка Avg*). Наши шесть: АПЛ E0, Ла Лига SP1, Серия А I1,
Бундеслига D1, Лига 1 F1, Португалия P1. Для общей шкалы еврокубков — ещё лиги их соперников (Нидерланды, Бельгия,
Турция, Шотландия, Греция — с ударами; Австрия, Швейцария, Дания, Норвегия, Швеция, Польша, Чехия — только счёт).
Еврокубки — ESPN scoreboard по месяцам (ЛЧ, ЛЕ, ЛК): счёт за 90 минут (без овертайма), команды ESPN → клуб football-data.
Матч лиги: {s, d, lg, h, a, hg, ag, sh: [удары х, г], st: [в створ х, г], pc: [П1 Х П2 закрытие Pinnacle],
            po: [открытие Pinnacle], ac: [средняя закрытие], o25: [ТБ ТМ 2,5 закрытие Pinnacle], a25: [средняя]}
Матч кубка: {s, d, lg: 'UCL'|'UEL'|'UECL', h, a (клуб football-data или 'espn:<id>'), hl, al (лига клуба), hg, ag, e: FT, n: нейтральное поле,
             bo: [П1 Х П2 букмекера ESPN], bt: [тотал, больше, меньше]}; xG — Understat (топ-5, без Португалии): xg: [х, г]
Кэш — .lines/football_hist/ (переносится itogi.yml). Отдельно: python team/picks/football_hist.py"""
import csv
import difflib
import gzip
import io
import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.lines', 'football_hist')
OUT = os.path.join(CACHE, 'hist.json.gz')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]          # год начала сезона
CUR = SEASONS[-1]
OURS = {'E0': 'АПЛ', 'SP1': 'Ла Лига', 'I1': 'Серия А', 'D1': 'Бундеслига', 'F1': 'Лига 1', 'P1': 'Португалия'}
MORE = ['N1', 'B1', 'T1', 'SC0', 'G1']                  # лиги соперников по еврокубкам, тот же формат CSV
EXTRA = {'AUT': 'aut.1', 'SWZ': 'sui.1', 'DNK': 'den.1', 'NOR': 'nor.1', 'SWE': 'swe.1', 'POL': 'pol.1'}
ESPN_LG = {'E0': 'eng.1', 'SP1': 'esp.1', 'I1': 'ita.1', 'D1': 'ger.1', 'F1': 'fra.1', 'P1': 'por.1', 'N1': 'ned.1',
           'B1': 'bel.1', 'T1': 'tur.1', 'SC0': 'sco.1', 'G1': 'gre.1', 'AUT': 'aut.1', 'SWZ': 'sui.1', 'DNK': 'den.1',
           'NOR': 'nor.1', 'SWE': 'swe.1', 'POL': 'pol.1', 'CZE': 'cze.1', 'CRO': 'cro.1', 'SRB': 'srb.1',
           'UKR': 'ukr.1', 'ISR': 'isr.1', 'CYP': 'cyp.1'}
CUPS = {'UCL': 'uefa.champions', 'UEL': 'uefa.europa', 'UECL': 'uefa.europa.conf'}
E = 'https://site.api.espn.com/apis/site/v2/sports/soccer/'
S = requests.Session()
S.headers.update(UA)


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def get(url, **kw):
    for _ in range(3):
        try:
            r = S.get(url, timeout=30, **kw)
            if r.status_code == 200:
                return r
        except Exception:
            pass
    return None


def fnum(v):
    try:
        f = float(v)
        return f if f > 1.0 else None
    except (TypeError, ValueError):
        return None


def trio(row, *keys):
    v = [fnum(row.get(k)) for k in keys]
    return v if all(v) else None


def ddate(v):
    d, m, y = v.split('/')
    y = int(y)
    y = y + 2000 if y < 100 else y
    return '%04d-%02d-%02d' % (y, int(m), int(d))


def season_of(day):
    return int(day[:4]) if int(day[5:7]) >= 7 else int(day[:4]) - 1


def league_csv(code, s):
    """Сезон лиги из football-data.co.uk. Прошлые сезоны — из кэша (не меняются), текущий — заново."""
    path = os.path.join(CACHE, 'fd_%s_%d.csv' % (code, s))
    if s != CUR and os.path.exists(path):
        txt = open(path, encoding='utf-8').read()
    else:
        r = get('https://www.football-data.co.uk/mmz4281/%02d%02d/%s.csv' % (s % 100, (s + 1) % 100, code))
        if not r:
            out('FH', 'нет CSV %s %d' % (code, s))
            return []
        txt = r.content.decode('utf-8-sig', 'replace')
        open(path, 'w', encoding='utf-8').write(txt)
    games = []
    for row in csv.DictReader(io.StringIO(txt)):
        if not row.get('HomeTeam') or row.get('FTHG') in (None, ''):
            continue
        g = dict(s=s, d=ddate(row['Date']), lg=code, h=row['HomeTeam'].strip(), a=row['AwayTeam'].strip(),
                 hg=int(row['FTHG']), ag=int(row['FTAG']))
        try:
            g['sh'] = [int(row['HS']), int(row['AS'])]
            g['st'] = [int(row['HST']), int(row['AST'])]
        except (KeyError, TypeError, ValueError):
            pass
        for k, keys in (('pc', ('PSCH', 'PSCD', 'PSCA')), ('po', ('PSH', 'PSD', 'PSA')), ('ac', ('AvgCH', 'AvgCD', 'AvgCA'))):
            v = trio(row, *keys)
            if v:
                g[k] = v
        for k, keys in (('o25', ('PC>2.5', 'PC<2.5')), ('a25', ('AvgC>2.5', 'AvgC<2.5'))):
            v = [fnum(row.get(x)) for x in keys]
            if all(v):
                g[k] = v
        games.append(g)
    return games


def extra_csv(code):
    """Доп. лиги football-data (new/<код>.csv — все сезоны одним файлом, только счёт)."""
    path = os.path.join(CACHE, 'fdx_%s.csv' % code)
    r = get('https://www.football-data.co.uk/new/%s.csv' % code)
    if r:
        open(path, 'w', encoding='utf-8').write(r.content.decode('utf-8-sig', 'replace'))
    if not os.path.exists(path):
        return []
    games = []
    for row in csv.DictReader(io.StringIO(open(path, encoding='utf-8').read())):
        try:
            d = ddate(row['Date'])
            hg, ag = int(row['HG']), int(row['AG'])
        except (KeyError, TypeError, ValueError):
            continue
        s = season_of(d)
        if s < SEASONS[0]:
            continue
        g = dict(s=s, d=d, lg=code, h=row['Home'].strip(), a=row['Away'].strip(), hg=hg, ag=ag)
        v = trio(row, 'PSCH', 'PSCD', 'PSCA')
        if v:
            g['pc'] = v
        games.append(g)
    return games


def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[^a-z0-9 ]", ' ', n)
    drop = {'fc', 'cf', 'sc', 'ac', 'afc', 'ssc', 'as', 'sv', 'fk', 'sk', 'if', 'bk', 'club', 'de', 'cd', 'rc', 'us',
            'ss', 'sl', 'vfb', 'vfl', 'tsg', '1', 'calcio', 'fussball', 'futebol', 'football', 'ogc', 'rcd', 'stade',
            'losc', 'kv', 'krc', 'rsc', 'kaa', 'royal', 'jk', 'nk', 'hnk', 'gnk', 'ud', 'sd', 'ca', 'cfc', 'pfc'}
    return ' '.join(w for w in n.split() if w not in drop)


ALIAS = {   # ESPN → football-data, где похожесть по буквам не помогает
    'manchester united': 'Man United', 'manchester city': 'Man City', 'wolverhampton wanderers': 'Wolves',
    'tottenham hotspur': 'Tottenham', 'nottingham forest': "Nott'm Forest", 'newcastle united': 'Newcastle',
    'atletico madrid': 'Ath Madrid', 'athletic bilbao': 'Ath Bilbao', 'real sociedad': 'Sociedad',
    'real betis': 'Betis', 'celta vigo': 'Celta', 'internazionale': 'Inter', 'ac milan': 'Milan',
    'bayern munich': 'Bayern Munich', 'borussia dortmund': 'Dortmund', 'bayer leverkusen': 'Leverkusen',
    'borussia monchengladbach': "M'gladbach", 'eintracht frankfurt': 'Ein Frankfurt', 'paris saint germain': 'Paris SG',
    'sporting cp': 'Sp Lisbon', 'sporting braga': 'Braga', 'vitoria guimaraes': 'Guimaraes', 'psv eindhoven': 'PSV Eindhoven',
    'az alkmaar': 'AZ Alkmaar', 'red bull salzburg': 'Salzburg', 'club brugge': 'Club Brugge', 'union st gilloise': 'St. Gilloise',
    'olympiacos': 'Olympiakos', 'fenerbahce': 'Fenerbahce', 'galatasaray': 'Galatasaray', 'pafos': 'Pafos',
}


def espn_teams(code, s):
    """ESPN: команды лиги в сезоне s → {id: имя}."""
    lg = ESPN_LG.get(code)
    if not lg:
        return {}
    r = get(E + lg + '/teams', params={'season': s})
    try:
        return {x['team']['id']: x['team']['displayName'] for x in r.json()['sports'][0]['leagues'][0]['teams']}
    except Exception:
        return {}


def match_name(name, cands):
    """Имя ESPN → имя football-data среди команд лиги этого сезона."""
    nn = norm(name)
    if nn in ALIAS and ALIAS[nn] in cands:
        return ALIAS[nn]
    by = {norm(c): c for c in cands}
    if nn in by:
        return by[nn]
    for k, c in by.items():           # одно имя целиком внутри другого: «Lazio» ↔ «SS Lazio»
        if k and (k in nn.split() or nn in k.split() or (len(k) > 3 and k in nn) or (len(nn) > 3 and nn in k)):
            return c
    m = difflib.get_close_matches(nn, list(by), n=1, cutoff=0.6)
    return by[m[0]] if m else None


def ml(v):
    """Американский кэф → десятичный."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(1 + v / 100, 3) if v > 0 else (round(1 + 100 / abs(v), 3) if v < 0 else None)


def cup_month(comp, ym):
    """ESPN scoreboard за месяц (dates=ГГГГММ) — завершённые матчи с кэфами букмекера ESPN, если есть."""
    path = os.path.join(CACHE, 'espn', '%s_%s.json' % (comp, ym))
    if os.path.exists(path):
        return json.load(open(path))
    r = get(E + CUPS[comp] + '/scoreboard', params={'dates': ym, 'limit': 400})
    if not r:
        return None
    evs = []
    for e in r.json().get('events') or []:
        c = (e.get('competitions') or [{}])[0]
        stname = ((e.get('status') or {}).get('type') or {}).get('name') or ''
        if not any(k in stname for k in ('FINAL', 'FULL_TIME', 'AET', 'PEN', 'EXTRA')):
            continue
        side = {}
        for x in c.get('competitors', []):
            side[x.get('homeAway')] = (x['team']['id'], x['team'].get('displayName'), int(float(x.get('score') or 0)))
        if 'home' not in side or 'away' not in side:
            continue
        e_ = 'PEN' if 'PEN' in stname else ('AET' if ('AET' in stname or 'EXTRA' in stname) else 'FT')
        h, a = side['home'], side['away']
        g = dict(d=(e.get('date') or '')[:10], lg=comp, hid=h[0], aid=a[0], hn=h[1], an=a[1], hg=h[2], ag=a[2], e=e_,
                 n=bool(c.get('neutralSite')))
        o = (c.get('odds') or [None])[0] or {}
        k1 = ml((o.get('homeTeamOdds') or {}).get('moneyLine'))
        kx = ml((o.get('drawOdds') or {}).get('moneyLine'))
        k2 = ml((o.get('awayTeamOdds') or {}).get('moneyLine'))
        if k1 and kx and k2:
            g['bo'] = [k1, kx, k2]
        if o.get('overUnder') and ml(o.get('overOdds')) and ml(o.get('underOdds')):
            g['bt'] = [o['overUnder'], ml(o['overOdds']), ml(o['underOdds'])]
        evs.append(g)
    if ym < date.today().strftime('%Y%m'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(evs, open(path, 'w'))
    return evs


def cup_months(s):
    """Месяцы еврокубков сезона: сентябрь — май (основной этап и плей-офф, без квалификации)."""
    res = []
    for m in range(9, 18):
        y, mm = s + (m - 1) // 12, (m - 1) % 12 + 1
        ym = '%04d%02d' % (y, mm)
        if ym <= date.today().strftime('%Y%m'):
            res.append(ym)
    return res


US = {'E0': 'EPL', 'SP1': 'La_liga', 'I1': 'Serie_A', 'D1': 'Bundesliga', 'F1': 'Ligue_1'}


def understat(code, s, names):
    """xG Understat по матчам: {(день, хозяева fd): [xG х, xG г]}. Прошлые сезоны — из кэша."""
    path = os.path.join(CACHE, 'us_%s_%d.json' % (code, s))
    if s != CUR and os.path.exists(path):
        j = json.load(open(path))
    else:
        hdr = {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://understat.com/league/%s/%d' % (US[code], s)}
        r = get('https://understat.com/getLeagueData/%s/%d' % (US[code], s), headers=hdr)
        if not r:
            return {}
        try:
            j = r.json()
        except ValueError:
            return {}
        json.dump(j, open(path, 'w'))
    res, miss = {}, set()
    for t in (j.get('teams') or {}).values():
        fd = match_name(t.get('title') or '', names)
        if not fd:
            miss.add(t.get('title'))
            continue
        for m in t.get('history') or []:
            if m.get('h_a') == 'h':
                res[(str(m.get('date'))[:10], fd)] = [round(float(m['xG']), 3), round(float(m['xGA']), 3)]
    if miss:
        out('FH', 'Understat %s %d: не сопоставлены %s' % (code, s, ', '.join(sorted(miss))))
    return res


def build():
    os.makedirs(CACHE, exist_ok=True)
    dom = {}
    for code in list(OURS) + MORE:
        dom[code] = [g for s in SEASONS for g in league_csv(code, s)]
        out('FH', '%s матчей %d, с Pinnacle закрытием %d' % (code, len(dom[code]), sum(1 for g in dom[code] if g.get('pc'))))
    for code in US:
        nx = 0
        for s in SEASONS:
            gs = [g for g in dom[code] if g['s'] == s]
            xs = understat(code, s, sorted({g['h'] for g in gs} | {g['a'] for g in gs}))
            for g in gs:
                v = xs.get((g['d'], g['h']))
                if v:
                    g['xg'] = v
                    nx += 1
        out('FH', '%s xG Understat у %d матчей из %d' % (code, nx, len(dom[code])))
    for code in EXTRA:
        dom[code] = extra_csv(code)
        out('FH', '%s матчей %d (только счёт)' % (code, len(dom[code])))
    # команды ESPN → лига и имя football-data, по сезонам
    fd_names = {(code, s): sorted({g['h'] for g in gs if g['s'] == s} | {g['a'] for g in gs if g['s'] == s})
                for code, gs in dom.items() for s in SEASONS}
    jobs = [(code, s) for code in ESPN_LG for s in SEASONS]
    with ThreadPoolExecutor(8) as ex:
        tl = dict(zip(jobs, ex.map(lambda j: espn_teams(*j), jobs)))
    idmap = {}          # (id, s) → (лига, имя fd или None)
    miss = []
    for (code, s), teams in tl.items():
        for tid, name in teams.items():
            cands = fd_names.get((code, s)) or []
            fd = match_name(name, cands) if cands else None
            if cands and not fd:
                miss.append('%s/%d %s' % (code, s, name))
            idmap[(tid, s)] = (code, fd)
    out('FH', 'ESPN команд-сезонов %d, не сопоставлено с football-data %d: %s' % (len(idmap), len(miss), '; '.join(miss[:25])))
    # еврокубки
    jobs = [(c, ym) for s in SEASONS for c in CUPS for ym in cup_months(s)]
    with ThreadPoolExecutor(8) as ex:
        days = list(ex.map(lambda j: cup_month(*j), jobs))
    cup, nolg = [], {}
    for evs in days:
        for e in evs or []:
            if e['hg'] is None or e['e'] != 'FT':       # счёт после овертайма — не 90 минут, такие матчи не берём
                continue
            s = season_of(e['d'])
            g = dict(s=s, d=e['d'], lg=e['lg'], hg=e['hg'], ag=e['ag'], e=e['e'], n=e['n'], hn=e['hn'], an=e['an'])
            for k in ('bo', 'bt'):
                if e.get(k):
                    g[k] = e[k]
            for k, tid, nm in (('h', e['hid'], e['hn']), ('a', e['aid'], e['an'])):
                lg, fd = idmap.get((tid, s)) or idmap.get((tid, s - 1)) or (None, None)
                g[k] = fd or 'espn:%s' % tid
                g[k + 'l'] = lg or '?'
                if not lg:
                    nolg[nm] = nolg.get(nm, 0) + 1
            cup.append(g)
    cup.sort(key=lambda g: g['d'])
    by = {}
    for g in cup:
        by.setdefault((g['s'], g['lg']), 0)
        by[(g['s'], g['lg'])] += 1
    out('FH', 'еврокубки: ' + ', '.join('%s %d/%02d: %d' % (c, s, (s + 1) % 100, n) for (s, c), n in sorted(by.items())))
    out('FH', 'клубы кубков без лиги (%d): %s' % (len(nolg), ', '.join(sorted(nolg, key=lambda k: -nolg[k])[:30])))
    data = dict(made=date.today().isoformat(), dom=dom, cup=cup)
    with gzip.open(OUT, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    out('FH', 'записано %s, %d КБ' % (OUT, os.path.getsize(OUT) // 1024))
    return data


def load(rebuild=False):
    if not rebuild and os.path.exists(OUT):
        with gzip.open(OUT, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('made') == date.today().isoformat():
            return data
    return build()


if __name__ == '__main__':
    load(rebuild=True)
