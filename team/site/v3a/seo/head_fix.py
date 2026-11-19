# -*- coding: utf-8 -*-
"""Заголовок <head> всех страниц сайта v3a (владелец 17.11: «Ночная арена» — основная тема, новая иконка).
Запускается в ежедневной сборке после seo (daily/run.py, шаг head) — так и заново собранные страницы матчей и клубов
получают то же самое. Для каждой страницы сайта (где подключён assets/nav.js):
  1) сразу после <meta charset> — короткий скрипт темы: «Ночная арена» по умолчанию (?bg=0 — прежняя), без мигания;
  2) <meta name="theme-color"> — цвет новой темы;
  3) ссылки на иконки (favicon.svg, favicon-32.png, apple-touch-icon.png) — с версией ?v=3: браузеры и sw.js держат
     картинки по адресу, без версии осталась бы старая иконка.
  4) <meta http-equiv="Content-Security-Policy"> — базовая защита (аудит 19.11): запрет плагинов (object-src),
     подмены <base> чужим адресом (base-uri) и отправки форм на чужие сайты (form-action). Скрипты и картинки не ограничивает —
     ничего на страницах не ломает.
Повторный запуск ничего не меняет. Папки proto/ и данных не трогает."""
import os, re, sys

V3A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNIP = ('<script>/*тема: «Ночная арена» по умолчанию; ?bg=0 — старая*/(function(){var d=document.documentElement;try{'
        'var q=new URLSearchParams(location.search).get("bg");if(q!==null)sessionStorage.setItem("jv-bg",/^[abcn]$/.test(q)?q:"0");'
        'var b=sessionStorage.getItem("jv-bg");if(b===null)b="n";if(b&&b!=="0")d.dataset.bg=b}catch(e){d.dataset.bg="n"}})()</script>')
CSP = ('<meta http-equiv="Content-Security-Policy" content="object-src \'none\'; base-uri \'self\'; form-action \'self\'">')
THEME = '#060b1a'
ICON_VER = '3'
SKIP = ('proto', 'data', '.git', 'node_modules')
CHARSET = re.compile(r'<meta charset[^>]*>', re.I)
TCOLOR = re.compile(r'<meta name="theme-color" content="#[0-9a-fA-F]{3,8}">')
ICON = re.compile(r'(href="(?:\.\./)*(?:favicon\.svg|favicon-32\.png|apple-touch-icon\.png))(\?v=\d+)?"')


def fix(s):
    if 'assets/nav.js' not in s:
        return s
    if 'jv-bg' not in s:
        m = CHARSET.search(s)
        if m:
            s = s[:m.end()] + SNIP + s[m.end():]
    if 'Content-Security-Policy' not in s:
        m = CHARSET.search(s)
        if m:
            s = s[:m.end()] + CSP + s[m.end():]
    s = TCOLOR.sub('<meta name="theme-color" content="%s">' % THEME, s)
    s = ICON.sub(lambda m: '%s?v=%s"' % (m.group(1), ICON_VER), s)
    return s


def main():
    n = 0
    for root, dirs, files in os.walk(V3A):
        rel = os.path.relpath(root, V3A).split(os.sep)
        if rel[0] in SKIP or any(p in ('data',) for p in rel):
            dirs[:] = []
            continue
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(root, f)
            try:
                s = open(p, encoding='utf-8').read()
            except Exception:  # noqa: BLE001
                continue
            t = fix(s)
            if t != s:
                open(p, 'w', encoding='utf-8').write(t)
                n += 1
    print('head_fix: обновлено страниц', n)
    return n


if __name__ == '__main__':
    main()
    sys.exit(0)
