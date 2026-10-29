# -*- coding: utf-8 -*-
"""История НХЛ для нового рейтинга (владелец 29.10: «пересоберём НХЛ, нужно больше точности»).

По каждому матчу регулярки сезонов 2023/24 … текущего:
  • счёт и окончание (API НХЛ, score/<день>; как nhl_data.season_games);
  • xG и голы в основное время у каждой команды, стартовый вратарь и что он «должен был» пропустить (xG по броскам
    в створ и мимо, без пустых ворот) — из файлов бросков MoneyPuck (shots_<год>.zip, зеркало peter-tanner.com;
    данные MoneyPuck — бесплатно для некоммерческого использования со ссылкой на moneypuck.com);
  • кэфы закрытия DraftKings / ESPN BET с ESPN (итоговая победа, фора ±1,5, тотал) — для проверки отбора ставок.

Набор кэшируется в .lines/nhl_hist/ (этот путь itogi.yml переносит из запуска в запуск); прошлые сезоны не качаются
повторно, текущий — дописывается. Структура матча:
  {id, s (сезон: 2025 = 2025/26), d (МСК 'YYYY-MM-DD HH:MM'), h, a (русские имена как в calc), hg, ag, e ('', 'ОТ', 'Б'),
   p (периоды), x: [xG хозяев, xG гостей] осн. время, r: [голы осн. время], g: [вратарь хозяев, вратарь гостей] (id),
   gs: {id вратаря: [xG против, пропущено]} за матч, o: кэфы {ml: [х, г], sp: ['h'|'a' — у кого −1,5, кэф х, кэф г],
   tot: [линия, больше, меньше]}}
Отдельно: python team/picks/nhl_hist.py  → печатает HIST сводку."""
import csv
import gzip
import io
import json
import os
import sys
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nhl_data as N  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.lines', 'nhl_hist')
SHOTS = 'https://peter-tanner.com/moneypuck/downloads/shots_%d.zip'
ESPN_SB = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=%s'
ESPN_ODDS = 'https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/events/%s/competitions/%s/odds'
HDR = {'User-Agent': 'Mozilla/5.0 (jarvibet research)'}
# Регулярка: первый и последний день (даты НХЛ); текущий сезон — до вчера
SEASONS = {2023: ('2023-10-10', '2024-04-18'), 2024: ('2024-10-04', '2025-04-17'), 2025: ('2025-10-07', '2026-04-18'),
           2026: ('2026-09-29', None)}
ODDS_FROM = 2024            # кэфы ESPN — с сезона 2024/25
ESPN_AB = {'SJ': 'SJS', 'NJ': 'NJD', 'LA': 'LAK', 'TB': 'TBL', 'UTAH': 'UTA', 'MON': 'MTL', 'WAS': 'WSH', 'CLB': 'CBJ'}


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def season_of(day):
    y, m = int(day[:4]), int(day[5:7])
    return y if m >= 8 else y - 1


# ---------------------------------------------------------------- матчи

def nhl_games(season, today):
    start, end = SEASONS[season]
    end = end or today
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    days = [(d0 + timedelta(i)).isoformat() for i in range((d1 - d0).days + 1)]
    with ThreadPoolExecutor(8) as ex:
        pages = list(ex.map(lambda d: (d, N.get('score/' + d)), days))
    games = []
    for d, pg in pages:
        for g in pg.get('games') or []:
            if g.get('gameType') != 2 or g.get('gameState') not in ('OFF', 'FINAL'):
                continue
            h, a = g['homeTeam'], g['awayTeam']
            per = [[0, 0] for _ in range(4)]
            for gl in g.get('goals') or []:
                pd = gl.get('periodDescriptor') or {}
                n = pd.get('number') or gl.get('period') or 0
                if pd.get('periodType') == 'SO' or n > 4 or n < 1:
                    continue
                per[n - 1][0 if N.dflt(gl.get('teamAbbrev')) == h['abbrev'] else 1] += 1
            end_ = {'OT': 'ОТ', 'SO': 'Б'}.get((g.get('gameOutcome') or {}).get('lastPeriodType'), '')
            games.append({'id': g['id'], 's': season, 'nd': d, 'd': N.msk(g['startTimeUTC']), 'ab': [h['abbrev'], a['abbrev']],
                          'h': N.ru(h['abbrev']), 'a': N.ru(a['abbrev']),
                          'hg': int(h.get('score') or 0), 'ag': int(a.get('score') or 0), 'e': end_,
                          'p': ['%d:%d' % tuple(x) for x in per[:3]] + (['%d:%d' % tuple(per[3])] if end_ else [''])})
    games.sort(key=lambda x: x['d'])
    return games


# ---------------------------------------------------------------- MoneyPuck: xG и вратари

def shots(season):
    """{id матча: {'x': [xG х, xG г], 'gs': {вратарь: [xG, голы]}, 'g1': [первый вратарь х, г]}} — осн. время, без пустых ворот
    (xG по пустым воротам в счёт команды идут, в счёт вратаря — нет)."""
    r = requests.get(SHOTS % season, headers=HDR, timeout=180)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = next(n for n in z.namelist() if n.endswith('.csv'))
    res = {}
    first = {}
    with z.open(name) as f:
        rd = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        out('HISTCOLS', '%d: %s' % (season, ','.join((rd.fieldnames or [])[:60])))
        for row in rd:
            try:
                if str(row.get('isPlayoffGame', '0')) not in ('0', '0.0'):
                    continue
                per = int(float(row.get('period') or 0))
                if per < 1 or per > 3:
                    continue
                gid = season * 1000000 + int(float(row['game_id']))
                home_shot = str(row.get('isHomeTeam')) in ('1', '1.0')
                xg = float(row.get('xGoal') or 0)
                goal = str(row.get('goal')) in ('1', '1.0')
            except (KeyError, ValueError):
                continue
            g = res.setdefault(gid, {'x': [0.0, 0.0], 'gs': {}, 'g1': [None, None]})
            g['x'][0 if home_shot else 1] += xg
            if str(row.get('shotOnEmptyNet')) in ('1', '1.0'):
                continue
            gk = str(row.get('goalieIdForShot') or '').split('.')[0]
            if not gk or gk == '0':
                continue
            side = 1 if home_shot else 0                      # бросок хозяев — в ворота вратаря гостей
            if g['g1'][side] is None:
                g['g1'][side] = gk
            s = g['gs'].setdefault(gk, [0.0, 0])
            s[0] += xg
            s[1] += 1 if goal else 0
    for g in res.values():
        g['x'] = [round(v, 3) for v in g['x']]
        g['gs'] = {k: [round(v[0], 3), v[1]] for k, v in g['gs'].items()}
    return res


# ---------------------------------------------------------------- ESPN: кэфы закрытия

def _dec(am):
    try:
        am = float(am)
    except (TypeError, ValueError):
        return None
    if not am:
        return None
    return round(1 + (am / 100 if am > 0 else 100 / -am), 3)


def _pick(o, side, key):
    t = o.get(side + 'TeamOdds') or {}
    for k in ('close', 'current'):
        v = ((t.get(k) or {}).get(key) or {})
        if isinstance(v, dict) and (v.get('decimal') or v.get('value')):
            return round(float(v.get('decimal') or v.get('value')), 3)
    return _dec(t.get({'moneyLine': 'moneyLine', 'spread': 'spreadOdds'}[key]))


def espn_odds(day_games):
    """day_games: {nd: [матчи]} → {id матча: кэфы}."""
    def sb(nd):
        try:
            r = requests.get(ESPN_SB % nd.replace('-', ''), headers=HDR, timeout=30)
            return nd, r.json().get('events') or []
        except Exception as e:  # noqa: BLE001
            return nd, []
    with ThreadPoolExecutor(8) as ex:
        boards = list(ex.map(sb, sorted(day_games)))
    todo = []
    for nd, evs in boards:
        by_home = {x['ab'][0]: x for x in day_games[nd]}
        for ev in evs:
            try:
                c = ev['competitions'][0]
                home = next(t for t in c['competitors'] if t.get('homeAway') == 'home')
                ab = home['team']['abbreviation']
                g = by_home.get(ESPN_AB.get(ab, ab))
                if g:
                    todo.append((g['id'], ev['id']))
            except (KeyError, StopIteration, IndexError):
                continue

    def one(t):
        gid, eid = t
        try:
            j = requests.get(ESPN_ODDS % (eid, eid), headers=HDR, timeout=30).json()
            items = sorted(j.get('items') or [], key=lambda x: (x.get('provider') or {}).get('priority', 9))
            if not items:
                return gid, None
            o = items[0]
            mh, ma = _pick(o, 'home', 'moneyLine'), _pick(o, 'away', 'moneyLine')
            fav = 'h' if (o.get('homeTeamOdds') or {}).get('favorite') else 'a'
            sh, sa = _pick(o, 'home', 'spread'), _pick(o, 'away', 'spread')
            res = {'ml': [mh, ma], 'sp': [fav, sh, sa], 'tot': [o.get('overUnder'), _dec(o.get('overOdds')), _dec(o.get('underOdds'))],
                   'pv': (o.get('provider') or {}).get('name')}
            return gid, res
        except Exception:  # noqa: BLE001
            return gid, None
    with ThreadPoolExecutor(12) as ex:
        return {gid: o for gid, o in ex.map(one, todo) if o}


# ---------------------------------------------------------------- сборка и кэш

def _path(season):
    return os.path.join(CACHE, 'season_%d.json.gz' % season)


def build(season, today, with_odds=True):
    games = nhl_games(season, today)
    try:
        sh = shots(season)
    except Exception as e:  # noqa: BLE001 — без xG рейтинг считается по голам
        out('HISTERR', 'броски MoneyPuck %d: %r' % (season, e))
        sh = {}
    odds = {}
    if with_odds and season >= ODDS_FROM:
        byday = defaultdict(list)
        for g in games:
            byday[g['nd']].append(g)
        odds = espn_odds(byday)
    miss_x = 0
    for g in games:
        s = sh.get(g['id'])
        if s:
            g['x'], g['gs'], g['g'] = s['x'], s['gs'], s['g1']
        else:
            miss_x += 1
        r = [0, 0]
        for p in g['p'][:3]:
            if p:
                a, b = p.split(':')
                r[0] += int(a)
                r[1] += int(b)
        g['r'] = r
        if g['id'] in odds:
            g['o'] = odds[g['id']]
    out('HIST', 'сезон %d/%02d: матчей %d, без xG %d, с кэфами %d' % (season, (season + 1) % 100, len(games), miss_x,
                                                                    sum(1 for g in games if g.get('o'))))
    return games


def load(seasons=None, today=None, refresh_current=True, with_odds=True):
    """Матчи сезонов (по умолчанию все из SEASONS) — из кэша или собранные заново."""
    today = today or datetime.now(timezone(timedelta(hours=-5))).date().isoformat()   # игровой день НХЛ (Нью-Йорк)
    cur = season_of(today)
    os.makedirs(CACHE, exist_ok=True)
    res = []
    for s in sorted(seasons or SEASONS):
        if s > cur:
            continue
        p = _path(s)
        games = None
        if os.path.exists(p) and not (s == cur and refresh_current):
            try:
                with gzip.open(p, 'rt', encoding='utf-8') as f:
                    games = json.load(f)
                out('HIST', 'сезон %d/%02d: из кэша, матчей %d' % (s, (s + 1) % 100, len(games)))
            except (OSError, ValueError):
                games = None
        if games is None:
            games = build(s, (date.fromisoformat(today) - timedelta(1)).isoformat() if s == cur else today,
                          with_odds or s != cur)
            if with_odds or s != cur:          # без кэфов текущий сезон в кэш не кладём — его перепишет проверка
                with gzip.open(p, 'wt', encoding='utf-8') as f:
                    json.dump(games, f, ensure_ascii=False, separators=(',', ':'))
        res += games
    res.sort(key=lambda g: g['d'])
    return res


if __name__ == '__main__':
    g = load()
    out('HIST', 'всего матчей %d' % len(g))
