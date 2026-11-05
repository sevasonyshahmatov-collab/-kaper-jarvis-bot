# -*- coding: utf-8 -*-
"""Футбол и экспрессы канала @jarvibet для «Честных итогов» по месяцам (владелец 05.11: «футбольные результаты в общий
расчёт за месяц и экспрессы тоже»).

Источник — та же лента t.me/s/jarvibet, что у хоккея (team/daily/channel.py), только посты, которые хоккейный разбор не берёт:
- **футбол** — пост «Лига чемпионов · 4 ноября · 23:00 МСК / ПСВ — Брюгге / Прогноз: … / Кэф: 1,60» (любой турнир, кроме КХЛ/НХЛ);
- **экспресс** — пост «… · экспресс / 1. А — Б, 20:45 МСК / ставка · 1,70 / … / Общий кэф: 3,07» (одна строка в итогах, кэф — общий).

Итог берём из канала, а не считаем сами (счёта футбола и ударов в данных лиг нет):
- футбол — строка «✅ ПСВ — Брюгге 1:2 · …» / «❌Леванте — Атлетико 0:2 (…)» в посте итогов, «✅ А — Б 2:1» в начале поста
  «Итог матча» или ✅/❌ в строке «Кэф: 1,74✅» самого поста (владелец так отмечает сыгранные);
- экспресс — пост «Итог экспресса ✅ Зашёл! / ❌ Не зашёл / ↩️ …» (ответ на купон или с теми же матчами) либо ✅/❌ у кэфа купона.
Нет итога — прогноз ждёт и в месяц не входит (как несыгранный хоккей)."""
import re
from datetime import datetime, timedelta

import channel
from data import MSK

HOCKEY = re.compile(r'(?i)^\W*(кхл|нхл)\b')
HEAD = re.compile(r'^\W*(?P<lg>[^·]+?)\s*·\s*(?P<d>\d{1,2})\s+(?P<m>[а-я]+)(?:\s*·\s*(?P<t>\d{1,2}[:.]\d\d)\s*МСК)?\s*$', re.I)
TEAMS = re.compile(r'^\W*(?P<h>[^—–]+?)\s+[—–]\s+(?P<a>[^—–]+?)\W*$')
BET = re.compile(r'(?i)^\W*прогноз\s*[:\-–—]\s*(?P<b>.+?)\s*$')
KEF = re.compile(r'(?i)^\W*кэф\s*[:\-–—]?\s*(?P<k>\d+(?:[.,]\d+)?)\s*(?P<mark>✅|❌|↩️?|➖)?')
TOTAL = re.compile(r'(?i)общий\s+кэф\s*[:\-–—]?\s*(?P<k>\d+(?:[.,]\d+)?)\s*(?P<mark>✅|❌|↩️?|➖)?')
LEG = re.compile(r'^\s*\d+\.\s*(?P<h>[^—–]+?)\s+[—–]\s+(?P<a>.+?)(?:,.*МСК)?\s*$')
RES = re.compile(r'^\s*(?P<mark>✅|❌|➖|↩️?|✔️)\s*(?:\d+\.\s*)?(?P<h>[^—–]+?)\s+[—–]\s+(?P<a>.+?)\s+(?P<hg>\d+)\s*:\s*(?P<ag>\d+)')
MARK = {'✅': 'win', '✔️': 'win', '❌': 'loss', '➖': 'push', '↩': 'push', '↩️': 'push'}
WINDOW = timedelta(days=4)


def _n(s):
    return re.sub(r'[^\w]+', ' ', (s or '').lower().replace('ё', 'е')).strip()


def _kef(s):
    try:
        return round(float(s.replace(',', '.')), 2)
    except (TypeError, ValueError):
        return None


def _when(post, d, m, t):
    """Дата из шапки поста («4 ноября», «23:00») + год публикации → datetime МСК."""
    mon = channel.MONTHS.get(m.lower())
    if not mon or not post.get('posted'):
        return post.get('posted')
    y = post['posted'].year
    hh, mm = (int(x) for x in re.split(r'[:.]', t)) if t else (12, 0)
    try:
        w = datetime(y, mon, int(d), hh, mm, tzinfo=MSK)
    except ValueError:
        return post['posted']
    if w - post['posted'] > timedelta(days=200):        # пост в декабре про матч в январе — год следующий
        w = w.replace(year=y - 1)
    elif post['posted'] - w > timedelta(days=200):
        w = w.replace(year=y + 1)
    return w


def _lines(post):
    return [t for t, _ in post.get('text') or []]


def foot_pick(post):
    """Пост-прогноз на футбол → dict или None."""
    L = _lines(post)
    if len(L) < 3 or HOCKEY.match(L[0]) or 'экспресс' in L[0].lower():
        return None
    h = HEAD.match(L[0])
    tm = TEAMS.match(L[1]) if h else None
    if not (h and tm):
        return None
    bet = kef = mark = None
    for t in L[2:8]:
        mb, mk = BET.match(t), KEF.match(t)
        if mb and bet is None:
            bet = mb.group('b').rstrip('✅❌➖ ')
        elif mk and kef is None:
            kef, mark = _kef(mk.group('k')), mk.group('mark')
    if not bet:
        return None
    lg = h.group('lg').strip()
    return dict(kind='foot', msg_id=post['id'], lg=lg, home=tm.group('h').strip(), away=tm.group('a').strip(),
                start=_when(post, h.group('d'), h.group('m'), h.group('t')), bet=bet[:1].upper() + bet[1:], kef=kef,
                mark=MARK.get(mark) if mark else None)


def express(post):
    """Пост-купон → dict или None: ноги (пары команд), общий кэф."""
    L = _lines(post)
    if not L or HOCKEY.match(L[0]) and 'экспресс' not in L[0].lower() or 'экспресс' not in L[0].lower():
        return None
    if re.search(r'(?i)итог', L[0]):
        return None
    legs = [(m.group('h').strip(), m.group('a').strip()) for m in (LEG.match(t) for t in L[1:]) if m]
    kef = mark = None
    for t in L:
        m = TOTAL.search(t)
        if m:
            kef, mark = _kef(m.group('k')), m.group('mark')
    if len(legs) < 2 or not kef:
        return None
    sport = 'КХЛ' if re.match(r'(?i)\W*кхл', L[0]) else 'НХЛ' if re.match(r'(?i)\W*нхл', L[0]) else 'Футбол'
    return dict(kind='express', msg_id=post['id'], lg=sport, legs=legs, kef=kef, start=post['posted'],
                mark=MARK.get(mark) if mark else None, head=L[0])


def _results(posts):
    """Строки итогов из всех постов: [(номер поста, когда, отметка, хозяева, гости, голы х, голы г)]."""
    out = []
    for p in posts:
        if re.search(r'(?i)экспресс', ' '.join(_lines(p)[:3])):    # итог экспресса: свои ставки по тем же матчам
            continue
        for t in _lines(p):
            m = RES.match(t)
            if m:
                out.append((p['id'], p.get('posted'), MARK.get(m.group('mark')), _n(m.group('h')), _n(m.group('a')),
                            int(m.group('hg')), int(m.group('ag'))))
    return out


def _express_status(text):
    t = text.lower()
    if re.search(r'не\s+заш[её]л|не\s+зашла|❌\s*не', t):
        return 'loss'
    if re.search(r'итог экспресса\s*↩|вернул|возврат', t):
        return 'push'
    if re.search(r'заш[её]л|✅\s*зашёл', t):
        return 'win'
    return None


def rows(posts):
    """Посты ленты → (строки для month_stats, ждут итога [(прогноз, почему)])."""
    res = _results(posts)
    foot, exp = {}, {}
    for p in posts:
        if p.get('reply'):                       # ответ на пост (итог матча, повтор) — не новый прогноз
            continue
        f = foot_pick(p)
        if f and f['start']:
            foot[(_n(f['home']), _n(f['away']), f['start'].date())] = f        # повтор поста — берём последний
            continue
        e = express(p)
        if e and e['start']:
            exp[e['msg_id']] = e
    out, wait = [], []
    for f in sorted(foot.values(), key=lambda f: f['msg_id']):
        hit = [r for r in res if r[3] == _n(f['home']) and r[4] == _n(f['away']) and r[0] != f['msg_id']
               and r[1] and timedelta(hours=-6) <= r[1] - f['start'] <= WINDOW]
        mark, g = f['mark'], {}                  # отметка владельца у кэфа («Кэф: 1,74✅»); пост итогов — важнее
        if hit:
            r = hit[-1]                          # последний итог (поздний пост поправляет ранний)
            mark, g = r[2], dict(hg=r[5], ag=r[6])
        if not mark:
            wait.append((f, 'нет итога в канале'))
            continue
        out.append(dict(kind='foot', msg_id=f['msg_id'], league='FOOT', lg=f['lg'], home=f['home'], away=f['away'],
                        start=f['start'], bet=f['bet'], short=f['bet'], kef=f['kef'], res=mark, g=g, legs=None))
    for e in sorted(exp.values(), key=lambda e: e['msg_id']):
        pairs = {(_n(h), _n(a)) for h, a in e['legs']}
        status = e['mark']
        for p in posts:
            if p['id'] <= e['msg_id'] or p['id'] in exp:
                continue
            text = '\n'.join(_lines(p))
            if not p.get('posted') or p['posted'] - e['start'] > WINDOW + timedelta(days=2):
                continue
            linked = p.get('reply') == e['msg_id']
            got = sum(1 for h, a in pairs if h in _n(text) and a in _n(text))
            if not (linked or (got >= min(2, len(pairs)) and re.search(r'(?i)экспресс|заш[её]л', text))):
                continue
            s = _express_status(text)
            if not s and got:                    # нет слов — по отметкам ног («✅ А — Б 2:1 · …»)
                marks = [MARK.get(m.group('mark')) for m in (RES.match(t) for t in _lines(p))
                         if m and (_n(m.group('h')), _n(m.group('a'))) in pairs]
                s = 'loss' if 'loss' in marks else 'win' if marks and all(m == 'win' for m in marks) else None
            if s:
                status = s
        if not status:
            wait.append((dict(e, home=e['head'], away='', bet='экспресс'), 'нет итога экспресса в канале'))
            continue
        n = len(e['legs'])
        out.append(dict(kind='express', msg_id=e['msg_id'], league='EXPRESS', lg='Экспресс · ' + e['lg'],
                        home='Экспресс: %s' % ', '.join('%s — %s' % hl for hl in e['legs']), away='',
                        start=e['start'], bet='%d %s, общий кэф' % (n, 'события' if n < 5 else 'событий'),
                        short='экспресс', kef=e['kef'], res=status, g={}, legs=None))
    return out, wait
