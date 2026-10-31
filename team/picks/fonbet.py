# -*- coding: utf-8 -*-
"""Линия Фонбета на матчи дня — по ней ставит владелец (31.10: «котировки нужно собирать максимально точно — пробуем
Фонбет»). Источник — открытая выгрузка линии, которую читает сайт Фонбета (обычный GET, ответ сжат gzip/br):
    https://line-lb51-w.bk6bba-resources.com/events/list?lang=ru&version=0&scopeMarket=1600   (запасной — line-lb61-w)
Облачная сессия до неё не достаёт, Actions — достаёт (пробы run 663 и 31.10, team/out/2026-10-31/fonbet/). Перестанет
отвечать / начнёт отказывать — НЕ обходить: прогнозы идут по Pinnacle, сказать руководителю.

Что внутри выгрузки: sports (лиги-сегменты), events (матчи; подсобытия с parentId — периоды, таймы, угловые, карточки,
удары…), customFactors [{e: событие, factors: [{f: код, v: кэф, pt: линия}]}]. Коды — таблица CODES ниже, сверены
31.10 по открытому каталогу factorsCatalog/tables и по сумме обратных кэфов (маржа 4–7 %) и с Pinnacle (fon_check.py).
В хоккее у Фонбета всё основное (исходы, форы, тоталы) — ОСНОВНОЕ время; «итоговая победа» (с ОТ и Б) — коды 7035/7036.
Инд. тоталов в хоккее в этой выгрузке нет (31.10) — для них остаётся Pinnacle.

Выход:
  flat(factors)          — {рынок: кэф} в именах football_wide: П1 Х П2 1Х Х2 12, Ф1 -1.5, Ф1 -1 (возврат при ровно),
                           П1 (ничья — возврат), ТБ 5.5 / ТМ 5.5, ИТ1Б 1.5 / ИТ2М 2.5, ОЗ да / ОЗ нет, итог П1 / итог П2;
  hockey_day(lg, day, want) — {(хозяева, гости): {'mks': рынки как у pin.py (period 6 — осн. время, 0 — с ОТ, 1–3 —
                           периоды), 'flat': {…}, 'start': ISO}}; calc.odds_for() читает их так же, как Pinnacle;
  foot_day(code, day)    — [{h, a, t: 'ЧЧ:ММ' МСК, flat: {рынок: кэф} — 90 минут, «1-й тайм …», «2-й тайм …»,
                           «угловые: ТБ 9.5», «угловые хозяев: Б 4.5», «жёлтые: …», «в створ: …»}];
  match_foot(events, ph, pa, t) — событие Фонбета к матчу Pinnacle (по времени начала, при нескольких — по названиям).
Печатает FONSTAT (сколько матчей), FONMATCH (матч, рынков), FON (основные рынки), FONMISS (не сопоставлен).
Пишет линию в .lines/fonbet/<день>.jsonl (кэш Actions, как .lines/lines.jsonl) — для проверок и экспрессов.
Отдельно: python team/picks/fonbet.py khl 2026-10-31 | nhl 2026-10-31 | foot E0 2026-10-31"""
import gzip
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import teams  # noqa: E402

HOSTS = ['https://line-lb51-w.bk6bba-resources.com', 'https://line-lb61-w.bk6bba-resources.com']
PATH = '/events/list?lang=ru&version=0&scopeMarket=1600'
HDR = {'Accept': 'application/json', 'Accept-Encoding': 'gzip', 'User-Agent': 'jarvis-line/1.0'}
MSK = timezone(timedelta(hours=3))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINES = os.path.join(ROOT, '.lines', 'fonbet')

# ---------- коды рынков (каталог factorsCatalog/tables, сверка 31.10) ----------
OUT = {921: 'П1', 922: 'Х', 923: 'П2', 924: '1Х', 925: 'Х2', 1571: '12', 7035: 'итог П1', 7036: 'итог П2',
       4241: 'ОЗ да', 4242: 'ОЗ нет'}
HC = [(927, 928), (910, 912), (989, 991), (1569, 1572), (1672, 1675), (1677, 1678), (1680, 1681), (1683, 1684),
      (1686, 1687), (1689, 1690), (1692, 1718)]                       # фора: (хозяева, гости), у каждой своя линия pt
TOT = [(930, 931), (1696, 1697), (1727, 1728), (1730, 1731), (1733, 1734), (1736, 1737), (1739, 1791), (1793, 1794),
       (1796, 1797), (1799, 1800), (1802, 1803), (1805, 1806)]         # тотал: (больше, меньше)
IT1 = [(1809, 1810), (1812, 1813), (1815, 1816), (1818, 1819), (1821, 1822), (1824, 1825), (1827, 1828), (1830, 1831),
       (2203, 2204)]                                                   # инд. тотал хозяев: (больше, меньше)
IT2 = [(1854, 1871), (1873, 1874), (1880, 1881), (1883, 1884), (1886, 1887), (1893, 1894), (1896, 1897), (1899, 1900)]
CODES = dict(OUT=OUT, HC=HC, TOT=TOT, IT1=IT1, IT2=IT2)

# Лиги: сегмент выгрузки (kind segment, род. 1 — футбол, 2 — хоккей) по началу названия; лишнее — по словам.
LEAGUES = {'khl': (2, ('Фонбет КХЛ', 'КХЛ')), 'nhl': (2, ('НХЛ',)),
           'E0': (1, ('Англия. Премьер-Лига',)), 'SP1': (1, ('Испания. Примера дивизион',)),
           'I1': (1, ('Италия. Серия А', 'Италия. Серия A')), 'D1': (1, ('Германия. Бундеслига',)),
           'F1': (1, ('Франция. Лига 1',)), 'UCL': (1, ('Лига чемпионов УЕФА',)), 'UEL': (1, ('Лига Европы УЕФА',))}
SKIP = ('Итоги', 'Специальн', 'Лучший', 'Статист', 'Кто выше', 'Победитель', 'Бундеслига 2', 'Бундеслига 3', 'Серия В',
        'Серия B', 'Серия С', 'RFEF', 'Команда забьет', 'Овечкин', 'женщ', 'Женщ', 'U19', 'U21', 'U23', 'Молод', 'Квалиф. Итоги',
        'Кубок Гагарина. Итоги', 'Голы', 'Матч звезд', 'Матч Звезд', 'Ставки на')
# подсобытия: название у Фонбета → приставка в наших именах
SUBS_FOOT = {'1-й тайм': '1-й тайм ', '2-й тайм': '2-й тайм ', 'угловые': 'угловые', 'желтые карты': 'жёлтые',
             'удары в створ': 'в створ'}
SUBS_HOCKEY = {'1-й период': 1, '2-й период': 2, '3-й период': 3}

_DATA = None


def _decode(b):
    if b[:2] == b'\x1f\x8b':
        return gzip.decompress(b)
    if b[:1] in (b'{', b'['):
        return b
    import brotli
    return brotli.decompress(b)


def load():
    """Вся выгрузка линии (один раз за запуск). Ошибка — исключение: вызывающий остаётся на Pinnacle."""
    global _DATA
    if _DATA is not None:
        return _DATA
    err = None
    for h in HOSTS:
        for k in range(2):
            try:
                r = requests.get(h + PATH, headers=HDR, timeout=40)
                print('FONHTTP %s %s' % (h.split('//')[1].split('.')[0], r.status_code), flush=True)
                if r.status_code in (401, 403, 429, 451):
                    raise RuntimeError('Фонбет отказал (%d) — не обходим, остаёмся на Pinnacle' % r.status_code)
                r.raise_for_status()
                _DATA = json.loads(_decode(r.content))
                return _DATA
            except RuntimeError:
                raise
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(2 + 3 * k)
    raise RuntimeError('линия Фонбета недоступна: %r' % err)


def _segments(league):
    parent, prefixes = LEAGUES[league]
    d = load()
    by = {s['id']: s for s in d.get('sports', [])}
    res = set()
    for s in by.values():
        nm = s.get('name') or ''
        if s.get('kind') != 'segment' or s.get('parentId') != parent or any(w in nm for w in SKIP):
            continue
        if any(nm.startswith(p) for p in prefixes):
            res.add(s['id'])
    return res


def _index():
    d = load()
    if '_subs' not in d:
        subs, facs = {}, {}
        for e in d.get('events', []):
            if e.get('parentId'):
                subs.setdefault(e['parentId'], []).append(e)
        for f in d.get('customFactors', []):
            facs.setdefault(f.get('e'), []).extend(f.get('factors') or [])
        d['_subs'], d['_facs'] = subs, facs
    return d['_subs'], d['_facs']


def _num(pt):
    try:
        return float(str(pt).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def flat(factors):
    """Коды одного события → {рынок: кэф}. Форы и тоталы — только парами с согласованной линией (иначе код не тот)."""
    by = {f.get('f'): f for f in factors or [] if f.get('v')}
    o = {}
    for c, nm in OUT.items():
        if c in by:
            o[nm] = float(by[c]['v'])
    for a, b in HC:
        if a in by and b in by:
            x, y = _num(by[a].get('pt')), _num(by[b].get('pt'))
            if x is None or y is None or abs(x + y) > 1e-9:
                continue
            for side, v, c in (('Ф1', x, a), ('Ф2', y, b)):
                if abs(v) < 1e-9:
                    o['%s (ничья — возврат)' % ('П1' if side == 'Ф1' else 'П2')] = float(by[c]['v'])
                elif abs(v - round(v)) < 1e-9:
                    o['%s %+d (возврат при ровно)' % (side, round(v))] = float(by[c]['v'])
                elif abs(v * 2 - round(v * 2)) < 1e-9:
                    o['%s %+.1f' % (side, v)] = float(by[c]['v'])
    for pairs, ov, un in ((TOT, 'ТБ', 'ТМ'), (IT1, 'ИТ1Б', 'ИТ1М'), (IT2, 'ИТ2Б', 'ИТ2М')):
        for a, b in pairs:
            if a in by and b in by:
                x, y = _num(by[a].get('pt')), _num(by[b].get('pt'))
                if x is None or x != y:
                    continue
                o['%s %.1f' % (ov, x)] = float(by[a]['v'])
                o['%s %.1f' % (un, x)] = float(by[b]['v'])
    return o


def overround(o):
    """Сумма обратных кэфов основных пар — для проверки кодов (ждём 1,03–1,12)."""
    res = {}
    if all(k in o for k in ('П1', 'Х', 'П2')):
        res['1Х2'] = round(1 / o['П1'] + 1 / o['Х'] + 1 / o['П2'], 3)
    for k in o:
        if k.startswith(('ТБ ', 'ИТ1Б ', 'ИТ2Б ')):
            u = k.replace('Б ', 'М ', 1)
            if u in o:
                res[k] = round(1 / o[k] + 1 / o[u], 3)
        elif k.startswith('Ф1 ') and '(' not in k:
            v = float(k.split()[1])
            u = 'Ф2 %+.1f' % -v
            if u in o:
                res[k] = round(1 / o[k] + 1 / o[u], 3)
    if 'итог П1' in o and 'итог П2' in o:
        res['итог'] = round(1 / o['итог П1'] + 1 / o['итог П2'], 3)
    return res


def _day_of(ts, league):
    dt = datetime.fromtimestamp(int(ts), timezone.utc)
    if league == 'nhl':
        return dt.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    return dt.astimezone(MSK).strftime('%Y-%m-%d')


def _events(league, day):
    segs = _segments(league)
    subs, facs = _index()
    res = []
    for e in load().get('events', []):
        if e.get('parentId') or e.get('sportId') not in segs or not e.get('startTime') or not e.get('team1'):
            continue
        if _day_of(e['startTime'], league) != day:
            continue
        sub = {}
        for x in subs.get(e['id'], []):
            sub.setdefault(str(x.get('name') or '').strip(), []).extend(facs.get(x['id'], []))
            for y in subs.get(x['id'], []):          # «угловые / 1-й тайм угловые» — второй уровень
                sub.setdefault(str(y.get('name') or '').strip(), []).extend(facs.get(y['id'], []))
        res.append(dict(id=e['id'], t1=e['team1'], t2=e['team2'], start=int(e['startTime']), main=facs.get(e['id'], []), sub=sub))
    return res


def _log(rec):
    try:
        os.makedirs(LINES, exist_ok=True)
        with open(os.path.join(LINES, rec['d'] + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')
    except OSError as e:
        print('FONLOGERR %r' % e, flush=True)


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace('+00:00', 'Z')


def _short(o, keys=('П1', 'Х', 'П2', '1Х', 'Х2', 'итог П1', 'итог П2', 'ОЗ да')):
    main = ['%s %.2f' % (k, o[k]) for k in keys if k in o]
    main += ['%s %.2f' % (k, v) for k, v in o.items() if k.startswith(('Ф1 ', 'ТБ ', 'ТМ ', 'ИТ1Б', 'ИТ2Б')) and '(' not in k]
    return ' · '.join(main)


# ---------- хоккей ----------

def _mks(o, period):
    """{рынок: кэф} → рынки как у pin.py для calc.odds_for (одна цена — тоже рынок)."""
    m = []
    P = lambda d, v, pts=None: dict(designation=d, points=pts, price=v)  # noqa: E731
    if all(k in o for k in ('П1', 'Х', 'П2')):
        m.append(dict(type='moneyline', period=period, side=None, alt=False, prices=[P('home', o['П1']), P('draw', o['Х']), P('away', o['П2'])]))
    if '1Х' in o:
        m.append(dict(type='spread', period=period, side=None, alt=True, prices=[P('home', o['1Х'], 0.5)]))
    if 'Х2' in o:
        m.append(dict(type='spread', period=period, side=None, alt=True, prices=[P('away', o['Х2'], 0.5)]))
    if period == 6 and 'итог П1' in o and 'итог П2' in o:
        m.append(dict(type='moneyline', period=0, side=None, alt=False, prices=[P('home', o['итог П1']), P('away', o['итог П2'])]))
    for k, v in o.items():
        p = k.split()
        if p[0] in ('Ф1', 'Ф2') and '(' not in k:
            m.append(dict(type='spread', period=period, side=None, alt=True,
                          prices=[P('home' if p[0] == 'Ф1' else 'away', v, float(p[1]))]))
        elif p[0] in ('ТБ', 'ТМ'):
            m.append(dict(type='total', period=period, side=None, alt=True, prices=[P('over' if p[0] == 'ТБ' else 'under', v, float(p[1]))]))
        elif p[0] in ('ИТ1Б', 'ИТ1М', 'ИТ2Б', 'ИТ2М'):
            m.append(dict(type='team_total', period=period, side='home' if p[0][2] == '1' else 'away', alt=True,
                          prices=[P('over' if p[0][3] == 'Б' else 'under', v, float(p[1]))]))
    return m


def hockey_day(league, day, want=None):
    """→ {(хозяева, гости): {mks, flat, per, start}}. want — пары из расписания лиги (сверка сторон)."""
    want = set(want or [])
    res = {}
    evs = _events(league, day)
    print('FONSTAT %s %s: матчей у Фонбета %d' % (league, day, len(evs)), flush=True)
    for e in evs:
        h, a = teams.fon_team(e['t1'], league), teams.fon_team(e['t2'], league)
        if not h or not a:
            print('FONMISS %s | %s — %s | нет в словаре teams.fon_team' % (league, e['t1'], e['t2']), flush=True)
            continue
        o = flat(e['main'])
        per = {n: flat(e['sub'].get(nm)) for nm, n in SUBS_HOCKEY.items() if e['sub'].get(nm)}
        if want and (h, a) not in want and (a, h) in want:
            print('FONMISS %s | %s — %s | стороны наоборот, не беру' % (league, h, a), flush=True)
            continue
        mks = _mks(o, 6)
        for n, po in per.items():
            mks += _mks(po, n)
        res[(h, a)] = dict(mks=mks, flat=o, per=per, start=_iso(e['start']))
        print('FONMATCH %s—%s | %s — %s | %s | рынков %d (+периоды %d) | маржа %s'
              % (h, a, e['t1'], e['t2'], _iso(e['start']), len(o), sum(len(v) for v in per.values()),
                 overround(o).get('1Х2')), flush=True)
        print('FON %s—%s | %s' % (h, a, _short(o)), flush=True)
        _log(dict(t=datetime.now(timezone.utc).isoformat()[:16], league=league.upper(), d=day, h=h, a=a, fh=e['t1'], fa=e['t2'],
                  start=_iso(e['start']), main=o, per={str(k): v for k, v in per.items()},
                  sub={k: flat(v) for k, v in e['sub'].items() if k not in SUBS_HOCKEY and len(v) < 80}))
    miss = [p for p in want if p not in res]
    if miss:
        print('FONMISS %s | нет у Фонбета (или не сопоставлено): %s' % (league, ', '.join('%s—%s' % p for p in miss)), flush=True)
    return res


# ---------- футбол ----------

def foot_flat(e):
    """Основное (90 минут) + таймы + угловые / жёлтые / удары в створ — в именах football_wide."""
    o = flat(e['main'])
    for nm, pre in SUBS_FOOT.items():
        fs = e['sub'].get(nm)
        if not fs:
            continue
        s = flat(fs)
        if pre.endswith(' '):                     # таймы: «1-й тайм П1», «1-й тайм ТБ 0.5», «1-й тайм ИТ1Б 0.5»
            for k, v in s.items():
                o[pre + k] = v
            continue
        for k, v in s.items():                    # статистика: имена football_wide.stat_markets
            p = k.split()
            if k == 'П1':
                o['%s: больше у хозяев' % pre] = v
            elif k == 'П2':
                o['%s: больше у гостей' % pre] = v
            elif k == 'Х':
                o['%s: поровну' % pre] = v
            elif p[0] in ('ТБ', 'ТМ'):
                o['%s: %s %s' % (pre, p[0], p[1])] = v
            elif p[0] in ('ИТ1Б', 'ИТ1М', 'ИТ2Б', 'ИТ2М'):
                o['%s %s: %s %s' % (pre, 'хозяев' if p[0][2] == '1' else 'гостей', p[0][3], p[1])] = v
            elif p[0] == 'Ф1' and '(' not in k:
                o['%s: фора хозяев %s' % (pre, p[1])] = v
    return o


def foot_day(code, day):
    """→ [{h, a, t, start, flat}] — матчи турнира у Фонбета в день (по Москве)."""
    res = []
    for e in _events(code, day):
        o = foot_flat(e)
        res.append(dict(h=e['t1'], a=e['t2'], t=datetime.fromtimestamp(e['start'], MSK).strftime('%H:%M'), start=e['start'], flat=o))
    return res


def _ru(name):
    try:
        sys.path.insert(0, os.path.join(ROOT, 'render'))
        import football as RF
        return RF.resolve(name)
    except Exception:  # noqa: BLE001
        return name


def _nm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^\wа-яё ]+', ' ', str(s or '').lower().replace('ё', 'е'))).strip()


def _sim(a, b):
    import difflib
    a, b = _nm(a), _nm(b)
    if not a or not b:
        return 0.0
    if a == b or a.split()[0] == b.split()[0] and len(a.split()[0]) > 3:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def match_foot(events, ph, pa, t, day=None, code=''):
    """Матч Pinnacle (имена англ., время ЧЧ:ММ МСК) → событие Фонбета: начало ±15 мин; одно — оно, несколько —
    по похожести русских названий (render/football.py) обеих команд. Не нашлось — None и FONMISS в лог."""
    def mins(x):
        hh, mm = x.split(':')
        return int(hh) * 60 + int(mm)
    cand = [e for e in events if abs(mins(e['t']) - mins(t)) <= 15]
    rh, ra = _ru(ph), _ru(pa)
    best = None
    if len(cand) == 1 and max(_sim(rh, cand[0]['h']), _sim(ra, cand[0]['a'])) >= 0.5:
        best = cand[0]
    elif cand:
        sc = sorted(((_sim(rh, e['h']) + _sim(ra, e['a']), i) for i, e in enumerate(cand)), reverse=True)
        if sc[0][0] >= 1.3:
            best = cand[sc[0][1]]
    if best is None:
        print('FONMISS %s | %s %s — %s (%s — %s) | у Фонбета в это время: %s' % (code, t, ph, pa, rh, ra,
              '; '.join('%s %s — %s' % (e['t'], e['h'], e['a']) for e in cand) or 'нет'), flush=True)
        return None
    if day and not best.get('_logged'):
        best['_logged'] = True
        _log(dict(t=datetime.now(timezone.utc).isoformat()[:16], league=code, d=day, h=rh, a=ra, fh=best['h'], fa=best['a'],
                  start=_iso(best['start']), main=best['flat']))
    print('FONMATCH %s | %s — %s | Фонбет: %s — %s | рынков %d | маржа 1Х2 %s'
          % (code, rh, ra, best['h'], best['a'], len(best['flat']), overround(best['flat']).get('1Х2')), flush=True)
    return best


if __name__ == '__main__':
    if sys.argv[1] in ('khl', 'nhl'):
        hockey_day(sys.argv[1], sys.argv[2])
    else:
        for x in foot_day(sys.argv[2], sys.argv[3]):
            print('FON', x['t'], x['h'], '—', x['a'], '|', _short(x['flat']))
