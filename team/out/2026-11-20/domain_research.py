# -*- coding: utf-8 -*-
"""Разовая проверка перед покупкой домена (20.11): свободны ли домены (WHOIS), что предлагают регистраторы
(2FA, DNSSEC, запрет переноса, автопродление, идентификация через Госуслуги), поиск знаков JARVIS.
Только чтение публичных страниц, ничего не регистрирует. Итог — в журнал запуска (DOMRES …)."""
import html
import re
import socket
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (jarvis-domain-research)', 'Accept-Language': 'ru'}


def p(*a):
    print('DOMRES', *a, flush=True)


def whois(server, q):
    try:
        s = socket.create_connection((server, 43), timeout=20)
        s.sendall((q + '\r\n').encode('idna' if False else 'utf-8'))
        out = b''
        while True:
            c = s.recv(4096)
            if not c:
                break
            out += c
        s.close()
        return out.decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return 'ERR %s' % e


def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return r.status, r.read(3_000_000).decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def text(h):
    h = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(h))


def snippets(t, words, width=260, limit=6):
    out, seen = [], set()
    for w in words:
        for m in re.finditer(re.escape(w), t, re.I):
            a = max(0, m.start() - width // 2)
            k = a // 200
            if k in seen:
                continue
            seen.add(k)
            out.append(t[a:a + width])
            if len(out) >= limit:
                return out
    return out


# ── 1. WHOIS ──
p('=== WHOIS')
for d in ['jarvibet.ru', 'jarvisbet.ru', 'jarvis-bet.ru', 'jarvibet.su', 'jarvis-ai.ru']:
    r = whois('whois.tcinet.ru', d)
    free = 'No entries found' in r
    keep = [l.strip() for l in r.splitlines() if re.match(r'\s*(domain|registrar|created|paid-till|free-date|state|org|person)\s*:', l, re.I)]
    p(d, 'СВОБОДЕН' if free else 'ЗАНЯТ', '|', ' ; '.join(keep)[:400] if not free else '', r[:120] if r.startswith('ERR') else '')
for d in ['jarvibet.com', 'jarvibet.net', 'jarvisbet.com', 'jarvis-bet.com']:
    r = whois('whois.verisign-grs.com', 'domain ' + d)
    free = 'No match for' in r
    keep = [l.strip() for l in r.splitlines() if re.match(r'\s*(Registrar|Creation Date|Registry Expiry Date|Domain Status|Name Server):', l)]
    p(d, 'СВОБОДЕН' if free else 'ЗАНЯТ', '|', ' ; '.join(keep[:8])[:500] if not free else '', r[:120] if r.startswith('ERR') else '')

# ── 2. Регистраторы и правила зоны ──
p('=== РЕГИСТРАТОРЫ')
pages = [
    ('reg.ru DNSSEC', 'https://help.reg.ru/support/dns-servery-i-nastroyka-zony/dopolnitelnyye-vozmozhnosti/dnssec', ['Госуслуг', 'ЕСИА', 'бесплатн', 'DNSSEC']),
    ('reg.ru 2FA', 'https://help.reg.ru/support/lichnyy-kabinet/bezopasnost-akkaunta/dvukhfaktornaya-avtorizatsiya', ['приложени', 'SMS', 'Telegram', 'ключ']),
    ('reg.ru автопродление', 'https://help.reg.ru/support/domains/prodleniye-domena/avtoprodleniye-domena', ['автопродлен', 'спис', 'баланс']),
    ('reg.ru запрет операций', 'https://help.reg.ru/support/domains/upravleniye-domenom/zapret-operatsiy-s-domenom', ['запрет', 'перенос', 'передач']),
    ('nic.ru защита от перехвата', 'https://www.nic.ru/help/protecting-a-domain-name-from-interception_13585.html', ['lock', 'transfer', 'two-factor', 'registrar']),
    ('nic.ru 2FA операций', 'https://www.nic.ru/help/two-factor-authentication-of-domain-operations_13109.html', ['DNSSEC', 'registrar', 'transfer', 'app', 'SMS']),
    ('cctld.ru главная', 'https://cctld.ru/', ['Госуслуг', 'ЕСИА', 'идентификац']),
    ('cctld.ru новости', 'https://cctld.ru/media/news/', ['Госуслуг', 'ЕСИА', 'идентификац', 'верификац']),
]
for name, url, words in pages:
    code, body = fetch(url)
    if code is None:
        p(name, 'НЕ ОТКРЫЛОСЬ', body[:150])
        continue
    t = text(body)
    p(name, 'код', code, 'длина', len(t))
    for s in snippets(t, words):
        p('   …', s)
    # ссылки на новости про Госуслуги/ЕСИА
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{0,200}(?:Госуслуг|ЕСИА|идентификац|верификац)[^<]{0,200})</a>', body, re.I):
        p('   ссылка:', m.group(1), '|', re.sub(r'\s+', ' ', html.unescape(m.group(2)))[:200])

# ── 3. Товарные знаки JARVIS ──
p('=== ЗНАКИ')
for name, url in [
    ('onlinepatent', 'https://onlinepatent.ru/trademarks/?q=jarvis'),
    ('tmsearch', 'https://tmsearch.ru/search?q=jarvis'),
    ('wipo branddb api', 'https://branddb.wipo.int/branddb/api/search?q=brandName:jarvis%20AND%20designation:RU'),
    ('fips', 'https://fips.ru/registers-web/action?acName=clickRegister&regName=RUTM'),
]:
    code, body = fetch(url)
    if code is None:
        p(name, 'НЕ ОТКРЫЛОСЬ', body[:150])
        continue
    t = text(body)
    p(name, 'код', code, 'длина', len(t))
    for s in snippets(t, ['JARVIS', 'ДЖАРВИС', 'Marvel'], width=300, limit=8):
        p('   …', s)
p('=== ГОТОВО')
