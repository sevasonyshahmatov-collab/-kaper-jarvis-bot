# -*- coding: utf-8 -*-
"""Фоновые рисунки команд для мини-приложения (владелец 25.10: «у каждой команды свои ассоциации — Колорадо горы,
Локомотив железная дорога, ЦСКА кони»). Рисунок — белые фигуры с разной прозрачностью на прозрачном фоне: приложение
использует его как маску и красит в цвета клуба (team/site/app/index.html, .art). Свои рисунки — без чужих фото и логотипов.

    python team/site/app_data/bg_art.py      → team/site/app/bg/<эмблема>.svg
"""
import math
import os
import random

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'bg')
W, H = 1600, 900


def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">%s</svg>' % (W, H, body)


def mountains():
    """Колорадо: три хребта с острыми пиками, снег на вершинах (снеговая линия, обрезанная по хребту), солнце."""
    rnd = random.Random(4)
    o = ['<circle cx="1210" cy="210" r="100" fill="#fff" fill-opacity=".22"/>',
         '<circle cx="1210" cy="210" r="140" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="3"/>']
    for k, (base, top, n, op, snow) in enumerate(((600, 300, 7, .16, 0), (720, 250, 6, .3, 330), (900, 180, 5, .55, 330))):
        xs = sorted(rnd.uniform(-60, W + 60) for _ in range(n))
        pts = [(-60, base)]
        for x in xs:                                     # пик и седловина после него
            pts += [(x, rnd.uniform(top, top + 120)), (x + rnd.uniform(110, 200), rnd.uniform(base - 160, base - 60))]
        pts += [(W + 60, base)]
        d = 'M' + ' L'.join('%.0f %.0f' % p for p in pts) + ' L%d %d L-60 %d Z' % (W + 60, H, H)
        o.append('<clipPath id="r%d"><path d="%s"/></clipPath><path d="%s" fill="#fff" fill-opacity="%.2f"/>' % (k, d, d, op))
        if snow:                                         # снег: верхняя полоса хребта неровной линией
            line = 'M-60 0 L%d 0 L%d %d ' % (W + 60, W + 60, top + snow - 120) + ' '.join(
                'L%.0f %.0f' % (x, top + snow - 120 + rnd.uniform(-40, 40)) for x in range(W, -80, -80)) + ' Z'
            o.append('<path d="%s" fill="#fff" fill-opacity=".85" clip-path="url(#r%d)"/>' % (line, k))
    return svg(''.join(o))


def taiga():
    """Сибирь: ряды елей (дальние бледнее), снежинки, сугробы."""
    rnd = random.Random(5)
    o = []

    def fir(x, y, h, op):
        w = h * .42
        tiers = ''.join('<path d="M%.0f %.0f L%.0f %.0f L%.0f %.0f Z"/>' % (
            x, y - h + k * h * .22, x - w * (.45 + k * .18), y - h * (.45 - k * .14), x + w * (.45 + k * .18), y - h * (.45 - k * .14))
            for k in range(3))
        return '<g fill="#fff" fill-opacity="%.2f">%s<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f"/></g>' % (
            op, tiers, x - h * .03, y - h * .2, h * .06, h * .2)
    for row, (y, hmin, hmax, op, n) in enumerate(((560, 120, 180, .16, 26), (700, 170, 250, .3, 20), (880, 260, 380, .55, 12))):
        xs = sorted(rnd.uniform(-60, W + 60) for _ in range(n))
        o += [fir(x, y + rnd.uniform(-20, 20), rnd.uniform(hmin, hmax), op) for x in xs]
    o.append('<path d="M-40 900 Q 400 800 800 860 T 1640 840 L1640 900 Z" fill="#fff" fill-opacity=".7"/>')
    for _ in range(40):                                # снежинки
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, 520), rnd.uniform(4, 11)
        arms = ''.join('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f"/>' % (
            x, y, x + r * math.cos(a), y + r * math.sin(a)) for a in (k * math.pi / 3 for k in range(6)))
        o.append('<g stroke="#fff" stroke-opacity="%.2f" stroke-width="2">%s</g>' % (rnd.uniform(.25, .6), arms))
    return svg(''.join(o))


def sea():
    """Адмирал: волны, парусник на горизонте, якорь."""
    o = []
    for k, (y, amp, op) in enumerate(((560, 14, .18), (630, 18, .26), (710, 24, .36), (800, 30, .5))):
        d = 'M-40 %d ' % y + ' '.join('Q %.0f %.0f %.0f %d' % (x + 60, y - amp if (i % 2) == 0 else y + amp, x + 120, y)
                                      for i, x in enumerate(range(-40, W + 120, 120)))
        o.append('<path d="%s L%d %d L-40 %d Z" fill="#fff" fill-opacity="%.2f"/>' % (d, W + 120, H, H, op))
    # парусник: корпус, мачты, паруса
    o.append('<g fill="#fff" fill-opacity=".55" transform="translate(1040 300) scale(1.25)">'
             '<path d="M0 220 L340 220 L300 270 L40 270 Z"/><rect x="118" y="20" width="8" height="200"/><rect x="218" y="40" width="8" height="180"/>'
             '<path d="M126 30 Q 190 90 126 200 Z"/><path d="M118 40 Q 60 110 118 200 Z" fill-opacity=".7"/>'
             '<path d="M226 50 Q 285 110 226 205 Z"/><path d="M218 60 Q 170 120 218 205 Z" fill-opacity=".7"/>'
             '<path d="M126 12 L160 22 L126 32 Z"/></g>')
    # якорь
    o.append('<g fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="14" stroke-linecap="round" transform="translate(260 170)">'
             '<circle cx="100" cy="40" r="28"/><line x1="100" y1="68" x2="100" y2="300"/><line x1="40" y1="120" x2="160" y2="120"/>'
             '<path d="M10 220 Q 30 320 100 310 Q 170 320 190 220"/><path d="M10 220 L-6 250 M10 220 L40 236 M190 220 L206 250 M190 220 L160 236"/></g>')
    return svg(''.join(o))


def factory():
    """Металлург: цех с пилообразной крышей, трубы с дымом, ковш льёт металл, искры."""
    rnd = random.Random(9)
    o = ['<path d="M-40 900 L-40 620 %s L1640 900 Z" fill="#fff" fill-opacity=".35"/>' % ' '.join(
        'L%d 620 L%d 540 L%d 620' % (x, x + 90, x + 140) for x in range(-40, 1640, 140))]
    for x, h, w in ((180, 430, 60), (320, 520, 70), (470, 380, 54), (1290, 470, 64), (1430, 400, 56)):
        o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fff" fill-opacity=".45"/>' % (x, 620 - h, w, h))
        o.append('<rect x="%d" y="%d" width="%d" height="12" fill="#fff" fill-opacity=".7"/>' % (x - 6, 620 - h, w + 12))
        for k in range(5):                               # дым
            o.append('<circle cx="%.0f" cy="%.0f" r="%.0f" fill="#fff" fill-opacity="%.2f"/>' % (
                x + w / 2 + k * 34 + rnd.uniform(-8, 8), 620 - h - 40 - k * 46, 30 + k * 14, .2 - k * .03))
    # ковш и струя металла
    o.append('<g transform="translate(760 250) rotate(18)"><path d="M0 0 L190 0 L165 170 Q 95 200 25 170 Z" fill="#fff" fill-opacity=".7"/>'
             '<rect x="-14" y="-16" width="218" height="22" rx="8" fill="#fff" fill-opacity=".85"/></g>')
    o.append('<path d="M935 330 Q 990 420 960 560 L1000 560 Q 1015 430 960 320 Z" fill="#fff" fill-opacity=".9"/>')
    o.append('<ellipse cx="985" cy="575" rx="120" ry="22" fill="#fff" fill-opacity=".8"/>')
    for _ in range(60):                                  # искры
        a, r = rnd.uniform(math.pi * 1.05, math.pi * 1.95), rnd.uniform(40, 260)
        x, y = 985 + r * math.cos(a), 570 + r * math.sin(a) * .8
        o.append('<circle cx="%.0f" cy="%.0f" r="%.1f" fill="#fff" fill-opacity="%.2f"/>' % (x, y, rnd.uniform(2, 5), rnd.uniform(.4, .95)))
    return svg(''.join(o))


def railway():
    """Локомотив: состав (тепловоз и вагоны) на насыпи, рельсы и шпалы, столбы с проводами."""
    o = ['<rect x="-40" y="742" width="1680" height="10" fill="#fff" fill-opacity=".8"/>',
         '<path d="M-40 760 L1640 760 L1640 800 L-40 800 Z" fill="#fff" fill-opacity=".25"/>']
    o += ['<rect x="%d" y="752" width="34" height="14" fill="#fff" fill-opacity=".55"/>' % x for x in range(-30, 1640, 64)]
    for x in range(60, 1640, 360):                       # столбы и провода
        o.append('<rect x="%d" y="380" width="10" height="362" fill="#fff" fill-opacity=".3"/><rect x="%d" y="392" width="70" height="8" fill="#fff" fill-opacity=".3"/>' % (x, x - 30))
    o.append('<path d="M-40 420 %s" fill="none" stroke="#fff" stroke-opacity=".25" stroke-width="3"/>' % ' '.join(
        'Q %d 470 %d 400' % (x + 180, x + 360) for x in range(-300, 1640, 360)))
    # тепловоз
    o.append('<g fill="#fff"><path d="M980 560 L1360 560 Q 1430 560 1460 620 L1480 700 L980 700 Z" fill-opacity=".85"/>'
             '<rect x="1040" y="590" width="70" height="50" rx="6" fill-opacity=".25"/><rect x="1130" y="590" width="70" height="50" rx="6" fill-opacity=".25"/>'
             '<path d="M1360 585 L1420 585 Q 1445 600 1452 640 L1360 640 Z" fill-opacity=".3"/><rect x="980" y="700" width="500" height="18" fill-opacity=".6"/>'
             '<circle cx="1470" cy="670" r="10" fill-opacity="1"/></g>')
    for x0 in (1020, 1400):
        o += ['<circle cx="%d" cy="730" r="24" fill="#fff" fill-opacity=".75"/>' % (x0 + k * 56) for k in range(2)]
    for start in (520, 60):                              # вагоны
        o.append('<g fill="#fff"><rect x="%d" y="580" width="430" height="120" rx="10" fill-opacity=".6"/>%s<rect x="%d" y="700" width="430" height="14" fill-opacity=".45"/>'
                 '<circle cx="%d" cy="730" r="22" fill-opacity=".6"/><circle cx="%d" cy="730" r="22" fill-opacity=".6"/>'
                 '<circle cx="%d" cy="730" r="22" fill-opacity=".6"/><circle cx="%d" cy="730" r="22" fill-opacity=".6"/></g>' % (
                     start, ''.join('<rect x="%d" y="605" width="52" height="40" rx="5" fill-opacity=".25"/>' % (start + 22 + k * 80) for k in range(5)),
                     start, start + 50, start + 104, start + 326, start + 380))
    return svg(''.join(o))


KNIGHT = ('M40 200 L160 200 L160 186 L150 180 L148 166 Q 152 130 140 104 Q 134 80 140 60 Q 142 40 128 28 L134 8 L118 22 '
          'Q 100 18 84 30 Q 60 48 46 78 Q 40 92 50 100 Q 62 106 74 98 Q 86 92 98 96 Q 80 122 70 150 L60 166 L52 180 L40 186 Z '
          'M96 46 a6 6 0 1 0 0.1 0 Z')


def horses():
    """ЦСКА («кони»): шахматные кони разного размера, как табун; звёзды армейского клуба."""
    rnd = random.Random(11)
    o = []
    for x, y, s, op in ((1020, 840, 3.2, .6), (1330, 840, 2.4, .42), (780, 840, 2.0, .3), (1500, 840, 1.6, .3), (160, 840, 1.9, .22), (440, 840, 1.4, .18)):
        o.append('<path d="%s" fill="#fff" fill-rule="evenodd" fill-opacity="%.2f" transform="translate(%d %d) scale(%.2f)"/>' % (KNIGHT, op, x, y - 200 * s, s))
    o.append('<rect x="-40" y="840" width="1680" height="60" fill="#fff" fill-opacity=".2"/>')
    for _ in range(14):                                  # звёзды
        cx, cy, r = rnd.uniform(40, W - 40), rnd.uniform(40, 420), rnd.uniform(10, 26)
        pts = ' '.join('%.0f,%.0f' % (cx + (r if k % 2 == 0 else r * .42) * math.sin(k * math.pi / 5),
                                      cy - (r if k % 2 == 0 else r * .42) * math.cos(k * math.pi / 5)) for k in range(10))
        o.append('<polygon points="%s" fill="#fff" fill-opacity="%.2f"/>' % (pts, rnd.uniform(.18, .45)))
    return svg(''.join(o))


ART = {'nhl_col': mountains, 'sibir': taiga, 'admiral': sea, 'metallurg': factory, 'lokomotiv': railway, 'cska': horses}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for slug, fn in ART.items():
        with open(os.path.join(OUT, slug + '.svg'), 'w', encoding='utf-8') as f:
            f.write(fn())
    print('фонов: %d → %s' % (len(ART), OUT))
