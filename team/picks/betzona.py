# -*- coding: utf-8 -*-
"""Прогнозы футбола с betzona.ru — база идей для наших футбольных постов (владелец 31.10).

Запуск только в Actions (сеть облака к сайту закрыта):
    python team/picks/betzona.py 2026-10-31            # прогнозы на день D и D+1
    python team/picks/betzona.py --probe               # разведка разметки (печать ссылок и текста страниц)
Вежливо: один проход в день, ≤1 запроса в секунду, не больше MAX_REQ страниц, без входа и обхода защиты.
Сырые страницы не сохраняются. Вывод — строки с метками (и копия ::notice PB_* — логи Actions из облака закрыты):
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
        self.links, self.text, self.classes, self.ld = [], [], {}, []
        self._skip, self._a, self._ld, self._buf = 0, None, None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for c in (a.get('class') or '').split():
            self.classes[c] = self.classes.get(c, 0) + 1
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self._ld = []
        if tag in self.SKIP:
            self._skip += 1
        if tag == 'a' and a.get('href'):
            self._a = [a['href'], []]
        if tag in self.BLOCK:
            self._flush()

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
        self._buf = []


def parse(html):
    p = Page()
    p.feed(html)
    p._flush()
    return p


def notices():
    """Строки BZ* пометками ::notice PB_i/n (gzip+base64), как foot_notice.py."""
    b = base64.b64encode(gzip.compress('\n'.join(OUT).encode('utf-8'))).decode()
    step = 3500
    parts = [b[i:i + step] for i in range(0, len(b), step)] or ['']
    for i, s in enumerate(parts[:10]):
        print('::notice title=PB_%d/%d::%s' % (i + 1, len(parts), s), flush=True)


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


def main(argv):
    try:
        if '--probe' in argv:
            probe()
        else:
            day = next((a for a in argv if re.match(r'\d{4}-\d\d-\d\d$', a)), datetime.now(MSK).strftime('%Y-%m-%d'))
            run(day)
    except Exception as e:
        out('BZERR', '%s: %s' % (type(e).__name__, e))
        out('BZDONE', 'ошибка, запросов %d' % _n[0])
    notices()


def run(day):
    raise NotImplementedError('парсер — после разведки')


if __name__ == '__main__':
    main(sys.argv[1:])
