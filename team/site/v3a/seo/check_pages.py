# -*- coding: utf-8 -*-
"""Проверка рабочих страниц сайта v3a перед открытием для поиска (список 13.11, п. 8). Без сети, только чтение.

Что проверяет на каждой публикуемой странице (без proto/, preview/, concepts/, daily/, seo/, index-old.html и
коротких переадресаций): <title> и meta description есть и не повторяются на других страницах; ровно один <h1> в
разметке. Страницы-шаблоны, где h1 рисует скрипт (профили, клубы по ?id=), перечислены в JS_H1 — у них h1 проверяется
в браузере (Playwright), здесь только title/description. Страницы клубов по понятным адресам (/khl/ska/) — копии
шаблона клуба (метка JV_TEAM_ID), у них так же.
Запуск: python3 team/site/v3a/seo/check_pages.py   (код выхода 1, если есть ошибки)
"""
import collections
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'proto', 'preview', 'concepts', 'daily', 'seo', 'search', 'live', 'brand'}
SKIP_FILES = {'index-old.html', 'offline.html', '404.html'}
# h1 ставит скрипт после загрузки данных (проверено в браузере 13.11: ровно один h1)
JS_H1 = {'hockey/player.html', 'football/player.html', 'team/index.html', 'football/team.html', 'hockey/league.html',
         'football/league.html', 'football/ucl.html', 'hockey/compare.html', 'football/compare.html', 'me/index.html',
         'hockey/players.html', 'hockey/players_khl.html', 'football/players.html', 'football/photo-credits.html'}


def pages():
    for d, ds, fs in os.walk(ROOT):
        rel_d = os.path.relpath(d, ROOT)
        top = rel_d.split(os.sep)[0]
        if top in SKIP_DIRS or '/assets/' in '/' + rel_d.replace(os.sep, '/') + '/':
            ds[:] = []
            continue
        for f in fs:
            if f.endswith('.html') and f not in SKIP_FILES:
                yield os.path.normpath(os.path.join(rel_d, f)).replace(os.sep, '/')


def main():
    titles, descs = collections.defaultdict(list), collections.defaultdict(list)
    errs, n = [], 0
    for rel in sorted(pages()):
        src = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if 'http-equiv="refresh"' in src:
            continue  # переадресация (папки лиг, /search/, /live/)
        n += 1
        t = re.search(r'<title>(.*?)</title>', src, re.S)
        d = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', src)
        if not t or not t.group(1).strip():
            errs.append('нет title: ' + rel)
        else:
            titles[html.unescape(t.group(1).strip())].append(rel)
        if not d or not d.group(1).strip():
            errs.append('нет description: ' + rel)
        else:
            descs[html.unescape(d.group(1).strip())].append(rel)
        body = re.sub(r'<script\b.*?</script>', '', src, flags=re.S)
        h1 = len(re.findall(r'<h1[\s>]', body))
        js_h1 = rel in JS_H1 or 'JV_TEAM_ID' in src   # страницы клубов /khl/ska/ — копии шаблона клуба
        if not js_h1 and h1 != 1:
            errs.append('h1: %d на %s' % (h1, rel))
    for kind, m in (('title', titles), ('description', descs)):
        for v, rels in m.items():
            if len(rels) > 1:
                errs.append('одинаковый %s у %d страниц: %s … «%s»' % (kind, len(rels), ', '.join(rels[:3]), v[:70]))
    print('страниц проверено: %d, ошибок: %d' % (n, len(errs)))
    for e in errs:
        print(' -', e)
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
