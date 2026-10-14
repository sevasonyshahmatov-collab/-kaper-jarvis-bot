# -*- coding: utf-8 -*-
"""«Граффити» — прогноз как стрит-арт: ночная бетонная стена под натриевым фонарём, краска из баллона на доли трека.

Стена — литой бетон: панели со швами, отверстия от стяжек опалубки, потёки, старые закраски серым и выцветшие
чужие теги; сверху светят оранжевые натриевые фонари (свет общий для стены и краски), снизу тротуар. Вся краска
ложится «распылением»: край с крапом, облачко перепыла клубного цвета, через долю-две из нижних краёв букв
бегут и замедляются потёки. Наклейки и плакаты «шлёпаются» на стену (удар, тень), трафареты — с перемычками.
Камера едет вдоль стены (интро → хозяева → гости) на долю, с размазом.

Сцены (u — доля трека; все склейки и акценты — на долях от self.drop; доли — reels_cfg/graffiti.json):
  интро (до b(−team−team2−buff)) — бирка JARVIS | NHL, обе эмблемы распылением (по доле), названия клубов
            «бомбингом» в цветах клубов, между ними VS, трафаретом день и время МСК, затем на полдоли три наклейки
            П1 · Х · П2 с кэфами основного времени крупно;
  хозяева (team долей, ~6 с) — камера переезжает к следующему куску стены: эмблема и имя клуба, плакат-вклейка
            с последними 3 играми (строка на полдоли: В/П, соперник, дата, дома/в гостях, счёт, ОТ/Б), под ним
            крупные цифры баллоном на четверти доли — очки, матчи, место, разница шайб; ниже маркером — заброшенные
            и пропущенные, серия (от двух подряд) или домашний/выездной итог (пустые поля не показываются);
  гости (team2 долей) — то же на следующем куске стены;
  закраска (buff долей) — фонарь мигает, валики серой краской закатывают стену полосами — ровно к дропу;
  ДРОП (hold долей, ~4 с) — на чистой серой стене взрывом распыляется большая цветная работа только выбранной
            команды: облако и брызги, одна эмблема, «ПОБЕДА …» объёмными буквами, трафаретом «В ОСНОВНОЕ ВРЕМЯ»
            (form.split_pick); через полдоли — наклейка с кэфом; на доли — пульс и блеск звёздочек, текут потёки;
  финал (cta долей) — поверх низа шлёпается плашка Telegram (C.tg_plate, текст по центру плашки).
lag — на сколько долей настоящий удар трека позже точки дропа сборки (vvs, участок 98,69 с: удар баса 99,58 с —
1,33 доли): видимый дроп self.drop = drop + lag·u, работа встаёт точно на удар.
@jarvibet — у низа безопасной зоны (y 1440) одинаково во всех сценах до плашки Telegram.
Кадр — чистая функция t: стена, свет, спрайты, поля распыления и потёки готовятся один раз (кеш модуля, общий
для процессов после fork), в кадре — только вырезка, маски проявления и наложение.
"""
import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

C.FONTS.setdefault('pango', 'Pangolin-Regular.ttf')         # «маркер» (кириллица есть)

M = 40                                    # запас стены на тряску и дрейф камеры
WW, WH = 3 * W + 2 * M, H + 2 * M
SEG = {'i': 0, 'h': 1, 'a': 2, 'p': 2}
HANDLE_Y = 1440
INK = (24, 24, 26)
PAPER = (236, 230, 214)
WHITE = (246, 244, 238)
BUFF = (124, 122, 118)

_CACHE = {}


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def streak_txt(s):
    """«П2» → «2 ПОРАЖЕНИЯ ПОДРЯД» (серии от двух); иначе пусто."""
    s = str(s or '').strip().upper()
    if len(s) < 2 or not s[1:].isdigit():
        return ''
    n = int(s[1:])
    if n < 2:
        return ''
    if s[0] in ('В', 'W'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'))
    if s[0] in ('П', 'L'):
        return '%d %s ПОДРЯД' % (n, plural(n, 'ПОРАЖЕНИЕ', 'ПОРАЖЕНИЯ', 'ПОРАЖЕНИЙ'))
    return ''


def venue_txt(rec):
    """Итог дома (если сегодня дома) или в гостях: «В ГОСТЯХ: 1 ПОБЕДА ИЗ 3» из записи «В-П-ПО»."""
    home = rec.get('home_today')
    r = rec.get('home_rec') if home else rec.get('road_rec') if home is not None else None
    try:
        w, l, o = [int(x) for x in str(r).split('-')[:3]]
    except Exception:
        return ''
    n = w + l + o
    if n <= 0:
        return ''
    return '%s: %d %s ИЗ %d' % ('ДОМА' if home else 'В ГОСТЯХ', w, plural(w, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), n)


def _lowfreq(rng, shape, cell, amp=1.0):
    """Плавный шум: случайная сетка с шагом cell, растянутая бикубически → float32 shape."""
    h, w = shape
    sm = rng.normal(0, 1, (h // cell + 3, w // cell + 3)).astype(np.float32)
    im = Image.fromarray(sm, 'F').resize((w + 2 * cell, h + 2 * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[cell:cell + h, cell:cell + w] * amp


def dilate(m, r):
    """Расширить маску L на ~r пикселей (размытие + порог, края мягкие)."""
    if r <= 0:
        return m
    b = m.filter(ImageFilter.GaussianBlur(r / 1.25))
    return b.point(lambda v: 255 if v > 30 else int(v * 255 / 30))


def shift(m, dx, dy):
    out = Image.new(m.mode, m.size, 0)
    out.paste(m, (int(dx), int(dy)))
    return out


def solid(size, col, mask):
    im = Image.new('RGBA', size, tuple(col)[:3] + (255,))
    im.putalpha(mask)
    return im


def lighten(c, k):
    return C.mix(c, (255, 255, 255), k)


def darken(c, k):
    return C.mix(c, (0, 0, 0), k)


def paint_col(c):
    """Клубный цвет как краска на тёмной стене: не темнее середины."""
    lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    return lighten(c, 0.45) if lum < 70 else lighten(c, 0.2) if lum < 110 else tuple(c)


# ─────────────────────────────── буквы ───────────────────────────────
def letters_mask(s, font, size, jitter, rng, track=-0.02):
    """Строка как маска L: каждая буква со своим наклоном/подскоком/масштабом (живой «граффити»-ритм)."""
    f = C.font(font, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.3)
    hh = asc + desc + 2 * pad
    xs, ims = [], []
    x = pad
    for ch in s:
        if ch == ' ':
            x += int(size * 0.32)
            continue
        g = Image.new('L', (int(f.getlength(ch)) + 2 * pad, hh), 0)
        ImageDraw.Draw(g).text((pad, pad), ch, font=f, fill=255)
        rot = rng.uniform(-6, 6) * jitter
        sc = 1 + rng.uniform(-0.05, 0.07) * jitter
        dy = rng.uniform(-0.07, 0.07) * size * jitter
        if abs(sc - 1) > 0.005:
            g = g.resize((max(1, int(g.width * sc)), max(1, int(g.height * sc))), Image.BICUBIC)
        if abs(rot) > 0.1:
            g = g.rotate(rot, Image.BICUBIC, expand=False)
        adv = f.getlength(ch) * sc
        xs.append((x - pad * sc, (hh - g.height) / 2 + dy))
        ims.append(g)
        x += adv + track * size
    wtot = int(x + pad)
    out = Image.new('L', (wtot, hh), 0)
    for (px, py), g in zip(xs, ims):
        tmp = Image.new('L', out.size, 0)
        tmp.paste(g, (int(px), int(py)))
        out = ImageChops.lighter(out, tmp)
    bb = out.getbbox()
    return out.crop(bb) if bb else out


def piece(rows, font='dela', sizes=(150,), max_w=1000, jitter=1.0, seed=1, fill=((255, 220, 90), (230, 140, 20)),
          ext_col=(30, 20, 40), ext=14, out1=6, out2=9, out2_col=WHITE, band=True, gap=-0.06, shine=True):
    """Объёмные буквы «как кусок граффити»: заливка градиентом с волнистой полосой, чёрный контур, объём (экструзия
    вниз-вправо), внешний светлый контур и тонкий чёрный кант; строки сливаются в одну работу. → RGBA."""
    rng = random.Random(seed)
    ms = []
    for k, s in enumerate(rows):
        sz = sizes[min(k, len(sizes) - 1)]
        m = letters_mask(s, font, sz, jitter, rng)
        if m.width > max_w:
            m = m.resize((int(max_w), max(1, int(m.height * max_w / m.width))), Image.LANCZOS)
        ms.append(m)
    P = out1 + out2 + ext + 10
    wmax = max(m.width for m in ms)
    hs = [m.height for m in ms]
    g = int(gap * max(hs))
    htot = sum(hs) + g * (len(ms) - 1)
    S = (wmax + 2 * P, htot + 2 * P)
    M0 = Image.new('L', S, 0)
    y = P
    row_spans = []
    for m in ms:
        tmp = Image.new('L', S, 0)
        tmp.paste(m, (P + (wmax - m.width) // 2, y))
        M0 = ImageChops.lighter(M0, tmp)
        row_spans.append((y, y + m.height))
        y += m.height + g
    D1 = dilate(M0, out1)
    E = D1.copy()
    for k in range(1, ext + 1):
        E = ImageChops.lighter(E, shift(D1, k * 0.8, k))
    D2 = dilate(E, out2) if out2 else E
    D3 = dilate(D2, 3)
    out = Image.new('RGBA', S, (0, 0, 0, 0))
    out.alpha_composite(solid(S, INK, D3))
    if out2:
        out.alpha_composite(solid(S, out2_col, D2))
    ext_img = C.vgrad(S[0], S[1], [(0, lighten(ext_col, 0.15)), (1, darken(ext_col, 0.35))]).convert('RGBA')
    ext_img.putalpha(E)
    out.alpha_composite(ext_img)
    out.alpha_composite(solid(S, INK, D1))
    # заливка: по строкам градиент сверху вниз + волнистая светлая полоса
    c_top, c_bot = fill
    arr = np.zeros((S[1], S[0], 3), np.float32)
    yy = np.arange(S[1], dtype=np.float32)[:, None]
    xx = np.arange(S[0], dtype=np.float32)[None, :]
    for (y0, y1) in row_spans:
        k = np.clip((yy - y0) / max(1, y1 - y0), 0, 1)
        sl = slice(max(0, y0 - 4), min(S[1], y1 + 4))
        kk = k[sl]
        col = np.array(c_top, np.float32) * (1 - kk[..., None]) + np.array(c_bot, np.float32) * kk[..., None]
        if band:
            wave = 0.58 + 0.05 * np.sin(xx / 46.0 + y0)
            bd = np.clip(1 - np.abs(kk - wave) / 0.05, 0, 1)[..., None]
            col = col * (1 - 0.55 * bd) + 255 * 0.55 * bd
        arr[sl] = np.broadcast_to(col, (sl.stop - sl.start, S[0], 3))
    fill_im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    fill_im.putalpha(M0)
    out.alpha_composite(fill_im)
    if shine:                                                # блик по верхне-левой кромке букв
        rim = ImageChops.subtract(M0, shift(M0, 5, 6)).filter(ImageFilter.GaussianBlur(1.2))
        out.alpha_composite(solid(S, (255, 255, 255), rim.point(lambda v: v * 190 // 255)))
        dk = ImageChops.subtract(M0, shift(M0, -4, -5)).filter(ImageFilter.GaussianBlur(1.2))
        out.alpha_composite(solid(S, (0, 0, 0), dk.point(lambda v: v * 70 // 255)))
    return out


def stencil(s, size, col=WHITE, max_w=None, font='rmono', seed=3, cut=True):
    """Трафарет: буквы с перемычкой (разрез посередине), мягкий край распыления и крап вокруг. → RGBA."""
    im = C.text(s, font, size, col, max_w=max_w)
    pad = 12
    a = np.zeros((im.height + 2 * pad, im.width + 2 * pad), np.uint8)
    a[pad:pad + im.height, pad:pad + im.width] = np.asarray(im.getchannel('A'))
    if cut:
        rows = np.where(a.max(1) > 128)[0]
        if len(rows):
            y0, y1 = rows[0], rows[-1]
            yc = int(y0 + (y1 - y0) * 0.5)
            hw = max(2, int((y1 - y0) * 0.05))
            a[yc - hw // 2:yc - hw // 2 + hw] = 0
    m = Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.9))
    rng = np.random.default_rng(seed)
    near = np.asarray(dilate(m, 7)) > 40
    spk = (rng.random(a.shape) > 0.975) & near & (a < 30)
    am = np.maximum(np.asarray(m), (spk * rng.integers(70, 190, a.shape)).astype(np.uint8))
    out = Image.new('RGBA', (a.shape[1], a.shape[0]), tuple(col)[:3] + (255,))
    out.putalpha(Image.fromarray(am))
    return out


def marker(s, size, col=WHITE, max_w=None):
    """Надпись маркером (Pangolin) с тёмной подложкой для читаемости. → RGBA."""
    t = C.text(s, 'pango', size, col, 400, max_w=max_w, stroke=max(2, size // 22), stroke_fill=(20, 20, 22))
    return C.with_shadow(t, 6, 0.55, 3)


def sticker(w, h, r, fill, border=WHITE, bw=8):
    """Наклейка: белая вырубка, внутри — заливка. → RGBA."""
    im = C.rrect(w, h, r, border)
    C.put(im, C.rrect(w - 2 * bw, h - 2 * bw, max(2, r - bw), fill), w / 2, h / 2)
    return im


def slap_ready(im, rot, sh=12, sa=0.5, dy=8):
    """Повернуть наклейку и подложить тень."""
    im = C.rotate(im, rot)
    return C.with_shadow(im, sh, sa, dy)


def star4(d, col=(255, 255, 255)):
    """Четырёхлучевая искра."""
    S = d * 3
    im = Image.new('L', (S, S), 0)
    dr = ImageDraw.Draw(im)
    c = S / 2
    r1, r2 = S / 2 - 2, S * 0.07
    pts = []
    for k in range(8):
        ang = math.pi / 4 * k - math.pi / 2
        r = r1 if k % 2 == 0 else r2
        pts.append((c + r * math.cos(ang), c + r * math.sin(ang)))
    dr.polygon(pts, fill=255)
    m = im.resize((d, d), Image.LANCZOS)
    out = solid((d, d), col, m)
    return C.glow(out, max(3, d // 10), 1.3, (255, 255, 255))


# ─────────────────────────────── распыление и потёки ───────────────────────────────
class Spray:
    """Поле проявления спрайта: порядок O (направление + шум) и крап R. reveal(p) → RGBA с маской."""

    def __init__(self, im, mode='lr', seed=1, soft=0.10):
        self.im = im
        self.soft = soft
        w, h = im.size
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if mode == 'rad':
            d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
            o = d / max(1e-3, d.max())
        elif mode == 'diag':
            o = (xx / w * 0.75 + yy / h * 0.25)
        else:
            o = xx / max(1, w - 1) * 0.86 + (yy / max(1, h - 1)) * 0.14
        o = o + _lowfreq(rng, (h, w), 22, 0.09) + rng.normal(0, 0.025, (h, w)).astype(np.float32)
        o = (o - o.min()) / max(1e-3, o.max() - o.min())
        self.O = o.astype(np.float32)
        self.R = rng.random((h, w), dtype=np.float32)
        self.A = np.asarray(im.getchannel('A'), np.float32)

    def reveal(self, p):
        if p >= 1:
            return self.im
        if p <= 0:
            return None
        s = self.soft
        edge = p * (1 + s)
        m = np.clip((edge - self.O) / s, 0, 1)
        ahead = (self.O > edge) & (self.O < edge + 0.09) & (self.R > 0.955)
        m = np.maximum(m, ahead * 0.85)
        out = self.im.copy()
        out.putalpha(Image.fromarray((self.A * m).astype(np.uint8)))
        return out


def drips_for(im, n, rng, scale=1.0, lmin=40, lmax=150, wmin=8, wmax=12, cols=None):
    """Потёки из нижних краёв непрозрачной части: [(x, y, w, L, col, delay, grow)] в координатах спрайта."""
    a = np.asarray(im.getchannel('A'))
    rgb = np.asarray(im.convert('RGB'))
    h, w = a.shape
    cand = np.argwhere((a[:-6] > 220) & (a[6:] < 20))
    if len(cand) == 0 or n <= 0:
        return []
    out, used = [], []
    tries = 0
    while len(out) < n and tries < 400:
        tries += 1
        y, x = cand[rng.integers(0, len(cand))]
        if x < 8 or x > w - 8 or any(abs(x - u_) < 34 * scale for u_ in used):
            continue
        used.append(x)
        col = tuple(int(v) for v in rgb[max(0, y - 6), x]) if cols is None else cols[rng.integers(0, len(cols))]
        if sum(col) < 60:
            continue
        ww = rng.uniform(wmin, wmax) * scale
        out.append((int(x), int(y), ww, rng.uniform(lmin, lmax) * scale, col, rng.uniform(0.0, 0.5),
                    rng.uniform(1.6, 3.0)))
    return out


def drip_sprite(w, L, col):
    """Потёк длиной L: тело + капля на конце (сглажено) → (тело RGBA, капля RGBA)."""
    ss = 3
    wi = max(2, int(round(w)))
    body = Image.new('RGBA', (wi * ss, int(L) * ss + 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rectangle((0, 0, wi * ss - 1, body.height), fill=tuple(col) + (255,))
    d.rectangle((0, 0, max(1, wi * ss // 4), body.height), fill=lighten(col, 0.25) + (255,))
    body = body.resize((wi, max(1, int(L))), Image.LANCZOS)
    tw, th = int(wi * 1.5) + 2, int(wi * 1.8) + 2
    tip = Image.new('RGBA', (tw * ss, th * ss), (0, 0, 0, 0))
    ImageDraw.Draw(tip).ellipse((0, 0, tw * ss - 1, th * ss - 1), fill=tuple(col) + (255,))
    ImageDraw.Draw(tip).ellipse((tw * ss * 0.2, th * ss * 0.15, tw * ss * 0.45, th * ss * 0.45), fill=lighten(col, 0.5) + (255,))
    tip = tip.resize((tw, th), Image.LANCZOS)
    return body, tip


# ─────────────────────────────── ролик ───────────────────────────────
class Graffiti(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 90, drop=24 * 60 / 90, line=None, team=9,
                 team2=8, buff=2, hold=6, cta=3.5, lag=0.0, seed=23, **kw):
        super().__init__(u, drop + lag * u, seed)
        self.line = tuple(line) if line else None
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.T1 = self.b(-(team + team2 + buff))
        self.T2 = self.b(-(team2 + buff))
        self.TB = self.b(-buff)
        self.buff_beats = buff
        if self.T1 < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = round(self.T1 - 0.35, 2)
        self.col = {'h': paint_col(fresh.club(self.h)), 'a': paint_col(fresh.club(self.a))}
        if sum((p - q) ** 2 for p, q in zip(self.col['h'], self.col['a'])) ** 0.5 < 90:
            alt = [c for c in (self.a.c0, self.a.c2, self.a.c1) if (max(c) - min(c)) > 50]
            if alt:
                self.col['a'] = paint_col(tuple(alt[-1]))
        self.key = (home, away, league, when, pick, coef, self.line, seed, round(u, 4), round(self.drop, 3), team, team2, buff)
        if self.key not in _CACHE:
            _CACHE[self.key] = self._build()
        self.G = _CACHE[self.key]

    # ── стена, свет, закраска ──
    def _wall(self):
        rng = np.random.default_rng(self.seed)
        sh = (WH, WW)
        base = 104 + _lowfreq(rng, sh, 260, 9) + _lowfreq(rng, sh, 70, 6) + _lowfreq(rng, sh, 14, 4)
        base += rng.normal(0, 5.5, sh).astype(np.float32)
        pits = rng.random(sh, dtype=np.float32) > 0.9985                              # раковины бетона
        base -= pits * 30
        # швы панелей и отверстия стяжек
        pw = 720
        for x in range(M + 300, WW, pw):
            base[:, x - 3:x + 2] -= 26
            base[:, x + 2:x + 4] += 10
        for y in (M + 196, M + 1560):
            base[y - 3:y + 2] -= 26
            base[y + 2:y + 4] += 10
        ly, lx = np.mgrid[-12:12, -12:12].astype(np.float32)
        dd = np.sqrt(ly ** 2 + lx ** 2)
        hole = -np.clip(9 - dd, 0, 1) * 46 + np.clip(1 - np.abs(dd - 10), 0, 1) * 12
        for x0 in range(M + 300 - pw, WW, pw):
            for cx in (x0 + 180, x0 + 540):
                for cy in (M + 420, M + 980, M + 1500):
                    if 12 <= cx < WW - 12:
                        base[cy - 12:cy + 12, cx - 12:cx + 12] += hole
        # потёки сверху вниз от швов
        streak = np.zeros(sh, np.float32)
        for _ in range(26):
            x = int(rng.uniform(0, WW))
            w = int(rng.uniform(14, 60))
            L = rng.uniform(300, 1300)
            y0 = int(rng.choice([M + 196, M]))
            ys = np.arange(WH, dtype=np.float32)
            prof = np.clip(1 - (ys - y0) / L, 0, 1) * (ys > y0)
            streak[:, max(0, x):min(WW, x + w)] += prof[:, None] * rng.uniform(6, 16)
        r = 6                                                                        # смягчить края по x
        cs = np.cumsum(np.pad(streak, ((0, 0), (r + 1, r))), 1, dtype=np.float32)
        streak = (cs[:, 2 * r + 1:] - cs[:, :-2 * r - 1]) / (2 * r + 1)
        base -= streak
        rgb = np.stack([base * 1.0, base * 0.985, base * 0.95], -1)
        # старые закраски (прямоугольники ровного серого) и выцветшие теги
        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for _ in range(9):
            x, y = rng.uniform(0, WW), rng.uniform(M + 200, M + 1450)
            w, h = rng.uniform(260, 620), rng.uniform(150, 420)
            g = int(rng.uniform(92, 128))
            d.rectangle((x, y, x + w, y + h), fill=(g, g - 1, g - 4, int(rng.uniform(70, 140))))
        lay = lay.filter(ImageFilter.GaussianBlur(1.5))
        img.alpha_composite(lay)
        tags = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(tags)
        pal = [(170, 60, 70), (60, 110, 170), (200, 200, 200), (70, 150, 90), (190, 150, 60), (30, 30, 30)]
        for _ in range(34):
            x, y = rng.uniform(0, WW), rng.uniform(M + 220, M + 1480)
            col = pal[int(rng.integers(0, len(pal)))]
            a = int(rng.uniform(30, 62))
            wd = int(rng.uniform(5, 11))
            pts = [(x, y)]
            ang = rng.uniform(-0.6, 0.6)
            for _k in range(int(rng.integers(5, 11))):
                ang += rng.uniform(-1.9, 1.9)
                st = rng.uniform(30, 90)
                x, y = x + math.cos(ang) * st, y + math.sin(ang) * st * 0.8
                pts.append((x, y))
            d.line(pts, fill=col + (a,), width=wd, joint='curve')
        tags = tags.filter(ImageFilter.GaussianBlur(1.6))
        img.alpha_composite(tags)
        arr = np.asarray(img.convert('RGB')).copy()
        # тротуар внизу (в зоне интерфейса площадки)
        gy = M + 1610
        arr[gy:] = (np.asarray(C.vgrad(WW, WH - gy, [(0, (66, 64, 62)), (0.08, (40, 40, 42)), (1, (22, 22, 26))])))
        arr[gy:gy + 6] = (130, 126, 118)
        return arr

    def _light(self):
        """Свет: натриевые фонари над серединой каждого куска стены + холодная подсветка. → uint16 (×128, не больше 2)."""
        yy = np.arange(WH, dtype=np.float32)[:, None] - M
        xx = np.arange(WW, dtype=np.float32)[None, :] - M
        dx = np.abs(((xx - W / 2) + W / 2) % W - W / 2)
        warm = np.exp(-((dx / 780.0) ** 2) - (((yy + 120) / 1650.0) ** 2))
        hot = np.exp(-((dx / 240.0) ** 2) - (((yy + 60) / 260.0) ** 2))
        amb = np.array([0.42, 0.46, 0.60], np.float32)
        sod = np.array([0.98, 0.74, 0.40], np.float32)
        lm = amb + warm[..., None] * sod + hot[..., None] * np.array([0.32, 0.22, 0.08], np.float32)
        vy = np.clip((yy - 1500) / 420.0, 0, 1)[..., None]                           # низ (тротуар) темнее
        lm = lm * (1 - 0.35 * vy)
        return np.clip(lm * 128, 0, 255).astype(np.uint16)

    def _buff_tex(self):
        rng = np.random.default_rng(self.seed + 5)
        hh, ww = WH, W + 2 * M
        streak = _lowfreq(rng, (hh // 40 + 4, ww), 3, 1.0)
        streak = np.asarray(Image.fromarray(streak, 'F').resize((ww, hh), Image.BICUBIC), np.float32) * 1.2
        base = (BUFF[0] + streak + _lowfreq(rng, (hh, ww), 120, 3.0) + _lowfreq(rng, (hh, ww), 26, 2.0)
                + rng.normal(0, 3.5, (hh, ww)).astype(np.float32))
        bw = W / 4
        for k in range(5):                                       # полосы валика — чуть разного тона
            x0 = int(M + k * bw - 10)
            base[:, max(0, x0):min(ww, int(x0 + bw + 20))] += (k % 2) * 2.5 - 1
            base[:, max(0, x0 - 3):max(0, x0 + 3)] -= 4
        rgb = np.stack([base, base * 0.985, base * 0.955], -1)
        return np.clip(rgb, 0, 255).astype(np.uint8)

    def _roller(self, bw):
        ww, hh = int(bw + 26), 300
        im = Image.new('RGBA', (ww, hh), (0, 0, 0, 0))
        cyl = C.vgrad(ww - 20, 60, [(0, (150, 148, 144)), (0.35, (186, 184, 180)), (0.7, (118, 116, 112)), (1, (70, 70, 72))])
        cyl = cyl.convert('RGBA')
        cyl.putalpha(C.rrect(ww - 20, 60, 22, (255, 255, 255)).getchannel('A'))
        C.put(im, cyl, 0, 0, anchor='tl')
        d = ImageDraw.Draw(im)
        d.line([(ww - 22, 30), (ww - 6, 30), (ww - 6, 110), (ww / 2 + 10, 150), (ww / 2 + 10, 300)], fill=(150, 154, 160, 255), width=7,
               joint='curve')
        d.rectangle((ww / 2 + 2, 170, ww / 2 + 18, 300), fill=(40, 42, 48, 255))
        return C.with_shadow(im, 10, 0.5, 10)

    # ── спрайты ──
    def _el(self, E, seg, spr, cx, cy, t0, kind='spray', dur=None, mode='lr', drips=0, haze=None, seed=0, end=None,
            drip_scale=1.0, drip_cols=None, lmax=150, lmin=40):
        e = dict(seg=seg, spr=spr, cx=cx, cy=cy, t0=t0, kind=kind, dur=dur if dur is not None else 0.32 * self.u, end=end)
        if kind == 'spray':
            e['sp'] = Spray(spr, mode, seed=self.seed * 31 + seed)
            if haze:
                big = Image.new('RGBA', (spr.width + 80, spr.height + 80), (0, 0, 0, 0))
                big.alpha_composite(C.tint(spr, haze), (40, 40))
                big = big.filter(ImageFilter.GaussianBlur(16))
                big.putalpha(big.getchannel('A').point(lambda v: int(v * 0.42)))
                e['haze'] = big
            if drips:
                rng = np.random.default_rng(self.seed * 7 + seed)
                ds = []
                for (x, y, w, L, col, dl, gr) in drips_for(spr, drips, rng, drip_scale, cols=drip_cols, lmax=lmax, lmin=min(lmin, lmax * 0.6)):
                    body, tip = drip_sprite(w, L, col)
                    ds.append((x - spr.width / 2, y - spr.height / 2, body, tip, dl, gr))
                e['drips'] = ds
        E.append(e)
        return e

    def _intro(self, E):
        u, T0 = self.u, 0.0
        b0 = self.b(math.ceil((0 - self.drop) / u + 0.2))                        # первая доля после старта
        tg = slap_ready(sticker(330, 74, 16, INK), -3, 8, 0.5, 6)
        C.put(tg, stencil(self.tag, 34, WHITE, 270, cut=False), tg.width / 2, tg.height / 2 - 3)
        self._el(E, 'i', tg, 540, 292, b0, 'slap')
        for side, x, k in (('h', 282, 0), ('a', 798, 1)):
            tm = self.h if side == 'h' else self.a
            emb = tm.emb(340)
            self._el(E, 'i', emb, x, 548, b0 + k * u, 'spray', 0.3 * u, 'rad', drips=2, haze=self.col[side], seed=10 + k,
                     drip_scale=1.0, lmax=70)
            nm = piece([tm.up], sizes=(118,), max_w=470, jitter=0.55, seed=40 + k,
                       fill=(lighten(self.col[side], 0.25), darken(self.col[side], 0.12)), ext_col=darken(self.col[side], 0.7),
                       ext=8, out1=5, out2=6, band=False)
            nm = C.fit(nm, 500, 170) if nm.width > 500 or nm.height > 170 else nm
            self._el(E, 'i', nm, x, 790, b0 + k * u + 0.5 * u, 'spray', 0.32 * u, 'lr', drips=3, haze=self.col[side],
                     seed=20 + k, lmax=60, drip_cols=[self.col[side]])
        vs = marker('VS', 76, WHITE)
        self._el(E, 'i', vs, 540, 560, b0 + 1.75 * u, 'spray', 0.2 * u, 'lr', seed=33)
        wt = C.with_shadow(stencil(self.when.upper(), 60, (255, 214, 92), 960, seed=5, cut=False), 6, 0.6, 3)
        self._el(E, 'i', wt, 540, 948, b0 + 2 * u, 'spray', 0.4 * u, 'lr', haze=(255, 200, 80), seed=34)
        if self.line:
            cols = [self.col['h'], (52, 52, 58), self.col['a']]
            rots = [-3.5, 2.0, -2.0]
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                st = self._odds_sticker(lab, v, cols[k])
                self._el(E, 'i', slap_ready(st, rots[k], 12, 0.55, 10), 200 + k * 340, 1182, b0 + (2.5 + 0.5 * k) * u, 'slap')

    def _odds_sticker(self, lab, v, col):
        w, h = 300, 236
        st = C.rrect(w, h, 26, WHITE)
        band = C.rrect(w - 20, 76, 16, col)
        C.put(st, band, w / 2, 48)
        tc = WHITE if 0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2] < 175 else INK
        C.put(st, C.text(lab, 'dela', 44, tc), w / 2, 48)
        C.put(st, C.text(C.fmt_k(v), 'dela', 104, INK, max_w=w - 36), w / 2, 156)
        return st

    def _row(self, g, w):
        h = 128
        r = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = 96
        ch = C.ellipse(d, d, F.res_col(g['res']))
        C.put(ch, C.text(g['res'] or '?', 'dela', 54, WHITE), d / 2, d / 2 + 1)
        C.put(r, ch, 26 + d / 2, h / 2)
        sc = C.text(g['score'], 'dela', 88, INK)
        nt = C.text(g['note'], 'dela', 40, (200, 40, 40)) if g['note'] else None
        right = w - 28
        if nt is not None:
            C.put(r, nt, right - nt.width, h / 2 - sc.height / 2 - 2, anchor='tl')
            right -= nt.width + 8
        C.put(r, sc, right - sc.width, h / 2 - sc.height / 2 + 4, anchor='tl')
        x0 = 26 + d + 24
        room = right - sc.width - 24 - x0
        op = C.text(g['opp'].upper(), 'osw', 64, INK, 700, max_w=room)
        sub = ' · '.join([x for x in (g['date'], 'ДОМА' if g['home'] else 'В ГОСТЯХ' if g['home'] is not None else '') if x])
        if sub:
            sb = C.text(sub, 'osw', 34, (96, 92, 86), 600, max_w=room)
            C.put(r, op, x0, 10, anchor='tl')
            C.put(r, sb, x0, h - sb.height - 14, anchor='tl')
        else:
            C.put(r, op, x0, h / 2 - op.height / 2, anchor='tl')
        return r

    def _poster(self, side, games):
        """Плакат-вклейка: бумага с рваным краем, складками и клеем; версии с 0..n строк (строки «печатаются» по одной)."""
        tm = self.h if side == 'h' else self.a
        rng = np.random.default_rng(self.seed + (1 if side == 'h' else 2))
        n = max(1, len(games))
        w, rh = 960, 128
        h = 26 + rh * n + 12 * (n - 1) + 26
        arr = np.ones((h, w, 3), np.float32) * np.array(PAPER, np.float32)
        arr += (_lowfreq(rng, (h, w), 60, 5) + rng.normal(0, 3, (h, w)).astype(np.float32))[..., None]
        # складки и клей
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        fold = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(fold)
        for _ in range(5):
            x0, y0 = rng.uniform(0, w), rng.uniform(-40, h)
            x1, y1 = x0 + rng.uniform(-300, 300), y0 + rng.uniform(80, 260)
            d.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 70), width=3)
            d.line([(x0 + 3, y0 + 2), (x1 + 3, y1 + 2)], fill=(0, 0, 0, 40), width=2)
        fold = fold.filter(ImageFilter.GaussianBlur(1.2))
        img.alpha_composite(fold)
        wm = C.fade(tm.emb(int(h * 0.9)).convert('LA').convert('RGBA'), 0.09)
        C.put(img, wm, w - wm.width / 2 - 20, h / 2)
        C.put(img, C.rrect(w, 14, 0, self.col[side]), w / 2, 7)
        # рваный край
        a = np.ones((h, w), np.float32) * 255
        ex = np.abs(_lowfreq(rng, (h, 1), 6, 4))[:, 0] + rng.uniform(0, 3, h)
        ey = np.abs(_lowfreq(rng, (1, w), 6, 4))[0] + rng.uniform(0, 3, w)
        xs = np.arange(w)[None, :]
        ys = np.arange(h)[:, None]
        a[(xs < ex[:, None]) | (xs > w - 1 - ex[::-1][:, None])] = 0
        a[(ys < ey[None, :]) | (ys > h - 1 - ey[::-1][None, :])] = 0
        img.putalpha(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
        vers = []
        cur = img.copy()
        vers.append(cur.copy())
        for k, g in enumerate(games):
            y = 26 + k * (rh + 12)
            if k:
                dl = ImageDraw.Draw(cur)
                for x in range(40, w - 40, 22):
                    dl.line([(x, y - 7), (x + 10, y - 7)], fill=(150, 144, 132, 255), width=2)
            C.put(cur, self._row(g, w), 0, y, anchor='tl')
            vers.append(cur.copy())
        return vers

    def _team(self, E, side, T):
        u = self.u
        tm = self.h if side == 'h' else self.a
        s, rec = self.s[side], self.rec[side]
        c = self.col[side]
        self._el(E, side, tm.emb(210), 152, 352, T + 0.75 * u, 'spray', 0.28 * u, 'rad', drips=2, haze=c, seed=50, lmax=60)
        nm = piece([tm.up], sizes=(150,), max_w=740, jitter=0.7, seed=60 + (side == 'a'),
                   fill=(lighten(c, 0.3), darken(c, 0.1)), ext_col=darken(c, 0.72), ext=10, out1=6, out2=8)
        nm = C.fit(nm, 790, 230) if nm.width > 790 or nm.height > 230 else nm
        self._el(E, side, nm, 290 + min(790, nm.width) / 2 - 20, 350, T + 1.0 * u, 'spray', 0.36 * u, 'lr', drips=4, haze=c,
                 seed=51, lmax=90, drip_cols=[c, lighten(c, 0.3)])
        vers = self._poster(side, s['games'])
        rot = -1.2 if side == 'h' else 1.0
        vv = [slap_ready(v, rot, 14, 0.55, 12) for v in vers]
        ph = vers[0].height
        PT = 470
        e = self._el(E, side, vv[0], 540, PT + ph / 2, T + 1.5 * u, 'poster')
        e['vers'] = vv
        e['rows_t'] = [T + (2.0 + 0.5 * k) * u for k in range(len(vers) - 1)]
        ytile = PT + ph + 92
        tiles = []
        if s['points'] is not None:
            tiles.append(('%d' % s['points'], [plural(s['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ')]))
        if s['gp'] is not None:
            tiles.append(('%d' % s['gp'], [plural(s['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ')]))
        if s['place'] is not None:
            tiles.append(('%d' % s['place'], ['МЕСТО'] + ([s['place_scope'].upper()] if s['place_scope'] else [])))
        if s['gd'] is not None:
            tiles.append((F.gd_txt(s['gd']), ['РАЗНИЦА', 'ШАЙБ']))
        nt = len(tiles)
        tw = 1000 / max(1, nt)
        for k, (num, labs) in enumerate(tiles):
            cx = 40 + tw * (k + 0.5)
            sp = piece([num], sizes=(124,), max_w=tw - 10, jitter=0.25, seed=70 + k, fill=(WHITE, (214, 212, 206)),
                       ext_col=darken(c, 0.15), ext=9, out1=5, out2=0, band=False)
            tt = T + (3.5 + 0.25 * k) * u
            self._el(E, side, sp, cx, ytile, tt, 'spray', 0.24 * u, 'lr', drips=1, haze=c, seed=80 + k, lmax=50,
                     drip_cols=[c])
            for j, lb in enumerate(labs):
                self._el(E, side, marker(lb, 46, WHITE, max_w=tw - 14), cx, ytile + sp.height / 2 + 18 + j * 50, tt + 0.12 * u,
                         'spray', 0.18 * u, 'lr', seed=90 + k * 3 + j)
        nlab = max([len(l) for _, l in tiles] + [1])
        lab_end = ytile + 66 + 18 + nlab * 50
        extra = []
        if rec.get('gf') is not None and rec.get('ga') is not None:
            extra.append('ЗАБИТО %d · ПРОПУЩЕНО %d' % (int(rec['gf']), int(rec['ga'])))
        st = streak_txt(rec.get('streak'))
        extra.append(st or venue_txt(rec))
        extra = [x for x in extra if x][:2]
        room0, room1 = lab_end, 1405                       # свободная полоса до @jarvibet
        step = 88
        y0 = (room0 + room1) / 2 - step * (len(extra) - 1) / 2
        for j, tx in enumerate(extra):
            col = (255, 214, 92) if j == 0 else lighten(c, 0.35)
            self._el(E, side, marker(tx, 64, col, max_w=980), 540, y0 + j * step, T + (4.75 + 0.5 * j) * u, 'spray', 0.3 * u,
                     'lr', seed=95 + j)
        self.layout[side] = dict(ytile=ytile, lab_end=lab_end, extra_y=y0, poster_h=ph)

    def _pick(self, E):
        u, D = self.u, self.drop
        tm = self.fav
        c = self.col[self.side]
        accent = (150, 70, 220) if c[2] < 150 else (240, 70, 120)
        # облако-подложка и брызги
        rng = np.random.default_rng(self.seed + 9)
        cw, chh = 1080, 1020
        cloud = Image.new('RGBA', (cw, chh), (0, 0, 0, 0))
        for k in range(26):
            r = rng.uniform(150, 300)
            x, y = rng.uniform(r * 0.6, cw - r * 0.6), rng.uniform(r * 0.6 + 40, chh - r * 0.6 - 40)
            col = accent if k % 3 else lighten(accent, 0.35)
            blob = C.radial(int(2 * r), int(2 * r), col, int(rng.uniform(130, 200)), 1.1)
            C.put(cloud, blob, x, y)
        sp_lay = Image.new('RGBA', (cw, chh), (0, 0, 0, 0))
        d = ImageDraw.Draw(sp_lay)
        for k in range(70):
            ang = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(300, 520)
            x, y = cw / 2 + math.cos(ang) * rr * 0.98, chh / 2 + math.sin(ang) * rr * 0.92
            col = [c, WHITE, lighten(accent, 0.3)][k % 3]
            r = rng.uniform(4, 16)
            d.ellipse((x - r, y - r, x + r, y + r), fill=col + (235,))
            for _ in range(int(rng.integers(1, 4))):
                rr2 = rr + rng.uniform(10, 60)
                x2, y2 = cw / 2 + math.cos(ang) * rr2, chh / 2 + math.sin(ang) * rr2 * 0.94
                r2 = r * rng.uniform(0.2, 0.5)
                d.ellipse((x2 - r2, y2 - r2, x2 + r2, y2 + r2), fill=col + (235,))
        sp_lay = sp_lay.filter(ImageFilter.GaussianBlur(0.8))
        self._el(E, 'p', cloud, 540, 330 + chh / 2, D, 'spray', 0.22 * u, 'rad', seed=100)
        self._el(E, 'p', sp_lay, 540, 330 + chh / 2, D + 0.02, 'spray', 0.3 * u, 'rad', seed=101)
        disc = Image.new('RGBA', (430, 430), (0, 0, 0, 0))
        C.put(disc, C.ellipse(420, 420, INK), 215, 215)
        C.put(disc, C.ellipse(398, 398, WHITE), 215, 215)
        C.put(disc, C.ellipse(378, 378, lighten(c, 0.55)), 215, 215)
        emb = tm.emb(318)
        C.put(disc, emb, 215, 215)
        self._el(E, 'p', disc, 540, 548, D, 'spray', 0.2 * u, 'rad', drips=3, haze=c, seed=102, lmax=50,
                 drip_cols=[lighten(c, 0.55), WHITE])
        words = self.pick1.split()
        rows = [words[0], ' '.join(words[1:])] if len(words) > 1 else [self.pick1]
        pc = piece(rows, sizes=(142, 142), max_w=1010, jitter=0.9, seed=110, fill=(lighten(c, 0.5), darken(c, 0.05)),
                   ext_col=darken(accent, 0.45), ext=16, out1=7, out2=10, gap=-0.1)
        pc = C.fit(pc, 1060, 420) if pc.width > 1060 or pc.height > 420 else pc
        self.pc_h = pc.height
        ypc = 752 + pc.height / 2
        self._el(E, 'p', pc, 540, ypc, D, 'spray', 0.22 * u, 'rad', drips=6, haze=accent, seed=103, lmax=34, lmin=18,
                 drip_cols=[lighten(c, 0.3), c])
        ysub = ypc + pc.height / 2 + 40
        if self.pick2:
            sub = C.with_shadow(stencil(self.pick2, 56, WHITE, 960, seed=8), 7, 0.75, 3)
            self._el(E, 'p', sub, 540, ysub, D, 'spray', 0.25 * u, 'lr', haze=WHITE, seed=104)
        cf = sticker(430, 146, 30, c)
        tc = INK if 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] > 150 else WHITE
        C.put(cf, C.text('КЭФ', 'dela', 42, tc), 98, 73)
        C.put(cf, C.text(C.fmt_k(self.coef), 'dela', 96, tc, max_w=230), 290, 75)
        self.coef_y = min(ysub + 40 + 80, 1205)
        self._el(E, 'p', slap_ready(cf, 4, 12, 0.55, 10), 540, self.coef_y, D + 0.5 * u, 'slap')
        tg = slap_ready(sticker(330, 74, 16, INK), 3, 8, 0.5, 6)
        C.put(tg, stencil(self.tag, 34, WHITE, 270, cut=False), tg.width / 2, tg.height / 2 - 3)
        self._el(E, 'p', tg, 540, 292, D + u, 'slap')
        self.stars = [(150, 400, 64, 0), (930, 380, 80, 1), (980, 760, 54, 2), (110, 980, 70, 3), (870, 1020, 58, 1)]
        self.star_im = {d_: star4(d_) for (_, _, d_, _) in self.stars}

    def _build(self):
        self.layout = {}
        E = []
        self._intro(E)
        self._team(E, 'h', self.T1)
        self._team(E, 'a', self.T2)
        self._pick(E)
        G = dict(E=E, wall=self._wall(), lm=self._light(), buff=self._buff_tex(), roller=self._roller(W / 4 + 30),
                 tgp=slap_ready(C.tg_plate(960, 170), 0, 12, 0.55, 10),
                 handle=C.with_shadow(C.text(C.HANDLE, 'dela', 50, WHITE, stroke=3, stroke_fill=INK), 8, 0.6, 4),
                 stars=self.stars, star_im=self.star_im, coef_y=self.coef_y, layout=self.layout)
        rng = np.random.default_rng(3)
        G['grain'] = [rng.normal(0, 4.5, (H // 2, W // 2)).astype(np.int16).repeat(2, 0).repeat(2, 1)[..., None] for _ in range(4)]
        bw = W / 4
        G['buff_edge'] = (_lowfreq(np.random.default_rng(4), (1, W), 9, 9)[0]).astype(np.float32)
        G['bw'] = bw
        return G

    # ── камера и время ──
    def _cam(self, t):
        u = self.u
        x = 0.0
        for k, T in ((1, self.T1), (2, self.T2)):
            if t >= T:
                x = (k - 1) * W + W * C.in_out(C.seg(t, T, T + 0.8 * u))
        sp = 0.0
        for T in (self.T1, self.T2):
            if T <= t < T + 0.8 * u:
                p = C.seg(t, T, T + 0.8 * u)
                sp = max(sp, math.sin(math.pi * p))
        dx = 10 * math.sin(t * 0.55) if t < self.drop else 0.0
        dy = 8 * math.sin(t * 0.43 + 1.0)
        sx, sy = C.shake(t, self.drop, 20, 0.4)
        for T in (self.T1 + 0.75 * u, self.T2 + 0.75 * u):
            if T <= t < T + 0.25:
                a, b = C.shake(t, T, 5, 0.22)
                sx, sy = sx + a, sy + b
        return x, dx + sx, dy + sy, sp

    def _flicker(self, t):
        u, D = self.u, self.drop
        f = 1.0
        if self.TB <= t < D:                                            # фонарь мигает, пока стену закатывают
            fi = int(t * 30)
            k = (fi * 7919) % 13
            f = 0.82 if k < 3 else 0.9
            if t < self.TB + 0.25:
                f = 0.55 if (fi % 3) else 1.0
        elif t >= D:
            f = 1.0 + 0.25 * (1 - C.seg(t, D, D + 0.5))
            for n in range(1, 9):
                tb = self.b(n)
                if tb <= t < tb + 0.3:
                    f += 0.06 * (1 - C.seg(t, tb, tb + 0.3))
        return f

    # ── кадр ──
    def _draw_el(self, fr, e, t, ox, oy):
        if t < e['t0']:
            return
        cx, cy = e['cx'] + ox, e['cy'] + oy
        kind = e['kind']
        if kind == 'spray':
            p = C.seg(t, e['t0'], e['t0'] + e['dur'])
            if 'haze' in e:
                C.put(fr, e['haze'], cx, cy, min(1.0, p * 1.6))
            im = e['sp'].reveal(p)
            if im is not None:
                C.put(fr, im, cx, cy)
            for (x, y, body, tip, dl, gr) in e.get('drips', ()):
                t0 = e['t0'] + e['dur'] + dl
                if t < t0:
                    continue
                k = C.out_cubic(C.seg(t, t0, t0 + gr))
                L = max(1, int(body.height * k))
                bx, by = cx + x - body.width / 2, cy + y - 3
                C.put(fr, body.crop((0, 0, body.width, L)), bx, by, anchor='tl')
                C.put(fr, tip, cx + x, by + L, 1.0)
        elif kind == 'slap':
            p = C.seg(t, e['t0'], e['t0'] + 0.16)
            s = 1 + 0.16 * (1 - C.out_back(p, 2.2))
            im = C.scale(e['spr'], s) if s > 1.003 else e['spr']
            C.put(fr, im, cx, cy, min(1.0, p * 4))
        elif kind == 'poster':
            p = C.seg(t, e['t0'], e['t0'] + 0.18)
            vv, rt = e['vers'], e['rows_t']
            n = sum(1 for x in rt if t >= x)
            base = vv[n]
            if p < 1:
                s = 1 + 0.08 * (1 - C.out_back(p, 1.8))
                C.put(fr, C.scale(base, s), cx, cy, min(1.0, p * 3))
                return
            C.put(fr, base, cx, cy)
            if n >= 1:
                q = C.seg(t, rt[n - 1], rt[n - 1] + 0.1)
                if q < 1:
                    C.put(fr, vv[n - 1], cx, cy)
                    C.put(fr, vv[n], cx, cy, q)

    def frame(self, t):
        G = self.G
        u, D = self.u, self.drop
        fi = int(round(t * C.FPS))
        cam, dx, dy, speed = self._cam(t)
        x0 = int(round(M + cam + dx))
        y0 = int(round(M + dy))
        x0 = max(0, min(WW - W, x0))
        y0 = max(0, min(WH - H, y0))
        if t < D:
            base = G['wall'][y0:y0 + H, x0:x0 + W]
        else:
            bx = x0 - 2 * W
            base = G['buff'][y0:y0 + H, bx:bx + W]
        fr = Image.fromarray(np.ascontiguousarray(base)).convert('RGBA')
        ox_cam = M + cam + dx
        oy = M - y0
        oxs = {}
        for sg, k in SEG.items():
            oxs[sg] = M + k * W - x0
        segs = ['i', 'h', 'a'] if t < D else ['p']
        for e in G['E']:
            if e['seg'] not in segs:
                continue
            ox = oxs[e['seg']]
            if ox <= -W or ox >= W:
                continue
            self._draw_el(fr, e, t, ox, oy)
        if self.TB <= t < D:
            fr = self._buff(fr, t, x0, y0)
        if t >= D:
            self._stars(fr, t, oxs['p'], oy)
        # свет и зерно
        arr = np.asarray(fr.convert('RGB'), np.uint16)
        lm = G['lm'][y0:y0 + H, x0:x0 + W]
        f = self._flicker(t)
        if abs(f - 1) > 0.005:
            arr = ((arr * lm >> 7) * f).astype(np.int32)
        else:
            arr = (arr * lm >> 7).astype(np.int32)
        arr += G['grain'][fi % 4]
        if t >= D and t < D + 0.14:                                   # вспышка на дропе
            arr += int(110 * (1 - C.seg(t, D, D + 0.14)))
        out = np.clip(arr, 0, 255).astype(np.uint8)
        if speed > 0.05:                                              # размаз при переезде камеры
            sh_ = int(28 * speed)
            out = ((out.astype(np.uint16) * 2 + np.roll(out, sh_, 1) + np.roll(out, -sh_, 1)) // 4).astype(np.uint8)
        fr = Image.fromarray(out)
        if D <= t < D + 0.45:                                         # удар: наезд камеры
            z = 1 + 0.06 * (1 - C.out_cubic(C.seg(t, D, D + 0.45)))
            fr = C.zoom(fr, z, W / 2, 760)
        elif t >= D:
            for n in range(1, 7):
                tb = self.b(n)
                if tb <= t < tb + 0.22:
                    fr = C.zoom(fr, 1 + 0.012 * (1 - C.seg(t, tb, tb + 0.22)), W / 2, 760)
                    break
        fr = fr.convert('RGBA')
        a_h = 1.0 if t < self.TC else 1 - C.seg(t, self.TC, self.TC + 0.12)
        C.put(fr, G['handle'], W / 2, HANDLE_Y, a_h)
        if t >= self.TC:
            p = C.seg(t, self.TC, self.TC + 0.18)
            s = 1 + 0.14 * (1 - C.out_back(p, 2.0))
            C.put(fr, C.scale(G['tgp'], s), W / 2, 1392, min(1.0, p * 4))
        return fr.convert('RGB')

    def _buff(self, fr, t, x0, y0):
        """Валики закатывают стену серым: 4 полосы, сверху вниз, внахлёст — к дропу стена чистая."""
        G = self.G
        u, D = self.u, self.drop
        bw = G['bw']
        nb = 4
        span = D - self.TB
        dur = span * 0.5
        step = (span - dur) / (nb - 1)
        bx = x0 - 2 * W
        buf = G['buff'][y0:y0 + H, bx:bx + W]
        ybot = np.full(W, -1.0, np.float32)
        rollers = []
        for k in range(nb):
            ts = self.TB + k * step
            if t < ts:
                continue
            p = C.in_out(C.seg(t, ts, ts + dur)) if t < ts + dur else 1.0
            yf = -80 + (H + 160) * p
            xa, xb = int(k * bw - (8 if k else 0)), int((k + 1) * bw + 8)
            ybot[max(0, xa):min(W, xb)] = np.maximum(ybot[max(0, xa):min(W, xb)], yf)
            if p < 1:
                rollers.append(((xa + xb) / 2, yf))
        if ybot.max() < 0:
            return fr
        ye = ybot + G['buff_edge']
        mask = (np.arange(H, dtype=np.float32)[:, None] < ye[None, :])
        arr = np.asarray(fr.convert('RGB')).copy()
        arr[mask] = buf[mask]
        fr = Image.fromarray(arr).convert('RGBA')
        for (cx, yf) in rollers:
            r = G['roller']
            C.put(fr, r, cx, yf - 30 + r.height / 2 - 60)
        return fr

    def _stars(self, fr, t, ox, oy):
        G = self.G
        for (x, y, d, ph) in G['stars']:
            t0 = self.drop + 0.12 + 0.05 * ph
            if t < t0:
                continue
            k = C.out_back(C.seg(t, t0, t0 + 0.2), 2.5)
            n = int((t - self.drop) / self.u)
            tb = self.b(n)
            pulse = 1 + 0.35 * (1 - C.seg(t, tb, tb + 0.25)) if (n + ph) % 2 == 0 else 1.0
            s = max(0.05, k * pulse * (0.85 + 0.15 * math.sin(t * 5 + ph)))
            C.put(fr, C.scale(G['star_im'][d], s), x + ox, y + oy)
