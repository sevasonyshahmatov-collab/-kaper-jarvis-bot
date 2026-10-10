# -*- coding: utf-8 -*-
"""Короткие вертикальные ролики (YouTube Shorts, VK Клипы, Rutube) в стиле баннеров «Бока»: свои, из данных канала,
без кадров матчей — претензий правообладателей нет.

    import shorts
    shorts.pick('Вегас', 'Торонто', 'ПТ 09.10 · 05:00 МСК', 'Тотал больше 5,5', 1.67, 'out/pick.mp4', league='NHL')
    shorts.result('Вегас', 'Торонто', 4, 3, 'out/result.mp4', mark='Б', when='ПТ 09.10',
                  pred='Тотал больше 5,5', coef=1.67, won=True, league='NHL')

1080×1920, 30 кадров/с, H.264 и тихая дорожка AAC (часть площадок не принимает ролик совсем без звука; музыку удобнее
добавить в самом приложении YouTube или VK — у них своя библиотека без претензий правообладателей).
Кадры рисует PIL (фон, эмблемы, шрифты — как у баннеров «Бока», nhl_kit._side), склеивает ffmpeg.
Ролик: эмблемы выезжают с боков → названия и время → прогноз и кэф (у итога — счёт и «ЗАШЁЛ / НЕ ЗАШЁЛ»)
→ в конце 1,5 с заставка @jarvibet.
"""
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw

import nhl
import nhl_kit
import poster

W, H, FPS = 1080, 1920, 30
PAN = (90, 150)                     # фон чуть больше кадра и медленно сдвигается — картинка «живая»
SAFE_BOTTOM = 1480                  # ниже — подпись и кнопки Shorts / Клипов: там только фон
OUTRO = 1.6                         # секунд заставки в конце
HANDLE = '@jarvibet'
GREEN, RED = nhl_kit.GREEN, nhl_kit.RED


def _style(league):
    """Шапка и акцент как у баннеров лиги: КХЛ — «JARVIS | KXL» золотом, НХЛ — «JARVIS | NHL» ледяным."""
    if str(league).upper() == 'NHL':
        nhl.register()
        return 'NHL', nhl.ICE
    return 'KXL', poster.ACC


# ── плавность ────────────────────────────────────────────────────────────────
def _p(t, a, b):
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


def _out(x):
    return 1 - (1 - x) ** 3


def _back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def fade(a, b, dy=36):
    """Проявиться, чуть поднимаясь."""
    return lambda t: (0, dy * (1 - _out(_p(t, a, b))), _out(_p(t, a, b)), 1.0)


def slide(a, b, dx):
    """Выехать сбоку."""
    return lambda t: (dx * (1 - _out(_p(t, a, b))), 0, min(1.0, _p(t, a, b) * 2.5), 1.0)


def pop(a, b, k0=0.55):
    """Выпрыгнуть: из меньшего размера с лёгким перелётом."""
    return lambda t: (0, 0, min(1.0, _p(t, a, b) * 3), k0 + (1 - k0) * _back(_p(t, a, b)) if t < b else 1.0)


def stamp(a, b, k0=1.9):
    """Печать: из крупного с размаху на место."""
    return lambda t: (0, 0, _out(_p(t, a, b)), k0 - (k0 - 1) * _out(_p(t, a, b)))


# ── рисование элементов ──────────────────────────────────────────────────────
def _font(kind, size):
    return poster._f7(kind, int(size))


def _text_layer(text, kind, size, fill=(255, 255, 255), max_w=None, spacing=0, min_size=24):
    f = _font(kind, size)
    if max_w:
        while f.getlength(text) + spacing * max(0, len(text) - 1) > max_w and size > min_size:
            size -= 2
            f = _font(kind, size)
    w = int(f.getlength(text) + spacing * max(0, len(text) - 1)) + 8
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (w, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        poster._spaced(d, (4, im.height // 2), text, f, fill + (255,), spacing)
    else:
        d.text((w / 2, im.height / 2), text, font=f, fill=fill + (255,), anchor='mm')
    return im


def _wrap(text, kind, size, max_w, lines=2, min_size=40):
    """Крупный текст в 1–2 строки по ширине max_w (уменьшается, пока не влезет)."""
    words = text.split()
    while True:
        f = _font(kind, size)
        rows, cur = [], ''
        for wd in words:
            nxt = (cur + ' ' + wd).strip()
            if f.getlength(nxt) <= max_w or not cur:
                cur = nxt
            else:
                rows.append(cur)
                cur = wd
        rows.append(cur)
        if (len(rows) <= lines and all(f.getlength(r) <= max_w for r in rows)) or size <= min_size:
            return rows, f, size
        size -= 4


def _block(rows, f, size, fill=(255, 255, 255)):
    lh = int(size * 1.08)
    w = int(max(f.getlength(r) for r in rows)) + 12
    im = Image.new('RGBA', (w, lh * len(rows) + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, r in enumerate(rows):
        d.text((w / 2, 8 + lh * i + lh / 2), r, font=f, fill=fill + (255,), anchor='mm')
    return im


def _pill(text, kind, size, fg, fill, outline=None, pad=(44, 22), label=None, label_size=None):
    """Плашка: как время и кэфы на баннере (скруглённая, полупрозрачная или залитая акцентом)."""
    f = _font(kind, size)
    lf = _font('info', label_size or size * 0.5) if label else None
    tw = f.getlength(text) + (lf.getlength(label) + size * 0.45 if label else 0)
    asc, desc = f.getmetrics()
    w, h = int(tw + pad[0] * 2), int(asc + desc * 0.4 + pad[1] * 2)
    im = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=fill, outline=outline, width=4 if outline else 0)
    x = 4 + pad[0]
    if label:
        d.text((x, 4 + h / 2), label, font=lf, fill=fg + (255,), anchor='lm')
        x += lf.getlength(label) + size * 0.45
    d.text((x, 4 + h / 2), text, font=f, fill=fg + (255,), anchor='lm')
    return im


def _brand(tag, accent, size=40):
    """Шапка «JARVIS | KXL» — как у баннеров."""
    fb = _font('brand', size)
    sp, bar = size * 0.12, size * 0.85
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in tag) + sp * max(0, len(tag) - 1)
    im = Image.new('RGBA', (int(w1 + 2 * bar + w2) + 8, int(size * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = im.height // 2
    poster._spaced(d, (4, y), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((4 + w1 + bar - 2, y - size * 0.55, 4 + w1 + bar + 2, y + size * 0.55), radius=2, fill=(255, 255, 255, 150))
    poster._spaced(d, (4 + w1 + 2 * bar, y), tag, fb, accent + (255,), sp)
    return im


def _emblem(team, col, max_w, max_h):
    """Эмблема с тенью; светлой подложкой — если эмблема сливается с цветом клуба на фоне (как на баннере)."""
    e = poster._raw_emblem(team, 200, 200)
    arr = np.asarray(e).astype(np.float32)
    op = arr[..., 3] > 128
    plate = bool(op.any()) and float(np.sqrt(((arr[..., :3][op].mean(axis=0) - np.array(col, np.float32)) ** 2).sum())) < 110
    e = poster._raw_emblem(team, max_w, max_h, plate=plate)
    pad = 60
    im = Image.new('RGBA', (e.width + pad * 2, e.height + pad * 2), (0, 0, 0, 0))
    poster._shadowed(im, e, (pad, pad), blur=22, off=(0, 14), color=(0, 0, 0, 130))
    return im


def _background(c1, c2, seed):
    bw, bh = W + PAN[0], H + PAN[1]
    bg = poster._fluid_bg(bw // 2, bh // 2, c1, c2, seed=seed).resize((bw, bh), Image.LANCZOS)
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    # снизу темнее — там текст прогноза; немного темнее за эмблемами по краям
    dim = (0.62 / (1 + np.exp(-((yy / bh) - 0.66) * 9))
           + 0.18 * np.exp(-(((yy / bh) - 0.06) ** 2) / 0.01))
    shade = Image.new('RGBA', (bw, bh), (5, 8, 14, 0))
    shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade)
    return poster._canvas_texture(bg, 1.0).convert('RGBA')


def _put(frame, im, cx, cy):
    """Наложить по центру (cx, cy), обрезая то, что за краем кадра."""
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, W - x), min(im.height, H - y)
    if r <= l or b <= t:
        return
    frame.alpha_composite(im.crop((l, t, r, b)) if (l, t, r, b) != (0, 0, im.width, im.height) else im, (x + l, y + t))


class _Clip:
    def __init__(self, home, away, league, seed=None):
        self.tag, self.accent = _style(league)
        h, a = nhl_kit._prep(home, away)
        self.home, self.away = h, a
        self.c1, self.c2 = poster.BANNER[h], poster.BANNER[a]
        self.seed = sum(map(ord, h + a)) % 997 if seed is None else seed
        self.items = []                 # (картинка, cx, cy, анимация)
        self.outro = []

    def add(self, im, cx, cy, anim, outro=False):
        (self.outro if outro else self.items).append((im, cx, cy, anim))

    def teams(self, t0=0.25, cy=450, names_y=690):
        e1 = _emblem(self.home, self.c1, 380, 340)
        e2 = _emblem(self.away, self.c2, 380, 340)
        gap = 40
        cx1, cx2 = W / 2 - gap / 2 - (e1.width - 120) / 2, W / 2 + gap / 2 + (e2.width - 120) / 2
        self.add(e1, cx1, cy, slide(t0, t0 + 0.8, -620))
        self.add(e2, cx2, cy, slide(t0 + 0.12, t0 + 0.92, 620))
        for team, cx, d in ((self.home, cx1, 0), (self.away, cx2, 0.1)):
            name = poster.SHORT.get(team, team).upper()
            self.add(_text_layer(name, 'team', 66, max_w=470), cx, names_y, fade(t0 + 0.75 + d, t0 + 1.25 + d))

    def common(self, label):
        tag, acc = self.tag, self.accent
        self.add(_brand(tag, acc), W / 2, 130, fade(0.0, 0.5, 20))
        self.add(_text_layer(label, 'info', 26, fill=(220, 226, 236), spacing=7), W / 2, 205, fade(0.15, 0.65, 20))

    def handle(self, y, t0):
        if y + 22 <= SAFE_BOTTOM:           # не влезает над подписью площадки — ник всё равно есть на заставке в конце
            self.add(_text_layer(HANDLE, 'info', 30, fill=self.accent, spacing=3), W / 2, y, fade(t0, t0 + 0.4, 0))

    def outro_card(self, dur):
        t0 = dur - OUTRO
        dark = Image.new('RGBA', (W, H), (6, 9, 15, 242))
        self.add(dark, W / 2, H / 2, lambda t: (0, 0, _out(_p(t, t0, t0 + 0.45)), 1.0), outro=True)
        self.add(_brand(self.tag, self.accent, 54), W / 2, H / 2 - 170, fade(t0 + 0.15, t0 + 0.6), outro=True)
        self.add(_text_layer(HANDLE, 'brand', 92, fill=self.accent), W / 2, H / 2, pop(t0 + 0.3, t0 + 0.8), outro=True)
        self.add(_text_layer('ПРОГНОЗЫ НА КХЛ И НХЛ КАЖДЫЙ ДЕНЬ', 'info', 30, fill=(230, 234, 242), max_w=940),
                 W / 2, H / 2 + 120, fade(t0 + 0.5, t0 + 0.95), outro=True)

    def frame(self, bg, t, dur):
        k = _out(t / dur) if dur else 0
        ox, oy = int(PAN[0] * k), int(PAN[1] * (1 - k))
        fr = bg.crop((ox, oy, ox + W, oy + H))
        for im, cx, cy, anim in self.items + self.outro:
            dx, dy, al, sc = anim(t)
            if al <= 0.003:
                continue
            if abs(sc - 1) > 0.004:
                im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
            if al < 0.997:
                im = im.copy()
                im.putalpha(im.getchannel('A').point(lambda v, al=al: int(v * al)))
            _put(fr, im, cx + dx, cy + dy)
        return fr

    def render(self, path, dur):
        saved = poster.FONTS7
        poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
        try:
            self.build(dur)
            self.outro_card(dur)
            bg = _background(self.c1, self.c2, self.seed)
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                   '-r', str(FPS), '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest',
                   '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                   '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', path]
            pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            n = int(round(dur * FPS))
            try:
                for i in range(n):
                    pr.stdin.write(self.frame(bg, i / FPS, dur).convert('RGB').tobytes())
            finally:
                pr.stdin.close()
            if pr.wait() != 0:
                raise RuntimeError('ffmpeg не собрал ролик: %s' % path)
            self.frame(bg, dur - OUTRO - 0.4, dur).convert('RGB').save(os.path.splitext(path)[0] + '_cover.jpg', quality=92)
            return path
        finally:
            poster.FONTS7 = saved


class _Pick(_Clip):
    def __init__(self, home, away, when, pred, coef, league, seed=None):
        super().__init__(home, away, league, seed)
        self.when, self.pred, self.coef = when, pred, coef

    def build(self, dur):
        self.common('ПРОГНОЗ НА МАТЧ')
        self.teams()
        if self.when:
            self.add(_pill(self.when, 'time', 32, (255, 255, 255), (8, 12, 20, 205), self.accent + (230,)),
                     W / 2, 805, fade(1.35, 1.8))
        self.add(_text_layer('ПРОГНОЗ', 'info', 28, fill=self.accent, spacing=9), W / 2, 930, fade(2.0, 2.4, 20))
        rows, f, size = _wrap(str(self.pred).upper(), 'team', 100, 880)
        blk = _block(rows, f, size)
        self.add(blk, W / 2, 955 + blk.height / 2, fade(2.15, 2.75, 50))
        y = 955 + blk.height
        if self.coef:
            y += 95
            self.add(_pill('%.2f' % float(self.coef), 'num', 84, (16, 18, 24), self.accent + (255,), label='КЭФ', label_size=32),
                     W / 2, y, pop(2.85, 3.35))
            y += 100
            self.add(_text_layer('коэффициент на момент публикации', 'info', 22, fill=(196, 202, 214)), W / 2, y, fade(3.3, 3.7, 0))
        self.handle(y + 70, 3.5)


class _Result(_Clip):
    def __init__(self, home, away, sh, sa, mark, when, pred, coef, won, league, seed=None):
        super().__init__(home, away, league, seed)
        self.sh, self.sa, self.mark, self.when = int(sh), int(sa), mark, when
        self.pred, self.coef, self.won = pred, coef, won

    def build(self, dur):
        self.common('ИТОГ МАТЧА')
        self.teams()
        if self.when:
            self.add(_pill(self.when, 'time', 30, (255, 255, 255), (8, 12, 20, 205), self.accent + (230,)),
                     W / 2, 795, fade(1.3, 1.7))
        win, lose = (255, 255, 255), (178, 188, 204)
        y = 940
        self.add(_text_layer(str(self.sh), 'num', 210, fill=win if self.sh > self.sa else lose), W / 2 - 150, y, pop(1.6, 2.0))
        self.add(_text_layer(':', 'num', 150, fill=self.accent), W / 2, y - 10, fade(1.75, 2.05, 0))
        self.add(_text_layer(str(self.sa), 'num', 210, fill=win if self.sa > self.sh else lose), W / 2 + 150, y, pop(1.9, 2.3))
        if self.mark:
            self.add(_pill(self.mark, 'num', 34, (255, 255, 255), (8, 12, 20, 205), (255, 255, 255, 90), pad=(30, 14)),
                     W / 2, y + 125, fade(2.3, 2.6, 10))
        y = 1125 + (25 if self.mark else 0)
        if self.pred:
            rows, f, size = _wrap(str(self.pred).upper(), 'team', 62, 860)
            blk = _block(rows, f, size)
            head = 'ПРОГНОЗ' + (' · КЭФ %.2f' % float(self.coef) if self.coef else '')
            self.add(_text_layer(head, 'info', 26, fill=self.accent, spacing=6), W / 2, y, fade(2.7, 3.1, 20))
            self.add(blk, W / 2, y + 30 + blk.height / 2, fade(2.85, 3.35, 40))
            y += 30 + blk.height + 90
        else:
            y += 50
        if self.won is not None:
            col = GREEN if self.won else RED
            self.add(_pill('ЗАШЁЛ' if self.won else 'НЕ ЗАШЁЛ', 'num', 76, (255, 255, 255), col + (255,), pad=(64, 24)),
                     W / 2, y, stamp(3.6, 4.0))
            y += 70
        self.handle(y + 50, 4.1)


def pick(home, away, when, pred, coef, path, league='KHL', dur=9.5, seed=None):
    """Ролик-прогноз: команды, время, прогноз крупно и кэф."""
    return _Pick(home, away, when, pred, coef, league, seed).render(path, dur)


def result(home, away, sh, sa, path, mark='', when=None, pred=None, coef=None, won=None, league='KHL', dur=9.5, seed=None):
    """Ролик-итог: счёт (ОТ/Б), прогноз и печать «ЗАШЁЛ / НЕ ЗАШЁЛ» (won=None — без печати)."""
    return _Result(home, away, sh, sa, mark, when, pred, coef, won, league, seed).render(path, dur)
