# -*- coding: utf-8 -*-
"""Раздел «Игроки» футбола по лигам (13.11): data/players.js (~2 МБ) страница грузила целиком даже ради одной лиги.
Пишет data/plg/meta.js (сезон, лиги, клубы — window.JV_PLAYERS_META) и data/plg/<лига>.js (игроки лиги; для «Лиги чемпионов» /
«Лиги Европы» — все, кто сыграл в турнире, поле cu). Страница football/players.html грузит meta.js и только нужную лигу,
«Все лиги» — все файлы. Сам data/players.js остаётся: его читают сборщики (split.py, фото) и photo-credits.html.
Вызывается из players_build.py; отдельно (без сети): python team/site/v3a/football/players_split.py"""
import json, os

H = os.path.dirname(os.path.abspath(__file__))


def jd(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def write_parts(data):
    d = os.path.join(H, 'data', 'plg')
    os.makedirs(d, exist_ok=True)
    P = data['players']
    lgs = [k for k in data['leagues'] if any(p['lg'] == k or k in (p.get('cu') or []) for p in P)]
    meta = {k: data[k] for k in ('built', 'season', 'leagues', 'teams', 'lu')}
    meta['lgs'] = lgs
    parts = {k: [p for p in P if p['lg'] == k or k in (p.get('cu') or [])] for k in lgs}
    # «Все лиги» = игроки по своей лиге (p.lg) без повторов: у турниров (ЛЧ, ЛЕ) в файле есть и игроки других лиг,
    # поэтому для «всех» у них отдельный файл <турнир>-own.js только с клубами, чья лига — сам турнир
    own, extra = [], {}
    for k in lgs:
        mine = [p for p in P if p['lg'] == k]
        if not mine:
            continue
        if len(mine) == len(parts[k]):
            own.append(k)
        else:
            own.append(k + '-own')
            extra[k + '-own'] = mine
    meta['own'] = own
    keep = {'meta.js'} | {k + '.js' for k in list(lgs) + list(extra)}
    for fn in os.listdir(d):
        if fn.endswith('.js') and fn not in keep:
            os.remove(os.path.join(d, fn))

    def put(fn, s):
        fp = os.path.join(d, fn)
        if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != s:
            open(fp, 'w', encoding='utf-8').write(s)

    put('meta.js', 'window.JV_PLAYERS_META=%s;\n' % jd(meta))
    for k, part in list(parts.items()) + list(extra.items()):
        put(k + '.js', '(window.JV_PLG=window.JV_PLG||{})[%s]=%s;\n' % (jd(k), jd(part)))
    return lgs


if __name__ == '__main__':
    src = open(os.path.join(H, 'data', 'players.js'), encoding='utf-8').read().strip()
    data = json.loads(src[src.index('=') + 1:].rstrip(';'))
    print('PLG', write_parts(data))
