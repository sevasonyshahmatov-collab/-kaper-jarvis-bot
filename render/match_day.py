"""«МАТЧ ДНЯ» (06.10.2026): постер на один матч по мотивам «День матча» клубов КХЛ.

Портрет 1080×1350 (сохраняется в 2×, см. quality.py). Фон — шёлк в цветах клубов с текстурой холста, как у «Боков».
Сверху «АКБ vs СЕВ» с эмблемами и арена; три вертикальные ячейки: слева хозяева, справа гости (фото игрока или,
если фото нет, эмблема клуба тон-в-тон), в центре — время и короткий текст о матче. Поверх ячеек — «Матч дня»
(заглавная Great Vibes, остальное Playfair Display). Снизу плашка JARVIS | KXL и линия П1 · Х · П2.
Вдоль краёв — подписи ячеек (игрок или клуб и город), как имя игрока на образце.

    import match_day
    match_day.render(dict(home='Ак Барс', away='Северсталь', home_abbr='АКБ', away_abbr='СЕВ',
                          arena='«Татнефть Арена» · Казань', date='среда, 7 октября', time='19:30',
                          odds=(2.05, 4.10, 3.30), text='Короткий текст о матче…',
                          home_photo='akbars.jpg', home_focus=(0.58, 0.36), home_label='Имя Фамилия №10',
                          away_photo=None, away_label='Северсталь · Череповец'), 'out/match_day.jpg', league='KHL')

home_focus / away_focus — где на фото лицо (доли ширины и высоты): по нему фото кадрируется в узкую ячейку.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import poster
import results_styles as rs
from results_styles2 import F, fit, club, spaced, _sticker
from results_ice2 import MANROPE
from ice_more import _emb, _put, DARK, GOLD_T, FOOT_ODDS

S, W = rs.S, rs.W
H = 1350
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
SCRIPT = 'GreatVibes-Regular.ttf'
SERIF = 'PlayfairDisplay-Regular.ttf'
SERIF_I = 'PlayfairDisplay-Italic.ttf'

# ячейки (в точках 1×): слева хозяева, по центру текст, справа гости
TOP, BOT = 214, 1150
CELLS = ((70, 345), (372, 708), (735, 1010))


def _mute(c, k=0.55):
    return tuple(int(v * k) for v in c)


def _silk(w, h, c1, c2, seed, tex=0.8):
    s = poster._canvas_texture(poster._fluid_bg(w, h, c1, c2, seed=seed), tex)
    return s.convert('RGBA')


def _mask(w, h, r_out, side):
    """Скругление как на образце: внешние углы крупные, внутренние — едва заметные."""
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    small = 10 * S
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=small, fill=255)
    if side in ('left', 'right'):
        m2 = Image.new('L', (w, h), 0)
        d2 = ImageDraw.Draw(m2)
        x0 = 0 if side == 'left' else -r_out
        d2.rounded_rectangle((x0, 0, x0 + w + r_out - 1, h - 1), radius=r_out, fill=255)
        m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(m2)))
    return m


def _photo_cell(path, w, h, focus, tint):
    """Фото игрока в узкую ячейку: кадр по лицу, чуть приглушённый цвет и тень снизу (под подписи)."""
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    fx, fy = focus or (0.5, 0.35)
    scale = max(w / im.width, h / im.height) * 1.0
    big = im.resize((max(w, int(im.width * scale)), max(h, int(im.height * scale))), Image.LANCZOS)
    cx, cy = int(fx * big.width), int(fy * big.height)
    x0 = min(max(0, cx - w // 2), big.width - w)
    y0 = min(max(0, cy - int(h * 0.30)), big.height - h)
    crop = big.crop((x0, y0, x0 + w, y0 + h))
    a = np.asarray(crop, np.float32)
    grey = a.mean(axis=2, keepdims=True)
    a = a * 0.72 + grey * 0.28                                           # немного «киношной» приглушённости
    a = a * 0.9 + np.array(tint, np.float32) * 0.1
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = a * (1 - 0.55 * np.clip((yy - 0.62) / 0.38, 0, 1))              # низ темнее
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
    return poster._canvas_texture(out, 0.5).convert('RGBA')


def _emblem_cell(team, w, h, seed):
    """Без фото: шёлк в цвете клуба, огромная эмблема тон-в-тон и та же эмблема наклейкой."""
    c = club(team)
    cell = _silk(w, h, _mute(c, 0.78), _mute(c, 0.36), seed)
    e = _emb(team, int(h * 0.62))
    ghost = e.convert('LA').convert('RGBA')
    ghost.putalpha(e.getchannel('A').point(lambda v: int(v * 0.16)))
    cell.alpha_composite(ghost, (int(w / 2 - ghost.width / 2), int(h * 0.56 - ghost.height / 2)))
    e2 = _sticker(_emb(team, int(min(w * 0.62, h * 0.22))), 5 * S)
    poster._shadowed(cell, e2, (int(w / 2 - e2.width / 2), int(h * 0.30 - e2.height / 2)), blur=14 * S, off=(0, 6 * S), color=(0, 0, 0, 120))
    return cell


def _vertical(ov, text, x, y, font, fill, up=True):
    """Подпись вдоль края (как имя игрока на образце): снизу вверх слева, сверху вниз справа."""
    w = int(font.getlength(text)) + 8 * S
    t = Image.new('RGBA', (w, int(font.size * 1.5)), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((4 * S, t.height / 2), text, font=font, anchor='lm', fill=fill)
    t = t.rotate(90 if up else -90, expand=True, resample=Image.BICUBIC)
    ov.alpha_composite(t, (int(x - t.width / 2), int(y - t.height / 2)))


def _wrap(text, font, max_w):
    lines, cur = [], ''
    for word in str(text).split():
        nxt = (cur + ' ' + word).strip()
        if font.getlength(nxt) <= max_w or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _title(ov, cx, cy, k=1.0):
    """«Матч дня»: рукописная «М» и антиква, вторая строка со сдвигом — как «День матча» на образце."""
    fc = F(SCRIPT, int(250 * k) * S)
    fr = F(SERIF, int(118 * k) * S)
    lay = Image.new('RGBA', ov.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    wm, wa, wd = fc.getlength('М'), fr.getlength('атч'), fr.getlength('дня')
    total = wm * 0.96 + wa
    x0 = cx * S - total / 2
    d.text((x0, cy * S + 12 * S * k), 'М', font=fc, anchor='ls', fill=(255, 255, 255, 255))
    d.text((x0 + wm * 0.96, cy * S), 'атч', font=fr, anchor='ls', fill=(255, 255, 255, 255))
    d.text((x0 + wm * 0.62, cy * S + 104 * S * k), 'дня', font=fr, anchor='ls', fill=(255, 255, 255, 255))
    sh = lay.getchannel('A').filter(ImageFilter.GaussianBlur(14 * S))
    shadow = Image.new('RGBA', ov.size, (0, 0, 0, 0))
    shadow.putalpha(sh.point(lambda v: int(v * 0.55)))
    ov.alpha_composite(shadow)
    ov.alpha_composite(lay)


def render(m, path, league='KHL'):
    league = league.upper()
    home, away = m['home'], m['away']
    ch, ca = club(home), club(away)
    seed = sum(map(ord, home + away)) % 997
    # фон: шёлк в цветах клубов, приглушённый и затемнённый к краям
    bg = _silk(W, H, _mute(ch, 0.62), _mute(ca, 0.62), seed, tex=0.9)
    a = np.asarray(bg, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = 1 - 0.45 * np.clip(np.sqrt(((xx / W - 0.5) * 1.2) ** 2 + ((yy / H - 0.5) * 1.0) ** 2) - 0.25, 0, 1)
    a[..., :3] *= vign[..., None]
    bg = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')

    ov = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # шапка: эмблема  АКБ  vs  СЕВ  эмблема, ниже арена
    fa = F(SERIF, 54 * S)
    fv = F(SERIF_I, 26 * S)
    ha, aa = m.get('home_abbr', rs._short(home)[:3].upper()), m.get('away_abbr', rs._short(away)[:3].upper())
    gap = 26 * S
    wh, wv, wa = fa.getlength(ha), fv.getlength('vs'), fa.getlength(aa)
    cx, ty = W * S / 2, 92 * S
    d.text((cx - wv / 2 - gap, ty), ha, font=fa, anchor='rm', fill=(255, 255, 255, 255))
    d.text((cx, ty + 4 * S), 'vs', font=fv, anchor='mm', fill=(255, 255, 255, 210))
    d.text((cx + wv / 2 + gap, ty), aa, font=fa, anchor='lm', fill=(255, 255, 255, 255))
    es = 64 * S
    for team, x in ((home, cx - wv / 2 - gap - wh - 22 * S - es / 2), (away, cx + wv / 2 + gap + wa + 22 * S + es / 2)):
        _put(ov, _emb(team, es), x, ty, blur=6)
    d = ImageDraw.Draw(ov)
    if m.get('arena'):
        spaced(d, (cx, 150 * S), m['arena'].upper(), F(MANROPE, 15 * S, 700), (255, 255, 255, 215), 2 * S)

    # ячейки
    h = (BOT - TOP) * S
    for i, (x0, x1) in enumerate(CELLS):
        w = (x1 - x0) * S
        side = ('left', 'center', 'right')[i]
        if side == 'center':
            cell = _silk(w, h, _mute(ch, 0.30), _mute(ca, 0.30), seed + 7)
            dark = Image.new('RGBA', (w, h), DARK + (110,))
            cell.alpha_composite(dark)
        else:
            team = home if side == 'left' else away
            ph, focus = m.get(side_key(side) + '_photo'), m.get(side_key(side) + '_focus')
            cell = _photo_cell(ph, w, h, focus, club(team)) if ph else _emblem_cell(team, w, h, seed + i)
        cell.putalpha(Image.fromarray(np.minimum(np.asarray(cell.getchannel('A')), np.asarray(_mask(w, h, 130 * S, side)))))
        poster._shadowed(ov, cell, (x0 * S, TOP * S), blur=18 * S, off=(0, 8 * S), color=(0, 0, 0, 130))
    d = ImageDraw.Draw(ov)

    # центр: дата и время сверху, текст о матче снизу (под заголовком)
    c0, c1 = CELLS[1]
    ccx = (c0 + c1) / 2 * S
    if m.get('date'):
        spaced(d, (ccx, 262 * S), m['date'].upper(), F(MANROPE, 14 * S, 800), (255, 255, 255, 200), 3 * S)
    if m.get('time'):
        d.text((ccx, 336 * S), m['time'], font=F(SERIF, 76 * S), anchor='mm', fill=(255, 255, 255, 255))
        spaced(d, (ccx, 398 * S), 'МСК', F(MANROPE, 14 * S, 800), GOLD_T + (255,), 4 * S)
    if m.get('text'):
        ft = F(MANROPE, 17 * S, 600)
        lines = _wrap(m['text'], ft, (c1 - c0 - 44) * S)[:9]
        lh = 26 * S
        y = 858 * S
        for ln in lines:
            d.text((ccx, y), ln, font=ft, anchor='mm', fill=(255, 255, 255, 228))
            y += lh

    # «Матч дня» поверх ячеек
    _title(ov, W / 2 + 18, 660)
    d = ImageDraw.Draw(ov)

    # подписи вдоль краёв
    fl = F(SERIF_I, 19 * S)
    _vertical(ov, m.get('home_label') or (home + ' · ' + m.get('home_city', '')).strip(' ·'), 38 * S, (TOP + BOT) / 2 * S, fl, (255, 255, 255, 215), up=True)
    _vertical(ov, m.get('away_label') or (away + ' · ' + m.get('away_city', '')).strip(' ·'), (W - 38) * S, (TOP + BOT) / 2 * S, fl, (255, 255, 255, 215), up=False)
    d = ImageDraw.Draw(ov)

    # низ: плашка бренда (вместо логотипа букмекера) и линия
    fb = poster._f7('brand', 20 * S) if hasattr(poster, '_f7') else F(MANROPE, 20 * S, 800)
    tag = rs.TAG[league]
    sp = 2.4 * S
    w1 = sum(fb.getlength(ch_) for ch_ in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(ch_) for ch_ in tag) + sp * (len(tag) - 1)
    bar = 16 * S
    pw = w1 + 2 * bar + w2 + 44 * S
    py = 1196 * S
    d.rounded_rectangle((cx - pw / 2, py - 22 * S, cx + pw / 2, py + 22 * S), radius=22 * S, outline=(255, 255, 255, 235), width=3 * S)
    x = cx - (w1 + 2 * bar + w2) / 2
    poster._spaced(d, (x, py), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x + w1 + bar - 1.5 * S, py - 11 * S, x + w1 + bar + 1.5 * S, py + 11 * S), radius=S, fill=(255, 255, 255, 140))
    poster._spaced(d, (x + w1 + 2 * bar, py), tag, fb, rs.ACCENT[league] + (255,), sp)
    if m.get('odds'):
        fo, fl2 = F(MANROPE, 22 * S, 800), F(MANROPE, 13 * S, 800)
        for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), m['odds'])):
            xx = cx + (k - 1) * 130 * S
            d.text((xx - 8 * S, 1256 * S), lab, font=fl2, anchor='rm', fill=(255, 255, 255, 150))
            d.text((xx - 2 * S, 1256 * S), '%.2f' % v, font=fo, anchor='lm', fill=(255, 255, 255, 255))
        d.text((cx, 1300 * S), FOOT_ODDS.lower(), font=F(MANROPE, 12 * S, 600), anchor='mm', fill=(255, 255, 255, 130))
    return rs._finish(bg, ov, H, path, grain=0.15)


def side_key(side):
    return 'home' if side == 'left' else 'away'
