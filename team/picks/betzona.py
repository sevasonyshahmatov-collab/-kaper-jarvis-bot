# -*- coding: utf-8 -*-
"""Прогнозы футбола с betzona.ru — база идей для наших футбольных постов (владелец 31.10).

Запуск только в Actions (сеть облака к сайту закрыта):
    python team/picks/betzona.py 2026-10-31            # прогнозы на день D и D+1
    python team/picks/betzona.py --probe               # разведка разметки (печать ссылок и текста страниц)
Вежливо: один проход в день, ≤1 запроса в секунду, не больше MAX_REQ страниц, без входа и обхода защиты.
Сырые страницы не сохраняются. Вывод — строки с метками (и копия ::notice BZ_* — логи Actions из облака закрыты):
    BZMATCH  лига | дата время МСК | хозяева — гости | url
    BZPRED   хозяева — гости | рынок | кэф | автор/рейтинг | довод (≤300 знаков)
    BZERR    ошибка;  BZDONE  итог
"""
import base64, gzip, json, re, sys, time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

BASE = 'https://betzona.ru/'
UA = 'Mozilla/5.0 (compatible; jarvibet-digest/1.0; one pass a day)'
MAX_REQ = 40
MSK = timezone(timedelta(hours=3))
OUT = []
_last = [0.0]
_n = [0]


def out(tag, text):
    line = '%s %s' % (tag, re.sub(r'\s+', ' ', str(text)).strip())
    OUT.append(line)
    print(line, flush=True)


def get(url):
    if _n[0] >= MAX_REQ:
        raise RuntimeError('лимит запросов %d' % MAX_REQ)
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _n[0] += 1
    r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'ru'}, timeout=25)
    _last[0] = time.time()
    if r.status_code != 200:
        raise RuntimeError('HTTP %d %s' % (r.status_code, url))
    r.encoding = r.apparent_encoding if not r.encoding or r.encoding.lower() == 'iso-8859-1' else r.encoding
    return r.text


class Page(HTMLParser):
    """Ссылки, видимый текст по блокам, классы, JSON-LD."""
    SKIP = {'script', 'style', 'noscript', 'svg'}
    BLOCK = {'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'br', 'section', 'article', 'td', 'span', 'a'}

    def __init__(self):
        super().__init__()
        self.links, self.text, self.classes, self.ld, self.ctext = [], [], {}, [], []
        self._cls = ''
        self._skip, self._a, self._ld, self._buf = 0, None, None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.BLOCK:
            self._flush()
        if a.get('class') and tag not in self.SKIP:
            self._cls = a['class'].split()[0]
        for c in (a.get('class') or '').split():
            self.classes[c] = self.classes.get(c, 0) + 1
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self._ld = []
        if tag in self.SKIP:
            self._skip += 1
        if tag == 'a' and a.get('href'):
            self._a = [a['href'], []]

    def handle_endtag(self, tag):
        if tag == 'script' and self._ld is not None:
            self.ld.append(''.join(self._ld))
            self._ld = None
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        if tag == 'a' and self._a:
            self.links.append((self._a[0], ' '.join(''.join(self._a[1]).split())))
            self._a = None
        if tag in self.BLOCK:
            self._flush()

    def handle_data(self, d):
        if self._ld is not None:
            self._ld.append(d)
        if self._skip:
            return
        if self._a:
            self._a[1].append(d)
        self._buf.append(d)

    def _flush(self):
        t = ' '.join(''.join(self._buf).split())
        if t:
            self.text.append(t)
            self.ctext.append((self._cls, t))
        self._buf = []


def parse(html):
    p = Page()
    p.feed(html)
    p._flush()
    return p


def notices():
    """Строки BZ* пометками ::notice BZ_i/n (gzip+base64), как foot_notice.py."""
    b = base64.b64encode(gzip.compress('\n'.join(OUT).encode('utf-8'))).decode()
    step = 3500
    parts = [b[i:i + step] for i in range(0, len(b), step)] or ['']
    for i, s in enumerate(parts[:10]):
        print('::notice title=BZ_%d/%d::%s' % (i + 1, len(parts), s), flush=True)


# ---------- разведка ----------
def probe():
    host = urlparse(BASE).netloc
    html = get(BASE)
    p = parse(html)
    out('BZPROBE', 'главная: %d знаков, ссылок %d' % (len(html), len(p.links)))
    seen, cand = set(), []
    for href, t in p.links:
        u = urljoin(BASE, href).split('#')[0]
        if urlparse(u).netloc != host or u in seen:
            continue
        seen.add(u)
        if re.search(r'futbol|football|soccer|prognoz|predict|express|tip', u, re.I) or re.search(r'футбол|прогноз', t, re.I):
            cand.append((u, t))
    for u, t in cand[:120]:
        out('BZLINK', '%s | %s' % (u, t[:90]))
    top = sorted(p.classes.items(), key=lambda x: -x[1])[:60]
    out('BZCLASS', ' '.join('%s:%d' % kv for kv in top))
    # разделы футбола
    sect = [u for u, t in cand if re.search(r'futbol|football', u, re.I)]
    sect = sorted(set(sect), key=len)[:3]
    for u in sect:
        try:
            q = parse(get(u))
        except Exception as e:
            out('BZERR', '%s: %s' % (u, e))
            continue
        out('BZSECT', '%s: ссылок %d, блоков текста %d' % (u, len(q.links), len(q.text)))
        out('BZCLASS', ' '.join('%s:%d' % kv for kv in sorted(q.classes.items(), key=lambda x: -x[1])[:60]))
        for t in q.text[:150]:
            out('BZTXT', t[:200])
        for href, t in q.links:
            v = urljoin(u, href)
            if urlparse(v).netloc == host and re.search(r'prognoz|predict', v, re.I):
                out('BZLINK', '%s | %s' % (v, t[:90]))
    # две страницы матча
    pages = [u for u, t in cand if re.search(r'prognoz|predict', u, re.I) and u.count('/') >= 5][:2]
    for u in pages:
        try:
            q = parse(get(u))
        except Exception as e:
            out('BZERR', '%s: %s' % (u, e))
            continue
        out('BZPAGE', u)
        for s in q.ld[:3]:
            out('BZLD', s[:1500])
        out('BZCLASS', ' '.join('%s:%d' % kv for kv in sorted(q.classes.items(), key=lambda x: -x[1])[:60]))
        for t in q.text[:220]:
            out('BZTXT', t[:200])
    out('BZDONE', 'probe, запросов %d' % _n[0])


def probe_urls(urls):
    for u in urls:
        try:
            q = parse(get(u))
        except Exception as e:
            out('BZERR', '%s: %s' % (u, e))
            continue
        out('BZPAGE', u)
        for s in q.ld[:3]:
            out('BZLD', s[:1500])
        for c, t in q.ctext[:400]:
            out('BZTXT', '[%s] %s' % (c, t[:300]))
    out('BZDONE', 'probe, запросов %d' % _n[0])


def main(argv):
    try:
        urls = [a for a in argv if a.startswith('http')]
        if '--probe' in argv and urls:
            probe_urls(urls)
        elif '--probe' in argv:
            probe()
        else:
            day = next((a for a in argv if re.match(r'\d{4}-\d\d-\d\d$', a)), datetime.now(MSK).strftime('%Y-%m-%d'))
            run(day)
    except Exception as e:
        out('BZERR', '%s: %s' % (type(e).__name__, e))
        out('BZDONE', 'ошибка, запросов %d' % _n[0])
    notices()


LEAGUES = {   # страница лиги на сайте → наш турнир; «Футбол. Англия» включает Чемпионшип — турнир сверяем по странице прогноза
    'prognozy-chempionat-england.html': 'АПЛ', 'prognozy-chempionat-spain.html': 'Ла Лига',
    'prognozy-chempionat-italy.html': 'Серия А', 'prognozy-chempionat-germanii.html': 'Бундеслига',
    'prognozy-chempionat-francii.html': 'Лига 1'}
CUP = [('Премьер-лига', 'Англия', 'АПЛ'), ('Ла Лига', 'Испания', 'Ла Лига'), ('Примера', 'Испания', 'Ла Лига'), ('Серия A', 'Италия', 'Серия А'),
       ('Серия А', 'Италия', 'Серия А'), ('Бундеслига', 'Германия', 'Бундеслига'), ('Лига 1', 'Франция', 'Лига 1'),
       ('Лига чемпионов', '', 'Лига чемпионов'), ('Лига Европы', '', 'Лига Европы')]
MON = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
       'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12, 'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
       'июн': 6, 'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
       'февр': 2, 'сент': 9, 'нояб': 11}
MKT = re.compile(r'^(П1|П2|Х|X|1X|X2|12|Победа ?[12]|Ничья|ТБ|ТМ|Ф1|Ф2|ИТБ|ИТМ|Обе|1-й тайм|Тотал|Фора)', re.I)


def ddate(t, year):
    m = re.search(r'(\d{1,2}) ([а-я]+)\.?,? (\d\d:\d\d)', t)
    if not m or m.group(2) not in MON:
        return None, None
    return '%d-%02d-%02d' % (year, MON[m.group(2)], int(m.group(1))), m.group(3)


def cup_of(text):
    for k, c, name in CUP:
        if k in text and (not c or c in text) and 'Кубок' not in text and 'Чемпионшип' not in text:
            return name
    return None


def cards(q, page_url):
    """Карточки экспертов (ссылка на страницу прогноза) и короткие прогнозы пользователей со страницы лиги."""
    exp, usr, cur = [], [], None
    links = {}
    for href, t in q.links:
        if 'prognoz-' in href and href.endswith('.html'):
            links.setdefault(re.sub(r'\s+', ' ', t), []).append(urljoin(page_url, href))
    for c, t in q.ctext:
        if c == 'bets-description-card__match-info__name-string':
            exp.append({'match': t})
        elif c == 'bets-description-card__match-info__description' and exp:
            exp[-1]['when'] = t
        elif c == 'bets-description-card__ratio__value' and exp:
            exp[-1]['odds'] = t
        elif c == 'bets-users-short-card__match-title':
            cur = {'match': t, 'body': []}
            usr.append(cur)
        elif cur is not None and c == 'mr-2' and 'when' not in cur:
            cur['when'] = t
        elif cur is not None and c == 'bets-users-short-card__header-user-info-name':
            cur['author'] = t
        elif cur is not None and c == 'bets-users-short-card__header-bet-title':
            cur['market'] = t
        elif cur is not None and c == 'bets-users-short-card__header-bet-ratio':
            cur['odds'] = t
        elif cur is not None and c == 'bets-users-short-card__body':
            cur['body'].append(t)
    # ссылки на страницы экспертов: по порядку карточек
    hrefs = [urljoin(page_url, h) for h, t in q.links if re.search(r'-prognoz-\d+\.html$', h) and ' - ' in t
             and re.search(r'\d\d:\d\d', t)]
    seen, uniq = set(), []
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return exp, usr, uniq


def detail(u):
    q = parse(get(u))
    d = {'url': u, 'info': [], 'raw': [], 'concl': []}
    teams, vals = [], []
    for i, (c, t) in enumerate(q.ctext):
        if c == 'icon-cup' and 'cup' not in d:
            d['cup'] = t
        elif c == 'match-review-head-team-name':
            teams.append(t)
        elif c == 'match-review-head-date' and 'date' not in d:
            d['date'] = t
        elif c == 'match-review-head-scores' and 'time' not in d:
            d['time'] = t
        elif c == 'author-stats_name' and 'author' not in d:
            d['author'] = t
        elif c == 'author-stats_stats-text' and 'astat' not in d:
            d['astat'] = t
        elif c == 'author-stats_value-text':
            vals.append(t)
        elif c == 'info':
            d['info'].append(t)
        elif c == 'bet_name' and 'market' not in d:
            d['market'] = t
        elif c == 'ratio' and 'odds' not in d:
            d['odds'] = t
        elif c == 'gray-block':
            d['concl'].append(t)
        elif re.search(r'bet|forecast|prognoz|stavk|ratio|coef|verdict|conclusion|outcome', c, re.I) \
                and c != 'forecast-description' and len(d['raw']) < 12:
            d['raw'].append('[%s] %s' % (c, t[:160]))
    d['teams'] = teams[:2]
    d['roi'], d['profit'], d['n'] = (vals + ['', '', ''])[:3]
    for line in d['raw']:
        t = line.split('] ', 1)[1]
        if 'market' not in d and MKT.match(t) and len(t) < 40:
            d['market'] = t
        if 'odds' not in d and re.fullmatch(r'\d\.\d{1,3}', t):
            d['odds'] = t
    return d, q


def run(day):
    d0 = datetime.strptime(day, '%Y-%m-%d')
    days = {day, (d0 + timedelta(days=1)).strftime('%Y-%m-%d')}
    exp_all, usr_all = [], []
    for page, lg in LEAGUES.items():
        u = urljoin(BASE, page)
        try:
            q = parse(get(u))
        except Exception as e:
            out('BZERR', '%s: %s' % (u, e))
            continue
        exp, usr, hrefs = cards(q, u)
        for k, e in enumerate(exp):
            e['lg'], e['url'] = lg, hrefs[k] if k < len(hrefs) else ''
            e['day'], e['time'] = ddate(e.get('when', ''), d0.year)
        for x in usr:
            x['lg'] = lg
            x['day'], x['time'] = ddate(x.get('when', ''), d0.year)
        exp_all += [e for e in exp if e['day'] in days]
        usr_all += [x for x in usr if x['day'] in days]
        out('BZLG', '%s: экспертов %d (на D/D+1 %d), коротких %d, ссылок %d' % (
            lg, len(exp), sum(e['day'] in days for e in exp), len(usr), len(hrefs)))
    # страницы экспертов — турнир, рынок, автор, доводы
    top = set()
    dbg = '--debug' in sys.argv
    for e in exp_all:
        if not e['url'] or _n[0] >= MAX_REQ - 1:
            continue
        try:
            d, q = detail(e['url'])
        except Exception as ex:
            out('BZERR', '%s: %s' % (e['url'], ex))
            continue
        cup = cup_of(d.get('cup', ''))
        if not cup:
            out('BZSKIP', '%s | %s — не топ-лига' % (e['match'], d.get('cup', '?')))
            continue
        top.add(e['match'])
        out('BZMATCH', '%s | %s %s | %s | %s' % (cup, e['day'], e['time'], e['match'].replace(' - ', ' — '), e['url']))
        out('BZPRED', '%s | %s | %s | эксперт %s, ROI %s, прогнозов %s (%s) | %s' % (
            e['match'], d.get('market', '?'), d.get('odds', e.get('odds', '?')), d.get('author', '?'), d['roi'], d['n'],
            d.get('astat', '').replace('Статистика прогнозов автора ', ''), ' '.join(d['concl'])[:450]))
        if dbg:
            dbg = False
            for c, t in q.ctext[250:700]:
                if c not in ('name', 'sub_name', 'drop', 'col', 'col-1', 'col-2') and 'menu' not in c:
                    out('BZDBG', '[%s] %s' % (c, t[:200]))
    for x in usr_all:
        if x['match'] not in top:
            continue
        tag = 'top'
        out('BZPRED', '%s | %s | %s | пользователь %s, %s %s, %s | %s' % (
            x['match'], x.get('market', '?'), x.get('odds', '?'), x.get('author', '?'), x['day'], x['time'], tag,
            ' '.join(x['body'])[:350]))
    out('BZDONE', '%s: экспертных %d, коротких %d, топ-матчей %d, запросов %d' % (
        day, len(exp_all), len(usr_all), len(top), _n[0]))


if __name__ == '__main__':
    main(sys.argv[1:])
