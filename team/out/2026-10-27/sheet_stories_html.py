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
 background:radial-gradient(900px 700px at 85%% 8%%,rgba(255,196,40,.14),transparent 60%%),
 radial-gradient(900px 800px at 0%% 62%%,rgba(60,110,255,.18),transparent 60%%),
 radial-gradient(700px 600px at 100%% 100%%,rgba(255,120,30,.10),transparent 60%%),
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
 filter:drop-shadow(0 6px 0 rgba(120,70,0,.55)) drop-shadow(0 0 18px rgba(255,190,40,.22))}
.sub{margin-top:18px;font:500 30px Onest;color:#bdb8cf}
.stage{position:absolute;left:28px;right:28px;top:575px;perspective:1600px}
.card{border-radius:36px;padding:34px;transform:var(--tilt);transform-origin:50%% 0;
 background:linear-gradient(145deg,rgba(30,28,44,.92),rgba(16,15,26,.94));
 border:1.5px solid rgba(255,255,255,.18);backdrop-filter:blur(18px);
 box-shadow:0 60px 120px rgba(0,0,0,.65),0 0 0 1px rgba(0,0,0,.3) inset,0 1px 0 rgba(255,255,255,.35) inset,
 -30px 30px 90px rgba(60,110,255,.14),30px -20px 90px rgba(255,190,40,.08)}
.row{display:flex;align-items:center;gap:20px;height:88px;padding:0 22px;margin:8px 0;border-radius:22px;
 background:linear-gradient(90deg,#2a2840,#1e1c2e);border:1px solid rgba(255,255,255,.10)}
.emb{object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,.6))}
.name{font:600 36px Osw;color:#fff;text-shadow:0 2px 6px rgba(0,0,0,.8);flex:1;white-space:nowrap;overflow:hidden}
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
.big .name{font-size:42px}.big .cell{width:124px;height:76px;font-size:38px}.big .emb{transform:scale(1.2)}
.big .ok,.big .no{width:110px;height:64px;font-size:30px}.big .big{font-size:46px}
""" % {'f': FONTS}


TILT = ['rotateX(8deg) rotateY(-9deg)']
FOOT = ['']


def dots(i, n=7):
    d = ''.join('<i style="display:inline-block;width:%dpx;height:14px;border-radius:7px;margin:0 6px;background:%s"></i>' % (
        44 if k == i else 14, '#ffc928' if k == i else 'rgba(255,255,255,.25)') for k in range(n))
    return ('<div style="position:absolute;top:1640px;width:100%%;text-align:center">%s<div style="margin-top:28px;'
            'font:700 32px Osw;letter-spacing:5px;color:#ffc928">ЛИСТАЙ ДАЛЬШЕ →</div></div>') % d


def page(tag, title, sub, body, cap='', lbl='как получить доступ', url='t.me/jarvibet'):
    return ('<html><head><meta charset="utf-8"><style>%s</style></head><body><div class="wrap">'
            '<div class="brand">JARVIS &nbsp;|&nbsp; <b>КХЛ · НХЛ</b></div>'
            '<div class="t"><span class="tag">%s</span><h1>%s</h1><div class="sub">%s</div></div>'
            '<div class="stage" style="--tilt:%s">%s</div><div class="cap">%s</div>'
            '%s</div></body></html>') % (
        CSS, tag, title, sub, TILT[0], body, cap, FOOT[0])


def heat(v):
    t = v / 100
    a, b = (214, 58, 70), (40, 190, 110)
    c1 = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    c2 = tuple(min(255, x + 45) for x in c1)
    return 'background:linear-gradient(180deg,rgb%s,rgb%s)' % (c2, c1)


def s1():
    tiles = [('📊', 'Прогнозы', 'все матчи дня'), ('🔥', 'Что заходит', 'по каждой команде'),
             ('⚖️', 'Модель vs рынок', 'чья логика точнее'), ('🎟️', 'Купон дня', 'самые уверенные'),
             ('🎯', 'Точность', 'как часто угадывает'), ('🏒', 'Команда', 'всё о клубе'),
             ('📈', 'Статистика', 'броски, большинство'), ('🎥', 'Эксперты', 'разборы с видео')]
    b = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:22px">' + ''.join(
        '<div class="row" style="height:165px;flex-direction:column;align-items:flex-start;justify-content:center;gap:6px">'
        '<div style="font:600 46px Osw;color:#fff"><span style="font-size:44px">%s</span>&nbsp; %s</div>'
        '<div style="font:500 34px Onest;color:#d0cce0">%s</div></div>' % t for t in tiles) + '</div>'
    return page('24 листа · КХЛ и НХЛ', 'АНАЛИТИЧЕСКАЯ<br>ТАБЛИЦА', 'JARVIS · для прогнозов на хоккей',
                '<div class="card">%s</div>' % b, '').replace('top:230px', 'top:210px') \
        .replace('<div class="stage" style="', '<div class="stage" style="top:600px;').replace('92px/1 Dela', '74px/1 Dela')


def s2():
    def side(t, p, g):
        return ('<div style="flex:1;text-align:center">%s<div style="font:600 44px Osw;margin-top:14px">%s</div>'
                '<div style="font:400 110px/1.1 Dela;color:%s;text-shadow:0 0 30px %s88">%d%%</div>'
                '<div style="font:500 28px Onest;color:#c9c5d8">ожид. голы <b style="color:#fff;font:700 34px Osw">%s</b></div></div>') % (
            emb(t, 200), t, COL2[t], COL2[t], p, g)
    b = ('<div style="display:flex;align-items:flex-start;gap:10px;padding:20px 0">%s'
         '<div style="font:400 60px Dela;color:#6f6a86;margin-top:80px">VS</div>%s</div>') % (
        side('Авангард', 87, '2,98'), side('Сочи', 13, '1,54'))
    b += ('<div class="bar" style="height:40px;border-radius:20px;margin:24px 10px"><i style="width:87%;border-radius:20px;'
          'background:linear-gradient(90deg,#c41e30,#ff6070);box-shadow:0 0 30px rgba(255,80,100,.6)"></i></div>')
    b += ('<div style="display:flex;gap:20px;margin-top:30px">'
          '<div class="row" style="flex:1;height:130px;flex-direction:column;justify-content:center;gap:4px">'
          '<div style="font:500 28px Onest;color:#c9c5d8">ожидаемый тотал</div><div style="font:400 50px Dela">4,52</div></div>'
          '<div class="row" style="flex:1;height:130px;flex-direction:column;justify-content:center;gap:4px">'
          '<div style="font:500 28px Onest;color:#c9c5d8">прогноз</div><div style="font:400 50px Dela;color:#5ff0a0">ЗАШЁЛ</div></div></div>')
    return page('лист «прогнозы»', 'РАСЧЁТ<br>МАТЧА', 'КХЛ · 10 сентября', '<div class="card">%s</div>' % b,
                'Шансы, голы и тотал для каждого матча считает модель.')


COL2 = {'Авангард': '#ff5a6e', 'Сочи': '#ffc23a'}


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
    return page('лист «Прогнозы — кратко»', 'ВСЕ<br>ПРОГНОЗЫ', 'КХЛ · каждый день',
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
          'box-shadow:0 0 40px rgba(62,224,138,.3)"><div style="font:600 34px Osw">КУПОН ИЗ 3 · ЗАШЛИ 3 ИЗ 3</div>'
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
            b += ('<div style="display:flex;align-items:center;gap:16px"><div class="bar" style="flex:1;height:32px">'
                  '<i class="%s" style="width:%d%%"></i></div><div style="width:90px;text-align:right;font:700 32px Osw">%d%%</div></div>') % (cl, v, v)
        b += '</div>'
    b += ('<div style="display:flex;justify-content:center;gap:50px;margin-top:18px;font:600 26px Onest">'
          '<span><i class="gold" style="display:inline-block;width:28px;height:14px;border-radius:7px"></i> таблица</span>'
          '<span><i class="blue" style="display:inline-block;width:28px;height:14px;border-radius:7px"></i> букмекер</span></div>')
    return page('лист «Модель vs рынок»', 'ТАБЛИЦА<br>И БУКМЕКЕР', 'шанс победы хозяев · 27 октября',
                '<div class="card" style="padding:24px">%s</div>' % b, '')


def s7():
    b = ('<div class="card" style="text-align:center;padding:70px 40px">'
         '<div style="width:220px;height:220px;margin:0 auto;border-radius:60px;display:flex;align-items:center;justify-content:center;'
         'background:linear-gradient(135deg,#feda75,#fa7e1e 30%,#d62976 60%,#962fbf 85%,#4f5bd5);box-shadow:0 30px 80px rgba(214,41,118,.5)">'
         '<svg width="130" height="130" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round">'
         '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg></div>'
         '<div style="font:400 64px/1.15 Dela;margin-top:60px;color:#fff">НАПИШИТЕ<br>В ДИРЕКТ</div>'
         '<div style="font:500 36px/1.4 Onest;color:#d8d4e6;margin-top:36px">чтобы получить<br>аналитическую таблицу</div>'
         '<div style="display:inline-block;margin-top:50px;padding:26px 60px;border-radius:50px;font:700 40px Osw;letter-spacing:3px;'
         'color:#1a1206;background:linear-gradient(180deg,#ffe27a,#ffb81c);box-shadow:0 0 40px rgba(255,201,40,.55)">'
         '«ТАБЛИЦА»</div><div style="font:500 30px Onest;color:#a9a4bb;margin-top:22px">одно слово — и пришлём доступ</div></div>')
    return page('доступ', 'КАК ПОЛУЧИТЬ<br>ТАБЛИЦУ', 'КХЛ и НХЛ · все листы', b, '').replace('92px/1 Dela', '84px/1 Dela')

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
