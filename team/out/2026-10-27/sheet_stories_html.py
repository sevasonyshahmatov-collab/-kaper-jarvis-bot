# -*- coding: utf-8 -*-
"""Хайлайт «Таблица», объёмный стиль (владелец 27.10: «плоско, скучно»): вёрстка HTML/CSS — свечение, стекло, тени,
наклон «3D», снимок браузером (Playwright). Данные — выгрузка листов таблицы 27.10 (team/out/2026-10-27/sheet_dump.py).

    python team/pins/sheet_stories_html.py <куда>
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONTS, EMB = os.path.join(ROOT, 'render', 'fonts'), os.path.join(ROOT, 'render', 'emblems')
SLUG = {'Металлург': 'metallurg', 'Локомотив': 'lokomotiv', 'Амур': 'amur', 'Нефтехимик': 'neftekhimik',
        'Северсталь': 'severstal', 'Барыс': 'barys', 'Динамо Москва': 'dinamo_msk', 'Лада': 'lada', 'Адмирал': 'admiral',
        'Салават Юлаев': 'salavat', 'Ак Барс': 'akbars', 'СКА': 'ska', 'ЦСКА': 'cska', 'Автомобилист': 'avtomobilist',
        'Трактор': 'traktor', 'Сибирь': 'sibir', 'Авангард': 'avangard', 'Шанхайские Драконы': 'shanghai', 'Сочи': 'sochi',
        'Динамо Минск': 'dinamo_minsk', 'Торпедо': 'torpedo'}
COL = {'Металлург': '#ee760c', 'Локомотив': '#d21e28', 'Амур': '#f0781e', 'Нефтехимик': '#285aa0', 'Северсталь': '#f0be00',
       'Барыс': '#28aabe', 'Динамо Москва': '#1e5ad2', 'Лада': '#2864aa', 'Шанхайские Драконы': '#f06414',
       'Динамо Минск': '#46aae6', 'Салават Юлаев': '#289650', 'Локомотив2': '#d21e28'}


def emb(t, size=72):
    return '<img class="emb" style="width:%dpx;height:%dpx" src="file://%s/%s.png">' % (size, size, EMB, SLUG[t])


CSS = """
@font-face{font-family:Dela;src:url(file://%(f)s/DelaGothicOne-Regular.ttf)}
@font-face{font-family:Onest;src:url(file://%(f)s/Onest[wght].ttf);font-weight:100 900}
@font-face{font-family:Osw;src:url(file://%(f)s/Oswald[wght].ttf);font-weight:200 700}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;font-family:Onest;color:#f4f2f7;
 background:radial-gradient(900px 700px at 85%% 8%%,rgba(255,196,40,.28),transparent 60%%),
 radial-gradient(900px 800px at 0%% 62%%,rgba(60,110,255,.30),transparent 60%%),
 radial-gradient(700px 600px at 100%% 100%%,rgba(255,120,30,.20),transparent 60%%),
 linear-gradient(160deg,#0d0b16 0%%,#121027 50%%,#07060c 100%%);position:relative}
body:before{content:"";position:absolute;inset:0;opacity:.35;mix-blend-mode:overlay;
 background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/></filter><rect width='100%%' height='100%%' filter='url(%%23n)'/></svg>")}
body:after{content:"";position:absolute;inset:0;background:
 repeating-linear-gradient(0deg,rgba(255,255,255,.025) 0 1px,transparent 1px 72px),
 repeating-linear-gradient(90deg,rgba(255,255,255,.025) 0 1px,transparent 1px 72px);
 -webkit-mask:linear-gradient(180deg,transparent,#000 30%%,#000 60%%,transparent);pointer-events:none}
.wrap{position:absolute;inset:0;z-index:2}
.brand{position:absolute;top:150px;width:100%%;text-align:center;font:600 26px Osw;letter-spacing:6px;color:#cfcbe0}
.brand b{color:#ffc928}
.tag{display:inline-block;margin:0 auto;padding:10px 26px;border-radius:40px;font:600 24px Onest;color:#ffe08a;
 background:linear-gradient(90deg,rgba(255,201,40,.18),rgba(255,201,40,.05));border:1px solid rgba(255,201,40,.45);
 box-shadow:0 0 30px rgba(255,201,40,.25)}
.t{position:absolute;top:230px;width:100%%;text-align:center}
h1{font:400 92px/1 Dela;letter-spacing:-1px;margin-top:26px;
 background:linear-gradient(180deg,#fff 0%%,#ffe7a0 55%%,#ffb81c 100%%);-webkit-background-clip:text;color:transparent;
 filter:drop-shadow(0 6px 0 rgba(120,70,0,.55)) drop-shadow(0 0 40px rgba(255,190,40,.45))}
.sub{margin-top:18px;font:500 30px Onest;color:#bdb8cf}
.stage{position:absolute;left:50px;right:50px;top:575px;perspective:1600px}
.card{border-radius:36px;padding:34px;transform:rotateX(9deg) rotateY(-7deg) rotateZ(1deg);transform-origin:50%% 0;
 background:linear-gradient(145deg,rgba(255,255,255,.13),rgba(255,255,255,.03));
 border:1.5px solid rgba(255,255,255,.18);backdrop-filter:blur(18px);
 box-shadow:0 60px 120px rgba(0,0,0,.65),0 0 0 1px rgba(0,0,0,.3) inset,0 1px 0 rgba(255,255,255,.35) inset,
 -30px 30px 90px rgba(60,110,255,.25),30px -20px 90px rgba(255,190,40,.18)}
.row{display:flex;align-items:center;gap:20px;height:88px;padding:0 22px;margin:8px 0;border-radius:22px;
 background:linear-gradient(90deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.07)}
.emb{object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,.6))}
.name{font:600 34px Osw;flex:1;white-space:nowrap;overflow:hidden}
.cell{width:118px;height:66px;border-radius:16px;display:flex;align-items:center;justify-content:center;
 font:700 34px Osw;text-shadow:0 2px 4px rgba(0,0,0,.4);box-shadow:0 8px 18px rgba(0,0,0,.35),0 1px 0 rgba(255,255,255,.35) inset}
.hd{display:flex;gap:20px;padding:0 22px;font:600 22px Onest;color:#9d98b3;letter-spacing:1px}
.ok,.no{width:96px;height:58px;border-radius:30px;display:flex;align-items:center;justify-content:center;font:700 26px Osw}
.ok{background:linear-gradient(180deg,#3ee08a,#13a35a);box-shadow:0 0 26px rgba(62,224,138,.55)}
.no{background:linear-gradient(180deg,#ff6b6b,#c62f3c);box-shadow:0 0 26px rgba(255,90,90,.45)}
.big{font:400 40px Dela;color:#fff}
.cap{position:absolute;top:1470px;width:100%%;text-align:center;font:500 32px/1.35 Onest;color:#d8d4e6;padding:0 90px}
.link{position:absolute;left:110px;right:110px;top:1660px;height:130px;border-radius:30px;border:3px dashed rgba(255,201,40,.8);
 display:flex;align-items:center;justify-content:center;font:600 34px Onest;color:#a9a4bb;background:rgba(255,201,40,.04)}
.lbl{position:absolute;top:1570px;width:100%%;text-align:center;font:700 34px Osw;letter-spacing:4px}
.bar{height:30px;border-radius:15px;background:rgba(255,255,255,.08);overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,.4) inset}
.bar i{display:block;height:100%%;border-radius:15px}
.gold{background:linear-gradient(90deg,#ffb81c,#ffe27a);box-shadow:0 0 24px rgba(255,201,40,.7)}
.blue{background:linear-gradient(90deg,#3a6dff,#8fb2ff);box-shadow:0 0 24px rgba(80,130,255,.7)}
""" % {'f': FONTS}


def page(tag, title, sub, body, cap='', lbl='как получить доступ', url='t.me/jarvibet'):
    return ('<html><head><meta charset="utf-8"><style>%s</style></head><body><div class="wrap">'
            '<div class="brand">JARVIS &nbsp;|&nbsp; <b>КХЛ · НХЛ</b></div>'
            '<div class="t"><span class="tag">%s</span><h1>%s</h1><div class="sub">%s</div></div>'
            '<div class="stage">%s</div><div class="cap">%s</div>'
            '<div class="lbl">%s</div><div class="link">%s</div></div></body></html>') % (
        CSS, tag, title, sub, body, cap, lbl.upper(), url)


def heat(v):
    t = v / 100
    a, b = (214, 58, 70), (40, 190, 110)
    c1 = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    c2 = tuple(min(255, x + 45) for x in c1)
    return 'background:linear-gradient(180deg,rgb%s,rgb%s)' % (c2, c1)


def s1():
    tiles = [('📊', 'Прогнозы', 'все матчи дня'), ('🔥', 'Что заходит', 'по каждой команде'),
             ('⚖️', 'Модель vs рынок', 'чья логика точнее'), ('🎟️', 'Купон дня', 'самые уверенные'),
             ('🎯', 'Точность', 'как часто угадывает'), ('🏒', 'Карточка команды', 'всё о клубе'),
             ('📈', 'Статистика', 'броски, большинство'), ('🎥', 'Эксперты', 'разборы с видео')]
    b = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:22px">' + ''.join(
        '<div class="row" style="height:150px;flex-direction:column;align-items:flex-start;justify-content:center;gap:6px">'
        '<div style="font:600 34px Osw"><span style="font-size:36px">%s</span>&nbsp; %s</div>'
        '<div style="font:500 24px Onest;color:#a9a4bb">%s</div></div>' % t for t in tiles) + '</div>'
    return page('24 листа · КХЛ и НХЛ', 'ТАБЛИЦА<br>JARVIS', 'вся аналитика в одном месте',
                '<div class="card">%s</div>' % b, 'листай вправо →').replace('top:230px', 'top:210px') \
        .replace('<div class="stage">', '<div class="stage" style="top:640px">').replace('92px/1 Dela', '120px/1 Dela')


def s2():
    rows = [('Победитель матча', 84, 77, 140), ('Исход осн. времени', 66, 62, 140), ('Фаворит проиграл — угадали', 13, 6, 19)]
    b = ''
    for lbl, a, k, n in rows:
        b += '<div style="margin:18px 0 34px"><div style="font:600 34px Osw;margin-bottom:16px">%s</div>' % lbl.upper()
        for v, cl, who in ((a, 'gold', 'таблица'), (k, 'blue', 'букмекер')):
            b += ('<div style="display:flex;align-items:center;gap:18px;margin:12px 0"><div style="width:150px;font:500 26px Onest;'
                  'color:#a9a4bb">%s</div><div class="bar" style="flex:1"><i class="%s" style="width:%d%%"></i></div>'
                  '<div style="width:170px;text-align:right;font:700 38px Osw">%d<span style="font-size:24px;color:#8d88a3">'
                  ' / %d</span></div></div>') % (who, cl, 100 * v // n, v, n)
        b += '</div>'
    return page('лист «Модель vs рынок»', 'МОДЕЛЬ<br>ПРОТИВ РЫНКА', 'КХЛ · 140 матчей сезона', '<div class="card">%s</div>' % b,
                'Расчёт таблицы против линии букмекера, по каждому матчу.')


def s3():
    data = [('Металлург', 60, 85, 90, 55), ('Локомотив', 63, 74, 84, 42), ('Амур', 56, 61, 72, 22),
            ('Нефтехимик', 53, 68, 84, 58), ('Северсталь', 50, 65, 75, 55), ('Барыс', 42, 58, 63, 84),
            ('Динамо Москва', 9, 50, 73, 45), ('Лада', 11, 37, 58, 58)]
    b = ('<div class="hd"><div style="width:72px"></div><div style="flex:1"></div>' + ''.join(
        '<div style="width:118px;text-align:center">%s</div>' % c for c in ('ПОБЕДА', 'НЕ ПРОИГР.', 'Ф +1,5', 'ТБ 4,5')) + '</div>')
    for r in data:
        b += '<div class="row">%s<div class="name">%s</div>%s</div>' % (
            emb(r[0], 66), r[0], ''.join('<div class="cell" style="%s">%d%%</div>' % (heat(v), v) for v in r[1:]))
    return page('лист «Что заходит»', 'ЧТО ЗАХОДИТ<br>У КОМАНД', 'КХЛ · доля матчей сезона',
                '<div class="card" style="padding:26px 22px">%s</div>' % b,
                'Что чаще всего заходит у каждой команды.')


def s4():
    rows = [('Амур', 'Адмирал', 'Амур', 62, '3:0', 1), ('Лада', 'Сочи', 'Лада', 51, '3:4', 0),
            ('Салават Юлаев', 'Ак Барс', 'Салават', 55, '1:2', 0), ('Локомотив', 'Северсталь', 'Локомотив', 63, '1:0', 1),
            ('СКА', 'ЦСКА', 'ЦСКА', 62, '1:3', 1), ('Автомобилист', 'Барыс', 'Автомобилист', 58, '4:1', 1),
            ('Трактор', 'Сибирь', 'Трактор', 63, '2:1', 1), ('Динамо Москва', 'Авангард', 'Авангард', 57, '2:3', 1)]
    b = ''
    for h, a, pk, p, sc, ok in rows:
        b += ('<div class="row">%s%s<div class="name" style="font-size:32px">%s <span style="color:#ffc928">%d%%</span></div>'
              '<div class="big" style="width:120px;text-align:right">%s</div><div class="%s">%s</div></div>') % (
            emb(h, 60), emb(a, 60), pk, p, sc, 'ok' if ok else 'no', 'ДА' if ok else 'НЕТ')
    return page('лист «Прогнозы — кратко»', 'ВСЕ<br>ПРОГНОЗЫ', 'КХЛ · 25–26 октября',
                '<div class="card" style="padding:24px">%s</div>' % b, 'После игры — счёт и зашёл ли. Ничего не удаляется.')


def s5():
    rows = [('Шанхайские Драконы', 'Сочи', 77.1), ('Металлург', 'Авангард', 75.6), ('Динамо Минск', 'Лада', 72.1)]
    b = ''
    for pk, op, p in rows:
        b += ('<div class="row" style="height:150px;background:linear-gradient(90deg,%s55,rgba(255,255,255,.03) 60%%)">%s'
              '<div style="flex:1"><div style="font:500 24px Onest;color:#bdb8cf">против: %s</div>'
              '<div style="font:600 36px Osw">%s</div></div><div class="big" style="color:#ffd24a">%s</div>'
              '<div class="ok" style="width:66px">✓</div></div>') % (COL[pk], emb(pk, 100), op, pk, ('%.1f%%' % p).replace('.', ','))
    b += ('<div style="margin-top:26px;padding:30px;border-radius:26px;display:flex;justify-content:space-between;align-items:center;'
          'background:linear-gradient(90deg,rgba(62,224,138,.25),rgba(62,224,138,.05));border:2px solid rgba(62,224,138,.6);'
          'box-shadow:0 0 40px rgba(62,224,138,.3)"><div style="font:600 34px Osw">КУПОН ИЗ 3 · ШАНС 42%</div>'
          '<div class="big" style="color:#5ff0a0">ЗАШЁЛ</div></div>')
    return page('лист «Купон дня»', 'КУПОН ДНЯ', 'самые уверенные прогнозы · 28.09', '<div class="card">%s</div>' % b,
                'Таблица сама собирает купон из самых уверенных исходов.')


def s6():
    rows = [('Салават Юлаев', 'Сочи', 73, 75), ('Лада', 'Адмирал', 40, 44), ('Нефтехимик', 'Металлург', 35, 36), ('СКА', 'Торпедо', 40, 54)]
    b = ''
    for h, a, t, k in rows:
        b += ('<div class="row" style="height:auto;padding:16px 22px;flex-direction:column;align-items:stretch;gap:8px">'
              '<div style="display:flex;align-items:center;gap:14px">%s%s<div class="name">%s — %s</div></div>') % (emb(h, 56), emb(a, 56), h, a)
        for v, cl in ((t, 'gold'), (k, 'blue')):
            b += ('<div style="display:flex;align-items:center;gap:16px"><div class="bar" style="flex:1;height:22px">'
                  '<i class="%s" style="width:%d%%"></i></div><div style="width:90px;text-align:right;font:700 32px Osw">%d%%</div></div>') % (cl, v, v)
        b += '</div>'
    b += ('<div style="display:flex;justify-content:center;gap:50px;margin-top:18px;font:600 26px Onest">'
          '<span><i class="gold" style="display:inline-block;width:28px;height:14px;border-radius:7px"></i> таблица</span>'
          '<span><i class="blue" style="display:inline-block;width:28px;height:14px;border-radius:7px"></i> букмекер</span></div>')
    return page('лист «Модель vs рынок»', 'ТАБЛИЦА<br>И БУКМЕКЕР', 'шанс победы хозяев · 27 октября',
                '<div class="card" style="padding:24px">%s</div>' % b, '')


if __name__ == '__main__':
    from playwright.sync_api import sync_playwright
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1080, 'height': 1920})
        for i, fn in enumerate([s1, s2, s3, s4, s5, s6]):
            h = os.path.join(out, 'table_%d.html' % (i + 1))
            open(h, 'w', encoding='utf-8').write(fn())
            pg.goto('file://' + h)
            pg.wait_for_timeout(400)
            f = os.path.join(out, 'table_%d.jpg' % (i + 1))
            pg.screenshot(path=f, type='jpeg', quality=93)
            print('STORY', f, flush=True)
        br.close()
