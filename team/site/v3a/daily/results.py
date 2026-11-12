# -*- coding: utf-8 -*-
"""Итоги прогнозов канала для сайта v3a — единая запись прогноза (владелец 10.11: «итогов на сайте нет»).

Без сети. Источники:
  • team/site/months_out/published.json — хоккейные прогнозы канала с итогом по счёту матча (team/site/months.py);
  • team/site/months_out/feed.json      — вся лента канала: экспрессы, «Итог экспресса», футбольные прогнозы и их итоги;
  • team/picks/SENT.md (ветка команды)  — что предлагала модель и её вероятность: метка «по модели» / «выбор автора»;
  • team/picks/EXPRESS_RESULTS.md       — итоги экспрессов, если поста с итогом в ленте не нашлось.
Ничего не выдумывает: нет итога в источниках — запись остаётся «без итога» и в статистику не входит.

  python team/site/v3a/daily/results.py [MONTHS_OUT] [TEAM_DIR]
     → data/results.json, data/results.js (window.__RESULTS), data/results-lite.js (window.__RESLITE — сводка для главной)

Запись (picks[]): id — номер поста в канале, url, sport hockey|football, lg, kind single|express,
  src model|author|None (None — метки нет: до 15.10 бот не вёл учёт), d — начало матча МСК, posted — когда вышел пост,
  h, a, bet, kef, pm — вероятность модели (доля) или None, r w|l|p|None, sc — счёт, u — результат в единицах при ставке 1,
  legs — ноги экспресса [{h, a, bet, kef, sc, r}], rid — номер поста с итогом.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(V3A, '..', '..', '..'))
MSK = timezone(timedelta(hours=3))
CHANNEL = 'jarvibet'
MON = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9,
       'октября': 10, 'ноября': 11, 'декабря': 12}
FOOT_LG = {'АПЛ': 'epl', 'Ла Лига': 'laliga', 'Серия А': 'seriea', 'Бундеслига': 'bundesliga', 'Лига 1': 'ligue1', 'РПЛ': 'rpl',
           'Лига чемпионов': 'ucl', 'ЛЧ': 'ucl', 'Лига Европы': 'uel', 'ЛЕ': 'uel', 'Лига конференций': 'uecl', 'Футбол': 'foot'}
LG_NAME = {'khl': 'КХЛ', 'nhl': 'НХЛ', 'epl': 'АПЛ', 'laliga': 'Ла Лига', 'seriea': 'Серия А', 'bundesliga': 'Бундеслига',
           'ligue1': 'Лига 1', 'rpl': 'РПЛ', 'ucl': 'Лига чемпионов', 'uel': 'Лига Европы', 'uecl': 'Лига конференций',
           'foot': 'Футбол'}
DASH = r'\s+[—–-]\s+'
OK, NO, BACK = '✅', '❌', '↩'


def _read(p):
    try:
        with open(p, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def _kef(s):
    m = re.search(r'(\d+)[,.](\d+)', s or '')
    return round(float(m.group(1) + '.' + m.group(2)), 2) if m else None


def _nt(s):
    """Название команды для сравнения."""
    return re.sub(r'[^a-zа-я0-9]', '', (s or '').lower().replace('ё', 'е'))


def _pair(h, a):
    return _nt(h) + '|' + _nt(a)


def _clean(s):
    return re.sub(r'\s+', ' ', re.sub('[%s%s%s️✔]' % (OK, NO, BACK), '', s or '')).strip(' .;·')


def _mark(s):
    """Отметка итога в строке: w / l / p / None."""
    if NO in s:
        return 'l'
    if BACK in s:
        return 'p'
    if OK in s or '✔' in s:
        return 'w'
    return None


def _units(r, kef):
    if r == 'w' and kef:
        return round(kef - 1, 2)
    if r == 'l':
        return -1.0
    if r == 'p':
        return 0.0
    return None


def _date(day, mon, hhmm, ref):
    """«3 ноября», «23:00» → время начала МСК; год — как у поста (ref), с поправкой на рубеж года."""
    y = ref.year
    d = datetime(y, mon, day, tzinfo=MSK)
    if (d - ref).days > 200:
        d = d.replace(year=y - 1)
    elif (ref - d).days > 200:
        d = d.replace(year=y + 1)
    if hhmm:
        h, m = hhmm
        d = d.replace(hour=h, minute=m)
    return d


# ---------------------------------------------------------------- экспрессы
EXP_HEAD = re.compile(r'^(?P<lg>[А-Яа-яЁё0-9 ]+?)\s*·\s*(?P<d>\d{1,2})\s+(?P<m>[а-я]+).*?·.*(?:экспресс|ставка на (?:два|три) матча)', re.I)
LEG_HEAD = re.compile(r'^(\d)\.\s*(.+?)%s(.+?)(?:,\s*(?:(\d{1,2})\s+([а-я]+),\s*)?(\d{1,2}):(\d\d)\s*МСК)?\s*$' % DASH)
LEG_BET = re.compile(r'^(.+?)\s*·\s*(\d+[,.]\d+)\s*$')
RES_LEG = re.compile(r'^\W*(?:\d\.\s*)?(.+?)%s(.+?)\s+(\d+:\d+(?:\s*(?:ОТ|Б))?)\s*·\s*(.+)$' % DASH)


def express_posts(feed):
    """Посты-экспрессы нового вида («НХЛ · 9 ноября · экспресс», ноги «1. A — B, 02:00 МСК» + «ставка · кэф», «Общий кэф: …»)."""
    out = []
    for x in feed:
        lines = [t.strip() for t in x['text'] if t.strip()]
        if not lines:
            continue
        m = EXP_HEAD.match(lines[0])
        if not m or m.group('m') not in MON:
            continue
        posted = datetime.fromisoformat(x['posted'])
        day0 = _date(int(m.group('d')), MON[m.group('m')], None, posted)
        legs, total, i = [], None, 1
        while i < len(lines):
            lh = LEG_HEAD.match(lines[i])
            if lh and i + 1 < len(lines) and LEG_BET.match(lines[i + 1]):
                lb = LEG_BET.match(lines[i + 1])
                d = day0
                if lh.group(4) and lh.group(5) in MON:
                    d = _date(int(lh.group(4)), MON[lh.group(5)], None, posted)
                if lh.group(6):
                    d = d.replace(hour=int(lh.group(6)), minute=int(lh.group(7)))
                legs.append(dict(h=lh.group(2).strip(), a=lh.group(3).strip(), bet=_clean(lb.group(1)), kef=_kef(lb.group(2)),
                                 d=d.strftime('%Y-%m-%d %H:%M')))
                i += 2
                continue
            mt = re.match(r'(?i)^общий к[эе]ф\w*\s*:?\s*(\d+[,.]\d+)(.*)$', lines[i])
            if mt:
                total = dict(kef=_kef(mt.group(1)), mark=_mark(mt.group(2)))
            i += 1
        if len(legs) < 2:
            continue
        lgname = m.group('lg').strip()
        lg = {'КХЛ': 'khl', 'НХЛ': 'nhl'}.get(lgname.upper()) or FOOT_LG.get(lgname, 'foot')
        tags = ' '.join(lines[-1:]).lower()
        if lg == 'foot':
            for k, v in (('лигачемпионов', 'ucl'), ('лигаевропы', 'uel'), ('лигаконференций', 'uecl')):
                if k in tags:
                    lg = v
        kef = total['kef'] if total else None
        if kef is None and all(l_['kef'] for l_ in legs):
            kef = 1.0
            for l_ in legs:
                kef *= l_['kef']
            kef = round(kef, 2)
        out.append(dict(id=x['id'], posted=posted, lg=lg, legs=legs, kef=kef, mark=total['mark'] if total else None))
    return out


def express_results(feed):
    """Посты с итогом экспресса → [{id, posted, r, pairs: {пара: (счёт, отметка)}}]."""
    out = []
    for x in feed:
        lines = [t.strip() for t in x['text'] if t.strip()]
        text = ' '.join(lines)
        legs = {}
        for t in lines:
            m = RES_LEG.match(_clean_keep(t))
            if m and _mark(t):
                legs[_pair(m.group(1), m.group(2))] = (m.group(3).strip(), _mark(t))
        if len(legs) < 2:
            continue
        low = text.lower()
        if not re.search(r'экспресс|итог ставки на два матча|зашёл!|зашел!', low):
            continue
        if re.search(r'не\s+заш', low):
            r = 'l'
        elif 'возврат' in low:
            r = 'p'
        elif re.search(r'заш[её]?л', low):
            r = 'w'
        else:
            marks = [v[1] for v in legs.values()]
            r = 'l' if 'l' in marks else 'w' if all(v == 'w' for v in marks) else None
        out.append(dict(id=x['id'], posted=datetime.fromisoformat(x['posted']), r=r, legs=legs))
    return out


def _clean_keep(t):
    """Строка ноги без отметок в начале («✅ A — B 0:6 · …») — отметку читаем отдельно."""
    return re.sub('^[%s%s%s️✔ ]+' % (OK, NO, BACK), '', t)


def ledger_express(text, year):
    """team/picks/EXPRESS_RESULTS.md → [{r, pairs}] — запасной источник итога экспресса."""
    out = []
    for line in text.splitlines():
        m = re.match(r'^- (\d\d)\.(\d\d) (\d\d):(\d\d) · (\S+) · (\S+) ([^·]+)· кэф ([^·]+)·(.*)$', line)
        if not m:
            continue
        r = {'зашёл': 'w', 'не зашёл': 'l', 'возврат': 'p'}.get(m.group(7).strip())
        legs = {}
        for part in m.group(9).split(';'):
            lm = re.match(r'^\s*(.+?)%s(.+?)\s+(\d+:\d+(?:\s*(?:ОТ|Б))?)' % DASH, part)
            if lm:
                legs[_pair(lm.group(1), lm.group(2))] = (lm.group(3), _mark(part))
        if legs and r:
            out.append(dict(r=r, legs=legs, pid=m.group(5)))
    return out


def build_express(feed, ledger_text):
    picks = []
    results = express_results(feed)
    led = ledger_express(ledger_text, 0)
    for e in express_posts(feed):
        pairs = [_pair(l_['h'], l_['a']) for l_ in e['legs']]
        res = None
        for r in results:
            if r['posted'] > e['posted'] and r['posted'] - e['posted'] < timedelta(days=3) and all(p in r['legs'] for p in pairs):
                res = r
                break
        if res is None:
            for r in led:
                if all(p in r['legs'] for p in pairs):
                    res = dict(r, id=None)
                    break
        out = None
        if res:
            out = res['r']
            for l_, p in zip(e['legs'], pairs):
                l_['sc'], l_['r'] = res['legs'][p]
            marks = [l_.get('r') for l_ in e['legs']]
            # «возврат» в учёте бота при всех зашедших ногах — экспресс зашёл (итог поста в канале — «Зашёл»)
            if out == 'p' and all(v == 'w' for v in marks):
                out = 'w'
        elif e['mark']:
            out = e['mark']                       # владелец отметил итог у общего кэфа («Общий кэф: 2,54✅»)
        first = min(l_['d'] for l_ in e['legs'])
        picks.append(dict(id=e['id'], url='https://t.me/%s/%d' % (CHANNEL, e['id']), sport='football' if e['lg'] not in ('khl', 'nhl') else 'hockey',
                          lg=e['lg'], kind='express', src='author', d=first, posted=e['posted'].strftime('%Y-%m-%d %H:%M'),
                          h='', a='', bet=('Экспресс из %d событий' if len(e['legs']) > 2 else 'Ставка на два матча') % (() if len(e['legs']) < 3 else len(e['legs'])), kef=e['kef'], pm=None, r=out,
                          sc='', u=_units(out, e['kef']), legs=e['legs'], rid=res.get('id') if res else None))
    return picks


# ---------------------------------------------------------------- футбол
FOOT_HEAD = re.compile(r'^(?P<lg>[А-Яа-яЁё0-9 ]+?)\s*·\s*(?P<d>\d{1,2})\s+(?P<m>[а-я]+)\s*·\s*(?P<hh>\d{1,2}):(?P<mm>\d\d)\s*МСК')
RES_LINE = re.compile(r'^(.+?)%s(.+?)\s+(\d+:\d+)(?:\s|$|[·(])' % DASH)


def foot_outcomes(feed):
    """Итоги одиночных прогнозов из постов канала (итоги дня, «Итог матча»): строка «✅ A — B 0:2 …» → {пара: [(когда, итог, счёт, пост)]}.
    Посты об экспрессах пропускаем — там итог ноги, а не прогноза."""
    out = {}
    for x in feed:
        lines = [t.strip() for t in x['text'] if t.strip()]
        if not lines or re.search(r'(?i)итог экспресса|итог ставки на|·\s*экспресс|общий к[эе]ф', ' '.join(lines[:3] + lines[-3:])):
            continue
        for t in lines:
            mk = _mark(t[:3])
            if not mk:
                continue
            m = RES_LINE.match(_clean_keep(t))
            if m:
                out.setdefault(_pair(m.group(1), m.group(2)), []).append((datetime.fromisoformat(x['posted']), mk, m.group(3), x['id']))
    return out


def build_football(feed, skip=(), hockey=False):
    """Посты-прогнозы вида «Лига · дата · время МСК / A — B / Прогноз: … / Кэф: …». hockey=True — хоккейные посты на ещё не
    сыгранные матчи (их нет в published.json): без итога, только для метки и ссылки на карточке матча."""
    picks = []
    lgs = {'КХЛ': 'khl', 'НХЛ': 'nhl'} if hockey else FOOT_LG
    outs = foot_outcomes(feed)
    for x in feed:
        lines = [t.strip() for t in x['text'] if t.strip()]
        if len(lines) < 4:
            continue
        m = FOOT_HEAD.match(lines[0])
        if not m or m.group('lg').strip() not in lgs or m.group('m') not in MON or x['id'] in skip:
            continue
        tm = re.match(r'^(.+?)%s(.+)$' % DASH, lines[1])
        bm = re.match(r'(?i)^прогноз\s*:\s*(.+)$', lines[2])
        km = re.match(r'(?i)^к[эе]ф\w*\s*:\s*(.+)$', lines[3])
        if not (tm and bm and km):
            continue
        posted = datetime.fromisoformat(x['posted'])
        start = _date(int(m.group('d')), MON[m.group('m')], (int(m.group('hh')), int(m.group('mm'))), posted)
        h, a = tm.group(1).strip(), tm.group(2).strip()
        kef = _kef(km.group(1))
        r, sc, rid = _mark(km.group(1)), '', None          # владелец ставит ✅/❌ у кэфа
        if hockey:
            r = None                               # итог хоккея — только по счёту (months.py), не по отметке
        for when, mk, score, pid in outs.get(_pair(h, a), []):
            if not hockey and timedelta(0) < when - start < timedelta(days=3):
                r, sc, rid = (r or mk), score, pid
                break
        bet = _clean(bm.group(1))
        bet = bet[:1].upper() + bet[1:] if not bet.isupper() else bet.capitalize()
        picks.append(dict(id=x['id'], url='https://t.me/%s/%d' % (CHANNEL, x['id']), sport='hockey' if hockey else 'football', lg=lgs[m.group('lg').strip()],
                          kind='single', src=None, d=start.strftime('%Y-%m-%d %H:%M'), posted=posted.strftime('%Y-%m-%d %H:%M'),
                          h=h, a=a, bet=bet, kef=kef, pm=None, r=r, sc=sc, u=_units(r, kef), rid=rid))
    return picks


def foot_scores():
    """football/data/football.json → {(пара, 'ГГГГ-ММ-ДД'): (голы хозяев, голы гостей)} — сыгранные матчи сезона."""
    try:
        d = json.loads(_read(os.path.join(V3A, 'football', 'data', 'football.json')))
    except ValueError:
        return {}
    out, teams = {}, d.get('teams') or {}
    for t in teams.values():
        for g in t.get('games') or []:
            o = teams.get(g.get('o'))
            if not o or g.get('gf') is None or g.get('ga') is None or not g.get('h'):
                continue
            out[(_pair(t['n'], o['n']), g['d'][:10])] = (int(g['gf']), int(g['ga']))
    return out


def _foot_leg(bet, h, a, hs, as_):
    """Простая футбольная ставка по счёту за 90 минут → w / l / p / None (None — не разобрал, итог не ставим)."""
    b = ' ' + re.sub(r'\s+', ' ', bet.lower().replace('ё', 'е')) + ' '
    if re.search(r'удар|углов|карточ|створ|офсайд|фол', b):
        return None

    def side(text):
        th, ta = _nt(h), _nt(a)
        t = _nt(text)
        fh = any(t.find(th[:n]) >= 0 for n in (len(th), max(4, len(th) - 2)) if n <= len(th))
        fa = any(t.find(ta[:n]) >= 0 for n in (len(ta), max(4, len(ta) - 2)) if n <= len(ta))
        return 'h' if fh and not fa else 'a' if fa and not fh else None

    def num(text):
        m = re.search(r'(\d+(?:[.,]\d+)?)', text)
        return float(m.group(1).replace(',', '.')) if m else None

    def ou(val, line, over):
        if val == line:
            return 'p'
        return 'w' if (val > line) == over else 'l'

    m = re.search(r'(больше|меньше)', b)
    if 'обе забьют' in b and not m:
        return 'w' if hs and as_ else 'l'
    if 'тотал' in b and m:
        over = m.group(1) == 'больше'
        line = num(b[b.find('тотал'):].replace('1х', '').replace('х2', ''))
        if line is None:
            return None
        if 'индивидуальн' in b or side(b.split('тотал', 1)[1].split('больше')[0].split('меньше')[0]):
            sd = side(b.split('тотал', 1)[1])
            if not sd:
                return None
            return ou(hs if sd == 'h' else as_, line, over)
        return ou(hs + as_, line, over)
    if 'не проиграет' in b or 'двойной шанс' in b or re.search(r'\b(1х|х1|х2|2х)\b', b):
        sd = 'h' if re.search(r'\b(1х|х1)\b', b) else 'a' if re.search(r'\b(х2|2х)\b', b) else side(b)
        if not sd:
            return None
        return 'w' if (hs >= as_ if sd == 'h' else as_ >= hs) else 'l'
    if 'фора' in b:
        sd = side(b)
        m2 = re.search(r'([+−–-])?\s*(\d+(?:[.,]\d+)?)', b[b.find('фора'):].replace('(', ' ').replace(')', ' '))
        if not sd or not m2:
            return None
        hc = float(m2.group(2).replace(',', '.')) * (-1 if m2.group(1) in ('−', '–', '-') else 1)
        diff = (hs - as_ if sd == 'h' else as_ - hs) + hc
        return 'w' if diff > 0 else 'l' if diff < 0 else 'p'
    if 'победа' in b:
        sd = side(b.split('победа', 1)[1])
        if not sd:
            return None
        return 'w' if (hs > as_ if sd == 'h' else as_ > hs) else 'l'
    return None


def foot_settle(bet, h, a, score):
    """Ставка (в том числе «A + B») по счёту → итог или None."""
    parts = [x for x in re.split(r'\s+\+\s+|\s+и\s+(?=тотал)', bet) if x.strip()]
    res = [_foot_leg(x, h, a, score[0], score[1]) for x in parts]
    if not res or any(r is None for r in res):
        return None
    return 'l' if 'l' in res else 'p' if all(r == 'p' for r in res) else 'w'


def by_score(picks):
    """Где итога в канале нет, а матч сыгран и ставка простая — итог по счёту (rs='score')."""
    sc = foot_scores()
    n = 0
    for p in picks:
        if p['sport'] != 'football':
            continue
        if p['kind'] == 'single' and not p['r']:
            g = sc.get((_pair(p['h'], p['a']), p['d'][:10]))
            if g:
                r = foot_settle(p['bet'], p['h'], p['a'], g)
                if r:
                    p.update(r=r, sc='%d:%d' % g, u=_units(r, p['kef']), rs='score')
                    n += 1
        elif p['kind'] == 'express' and not p['r']:
            rs = []
            for l_ in p['legs']:
                g = sc.get((_pair(l_['h'], l_['a']), l_['d'][:10]))
                r = foot_settle(l_['bet'], l_['h'], l_['a'], g) if g else None
                if r:
                    l_['sc'], l_['r'] = '%d:%d' % g, r
                rs.append(r)
            if rs and all(rs):
                r = 'l' if 'l' in rs else 'p' if all(x == 'p' for x in rs) else 'w'
                p.update(r=r, u=_units(r, p['kef']), rs='score')
                n += 1
    return n


# ---------------------------------------------------------------- хоккей + метка «модель / автор»
def sent_rows(text):
    """team/picks/SENT.md → {(пара, 'ММ-ДД'): [{bet, kef, pm, lg}]} — что предлагала модель."""
    out = {}
    for line in text.splitlines():
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) < 6 or not re.fullmatch(r'\d{4}-\d+', c[0]):
            continue
        m = re.match(r'(.+?)%s(.+?),\s*(\d\d)\.(\d\d)\s+(\d\d):(\d\d)' % DASH, c[2])
        if not m:
            continue
        pm = re.match(r'\s*(\d+(?:[,.]\d+)?)\s*%', c[5])
        bet = re.sub(r'\s*\([^)]*\)', '', c[3]).strip()
        out.setdefault((_pair(m.group(1), m.group(2)), '%s-%s' % (m.group(4), m.group(3))), []).append(
            dict(bet=bet, kef=_kef(c[4]), pm=round(float(pm.group(1).replace(',', '.')) / 100, 3) if pm else None, lg=c[1], pid=c[0]))
    return out


def _legs(settle, bet, h, a):
    try:
        return json.dumps(settle.parse(bet, h, a), sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return None


def _same_bet(settle, b1, b2, h, a):
    n = lambda s: re.sub(r'[^a-zа-я0-9]', '', s.lower().replace('ё', 'е'))  # noqa: E731
    if n(b1) == n(b2):
        return True
    if settle is None:
        return False
    l1, l2 = _legs(settle, b1, h, a), _legs(settle, b2, h, a)
    return bool(l1) and l1 == l2


def build_hockey(published, feed, sent, settle):
    posted = {x['id']: x['posted'] for x in feed}
    picks = []
    first_bot = min((k[1] for k in sent), default=None)
    for p in published:
        kef = p.get('kef')
        r = {'win': 'w', 'loss': 'l', 'push': 'p'}.get(p.get('r'))
        src, pm = None, None
        cands = sent.get((_pair(p['h'], p['a']), p['d'][5:10]))
        if cands:
            src = 'author'                        # бот предлагал этот матч; владелец поставил своё — «выбор автора»
            for c in cands:
                if _same_bet(settle, c['bet'], p['bet'], p['h'], p['a']):
                    src, pm = 'model', c['pm']    # ставка как у модели
                    break
        ps = posted.get(p['id'])
        picks.append(dict(id=p['id'], url='https://t.me/%s/%d' % (CHANNEL, p['id']), sport='hockey', lg=p['lg'], kind='single', src=src,
                          d=p['d'], posted=ps[:16].replace('T', ' ') if ps else None, h=p['h'], a=p['a'], bet=p['bet'], kef=kef, pm=pm,
                          r=r, sc=p.get('sc') or '', u=_units(r, kef), rid=None))
    return picks, first_bot


def label_football(picks, sent, settle=None):
    for p in picks:
        if p['kind'] != 'single':
            continue
        cands = sent.get((_pair(p['h'], p['a']), p['d'][5:10]))
        if cands:
            p['src'] = 'author'
            for c in cands:
                if _same_bet(settle, c['bet'], p['bet'], p['h'], p['a']):
                    p['src'], p['pm'] = 'model', c['pm']


def match_posts(picks):
    """Матчи окна сайта (data/today.json, football.json up) → {ключ матча: пост в канале}: метка и ссылка на карточке матча."""
    idx = {}
    try:
        for m in json.loads(_read(os.path.join(V3A, 'data', 'today.json')) or '{}').get('matches') or []:
            idx[(_pair(m.get('hn'), m.get('an')), m['key'].split('|')[1])] = m['key']
    except (ValueError, KeyError):
        pass
    try:
        fb = json.loads(_read(os.path.join(V3A, 'football', 'data', 'football.json')) or '{}')
        tn = {k: v.get('n') for k, v in (fb.get('teams') or {}).items()}
        for m in fb.get('up') or []:
            idx[(_pair(tn.get(m['h']), tn.get(m['a'])), m['t'][:10])] = '%s|%s|%s|%s' % (m['lg'], m['t'][:10], m['h'], m['a'])
    except (ValueError, KeyError):
        pass
    out = {}
    for p in picks:
        if p['kind'] != 'single':
            continue
        k = idx.get((_pair(p['h'], p['a']), p['d'][:10]))
        if k:
            out[k] = dict(id=p['id'], url=p['url'], src=p['src'], bet=p['bet'], kef=p['kef'], r=p['r'])
    return out


# ---------------------------------------------------------------- сводка
def tally(rows):
    done = [p for p in rows if p['r']]
    w = sum(1 for p in done if p['r'] == 'w')
    l_ = sum(1 for p in done if p['r'] == 'l')
    ku = [p for p in done if p.get('kef') and p['r'] in ('w', 'l')]
    units = round(sum(p['u'] for p in ku), 2)
    kefs = [p['kef'] for p in done if p.get('kef')]
    return dict(n=len(done), w=w, l=l_, p=len(done) - w - l_, units=units, nk=len(ku),
                roi=round(100 * units / len(ku), 1) if ku else None,
                kef=round(sum(kefs) / len(kefs), 2) if kefs else None,
                rate=round(100 * w / (w + l_), 1) if (w + l_) else None)


MONTH = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def summary(picks, now):
    def grp(rows):
        return dict(all=tally(rows), model=tally([p for p in rows if p['src'] == 'model' and p['kind'] == 'single']),
                    author=tally([p for p in rows if p['src'] == 'author' and p['kind'] == 'single']),
                    express=tally([p for p in rows if p['kind'] == 'express']),
                    single=tally([p for p in rows if p['kind'] == 'single']),
                    hockey=tally([p for p in rows if p['sport'] == 'hockey' and p['kind'] == 'single']),
                    football=tally([p for p in rows if p['sport'] == 'football' and p['kind'] == 'single']))
    months = []
    for k in sorted({p['d'][:7] for p in picks if p['r']}, reverse=True):
        rows = [p for p in picks if p['d'][:7] == k]
        months.append(dict(m=k, name='%s %s' % (MONTH[int(k[5:])], k[:4]), live=int(k == now.strftime('%Y-%m')), **grp(rows)))
    # калибровка модели: по ставкам «по модели» с вероятностью — что обещала и сколько зашло
    cal = []
    mp = [p for p in picks if p['src'] == 'model' and p['pm'] and p['r'] in ('w', 'l')]
    for lo, hi in ((0.5, 0.6), (0.6, 0.7), (0.7, 1.01)):
        rs = [p for p in mp if lo <= p['pm'] < hi]
        if rs:
            cal.append(dict(lo=int(lo * 100), hi=min(int(hi * 100), 100), n=len(rs), w=sum(1 for p in rs if p['r'] == 'w'),
                            pm=round(100 * sum(p['pm'] for p in rs) / len(rs), 1)))
    days = sorted({p['d'][:10] for p in picks if p['r']})
    last = days[-1] if days else None
    return dict(total=grp(picks), months=months, cal=cal, last_day=last, pending=sum(1 for p in picks if not p['r']))


def add_emblems(picks):
    """Эмблемы клубов к названиям (правило владельца 11.11): he / ae — путь от корня сайта; у экспрессов — в каждом событии.
    Названия в постах те же, что на сайте: хоккей — names в assets/data/teams.json, футбол — n клубов в football.json."""
    maps = []
    try:
        t = json.loads(_read(os.path.join(V3A, 'assets', 'data', 'teams.json')) or '{}')
        maps.append(('assets/em/%s.webp', {v: k for k, v in (t.get('names') or {}).items()}))
    except ValueError:
        pass
    try:
        fb = json.loads(_read(os.path.join(V3A, 'football', 'data', 'football.json')) or '{}')
        maps.append(('assets/fc/%s.webp', {v.get('n'): k for k, v in (fb.get('teams') or {}).items()}))
    except ValueError:
        pass

    def em(name, foot):
        for pat, mp in (maps[::-1] if foot else maps):
            rel = pat % mp[name] if name in mp else None
            if rel and os.path.exists(os.path.join(V3A, rel)):
                return rel
        return None

    for p in picks:
        foot = p.get('sport') == 'football'
        for x in [p] + (p.get('legs') or []):
            for k, e in (('h', 'he'), ('a', 'ae')):
                v = em(x.get(k), foot) if x.get(k) else None
                if v:
                    x[e] = v


# Показ ставки на сайте: владелец пишет ставки в канале от руки — «2.5» и «2,5», «Нешвила» и «Нэшвилла», «ИТ1Б (2.5)».
# Приводим к одному виду только текст для показа; сверка с моделью и расчёт итога идут до этого, по исходному тексту (12.11).
_TYPOS = {'Нешвила': 'Нэшвилла', 'Нешвилла': 'Нэшвилла', 'Нешвилл': 'Нэшвилл', 'Нешвил': 'Нэшвилл', 'ска': 'СКА', 'цска': 'ЦСКА'}
_NUM = r'\d+(?:,\d+)?'


def show_bet(bet):
    b = re.sub(r'(?<=\d)\.(?=\d)', ',', bet or '')
    b = re.sub(r'\(\s*([+\-−]?%s)\s*\)' % _NUM, r'\1', b)                      # «(2,5)» → «2,5»
    b = re.sub(r'(?<![\d,])-(?=\d)', '−', b)                                   # минус, а не дефис
    m = re.fullmatch(r'ИТ([12])\s*([БМ])\s*(%s)' % _NUM, b, re.I)
    if m:
        b = 'Индивидуальный тотал %s %s %s' % ('хозяев' if m.group(1) == '1' else 'гостей',
                                                'больше' if m.group(2).upper() == 'Б' else 'меньше', m.group(3))
    b = re.sub(r'\+\s*(%s)\s+(больше|меньше)\b' % _NUM, r'+ тотал \2 \1', b)   # «Х2 + 5,5 меньше»
    b = re.sub(r'(?<![+\-−\d,])\b(%s)\s+(больше|меньше)\b' % _NUM, r'\2 \1', b)  # «тотал 2,5 больше» → «тотал больше 2,5»
    b = re.sub(r'[А-Яа-яЁё]+', lambda w: _TYPOS.get(w.group(0), w.group(0)), b)
    b = re.sub(r'\s+', ' ', b).strip()
    return b[:1].upper() + b[1:] if b else b


def _cap_club(bet, names):
    """«тотал металлурга», «фора каролины» → с заглавной: слово начинается как название клуба из этого же прогноза."""
    def fix(w):
        t = w.group(0)
        if t != t.lower() and t != t.capitalize():
            return t
        tl = t.lower().replace('ё', 'е')
        if tl in ('ска', 'цска'):
            return tl.upper()
        for n in names:
            nl = n.lower().replace('ё', 'е')
            if ' ' not in n and '-' not in n and len(nl) >= 5 and t == t.lower() and tl.startswith(nl[:len(nl) - 1]) and len(tl) <= len(nl) + 3:
                return t[:1].upper() + t[1:]
        return t
    return re.sub(r'[А-Яа-яЁё]+', fix, bet)


def show_bets(picks):
    for p in picks:
        legs = p.get('legs') or []
        names = {x for x in [p.get('h'), p.get('a')] + [l_.get(k) for l_ in legs for k in ('h', 'a')] if x}
        p['bet'] = _cap_club(show_bet(p.get('bet')), names)
        for leg in legs:
            leg['bet'] = _cap_club(show_bet(leg.get('bet')), names)


def main():
    mo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'team', 'site', 'months_out')
    team = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'team')
    published = json.loads(_read(os.path.join(mo, 'published.json')) or '[]')
    feed = json.loads(_read(os.path.join(mo, 'feed.json')) or '[]')
    if not published or not feed:
        print('RESULTS нет данных канала (%s) — прежние итоги оставлены' % mo)
        return 1
    settle = None
    for d in (os.path.join(team, 'daily'), os.path.join(ROOT, 'team', 'daily')):
        if os.path.exists(os.path.join(d, 'settle.py')):
            sys.path.insert(0, d)
            try:
                import settle  # noqa: E402
            except Exception as e:  # noqa: BLE001
                print('RESULTS settle не загрузился: %s' % e)
            break
    sent = sent_rows(_read(os.path.join(team, 'picks', 'SENT.md')))
    hockey, first_bot = build_hockey(published, feed, sent, settle)
    foot = build_football(feed)
    label_football(foot, sent)
    now0 = datetime.now(MSK).strftime('%Y-%m-%d %H:%M')
    known = {(_pair(p['h'], p['a']), p['d'][:10]) for p in hockey}
    ahead = [p for p in build_football(feed, skip={p['id'] for p in hockey}, hockey=True)
             if p['d'] > now0 and (_pair(p['h'], p['a']), p['d'][:10]) not in known]
    try:
        from settle import canon
        for p in ahead:
            p['h'], p['a'] = canon(p['h']), canon(p['a'])
    except Exception:  # noqa: BLE001
        pass
    label_football(ahead, sent, settle)
    hockey += ahead
    exp = build_express(feed, _read(os.path.join(team, 'picks', 'EXPRESS_RESULTS.md')))
    nsc = by_score(foot + exp)
    picks = sorted(hockey + foot + exp, key=lambda p: (p['d'], p['id']), reverse=True)
    add_emblems(picks)
    show_bets(picks)
    now = datetime.now(MSK)
    out = dict(built=now.strftime('%Y-%m-%d %H:%M'), since=min(p['d'][:10] for p in picks), channel='https://t.me/' + CHANNEL,
               labels_since='2026-10-15' if sent else None, sum=summary(picks, now), picks=picks)
    dd = os.path.join(V3A, 'data')
    with open(os.path.join(dd, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(dd, 'results.js'), 'w', encoding='utf-8') as f:
        f.write('window.__RESULTS=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
    last = out['sum']['last_day']
    lite = dict(built=out['built'], since=out['since'], sum=dict(total=out['sum']['total'], months=out['sum']['months'][:1]),
                last_day=last, last=[p for p in picks if p['d'][:10] == last and p['r']],
                recent=[dict(r=p['r'], kind=p['kind']) for p in picks if p['r']][:20])
    with open(os.path.join(dd, 'results-lite.js'), 'w', encoding='utf-8') as f:
        f.write('window.__RESLITE=' + json.dumps(lite, ensure_ascii=False, separators=(',', ':')) + ';\n')
    posts = match_posts(picks)
    with open(os.path.join(dd, 'posts.js'), 'w', encoding='utf-8') as f:
        f.write('window.JV_POSTS=' + json.dumps(posts, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print('RESULTS матчей окна с постом в канале: %d' % len(posts))
    t = out['sum']['total']
    print('RESULTS прогнозов %d: хоккей %d, футбол %d, экспрессы %d; с итогом %d (зашло %d, не зашло %d, возврат %d), без итога %d; '
          'по модели %d, выбор автора %d; итог по счёту (не из канала): %d' % (len(picks), len(hockey), len(foot), len(exp), t['all']['n'], t['all']['w'], t['all']['l'],
                                               t['all']['p'], out['sum']['pending'], t['model']['n'], t['author']['n'], nsc))
    return 0


if __name__ == '__main__':
    sys.exit(main())
