"""Послематчевая сторис 1080×1920: фон в цвете победителя с огромной эмблемой, выходящей за края,
в центре белая карточка со счётом, знаком лиги сверху и подписью исхода снизу.

    import story_result as sr
    sr.render(dict(home='Колорадо', away='Лос-Анджелес', sh=2, sa=0, mark=''), 'story.jpg', league='NHL')

mark: '' — основное время, 'ОТ' — овертайм, 'Б' — буллиты. Подпись: «ПОБЕДА КОЛОРАДО В ОСНОВНОЕ ВРЕМЯ».
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, OSW, UNB

S = 2
W, H = 1080, 1920
GRAIN = 1.3        # сила зерна фона (фактура как у баннеров на один матч)
HERE = os.path.dirname(os.path.abspath(__file__))
OUTCOME = {'': 'В ОСНОВНОЕ ВРЕМЯ', 'ОТ': 'В ОВЕРТАЙМЕ', 'Б': 'ПО БУЛЛИТАМ', 'ОТ/Б': 'В ОВЕРТАЙМЕ / ПО БУЛЛИТАМ'}
# родительный падеж для подписи «ПОБЕДА …»; нет в словаре — пишем как есть
GEN = {'Колорадо': 'КОЛОРАДО', 'Лос-Анджелес': 'ЛОС-АНДЖЕЛЕСА', 'Флорида': 'ФЛОРИДЫ', 'Каролина': 'КАРОЛИНЫ',
       'Торонто': 'ТОРОНТО', 'Монреаль': 'МОНРЕАЛЯ', 'Бостон': 'БОСТОНА', 'Рейнджерс': 'РЕЙНДЖЕРС',
       'Эдмонтон': 'ЭДМОНТОНА', 'Ванкувер': 'ВАНКУВЕРА', 'Вегас': 'ВЕГАСА', 'Чикаго': 'ЧИКАГО',
       'Филадельфия': 'ФИЛАДЕЛЬФИИ', 'Питтсбург': 'ПИТТСБУРГА', 'Айлендерс': 'АЙЛЕНДЕРС'}


def _shield(league, h):
    """Цветной знак лиги: тёмный щит с белой полосой (из силуэтов league/*_dark.png)."""
    p = os.path.join(HERE, 'league', league.lower() + '_dark.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGBA')
    im = im.crop(im.getbbox())
    a = np.asarray(im.getchannel('A')) > 40
    # всё, что не снаружи силуэта, — тело щита: заливаем снаружи от краёв
    outside = Image.fromarray((~a * 255).astype(np.uint8)).convert('L')
    pad = Image.new('L', (outside.width + 2, outside.height + 2), 255)
    pad.paste(outside, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    body = (np.asarray(pad)[1:-1, 1:-1] != 128)
    rgb = np.zeros(a.shape + (4,), np.uint8)
    rgb[body] = (255, 255, 255, 255)
    rgb[a] = (14, 16, 20, 255)
    sh = Image.fromarray(rgb, 'RGBA')
    # серебряный кант
    edge = Image.fromarray((body * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    out = Image.new('RGBA', sh.size, (0, 0, 0, 0))
    out.paste((190, 196, 204, 255), (0, 0), edge)
    out.alpha_composite(sh)
    k = h / out.height
    return out.resize((int(out.width * k), int(h)), Image.LANCZOS)


def _background(team):
    c = np.array(club(team), np.float32)
    ys = np.linspace(0, 1, H * S, dtype=np.float32)[:, None, None]
    xs = np.linspace(-1, 1, W * S, dtype=np.float32)[None, :, None]
    base = c * (0.62 + 0.5 * ys) * (1 - 0.12 * xs ** 2)                  # тёмный верх → яркий низ
    bg = Image.fromarray(np.clip(np.repeat(base, W * S, axis=1) if base.shape[1] == 1 else base, 0, 255).astype(np.uint8), 'RGB')
    return bg.convert('RGBA'), c


def _giant(bg, team, c):
    """Огромная эмблема тон-в-тон: светлые места — светлее фона, тёмные — темнее; выходит за края."""
    e = poster._raw_emblem(team, int(W * 1.7 * S), int(H * 1.0 * S))
    g = np.asarray(e.convert('L'), np.float32)[..., None] / 255
    al = np.asarray(e.getchannel('A'), np.float32)[..., None] / 255
    tint = np.clip(c * (0.72 + 0.62 * g) + 22 * g, 0, 255)          # оттенки цвета клуба, без ухода в розовый
    lay = np.concatenate([tint, al * 225], axis=2).astype(np.uint8)
    lay = Image.fromarray(lay, 'RGBA').rotate(-8, Image.BICUBIC, expand=True)
    lay = lay.filter(ImageFilter.GaussianBlur(3 * S))                    # эмблема растянута сильно — сглаживаем края
    x = int(W * S * 0.55 - lay.width / 2)
    y = int(H * S * 0.52 - lay.height / 2)
    bg.alpha_composite(lay, (x, y)) if x >= 0 and y >= 0 else _paste_clip(bg, lay, x, y)
    return bg


def _paste_clip(dst, src, x, y):
    x0, y0 = max(0, -x), max(0, -y)
    crop = src.crop((x0, y0, min(src.width, dst.width - x), min(src.height, dst.height - y)))
    dst.alpha_composite(crop, (max(0, x), max(0, y)))


def render(it, path, league='NHL'):
    it = rs._resolve([it], league.upper())[0]
    home, away, sh, sa = it['home'], it['away'], it['sh'], it['sa']
    win = home if sh > sa else away
    bg, c = _background(win)
    bg = _giant(bg, win, c)
    d = ImageDraw.Draw(bg)

    # огромное название победителя сверху, срезано краем
    word = rs._short(win).upper()
    f = fit(word, OSW, 300 * S, (W - 40) * S, 700)
    txt = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    spaced(ImageDraw.Draw(txt), (W * S / 2, 70 * S), word, f, (255, 255, 255, 46), 14 * S)
    bg.alpha_composite(txt)

    # белая карточка
    cw, ch = 800, 380
    x0, y0 = (W - cw) / 2 * S, 780 * S
    card = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((x0, y0, x0 + cw * S, y0 + ch * S), radius=14 * S, fill=(255, 255, 255, 236))
    shadow = card.filter(ImageFilter.GaussianBlur(24 * S))
    sa_ = np.asarray(shadow.getchannel('A'), np.float32) * 0.35
    sh_img = Image.new('RGBA', bg.size, (20, 0, 10, 0))
    sh_img.putalpha(Image.fromarray(sa_.astype(np.uint8)))
    bg.alpha_composite(sh_img, (0, 10 * S))
    bg.alpha_composite(card)
    d = ImageDraw.Draw(bg)

    mid = y0 + 165 * S
    for team, cx in ((home, x0 + 150 * S), (away, x0 + (cw - 150) * S)):
        e = poster._raw_emblem(team, 170 * S, 150 * S)
        poster._shadowed(bg, e, (int(cx - e.width / 2), int(mid - e.height / 2)), blur=6 * S, off=(0, 3 * S), color=(0, 0, 0, 60))
    d = ImageDraw.Draw(bg)
    fs = F(UNB, 104 * S, 800)
    d.text((W * S / 2, mid), '%d - %d' % (sh, sa), font=fs, anchor='mm', fill=(14, 16, 20, 255))
    line = 'ПОБЕДА %s %s' % (GEN.get(win, rs._short(win).upper()), OUTCOME.get(it.get('mark') or '', ''))
    d.text((W * S / 2, y0 + 300 * S), line, font=fit(line, OSW, 46 * S, (cw - 70) * S, 700), anchor='mm', fill=(14, 16, 20, 255))

    sh_logo = _shield(league, 116 * S)
    if sh_logo:
        poster._shadowed(bg, sh_logo, (int(W * S / 2 - sh_logo.width / 2), int(y0 - sh_logo.height * 0.55)),
                         blur=8 * S, off=(0, 4 * S), color=(0, 0, 0, 90))
    d = ImageDraw.Draw(bg)
    spaced(d, (W * S / 2, (H - 90) * S), '@jarvibet', F(UNB, 26 * S, 700), (255, 255, 255, 230), 2 * S)

    out = bg.convert('RGB').resize((W, H), Image.LANCZOS)
    # зернистость: фактура холста + мелкое зерно по фону, на карточке — слабее, чтобы счёт читался чисто
    strong = np.asarray(poster._canvas_texture(out, GRAIN), np.float32)
    soft = np.asarray(poster._canvas_texture(out, GRAIN * 0.3), np.float32)
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle((x0 / S, y0 / S, x0 / S + cw, y0 / S + ch), radius=14, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(2)), np.float32)[..., None] / 255
    out = Image.fromarray(np.clip(strong * (1 - m) + soft * m, 0, 255).astype(np.uint8), 'RGB')
    out.save(path, quality=93, subsampling=0, optimize=True)
    return path
