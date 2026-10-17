# -*- coding: utf-8 -*-
"""Расписание и счёт для утренних постов: приложение КХЛ (khl.api.webcaster.pro) и API НХЛ (api-web.nhle.com) — те же
источники и те же функции имён/времени, что у team/picks/khl_data.py и nhl_data.py. Облачная сессия до них не достаёт —
в Actions достаёт. Без сети: DAILY_MOCK=<файл.json> с ответами API (формат — team/daily/test_daily.py, mock_api()).

Матч в одном виде для обеих лиг:
  {league: 'KHL'|'NHL', id, start: datetime МСК, home, away, state: 'final'|'live'|'future'|'off', hg, ag, end: ''|'ОТ'|'Б'}
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'picks'))

import teams  # noqa: E402  KHL_IDS, NHL_RU

MSK = timezone(timedelta(hours=3))
KHL_BASE = 'https://khl.api.webcaster.pro/api/khl_mobile/'
NHL_BASE = 'https://api-web.nhle.com/v1/'
_MOCK = None
_SESSION = None


def err(e):
    """Коротко об ошибке для строки владельцу."""
    return '%s: %s' % (type(e).__name__, str(e)[:90])


def now_msk():
    v = os.environ.get('DAILY_NOW')                        # проверка: «2026-10-16 06:05»
    return datetime.strptime(v, '%Y-%m-%d %H:%M').replace(tzinfo=MSK) if v else datetime.now(MSK)


def _mock():
    global _MOCK
    if _MOCK is None and os.environ.get('DAILY_MOCK'):
        with open(os.environ['DAILY_MOCK'], encoding='utf-8') as f:
            _MOCK = json.load(f)
    return _MOCK


def set_mock(obj):
    """Для проверок: подставить ответы API без файла."""
    global _MOCK
    _MOCK = obj


def _http(url):
    global _SESSION
    import requests
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers['User-Agent'] = 'Mozilla/5.0'
    for k in range(3):
        try:
            r = _SESSION.get(url, timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if k == 2:
                raise
            print('DAILYERR повтор %s: %r' % (url, e), flush=True)
            time.sleep(1 + k)


# ---------------------------------------------------------------- КХЛ

def _khl_mock(m, path):
    k = m.get('khl') or {}
    if path.startswith('data.json'):
        return k.get('data.json') or {}
    if path.startswith('event_v2.json'):
        eid = re.search(r'id=(\d+)', path).group(1)
        return {'event': (k.get('details') or {}).get(eid) or {}}
    if path.startswith('events_v2.json'):
        q = dict(re.findall(r'q%5B(\w+)%5D=(\d+)', path))
        page = int(re.search(r'page=(\d+)', path).group(1))
        frm, to = int(q.get('start_at_gt_time_from_unixtime', 0)), int(q.get('start_at_lt_time_from_unixtime', 1 << 40))
        evs = [w for w in k.get('events') or [] if frm < int((w.get('event') or w)['start_at']) / 1000 < to]
        evs.sort(key=lambda w: int((w.get('event') or w)['start_at']))
        return evs[(page - 1) * 16:page * 16]
    raise KeyError(path)


def khl_get(path):
    m = _mock()
    return _khl_mock(m, path) if m is not None else _http(KHL_BASE + path)


def _khl_team(t):
    t = t or {}
    return teams.KHL_IDS.get(t.get('id')) or str(t.get('name') or '').strip()


def _msk_dt(ts):
    if isinstance(ts, str) and not ts.isdigit():
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(MSK)
    v = float(ts or 0)
    return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, MSK)


def khl_games(t0, t1, detail_if=None):
    """Матчи КХЛ с началом в [t0, t1) (datetime МСК). detail_if(home, away) → True — для сыгранных взять ОТ/Б из карточки
    матча (event_v2), как khl_data.fetch; без него ОТ/Б только из списка (обычно там нет)."""
    boot = khl_get('data.json')
    stage = boot.get('current_stage_id')
    frm, to = int(t0.timestamp()) - 1, int(t1.timestamp())
    raw = []
    for page in range(1, 41):
        arr = khl_get('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
                      '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, stage))
        if not isinstance(arr, list) or not arr:
            break
        raw += [w.get('event') or w for w in arr]
        if len(arr) < 16:
            break
    now = now_msk()
    games, need = [], []
    for e in raw:
        if e.get('type_id') not in (18, 24, None):
            continue
        st = _msk_dt(e.get('start_at'))
        if not (t0 <= st < t1):
            continue
        g = dict(league='KHL', id=e.get('id'), start=st, home=_khl_team(e.get('team_a')), away=_khl_team(e.get('team_b')),
                 state='final' if e.get('game_state_key') == 'finished' else 'live' if st <= now else 'future',
                 hg=None, ag=None, end='', src='КХЛ-прил event %s' % e.get('id'))
        sc = str(e.get('score') or '').split(':')
        if g['state'] == 'final' and len(sc) == 2 and all(x.strip().isdigit() for x in sc):
            g['hg'], g['ag'] = int(sc[0]), int(sc[1])
        if g['state'] == 'final' and detail_if and detail_if(g['home'], g['away']):
            need.append(g)
        games.append(g)

    def det(g):
        try:
            j = khl_get('event_v2.json?id=%s' % g['id'])
            d = j.get('event') or j
        except Exception as err:  # noqa: BLE001
            print('DAILYERR КХЛ карточка %s: %r' % (g['id'], err), flush=True)
            return
        sc = str(d.get('score') or '').split(':')
        if len(sc) == 2 and all(x.strip().isdigit() for x in sc):
            g['hg'], g['ag'] = int(sc[0]), int(sc[1])
        khl_regulation(g, d.get('scores') or {})

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(det, need))
    for g in games:
        if g['state'] == 'final' and g['hg'] is None:
            g['state'] = 'live'                            # счёта нет — считаем, что ещё не закончен
    games.sort(key=lambda g: g['start'])
    return games


def _pair_goals(v):
    m = re.match(r'\s*(\d+)\s*[:\-]\s*(\d+)', str(v or ''))
    return (int(m.group(1)), int(m.group(2))) if m else None


def khl_regulation(g, s):
    """Счёт основного времени и ОТ/Б матча КХЛ из карточки (scores: first_period, second_period, third_period,
    overtime, bullitt — строки «1:0»). Главный признак — сумма трёх периодов: совпала с итоговым счётом — ОТ не было
    (строка overtime «0:0» — не овертайм). Не совпала: в овертайме есть шайбы — ОТ, иначе буллиты. Периодов нет —
    по флагам overtime/bullitt (только с шайбами) и правилу «победа в ОТ/Б — на одну шайбу»."""
    per = [_pair_goals(s.get(k)) for k in ('first_period', 'second_period', 'third_period')]
    ot, so = _pair_goals(s.get('overtime')), _pair_goals(s.get('bullitt'))
    if all(per) and g.get('hg') is not None:
        rh, ra = sum(x[0] for x in per), sum(x[1] for x in per)
        if (rh, ra) == (g['hg'], g['ag']):
            g['end'], g['reg'], g['how'] = '', (rh, ra), 'периоды'
        else:
            g['end'] = 'ОТ' if ot and sum(ot) > 0 else 'Б'
            g['reg'], g['how'] = (rh, ra), 'периоды'
            if rh != ra:
                g['warn'] = 'КХЛ: периоды %d:%d не ничья, а итог %d:%d — проверить' % (rh, ra, g['hg'], g['ag'])
        return
    has_ot = bool(ot and sum(ot) > 0) or (s.get('overtime') not in (None, '', '0:0', '0-0', False, 0) and not ot)
    has_so = bool(so and sum(so) > 0) or (s.get('bullitt') not in (None, '', '0:0', '0-0', False, 0) and not so)
    g['end'] = 'Б' if has_so else 'ОТ' if has_ot else ''
    if g['end'] and g.get('hg') is not None and abs(g['hg'] - g['ag']) != 1:
        g['warn'] = 'КХЛ: отмечен %s, но разница %d:%d — считаю основным временем' % (g['end'], g['hg'], g['ag'])
        g['end'] = ''
    g['how'] = 'флаги карточки'


# ---------------------------------------------------------------- НХЛ

def nhl_regulation(g, raw):
    """ОТ/Б и счёт основного времени матча НХЛ из ответа score/<день>. Три источника: gameOutcome.lastPeriodType,
    periodDescriptor (номер > 3 или тип OT/SO) и голы по периодам (goals[].periodDescriptor). Раньше брали только
    gameOutcome — в состоянии FINAL (до OFF) его бывает нет, и матч с ОТ считался как в основное время."""
    last = (raw.get('gameOutcome') or {}).get('lastPeriodType')
    pd = raw.get('periodDescriptor') or {}
    by_pd = pd.get('periodType') if pd.get('periodType') in ('OT', 'SO') else ('OT' if (pd.get('number') or 0) > 3 else None)
    reg = [0, 0]
    goals = raw.get('goals') or []
    so_goal = ot_goal = False
    hab = raw['homeTeam']['abbrev']
    for gl in goals:
        d = gl.get('periodDescriptor') or {}
        n, t = d.get('number') or gl.get('period') or 0, d.get('periodType')
        if t == 'SO' or n >= 5 and t != 'OT':
            so_goal = True
            continue
        if t == 'OT' or n > 3:
            ot_goal = True
            continue
        ab = gl.get('teamAbbrev')
        ab = ab.get('default') if isinstance(ab, dict) else ab
        reg[0 if ab == hab else 1] += 1
    from_goals = 'SO' if so_goal else 'OT' if ot_goal else None
    kinds = [x for x in (last, by_pd, from_goals) if x in ('OT', 'SO')]
    kind = 'SO' if 'SO' in kinds else 'OT' if kinds else None
    g['end'] = {'OT': 'ОТ', 'SO': 'Б'}.get(kind, '')
    g['how'] = 'gameOutcome=%s periodDescriptor=%s/%s голы=%s' % (last, pd.get('number'), pd.get('periodType'), len(goals))
    total = g['hg'] + g['ag']
    if goals and sum(reg) + (1 if g['end'] else 0) == total:
        g['reg'] = tuple(reg)
    elif not g['end']:
        g['reg'] = (g['hg'], g['ag'])
    if g['end'] and abs(g['hg'] - g['ag']) != 1:
        g['warn'] = 'НХЛ: %s, но разница %d:%d — проверить' % (g['end'], g['hg'], g['ag'])
    if last in ('OT', 'SO', 'REG') and last != (kind or 'REG'):
        g['warn'] = 'НХЛ: источники ОТ/Б расходятся (%s)' % g['how']


def nhl_get(path):
    m = _mock()
    if m is not None:
        v = (m.get('nhl') or {}).get(path)
        if v is None and path.startswith('score/'):
            v = {'games': []}                          # как у API: в этот день матчей нет
        if v is None:
            raise KeyError(path)
        return v
    return _http(NHL_BASE + path)


def nhl_day(day):
    """Матчи игрового дня НХЛ (дата по Нью-Йорку, у нас — ночь на следующее число)."""
    out = []
    now = now_msk()
    for g in nhl_get('score/' + day).get('games') or []:
        if g.get('gameType') not in (2, 3):
            continue
        h, a = g['homeTeam'], g['awayTeam']
        st = _msk_dt(g['startTimeUTC'])
        s = g.get('gameState')
        state = 'final' if s in ('OFF', 'FINAL') else 'off' if s in ('PPD', 'CNCL', 'SUSP') else \
            'live' if s in ('LIVE', 'CRIT') or st <= now else 'future'
        x = dict(league='NHL', id=g.get('id'), start=st, home=teams.NHL_RU.get(h['abbrev'], h['abbrev']),
                 away=teams.NHL_RU.get(a['abbrev'], a['abbrev']), ab_h=h['abbrev'], ab_a=a['abbrev'], state=state,
                 hg=int(h.get('score') or 0) if state == 'final' else None,
                 ag=int(a.get('score') or 0) if state == 'final' else None, end='', src='НХЛ-API score/%s' % day)
        if state == 'final':
            nhl_regulation(x, g)
        out.append(x)
    out.sort(key=lambda g: g['start'])
    return out


def nhl_leaders(n=8):
    """Аббревиатуры n лучших клубов лиги по официальной таблице (для «встречи лидеров»); нет данных — пусто."""
    try:
        rows = nhl_get('standings/now').get('standings') or []
    except Exception as e:  # noqa: BLE001
        print('DAILYERR standings %r' % e, flush=True)
        return set()
    out = set()
    for r in rows:
        ab = r.get('teamAbbrev')
        ab = ab.get('default') if isinstance(ab, dict) else ab
        if (r.get('leagueSequence') or 99) <= n and (r.get('gamesPlayed') or 0) >= 5:
            out.add(ab)
    return out


def nhl_game_day(start):
    """Игровой день НХЛ по времени начала МСК: Нью-Йорк — МСК минус 7–8 часов."""
    return (start - timedelta(hours=8)).date().isoformat()


# ---------------------------------------------------------------- всё нужное утру

def day_bounds(d):
    t0 = datetime(d.year, d.month, d.day, tzinfo=MSK)
    return t0, t0 + timedelta(days=1)


def morning_games(d):
    """→ (матчи КХЛ этой даты по Москве, матчи НХЛ ночи на следующее число, лидеры НХЛ, ошибки)."""
    errs = []
    khl, nhl = [], []
    try:
        khl = khl_games(*day_bounds(d))
    except Exception as e:  # noqa: BLE001
        errs.append('КХЛ: расписание не загрузилось (%s)' % err(e))
    try:
        nhl = nhl_day(d.isoformat())
    except Exception as e:  # noqa: BLE001
        errs.append('НХЛ: расписание не загрузилось (%s)' % err(e))
    leaders = nhl_leaders() if nhl else set()
    return [g for g in khl if g['state'] != 'off'], [g for g in nhl if g['state'] != 'off'], leaders, errs


def games_for(picks, pad_days=1):
    """Счёт матчей прогнозов: КХЛ — одним запросом по датам прогнозов, НХЛ — по игровым дням. → ({(лига, х, г, дата): матч}, ошибки)."""
    errs, found = [], {}
    khl = [p for p in picks if p['league'] == 'KHL']
    nhl = [p for p in picks if p['league'] == 'NHL']
    if khl:
        want = {(p['home'], p['away']) for p in khl}
        t0 = min(p['start'] for p in khl) - timedelta(days=pad_days)
        t1 = max(p['start'] for p in khl) + timedelta(days=pad_days)
        try:
            for g in khl_games(t0, t1, detail_if=lambda h, a: (h, a) in want):
                found.setdefault(('KHL', g['home'], g['away']), []).append(g)
        except Exception as e:  # noqa: BLE001
            errs.append('КХЛ: счёт не загрузился (%s)' % err(e))
    days = sorted({nhl_game_day(p['start']) for p in nhl} |
                  {(date.fromisoformat(nhl_game_day(p['start'])) + timedelta(days=k)).isoformat() for p in nhl for k in (-1, 1)})
    failed = []
    for day in days:
        try:
            for g in nhl_day(day):
                found.setdefault(('NHL', g['home'], g['away']), []).append(g)
        except KeyError:
            pass                                       # в макете нет этого дня
        except Exception as e:  # noqa: BLE001
            failed.append((day, e))
    if failed:
        errs.append('НХЛ: счёт не загрузился за %s (%s)' % (', '.join(d[5:] for d, _ in failed), err(failed[-1][1])))
    return found, errs


def match_game(found, p):
    """Матч прогноза p среди загруженных: те же лига и пара, начало ближе всего ко времени из SENT (до ±30 ч)."""
    best = None
    for g in found.get((p['league'], p['home'], p['away'])) or []:
        dt = abs((g['start'] - p['start']).total_seconds())
        if dt <= 30 * 3600 and (best is None or dt < best[0]):
            best = (dt, g)
    return best[1] if best else None
