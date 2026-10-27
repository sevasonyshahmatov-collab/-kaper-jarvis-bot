# -*- coding: utf-8 -*-
"""Карусель «Аналитическая таблица» 1080×1350, версия после разбора impeccable (владелец 27.10): первый слайд — факт
про статистику, на каждом слайде строка вывода и номер, крупнее текст, понятные ярлыки, золото — главный цвет,
красный/зелёный — только «зашёл / не зашёл», без эмодзи, свечение заголовка — только на первом слайде.
Слайды 2–7 — из sheet_stories_html.py (данные те же); здесь — обложка, обёртка и стиль.

    python team/pins/carousel_table.py <куда>   → <куда>/car_N.html (снимок — shot_car.js)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet_stories_html as M  # noqa: E402

N = 7
TAGS = {'лист «прогнозы»': 'шансы на матч', 'лист «Что заходит»': 'статистика команд', 'прогнозы канала': 'наши прогнозы',
        'прогнозы одного дня': 'один день — три прогноза', 'лист «Модель vs рынок»': 'таблица против линии', 'доступ': 'доступ'}
TAKE = {2: 'Модель дала Авангарду 87 % — прогноз зашёл',
        3: 'Юта и Колорадо: тотал больше 4,5 во всех матчах сезона',
        4: '6 из 8 зашли: исходы, форы и тоталы',
        5: 'Три из трёх за один день',
        6: 'Таблица осторожнее рынка во всех 4 матчах',
        7: ''}

CSS = """
body{height:1350px}
.brand{top:40px!important}
h1{filter:drop-shadow(0 5px 0 rgba(120,70,0,.5))!important}
.sub{font-size:34px!important}
.cap{font-size:36px!important;color:#e6e2f2!important}
.hd{font-size:26px!important;color:#c9c5d8!important}
.tag{font-size:28px!important}
.blue{background:linear-gradient(90deg,#8a879c,#d8d5e6)!important;box-shadow:none!important}
.lgt{font:600 22px Osw;letter-spacing:1px;margin-left:12px;color:#9d98b3;vertical-align:middle}
.take{margin:0 0 22px;padding:22px 30px;border-radius:24px;font:600 40px/1.15 Osw;color:#fff;
 background:linear-gradient(90deg,rgba(255,201,40,.22),rgba(255,201,40,.04));border-left:8px solid #ffc928}
.cnt{position:absolute;top:36px;right:44px;font:700 28px Osw;letter-spacing:2px;color:#ffc928}
.cnt span{color:#77738a}
"""


def gold(v):
    """Ячейка: чем чаще заходит, тем насыщеннее золото; цифра всегда читается."""
    a = 0.12 + 0.88 * v / 100
    ink = '#1a1206' if v >= 55 else '#fff'
    return ('background:rgba(255,190,30,%.2f);color:%s;box-shadow:0 0 %dpx rgba(255,190,30,%.2f);text-shadow:none' %
            (a, ink, int(24 * v / 100), 0.5 * v / 100))


def lg(t):
    return '<span class="lgt">%s</span>' % ('НХЛ' if t not in M.SLUG else 'КХЛ')


M.heat = gold
M.lg_tag = lg
_page = M.page
CUR = [1]


def page(tag, title, sub, body, cap='', *a, **k):
    i = CUR[0]
    t = TAKE.get(i)
    if t:
        body = body.replace('<div class="card"', '<div class="take">%s</div><div class="card"' % t, 1)
    h = _page(TAGS.get(tag, tag), title, sub, body, '')   # вывод — строкой над карточкой, подпись снизу не нужна
    extra = '.row{padding:6px 20px!important;gap:4px!important;margin:6px 0!important;max-height:none!important;flex:0 0 auto!important}.bar{height:18px!important}.row .emb{width:46px!important;height:46px!important}.row .name{font-size:32px!important}.card{justify-content:flex-start!important}' if i == 6 else ''
    h = h.replace('</style>', CSS + extra + '</style>', 1).replace('<div class="wrap">',
                                                            '<div class="wrap"><div class="cnt">%d<span> / %d</span></div>' % (i, N), 1)
    h = h.replace('height:1920px', 'height:1350px').replace('top:230px', 'top:92px').replace('top:210px', 'top:80px')
    return h.replace('h1{font:400 92px', 'h1{font:400 76px')


M.page = page

ICON = {  # простые значки в фирменном золоте вместо эмодзи
    'chart': '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />',
    'team': '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/>',
    'list': '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'}


def ico(k):
    return ('<svg width="54" height="54" viewBox="0 0 24 24" fill="none" stroke="#ffc928" stroke-width="2.2" stroke-linecap="round">'
            '%s</svg>') % ICON[k]


def cover():
    stats = [('54', 'команды КХЛ и НХЛ'), ('6', 'показателей у каждой'), ('159', 'прогнозов на этих данных')]
    chips = ''.join('<div style="flex:1;padding:26px 10px;border-radius:24px;background:#22203a;border:1px solid rgba(255,201,40,.35);'
                    'text-align:center"><div style="font:400 72px/1 Dela;color:#ffc928">%s</div>'
                    '<div style="font:500 28px/1.2 Onest;color:#e0dcf0;margin-top:10px">%s</div></div>' % s for s in stats)
    inside = [('list', 'Прогнозы на каждый матч'), ('team', 'Что заходит у каждой команды'),
              ('target', 'Шансы модели против линии'), ('chart', 'Счёт и итог после игры')]
    rows = ''.join('<div style="display:flex;align-items:center;gap:22px;padding:14px 0;font:600 40px Osw;color:#fff">%s%s</div>' % (
        ico(k), t) for k, t in inside)
    body = ('<div class="card" style="padding:36px 40px"><div style="display:flex;gap:18px">%s</div>'
            '<div style="font:600 28px Onest;color:#9d98b3;letter-spacing:3px;margin:34px 0 6px">ВНУТРИ ТАБЛИЦЫ</div>%s</div>') % (chips, rows)
    h = page('аналитическая таблица JARVIS', 'СТАТИСТИКА,<br>НА КОТОРОЙ СТОИТ<br>КАЖДЫЙ ПРОГНОЗ', 'КХЛ и НХЛ · обновляется каждый день', body)
    return h.replace('drop-shadow(0 5px 0 rgba(120,70,0,.5))!important', 'drop-shadow(0 6px 0 rgba(120,70,0,.55)) '
                     'drop-shadow(0 0 22px rgba(255,190,40,.3))!important').replace('h1{font:400 76px', 'h1{font:400 64px')


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    M.TILT[0] = 'none'
    M.FOOT[0] = ''
    for i, fn in enumerate([cover, M.s2, M.s3, M.s4, M.s5, M.s6, M.s7], 1):
        CUR[0] = i
        open(os.path.join(out, 'car_%d.html' % i), 'w', encoding='utf-8').write(fn())
