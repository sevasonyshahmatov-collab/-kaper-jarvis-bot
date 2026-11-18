# -*- coding: utf-8 -*-
"""Оси навыков игроков НХЛ по рейтингам игры EA SPORTS NHL (владелец 18.11: «возьми данные по аналогии с игрой НХЛ —
там хорошо статистика расписана»).

Страница рейтингов www.ea.com/games/nhl/ratings отдаёт 300 лучших игроков (6 страниц по 50) с атрибутами игры.
Скрипт сводит атрибуты к нашим пяти осям (среднее нескольких атрибутов) и сохраняет только эти пять чисел на игрока
в hockey/data/nhl_ea.json — сами атрибуты игры не храним и не показываем. Как числа осей переводятся в оценку на сайте
(шкала, «99 — один на ось»), — в daily/split.py, skills().

Запуск: python3 team/site/v3a/hockey/ea_axes.py            — скачать и сохранить
        python3 team/site/v3a/hockey/ea_axes.py --dir D    — взять уже скачанные страницы D/p1.html … p6.html
"""
import json, os, re, sys, time, unicodedata, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data', 'nhl_ea.json')
URL = 'https://www.ea.com/games/nhl/ratings?page=%d'
# ось -> атрибуты игры (катание — скорость и ускорение важнее манёвренности)
AX = {'Катание': {'speed': 2, 'acceleration': 2, 'agility': 1},
      'Бросок': {'wristshotAccuracy': 1, 'wristshotPower': 1, 'slapshotAccuracy': 1, 'slapshotPower': 1},
      'Руки': {'deking': 1, 'puckControl': 1, 'handeye': 1},
      'Интеллект': {'offensiveAwareness': 1, 'passing': 1},
      'Оборона': {'defensiveAwareness': 2, 'stickChecking': 1, 'shotBlocking': 1}}


def nk(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', s)


def pages(src):
    for i in range(1, 7):
        if src:
            s = open(os.path.join(src, 'p%d.html' % i), encoding='utf-8').read()
        else:
            req = urllib.request.Request(URL % i, headers={'User-Agent': 'Mozilla/5.0'})
            s = urllib.request.urlopen(req, timeout=40).read().decode('utf-8')
            time.sleep(1)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
        items = json.loads(m.group(1))['props']['pageProps']['ratingDetails']['items']
        if not items:
            break
        yield from items


def main():
    src = sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else None
    P = json.load(open(os.path.join(HERE, 'data', 'nhl_players.json'), encoding='utf-8'))['players']
    by = {}
    for p in P:
        by.setdefault(nk(p.get('n') or ''), []).append(p)
    out, miss, game = {}, [], ''
    for x in pages(src):
        pos = (x.get('position') or {}).get('shortLabel')
        if pos == 'G':
            continue
        st = {k: (v or {}).get('value') or 0 for k, v in (x.get('stats') or {}).items()}
        cand = by.get(nk('%s %s' % (x.get('firstName', ''), x.get('lastName', ''))), [])
        if len(cand) > 1:                                    # тёзки (два Элиаса Петтерссона) — по амплуа
            d = pos in ('LD', 'RD')
            cand = [p for p in cand if (p.get('pos') == 'D') == d]
        if len(cand) != 1:
            miss.append('%s %s' % (x.get('firstName'), x.get('lastName')))
            continue
        ax = {}
        for name, ws in AX.items():
            vals = [(st.get(k) or 0, w) for k, w in ws.items() if st.get(k)]
            if vals:
                ax[name] = round(sum(v * w for v, w in vals) / sum(w for _, w in vals), 2)
        if len(ax) == len(AX):
            out[str(cand[0]['id'])] = ax
        game = game or (x.get('avatarUrl') or '')
    g = re.search(r'/(NHL\d+)/', game)
    json.dump({'src': 'EA SPORTS ' + (g.group(1) if g else 'NHL') + ' ratings', 'date': date.today().isoformat(),
               'p': out, 'miss': miss}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('nhl_ea: игроков', len(out), '; не найдены у нас:', len(miss), ', '.join(miss[:12]))


if __name__ == '__main__':
    main()
