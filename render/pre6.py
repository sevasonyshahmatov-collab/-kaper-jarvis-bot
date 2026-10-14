"""Предматчевые баннеры — 6 шаблонов (14.10.2026, пробы для владельца). Портрет 1080×1350 × quality.S.

    import pre6
    p = dict(home='Колорадо', away='Даллас', date='четверг, 15 октября', time='03:30', line=(2.18, 4.24, 2.81),
             pick='ПОБЕДА КОЛОРАДО', odds=2.18, side='home',
             tape=[('ПОБЕДЫ', '4 из 6', '2 из 6'), ('ШАЙБ ЗА ИГРУ', '4.83', '2.17'), ('ПРОПУСКАЮТ', '3.17', '1.67')],
             facts=['4,83 шайбы за игру — лучшая атака лиги', 'Маккиннон: 12 очков в 6 матчах'])
    pre6.render(p, 'out/p.jpg', style='ticket')   # ticket | card | fight | board | cover | odds

  ticket «Билет»        — билет на матч: поля даты, начала и линии, отрывной корешок с прогнозом и штрихкодом
  card   «Карточка»     — коллекционная карточка выбранного клуба: голографическая рамка, цифры, прогноз внизу
  fight  «Афиша боя»    — плакат главного боя: имена крупно, «VS», сравнение по строкам, ставка вечера
  board  «Доска»        — тактическая доска тренера: площадка маркером, крестики-нолики, прогноз обведён красным
  cover  «Обложка»      — обложка журнала: клуб на обложке, заголовки фактами, прогноз главным заголовком
  odds   «Кэф»          — минимализм: градиент в цветах клубов, гигантский кэф, стеклянная карточка с прогнозом
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import bkit as K
from bkit import S, W, H

GOLD = (232, 186, 82)


def _tag(p):
    return 'NHL' if K.league_of(p['home'], p['away']) == 'NHL' else 'KXL'


def _lg(p):
    return 'НХЛ' if _tag(p) == 'NHL' else 'КХЛ'


def _pt(p):
    return p['home'] if p.get('side', 'home') == 'home' else p['away']


def _brand(d, x, y, col=(255, 255, 255), acc=GOLD, size=30, anchor='mm', tag='KXL'):
    f = K.font('mont', size, 900)
    a, b = 'JARVIS', ' | ' + tag
    w = f.getlength(a + b) / S
    x0 = x - w / 2 if anchor == 'mm' else x
    K.text(d, (x0, y), a, f, col, 'lm')
    K.text(d, (x0 + f.getlength(a) / S, y), b, f, acc, 'lm')


def _barcode(d, x0, y0, x1, y1, ink, seed=4, vertical=False):
    rnd = np.random.default_rng(seed)
    p = x0 if not vertical else y0
    end = x1 if not vertical else y1
    while p < end:
        w = int(rnd.choice([2, 3, 3, 5, 7]))
        if vertical:
            d.rectangle((x0 * S, p * S, x1 * S, (p + w) * S), fill=ink)
        else:
            d.rectangle((p * S, y0 * S, (p + w) * S, y1 * S), fill=ink)
        p += w + int(rnd.choice([2, 4, 5]))


# ── 1. Билет ────────────────────────────────────────────────────────────────────────────────────────────────────────
def ticket(p, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (20, 22, 30)), (1, (8, 8, 12))]))
    K.glow_blob(img, W / 2, 520, 600, (90, 90, 120), 0.3)
    tw, th, x0, y0 = 880, 1210, 100, 70
    tk = Image.new('RGBA', (tw * S, th * S), (0, 0, 0, 0))
    td = ImageDraw.Draw(tk)
    td.rounded_rectangle((0, 0, tw * S, th * S), 34 * S, fill=(248, 245, 238, 255))
    stub_y = 900
    for cx in (0, tw):                                             # вырезы у линии отрыва
        td.ellipse(((cx - 34) * S, (stub_y - 34) * S, (cx + 34) * S, (stub_y + 34) * S), fill=(0, 0, 0, 0))
    for x in range(50, tw - 40, 26):
        td.line((x * S, stub_y * S, (x + 12) * S, stub_y * S), fill=(170, 166, 156), width=3 * S)
    hc, ac = K.color(p['home']), K.color(p['away'])
    band = Image.new('RGBA', (tw * S, 300 * S), hc + (255,))
    ImageDraw.Draw(band).polygon([(tw * 0.55 * S, 0), (tw * S, 0), (tw * S, 300 * S), (tw * 0.42 * S, 300 * S)], fill=ac + (255,))
    mask = Image.new('L', band.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw * S, 340 * S), 34 * S, fill=255)
    band.putalpha(mask)
    tk.alpha_composite(band)
    for j, t in enumerate((p['home'], p['away'])):
        e = K.emblem(t, 200, sticker=True)
        tk.alpha_composite(e, (int((tw / 2 + (-230 if j == 0 else 230)) * S - e.width / 2), int(150 * S - e.height / 2)))
    K.text(td, (tw / 2, 150), 'VS', K.font('osw', 70, 700), (255, 255, 255))
    ink = (28, 28, 34)
    _brand(td, tw / 2, 345, ink, (200, 30, 40), 28, tag=_tag(p))
    nm = '%s — %s' % (K.short(p['home']).upper(), K.short(p['away']).upper())
    K.text(td, (tw / 2, 420), nm, K.fit(nm, 'osw', 70, tw - 80, 700), ink)
    K.text(td, (tw / 2, 480), 'РЕГУЛЯРНЫЙ ЧЕМПИОНАТ · %s' % _lg(p), K.font('mont', 22, 800), (120, 118, 112))
    fields = [('ДАТА', p['date'].split(', ')[-1].upper()), ('НАЧАЛО', p['time'] + ' МСК'), ('ЛИГА', _lg(p))]
    for i, (lab, val) in enumerate(fields):
        x = 60 + i * (tw - 120) / 3
        K.text(td, (x, 540), lab, K.font('mont', 20, 800), (140, 136, 128), 'lm')
        K.text(td, (x, 585), val, K.fit(val, 'osw', 40, (tw - 160) / 3, 700), ink, 'lm')
    td.line((60 * S, 630 * S, (tw - 60) * S, 630 * S), fill=(214, 208, 196), width=2 * S)
    K.text(td, (60, 670), 'ЛИНИЯ · ОСНОВНОЕ ВРЕМЯ', K.font('mont', 20, 800), (140, 136, 128), 'lm')
    for i, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), p['line'])):
        x = 60 + i * 260
        K.rrect(td, (x, 700, x + 240, 820), 18, fill=(236, 232, 222, 255))
        K.text(td, (x + 120, 728), lab, K.font('mont', 22, 900), (120, 118, 112))
        K.text(td, (x + 120, 785), K.fmt_k(v), K.font('osw', 58, 700), ink)
    # корешок
    K.text(td, (60, 960), 'ПРОГНОЗ', K.font('mont', 24, 900), (200, 30, 40), 'lm')
    K.text(td, (60, 1025), p['pick'], K.fit(p['pick'], 'osw', 66, tw - 380, 700), ink, 'lm')
    K.text(td, (60, 1090), 'КЭФ ' + K.fmt_k(p['odds']), K.font('osw', 54, 700), (200, 30, 40), 'lm')
    _barcode(td, tw - 250, 950, tw - 60, 1140, ink + (255,), vertical=True)
    K.text(td, (60, 1160), '@jarvibet', K.font('mont', 24, 900), ink, 'lm')
    tk = tk.rotate(1.5, expand=True, resample=Image.BICUBIC)
    sh = Image.new('RGBA', tk.size, (0, 0, 0, 0))
    sh.putalpha(tk.getchannel('A').filter(ImageFilter.GaussianBlur(24 * S)).point(lambda v: v * 170 // 255))
    img.alpha_composite(sh, (int(x0 * S - 20 * S + 10 * S), int(y0 * S - 20 * S + 30 * S)))
    img.alpha_composite(tk, (int(x0 * S - 20 * S), int(y0 * S - 20 * S)))


# ── 2. Коллекционная карточка ───────────────────────────────────────────────────────────────────────────────────────
def _holo(w, h, phase=0.0):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    hue = ((x / w * .7 + y / h * .45) + phase + .06 * np.sin(x / w * 11 + y / h * 7)) % 1
    i = (hue * 6).astype(int) % 6
    f = hue * 6 - np.floor(hue * 6)
    v, s = 1.0, 0.5
    pp, q, tt = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, pp, pp, tt, v])
    g = np.choose(i, [tt, v, v, q, pp, pp])
    b = np.choose(i, [pp, pp, tt, v, v, q])
    return Image.fromarray((np.dstack([r, g, b]) * 255).astype(np.uint8), 'RGB').convert('RGBA')


def card(p, img):
    d = ImageDraw.Draw(img)
    t = _pt(p)
    c = K.color(t)
    img.alpha_composite(K.vgrad(W, H, [(0, K.mix(c, -0.82)), (1, (6, 6, 10))]))
    rnd = np.random.default_rng(5)
    for _ in range(140):                                          # блёстки
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1, 3)
        d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=(255, 255, 255, int(rnd.uniform(60, 200))))
    cx0, cy0, cw, ch = 110, 80, 860, 1190
    K.shadow(img, (cx0, cy0, cx0 + cw, cy0 + ch), 40, 30, 200, 20)
    holo = _holo((cw // 2) * S // 1, (ch // 2) * S // 1, 0.15).resize((cw * S, ch * S), Image.BICUBIC)
    m = Image.new('L', holo.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, cw * S, ch * S), 40 * S, fill=255)
    holo.putalpha(m)
    img.alpha_composite(holo, (cx0 * S, cy0 * S))
    inner = (cx0 + 26, cy0 + 26, cx0 + cw - 26, cy0 + ch - 26)
    K.rrect(d, inner, 26, fill=(14, 14, 20, 255))
    art = (inner[0] + 24, inner[1] + 110, inner[2] - 24, inner[1] + 640)
    art_img = K.vgrad(art[2] - art[0], art[3] - art[1], [(0, K.mix(c, 0.25)), (1, K.mix(c, -0.55))])
    am = Image.new('L', art_img.size, 0)
    ImageDraw.Draw(am).rounded_rectangle((0, 0, art_img.width, art_img.height), 20 * S, fill=255)
    art_img.putalpha(am)
    img.alpha_composite(art_img, (int(art[0] * S), int(art[1] * S)))
    K.glow_blob(img, (art[0] + art[2]) / 2, (art[1] + art[3]) / 2, 260, (255, 255, 255), 0.25)
    K.put(img, K.emblem(t, 400, sticker=True), (art[0] + art[2]) / 2, (art[1] + art[3]) / 2)
    K.text(d, (inner[0] + 30, inner[1] + 58), K.short(t).upper(), K.fit(K.short(t).upper(), 'osw', 62, 560, 700),
           (255, 255, 255), 'lm')
    K.rrect(d, (inner[2] - 230, inner[1] + 26, inner[2] - 24, inner[1] + 90), 32, fill=GOLD + (255,))
    K.text(d, (inner[2] - 127, inner[1] + 58), 'КЭФ ' + K.fmt_k(p['odds']), K.font('osw', 38, 700), (30, 22, 6))
    vs = 'VS %s · %s · %s МСК' % (K.short(p['away'] if t == p['home'] else p['home']).upper(),
                                   p['date'].split(', ')[-1].upper(), p['time'])
    K.text(d, ((inner[0] + inner[2]) / 2, art[3] + 44), vs, K.fit(vs, 'mont', 28, cw - 120, 900), (200, 204, 216))
    y = art[3] + 100
    me = 0 if t == p['home'] else 1
    for lab, vh, va in p.get('tape', [])[:4]:
        K.text(d, (inner[0] + 40, y), lab, K.font('mont', 26, 800), (170, 174, 188), 'lm')
        K.text(d, (inner[2] - 40, y), (vh, va)[me], K.font('osw', 44, 700), (255, 255, 255), 'rm')
        d.line(((inner[0] + 40) * S, (y + 34) * S, (inner[2] - 40) * S, (y + 34) * S), fill=(50, 52, 62), width=S)
        y += 70
    K.rrect(d, (inner[0] + 24, inner[3] - 150, inner[2] - 24, inner[3] - 24), 22, fill=K.mix(c, -0.35) + (255,),
            outline=GOLD, width=3)
    K.text(d, (inner[0] + 60, inner[3] - 110), 'ПРОГНОЗ', K.font('mont', 22, 900), GOLD, 'lm')
    K.text(d, (inner[0] + 60, inner[3] - 62), p['pick'], K.fit(p['pick'], 'osw', 50, cw - 200, 700), (255, 255, 255), 'lm')
    _brand(d, W / 2, 1310, size=24, tag=_tag(p))


# ── 3. Афиша боя ────────────────────────────────────────────────────────────────────────────────────────────────────
def fight(p, img):
    d = ImageDraw.Draw(img)
    hc, ac = K.color(p['home']), K.color(p['away'])
    top = K.vgrad(W, 700, [(0, K.mix(hc, -0.2)), (1, K.mix(hc, -0.75))])
    bot = K.vgrad(W, 700, [(0, K.mix(ac, -0.75)), (1, K.mix(ac, -0.2))])
    img.alpha_composite(top, (0, 0))
    img.alpha_composite(bot, (0, 650 * S))
    diag = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(diag).polygon([(0, 600 * S), (W * S, 520 * S), (W * S, 760 * S), (0, 840 * S)], fill=(10, 10, 12, 255))
    img.alpha_composite(diag)
    K.text(d, (W / 2, 70), 'ГЛАВНЫЙ МАТЧ НОЧИ' if _tag(p) == 'NHL' else 'ГЛАВНЫЙ МАТЧ ДНЯ', K.font('mont', 30, 900), GOLD)
    K.text(d, (W / 2, 112), '%s · %s МСК' % (p['date'].upper(), p['time']), K.font('mont', 24, 800), (240, 236, 228))
    K.put(img, K.emblem(p['home'], 330), 780, 360)
    K.put(img, K.emblem(p['away'], 330), 300, 990)
    K.text(d, (60, 330), K.short(p['home']).upper(), K.fit(K.short(p['home']).upper(), 'alumni', 210, 560, 900),
           (255, 255, 255), 'lm')
    K.text(d, (1020, 1020), K.short(p['away']).upper(), K.fit(K.short(p['away']).upper(), 'alumni', 210, 560, 900),
           (255, 255, 255), 'rm')
    K.glow_text(img, (W / 2, 680), 'VS', K.font('alumni', 200, 900), GOLD, 16, 1.6, core=(255, 236, 170))
    y = 470
    for lab, vh, va in p.get('tape', [])[:3]:
        K.text(d, (60, y), vh, K.font('osw', 40, 700), (255, 255, 255), 'lm')
        K.text(d, (210, y), lab, K.font('mont', 22, 800), (220, 214, 200), 'lm')
        y += 50
    y = 800
    for lab, vh, va in p.get('tape', [])[:3]:
        K.text(d, (1020, y), va, K.font('osw', 40, 700), (255, 255, 255), 'rm')
        K.text(d, (870, y), lab, K.font('mont', 22, 800), (220, 214, 200), 'rm')
        y += 50
    K.rrect(d, (60, 1170, 1020, 1300), 20, fill=(12, 12, 14, 235), outline=GOLD, width=3)
    K.text(d, (100, 1205), 'СТАВКА ВЕЧЕРА', K.font('mont', 22, 900), GOLD, 'lm')
    K.text(d, (100, 1260), p['pick'], K.fit(p['pick'], 'osw', 54, 640, 700), (255, 255, 255), 'lm')
    K.text(d, (980, 1235), K.fmt_k(p['odds']), K.font('osw', 90, 700), GOLD, 'rm')
    _brand(d, W / 2, 1328, size=20, tag=_tag(p))


# ── 4. Тактическая доска ────────────────────────────────────────────────────────────────────────────────────────────
def _marker_line(d, pts, col, w=6, seed=1):
    rnd = np.random.default_rng(seed)
    jit = [(x + rnd.normal(0, 1.2), y + rnd.normal(0, 1.2)) for x, y in pts]
    d.line([(x * S, y * S) for x, y in jit], fill=col, width=int(w * S), joint='curve')


def board(p, img):
    d = ImageDraw.Draw(img)
    img.alpha_composite(K.vgrad(W, H, [(0, (70, 74, 80)), (1, (40, 42, 46))]))
    K.rrect(d, (30, 30, 1050, 1320), 24, fill=(176, 180, 186, 255))
    K.rrect(d, (52, 52, 1028, 1298), 14, fill=(250, 250, 248, 255))
    BL, RD, BK = (30, 70, 190), (214, 36, 40), (30, 30, 36)
    hand = lambda s: K.font('hand', s, 700)
    K.text(d, (W / 2, 120), '%s — %s' % (K.short(p['home']), K.short(p['away'])), K.fit('%s — %s' % (K.short(p['home']),
           K.short(p['away'])), 'hand', 92, 900, 700), BK)
    K.text(d, (W / 2, 200), '%s, %s по Москве' % (p['date'].split(', ')[-1], p['time']), hand(50), (90, 90, 96))
    rx0, ry0, rx1, ry1 = 120, 260, 960, 700                           # площадка
    _marker_line(d, [(rx0 + 80, ry0), (rx1 - 80, ry0)], BL, 6, 1)
    _marker_line(d, [(rx0 + 80, ry1), (rx1 - 80, ry1)], BL, 6, 2)
    for cx, sgn in ((rx0 + 80, -1), (rx1 - 80, 1)):
        pts = [(cx + sgn * 80 * math.sin(a), (ry0 + ry1) / 2 - (ry1 - ry0) / 2 * math.cos(a))
               for a in np.linspace(0, math.pi, 24)]
        _marker_line(d, pts, BL, 6, 3)
    _marker_line(d, [(W / 2, ry0), (W / 2, ry1)], RD, 6, 4)
    for x in (W / 2 - 150, W / 2 + 150):
        _marker_line(d, [(x, ry0), (x, ry1)], BL, 5, 5)
    rnd = np.random.default_rng(3)
    for i in range(5):                                                 # крестики и нолики
        x, y = rnd.uniform(rx0 + 120, W / 2 - 60), rnd.uniform(ry0 + 60, ry1 - 60)
        _marker_line(d, [(x - 16, y - 16), (x + 16, y + 16)], RD, 6, 10 + i)
        _marker_line(d, [(x + 16, y - 16), (x - 16, y + 16)], RD, 6, 20 + i)
        x2, y2 = rnd.uniform(W / 2 + 60, rx1 - 120), rnd.uniform(ry0 + 60, ry1 - 60)
        d.ellipse(((x2 - 18) * S, (y2 - 18) * S, (x2 + 18) * S, (y2 + 18) * S), outline=BL, width=6 * S)
    _marker_line(d, [(330, 560), (430, 480), (560, 470), (680, 430), (790, 470)], BK, 5, 40)
    _marker_line(d, [(770, 450), (792, 472), (765, 490)], BK, 5, 41)
    for j, t in enumerate((p['home'], p['away'])):
        K.put(img, K.emblem(t, 120), rx0 + 40 if j == 0 else rx1 - 40, ry0 - 50)
    y = 770
    for lab, vh, va in p.get('tape', [])[:3]:
        s = '%s: %s — %s' % (lab.capitalize(), vh, va)
        K.text(d, (110, y), '• ' + s, K.fit('• ' + s, 'hand', 54, 860, 700), BK, 'lm')
        y += 66
    K.text(d, (W / 2, 1030), 'Линия: %s · %s · %s' % tuple(K.fmt_k(v) for v in p['line']), hand(52), (90, 90, 96))
    txt = '%s — %s!' % (p['pick'], K.fmt_k(p['odds']))
    f = K.fit(txt, 'hand', 96, 800, 700)
    K.text(d, (W / 2, 1160), txt, f, RD)
    tw = f.getlength(txt) / S
    pts = [(W / 2 + (tw / 2 + 50) * math.cos(a), 1165 + 85 * math.sin(a)) for a in np.linspace(0.2, 2 * math.pi + 0.5, 40)]
    _marker_line(d, pts, RD, 6, 50)
    K.text(d, (1000, 1270), '@jarvibet', hand(44), BK, 'rm')


# ── 5. Обложка журнала ──────────────────────────────────────────────────────────────────────────────────────────────
def cover(p, img):
    d = ImageDraw.Draw(img)
    t = _pt(p)
    c = K.color(t)
    img.alpha_composite(K.vgrad(W, H, [(0, K.mix(c, 0.1)), (.6, c), (1, K.mix(c, -0.6))]))
    K.glow_blob(img, 620, 700, 520, (255, 255, 255), 0.35)
    e = K.emblem(t, 700)
    sh = Image.new('RGBA', e.size, (0, 0, 0, 0))
    sh.putalpha(e.getchannel('A').filter(ImageFilter.GaussianBlur(30 * S)).point(lambda v: v * 150 // 255))
    e = K.emblem(t, 600)
    sh = Image.new('RGBA', e.size, (0, 0, 0, 0))
    sh.putalpha(e.getchannel('A').filter(ImageFilter.GaussianBlur(30 * S)).point(lambda v: v * 150 // 255))
    K.put(img, sh, 740, 790)
    K.put(img, e, 730, 760)
    K.text(d, (W / 2, 150), 'JARVIS', K.font('play', 210, 700), (255, 255, 255))
    K.text(d, (60, 290), '%s · ВЫПУСК %s' % (_lg(p), p['date'].split(', ')[-1].upper()), K.font('mont', 22, 900),
           (255, 255, 255), 'lm')
    lines = p.get('facts', [])[:3]
    y = 400
    for s in lines:
        words, cur, ln = s.split(), '', []
        for wd in words:
            if K.font('osw', 40, 700).getlength((cur + ' ' + wd).strip()) > 330 * S:
                ln.append(cur)
                cur = wd
            else:
                cur = (cur + ' ' + wd).strip()
        ln.append(cur)
        for k_, l_ in enumerate(ln):
            K.text(d, (60, y), l_.upper(), K.font('osw', 40, 700), (255, 255, 255), 'lm')
            y += 48
        d.line((60 * S, (y - 10) * S, 160 * S, (y - 10) * S), fill=GOLD, width=4 * S)
        y += 40
    K.rrect(d, (60, 1080, 1020, 1290), 10, fill=(10, 10, 12, 230))
    K.text(d, (90, 1120), 'ГЛАВНЫЙ ПРОГНОЗ НОМЕРА', K.font('mont', 24, 900), GOLD, 'lm')
    K.text(d, (90, 1195), p['pick'], K.fit(p['pick'], 'osw', 84, 700, 700), (255, 255, 255), 'lm')
    K.text(d, (990, 1195), K.fmt_k(p['odds']), K.font('osw', 100, 700), GOLD, 'rm')
    vs = 'VS %s · %s МСК' % (K.short(p['away'] if t == p['home'] else p['home']).upper(), p['time'])
    K.text(d, (90, 1255), vs, K.font('mont', 24, 800), (200, 200, 206), 'lm')
    K.text(d, (990, 1255), '@jarvibet', K.font('mont', 24, 900), (200, 200, 206), 'rm')


# ── 6. Кэф (минимализм) ─────────────────────────────────────────────────────────────────────────────────────────────
def odds(p, img):
    d = ImageDraw.Draw(img)
    hc, ac = K.color(p['home']), K.color(p['away'])
    img.alpha_composite(K.vgrad(W, H, [(0, (10, 10, 14)), (1, (4, 4, 6))]))
    K.glow_blob(img, 180, 260, 640, hc, 0.75)
    K.glow_blob(img, 920, 1080, 640, ac, 0.75)
    K.glow_blob(img, 760, 380, 360, K.mix(hc, 0.4), 0.3)
    _brand(d, 70, 80, anchor='lm', size=28, tag=_tag(p))
    K.text(d, (1010, 80), '%s · %s МСК' % (p['date'].split(', ')[-1].upper(), p['time']), K.font('mont', 24, 800),
           (230, 230, 236), 'rm')
    big = K.fmt_k(p['odds'])
    f = K.fit(big, 'alumni', 560, 960, 900)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W / 2 * S, 560 * S), big, font=f, fill=(255, 255, 255, 255), anchor='mm')
    img.alpha_composite(lay)
    K.text(d, (W / 2, 220), 'КЭФ НА ПРОГНОЗ', K.font('mont', 30, 900), (240, 240, 245))
    gx0, gy0, gx1, gy1 = 70, 900, 1010, 1270                          # «стекло»
    crop = img.crop((gx0 * S, gy0 * S, gx1 * S, gy1 * S)).filter(ImageFilter.GaussianBlur(30 * S))
    m = Image.new('L', crop.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, crop.width, crop.height), 36 * S, fill=255)
    crop.putalpha(m)
    img.alpha_composite(crop, (gx0 * S, gy0 * S))
    gl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    K.rrect(ImageDraw.Draw(gl), (gx0, gy0, gx1, gy1), 36, fill=(255, 255, 255, 36), outline=(255, 255, 255, 130), width=2)
    img.alpha_composite(gl)
    for j, t in enumerate((p['home'], p['away'])):
        K.put(img, K.emblem(t, 110), 160 + j * 130, 975)
    K.text(d, (320, 975), '%s — %s' % (K.short(p['home']).upper(), K.short(p['away']).upper()),
           K.fit('%s — %s' % (K.short(p['home']).upper(), K.short(p['away']).upper()), 'osw', 44, 660, 700),
           (255, 255, 255), 'lm')
    K.text(d, (120, 1100), 'ПРОГНОЗ', K.font('mont', 24, 900), (230, 230, 236), 'lm')
    K.text(d, (120, 1170), p['pick'], K.fit(p['pick'], 'osw', 76, 820, 700), (255, 255, 255), 'lm')
    ln = 'П1 %s · Х %s · П2 %s' % tuple(K.fmt_k(v) for v in p['line'])
    K.text(d, (120, 1235), ln, K.font('mont', 24, 800), (210, 210, 220), 'lm')
    K.text(d, (960, 1235), '@jarvibet', K.font('mont', 24, 900), (255, 255, 255), 'rm')


STYLES = {'ticket': ticket, 'card': card, 'fight': fight, 'board': board, 'cover': cover, 'odds': odds}


def render(p, path, style='ticket'):
    K.prep(K.league_of(p['home'], p['away']))
    img = K.canvas()
    STYLES[style](p, img)
    return K.save(img, path, grain=3)


if __name__ == '__main__':
    import sys
    p = dict(home='Колорадо', away='Даллас', date='четверг, 15 октября', time='03:30', line=(2.18, 4.24, 2.81),
             pick='ПОБЕДА КОЛОРАДО', odds=2.18, side='home',
             tape=[('ПОБЕДЫ', '4 из 6', '2 из 6'), ('ШАЙБ ЗА ИГРУ', '4.83', '2.17'), ('ПРОПУСКАЮТ', '3.17', '1.67'),
                   ('БОЛЬШИНСТВО', '23.8%', '14.3%')],
             facts=['4,83 шайбы за игру — лучшая атака', 'Маккиннон: 12 очков за 6 матчей', 'Дома 2 победы в 3 играх'])
    for st in (sys.argv[1:] or STYLES):
        print(render(p, 'out/pre6/pre_%s.jpg' % st, st))
