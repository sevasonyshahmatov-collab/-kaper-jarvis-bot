#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка домена сайта в день покупки и после (docs/handoff/SITE_DOMAIN_DAY.md). Только чтение: DNS через публичный
DNS-over-HTTPS (dns.google), сайт — обычными запросами. Ничего не меняет.

Запуск: python3 team/site/v3a/seo/domain_check.py домен.ru [--open]
  --open — проверять и открытие для поиска (после SITE_INDEXING_OPEN=1): без noindex, robots разрешает, sitemap на домен.
Итог: строки «ОК» / «ВНИМАНИЕ» / «ОШИБКА»; код выхода 1, если есть ошибки."""
import json
import random
import re
import ssl
import string
import sys
import urllib.error
import urllib.request

GH_A = {'185.199.108.153', '185.199.109.153', '185.199.110.153', '185.199.111.153'}
GH_AAAA = {'2606:50c0:8000::153', '2606:50c0:8001::153', '2606:50c0:8002::153', '2606:50c0:8003::153'}
GH_IO = 'sevasonyshahmatov-collab.github.io'
UA = {'User-Agent': 'jarvis-domain-check/1.0'}
res = {'ОК': 0, 'ВНИМАНИЕ': 0, 'ОШИБКА': 0}


def say(level, text):
    res[level] += 1
    print('%-9s %s' % (level, text))


def dns(name, typ):
    """Ответы DNS (строки) или None, если запрос не удался."""
    url = 'https://dns.google/resolve?name=%s&type=%s' % (name, typ)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            d = json.load(r)
    except Exception as e:  # noqa: BLE001
        print('           (DNS %s %s не удалось спросить: %s)' % (name, typ, e))
        return None
    return [a['data'].strip('"').rstrip('.') for a in d.get('Answer', []) if a.get('type') == {'A': 1, 'AAAA': 28, 'CNAME': 5, 'TXT': 16, 'CAA': 257}[typ]], d.get('AD')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(url, follow=True):
    """(код, заголовки, текст, конечный адрес) или (None, ошибка, '', url)."""
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return r.status, r.headers, r.read(400000).decode('utf-8', 'replace'), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read(200000).decode('utf-8', 'replace') if e.fp else '', url
    except Exception as e:  # noqa: BLE001
        return None, str(e), '', url


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    dom = args[0].lower().strip().rstrip('/').replace('https://', '').replace('http://', '')
    want_open = '--open' in sys.argv
    print('Домен: %s%s\n' % (dom, ' (проверка открытия для поиска)' if want_open else ''))

    # ── DNS ──
    r = dns(dom, 'A')
    if r:
        a, ad = r
        if set(a) == GH_A:
            say('ОК', 'A: четыре адреса GitHub Pages')
        elif set(a) <= GH_A and a:
            say('ВНИМАНИЕ', 'A: только %d из 4 адресов GitHub Pages: %s' % (len(a), ', '.join(a)))
        else:
            say('ОШИБКА', 'A: чужие или нет адресов: %s' % (', '.join(a) or 'пусто'))
        say('ОК' if ad else 'ВНИМАНИЕ', 'DNSSEC: %s' % ('подпись проверена' if ad else 'не включён (включить у регистратора, если есть)'))
    r = dns(dom, 'AAAA')
    if r is not None:
        aaaa = set(r[0])
        say('ОК' if aaaa == GH_AAAA else 'ВНИМАНИЕ', 'AAAA: %s' % ('четыре адреса GitHub Pages' if aaaa == GH_AAAA else (', '.join(sorted(aaaa)) or 'нет (желательно добавить)')))
    r = dns('www.' + dom, 'CNAME')
    if r is not None:
        c = r[0]
        say('ОК' if c and c[0].lower() == GH_IO else 'ВНИМАНИЕ', 'www: %s' % (('CNAME на ' + c[0]) if c else 'нет CNAME на ' + GH_IO))
    rnd = ''.join(random.choice(string.ascii_lowercase) for _ in range(12))
    r = dns('%s.%s' % (rnd, dom), 'A')
    if r is not None:
        say('ОШИБКА' if r[0] else 'ОК', 'Запись * (все поддомены): %s' % ('ЕСТЬ — убрать: чужой сайт на GitHub может занять любой поддомен' if r[0] else 'нет'))
    r = dns(dom, 'CAA')
    if r is not None:
        caa = ' | '.join(r[0])
        say('ОК' if 'letsencrypt.org' in caa else 'ВНИМАНИЕ', 'CAA: %s' % (caa or 'нет (рекомендуется: 0 issue "letsencrypt.org")'))
    r = dns(dom, 'TXT')
    if r is not None:
        spf = [t for t in r[0] if t.startswith('v=spf1')]
        say('ОК' if spf else 'ВНИМАНИЕ', 'SPF: %s' % (spf[0] if spf else 'нет — от имени домена можно слать письма (пока почты нет: "v=spf1 -all")'))
    r = dns('_dmarc.' + dom, 'TXT')
    if r is not None:
        dm = [t for t in r[0] if t.startswith('v=DMARC1')]
        say('ОК' if dm and 'p=reject' in dm[0] else 'ВНИМАНИЕ', 'DMARC: %s' % (dm[0] if dm else 'нет (пока почты нет: "v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s")'))
    r = dns('_github-pages-challenge-sevasonyshahmatov-collab.' + dom, 'TXT')
    if r is not None:
        say('ОК' if r[0] else 'ОШИБКА', 'Домен подтверждён в аккаунте GitHub (TXT _github-pages-challenge): %s' % ('да' if r[0] else 'НЕТ — сделать до DNS-записей сайта и не удалять'))

    # ── HTTPS и переадресации ──
    code, hd, body, final = get('https://%s/' % dom)
    if code is None:
        say('ОШИБКА', 'https://%s/ не открывается: %s' % (dom, hd))
        body = ''
    else:
        say('ОК' if code == 200 else 'ОШИБКА', 'https://%s/ — код %s' % (dom, code))
        hsts = hd.get('Strict-Transport-Security') if hd else None
        say('ОК' if hsts else 'ВНИМАНИЕ', 'HSTS: %s' % (hsts or 'нет (на GitHub Pages включается вместе с «Enforce HTTPS»)'))
    code, hd, _, _ = get('http://%s/' % dom, follow=False)
    loc = hd.get('Location', '') if code and hasattr(hd, 'get') else ''
    say('ОК' if code in (301, 308) and loc.startswith('https://') else 'ОШИБКА',
        'http → https: %s' % ('%s → %s' % (code, loc) if code else 'нет ответа') + ('' if loc.startswith('https://') else ' — включить «Enforce HTTPS»'))
    code, hd, _, final = get('https://www.%s/' % dom)
    say('ОК' if code == 200 and dom in final and '://www.' not in final else 'ВНИМАНИЕ', 'www → основной адрес: %s' % (final if code else 'не открывается'))
    code, hd, _, final = get('https://%s/' % GH_IO)
    say('ОК' if code == 200 and dom in final else 'ВНИМАНИЕ', 'Старый адрес github.io ведёт на домен: %s' % (final if code else 'нет ответа'))
    code, _, _, _ = get('https://%s/no-such-page-%s/' % (dom, rnd))
    say('ОК' if code == 404 else 'ОШИБКА', 'Несуществующая страница — код %s (нужно 404)' % code)

    # ── адрес в страницах и поиск ──
    if body:
        if 'jarvibet.example' in body or GH_IO in body:
            say('ОШИБКА', 'Главная: в коде остались заглушка или старый адрес — запустить сборку с SITE_ORIGIN')
        else:
            say('ОК', 'Главная: заглушки и старого адреса нет')
        can = re.search(r'<link rel="canonical" href="([^"]+)"', body)
        say('ОК' if can and can.group(1).startswith('https://%s/' % dom) else 'ОШИБКА', 'canonical главной: %s' % (can.group(1) if can else 'нет'))
        if 'http://' in re.sub(r'http://www\.w3\.org[^"\']*', '', body):
            say('ВНИМАНИЕ', 'Главная: есть ссылки http:// (смешанное содержимое?)')
        noidx = 'name="robots" content="noindex' in body
        if want_open:
            say('ОШИБКА' if noidx else 'ОК', 'Главная открыта для поиска' if not noidx else 'Главная всё ещё noindex')
        else:
            say('ОК' if noidx else 'ВНИМАНИЕ', 'Главная закрыта от поиска (noindex), как и нужно до открытия' if noidx else 'Главная без noindex')
    code, _, rob, _ = get('https://%s/robots.txt' % dom)
    if code == 200:
        allow = re.search(r'^\s*Disallow:\s*/\s*$', rob, re.M) is None
        if want_open:
            say('ОК' if allow and ('Sitemap: https://%s/sitemap.xml' % dom) in rob else 'ОШИБКА', 'robots.txt разрешает обход и указывает sitemap на домен')
        else:
            say('ОК', 'robots.txt открывается')
    else:
        say('ОШИБКА', 'robots.txt — код %s' % code)
    code, _, sm, _ = get('https://%s/sitemap.xml' % dom)
    if want_open:
        bad = re.findall(r'<loc>(?!https://%s/)' % re.escape(dom), sm or '')
        say('ОК' if code == 200 and not bad and '<loc>' in sm else 'ОШИБКА', 'sitemap.xml: код %s, чужих адресов %d' % (code, len(bad)))
    code, _, dr, _ = get('https://%s/draft/' % dom)
    if code == 200:
        say('ОК' if 'name="robots" content="noindex' in dr else 'ОШИБКА', 'Черновик /draft/ закрыт от поиска (noindex)')

    print('\nИтог: ОК %(ОК)d, внимание %(ВНИМАНИЕ)d, ошибок %(ОШИБКА)d' % res)
    return 1 if res['ОШИБКА'] else 0


if __name__ == '__main__':
    sys.exit(main())
