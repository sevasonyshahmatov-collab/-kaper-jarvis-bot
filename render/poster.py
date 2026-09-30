"""Постеры матчей КХЛ в стиле канала JARVISBET.

render_match(m, path) — афиша одного матча 1280x720.
render_day(matches, path) — афиша дня со всеми матчами 1080x1350 (для поста игры с кнопками).
m = {home, away, time, day_title, odds_h, odds_a, form_h: 'WWLWL', form_a: '...'}
"""
import os, math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
EMB = os.path.join(HERE, 'emblems')

# шрифты: в бою — Unbounded/Inter (скачиваются на GitHub), здесь — ближайшая замена
def _font(kind, size):
    cands = {
        'display': [os.path.join(HERE, 'fonts', 'Unbounded.ttf'), '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'],
        'bold': [os.path.join(HERE, 'fonts', 'Inter-Bold.ttf'), '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'],
        'text': [os.path.join(HERE, 'fonts', 'Inter.ttf'), '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'],
    }[kind]
    for p in cands:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            if p.endswith('Unbounded.ttf'):
                try: f.set_variation_by_axes([800])
                except Exception: pass
            return f
    return ImageFont.load_default()

DARK = (10, 14, 23)
NEON = (57, 255, 136)
RED = (255, 56, 96)

# клуб: эмблема и два фирменных цвета
TEAMS = {
    'Авангард': ('avangard', (200, 16, 46), (40, 40, 40)),
    'Автомобилист': ('avtomobilist', (227, 6, 19), (20, 20, 20)),
    'Адмирал': ('admiral', (200, 169, 106), (20, 24, 40)),
    'Ак Барс': ('akbars', (0, 122, 72), (227, 6, 19)),
    'Амур': ('amur', (242, 101, 34), (27, 42, 74)),
    'Барыс': ('barys', (42, 167, 184), (20, 45, 80)),
    'Динамо Москва': ('dinamo_msk', (0, 61, 165), (120, 160, 255)),
    'Динамо Минск': ('dinamo_minsk', (77, 178, 236), (15, 20, 30)),
    'Лада': ('lada', (15, 76, 129), (200, 210, 225)),
    'Локомотив': ('lokomotiv', (227, 6, 19), (27, 77, 161)),
    'Металлург': ('metallurg', (245, 166, 35), (27, 42, 90)),
    'Нефтехимик': ('neftekhimik', (28, 63, 110), (200, 40, 50)),
    'Салават Юлаев': ('salavat', (212, 175, 55), (46, 49, 146)),
    'Северсталь': ('severstal', (255, 204, 0), (60, 60, 60)),
    'Сибирь': ('sibir', (27, 50, 90), (180, 200, 230)),
    'СКА': ('ska', (227, 30, 36), (31, 78, 158)),
    'Сочи': ('sochi', (245, 180, 0), (20, 40, 80)),
    'Спартак': ('spartak', (215, 20, 26), (240, 240, 240)),
    'Торпедо': ('torpedo', (30, 58, 147), (227, 6, 19)),
    'Трактор': ('traktor', (170, 170, 170), (30, 30, 30)),
    'ЦСКА': ('cska', (227, 6, 19), (27, 58, 140)),
    'Шанхайские Драконы': ('shanghai', (255, 90, 0), (255, 170, 0)),
}
SHORT = {'Шанхайские Драконы': 'Шанхай', 'Салават Юлаев': 'Салават', 'Динамо Москва': 'Динамо М', 'Динамо Минск': 'Динамо Мн'}

def _emblem(team, size):
    slug = TEAMS.get(team, (None,))[0]
    p = os.path.join(EMB, (slug or '') + '.png')
    if not slug or not os.path.exists(p):
        # нет файла — круглая плашка с инициалами
        im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = TEAMS.get(team, (None, (120, 120, 120)))[1]
        d.ellipse((0, 0, size - 1, size - 1), fill=c + (255,), outline=(255, 255, 255, 255), width=max(3, size // 30))
        t = ''.join(w[0] for w in team.split()[:2]).upper()
        f = _font('display', size // 3)
        d.text((size / 2, size / 2), t, font=f, fill='white', anchor='mm')
        return im
    im = Image.open(p).convert('RGBA')
    sc = min(size / im.width, size / im.height)
    im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    # белая «наклейка»: скруглённый контур + залитые дырки — тёмные эмблемы не теряются на тёмном фоне
    pad = max(10, size // 14)
    canvas = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad), im)
    a = canvas.getchannel('A').point(lambda v: 255 if v > 40 else 0)
    r = max(4, size // 40)
    sil = a.filter(ImageFilter.GaussianBlur(r)).point(lambda v: 255 if v > 18 else 0)
    # закрываем дырки: всё, что не достижимо от края, — внутри эмблемы
    rgb = Image.merge('RGB', (sil, sil, sil))
    ImageDraw.floodfill(rgb, (0, 0), (255, 0, 0), thresh=10)
    outside = rgb.getchannel('G').point(lambda v: 255 if v < 128 else 0)   # красное = снаружи
    filled = ImageChops.invert(outside)
    filled = filled.filter(ImageFilter.GaussianBlur(1.2))
    plate = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
    plate.putalpha(filled)
    return Image.alpha_composite(plate, canvas)

def _glow(size, color, alpha=200, blur=120):
    w, h = size
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.1, h * 0.1, w * 0.9, h * 0.9), fill=color + (alpha,))
    return im.filter(ImageFilter.GaussianBlur(blur))

def _background(W, H, c1, c2, seed=7):
    rnd = random.Random(seed)
    bg = Image.new('RGBA', (W, H), DARK + (255,))
    # цвета клубов втекают с краёв к центру
    grad = Image.new('RGBA', (W, H))
    px = grad.load()
    for x in range(W):
        t = x / (W - 1)
        wl = max(0.0, 1 - t / 0.62) ** 1.6
        wr = max(0.0, (t - 0.38) / 0.62) ** 1.6
        for y in range(0, H, 1):
            pass
        col = tuple(int(DARK[i] + (c1[i] - DARK[i]) * wl * 0.85 + (c2[i] - DARK[i]) * wr * 0.85) for i in range(3))
        for y in range(H):
            px[x, y] = col + (255,)
    bg = Image.alpha_composite(bg, grad)
    # мягкие размытые пятна для глубины
    for c, cx, cy, r, a in [(c1, 0.12, 0.25, 0.45, 150), (c2, 0.88, 0.75, 0.45, 150), (c1, 0.25, 0.9, 0.3, 90), (c2, 0.75, 0.1, 0.3, 90)]:
        blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(blob).ellipse(((cx - r) * W, (cy - r) * H, (cx + r) * W, (cy + r) * H), fill=tuple(min(255, int(v * 1.1)) for v in c) + (a,))
        bg = Image.alpha_composite(bg, blob.filter(ImageFilter.GaussianBlur(W // 10)))
    # затемнение по центру и снизу — под текст
    vign = Image.new('L', (W, H), 0)
    ImageDraw.Draw(vign).ellipse((W * 0.3, H * 0.05, W * 0.7, H * 0.95), fill=150)
    vign = vign.filter(ImageFilter.GaussianBlur(W // 12))
    dark = Image.new('RGBA', (W, H), DARK + (0,)); dark.putalpha(vign)
    bg = Image.alpha_composite(bg, dark)
    bottom = Image.new('L', (W, H), 0)
    ImageDraw.Draw(bottom).rectangle((0, H * 0.72, W, H), fill=200)
    bottom = bottom.filter(ImageFilter.GaussianBlur(H // 8))
    dk = Image.new('RGBA', (W, H), DARK + (0,)); dk.putalpha(bottom)
    bg = Image.alpha_composite(bg, dk)
    # тонкие диагональные «лёд»-штрихи
    lines = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for i in range(14):
        x = rnd.randint(-W // 4, W)
        ld.line((x, 0, x + H * 0.6, H), fill=(255, 255, 255, rnd.randint(6, 16)), width=rnd.randint(1, 3))
    bg = Image.alpha_composite(bg, lines)
    # зерно
    noise = Image.effect_noise((W, H), 18).convert('L').point(lambda v: int(v * 0.10))
    nz = Image.new('RGBA', (W, H), (255, 255, 255, 0)); nz.putalpha(noise)
    return Image.alpha_composite(bg, nz)

def _shadowed(canvas, im, xy, blur=18, off=(0, 10), color=(0, 0, 0, 170)):
    sh = Image.new('RGBA', im.size, color)
    sh.putalpha(im.getchannel('A').point(lambda v: int(v * color[3] / 255)))
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    layer.paste(sh, (xy[0] + off[0], xy[1] + off[1]), sh)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(im, xy)

def _layer_draw(img):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)

def _text_center(d, xy, text, font, fill, stroke=0, stroke_fill=None):
    d.text(xy, text, font=font, fill=fill, anchor='mm', stroke_width=stroke, stroke_fill=stroke_fill)

def _fit(text, kind, size, max_w):
    f = _font(kind, size)
    while f.getlength(text) > max_w and size > 14:
        size -= 2; f = _font(kind, size)
    return f

def _form_dots(d, cx, y, form, r=9, gap=28):
    form = (form or '')[-5:]
    if not form: return
    x0 = cx - (len(form) - 1) * gap / 2
    for i, ch in enumerate(form):
        col = NEON if ch in 'WВ' else (RED if ch in 'LП' else (255, 200, 60))
        x = x0 + i * gap
        d.ellipse((x - r, y - r, x + r, y + r), fill=col + (255,))

def _watermark(img, W, H, size=26):
    f = _font('display', size)
    t = 'JARVISBET'
    w = f.getlength(t)
    L, ld = _layer_draw(img)
    ld.rounded_rectangle((W - w - 64, H - size - 42, W - 24, H - 22), radius=12, fill=(10, 14, 23, 210), outline=NEON + (255,), width=2)
    img.alpha_composite(L)
    ImageDraw.Draw(img).text((W - w / 2 - 44, H - size / 2 - 32), t, font=f, fill=NEON, anchor='mm')

def render_match(m, path):
    W, H = 1280, 720
    c1 = TEAMS.get(m['home'], (None, (90, 90, 90)))[1]
    c2 = TEAMS.get(m['away'], (None, (90, 90, 90)))[1]
    img = _background(W, H, c1, c2)
    d = ImageDraw.Draw(img)
    # верх: лига · день · время
    f = _font('bold', 26)
    top = 'КХЛ  ·  ' + m['day_title'] + '  ·  ' + m['time'] + ' МСК'
    L, ld = _layer_draw(img)
    ld.rounded_rectangle((W / 2 - f.getlength(top) / 2 - 26, 34, W / 2 + f.getlength(top) / 2 + 26, 84), radius=25, fill=(10, 14, 23, 190), outline=(255, 255, 255, 40), width=1)
    img.alpha_composite(L); d = ImageDraw.Draw(img)
    _text_center(d, (W / 2, 59), top, f, (230, 235, 240))
    # эмблемы
    es = 330
    for team, cx, col in [(m['home'], W * 0.24, c1), (m['away'], W * 0.76, c2)]:
        g = _glow((es + 200, es + 200), tuple(min(255, int(v * 1.2) + 30) for v in col), alpha=170, blur=55)
        img.alpha_composite(g, (int(cx - g.width / 2), int(300 - g.height / 2)))
        e = _emblem(team, es)
        _shadowed(img, e, (int(cx - e.width / 2), int(300 - e.height / 2)))
    d = ImageDraw.Draw(img)
    # VS
    fv = _font('display', 96)
    _text_center(d, (W / 2, 290), 'VS', fv, (255, 255, 255), stroke=3, stroke_fill=(10, 14, 23))
    # названия
    for team, cx in [(m['home'], W * 0.24), (m['away'], W * 0.76)]:
        name = SHORT.get(team, team).upper()
        fn = _fit(name, 'display', 50, 440)
        _text_center(d, (cx, 520), name, fn, (255, 255, 255), stroke=2, stroke_fill=(10, 14, 23))
    _form_dots(d, W * 0.24, 568, m.get('form_h'))
    _form_dots(d, W * 0.76, 568, m.get('form_a'))
    # низ: коэффициенты + призыв
    fo = _font('display', 34)
    fl = _font('text', 20)
    L, ld = _layer_draw(img)
    for label, val, cx in [('П1', m.get('odds_h'), W * 0.40), ('П2', m.get('odds_a'), W * 0.60)]:
        if val: ld.rounded_rectangle((cx - 90, 600, cx + 90, 672), radius=18, fill=(255, 255, 255, 26), outline=(255, 255, 255, 70), width=2)
    img.alpha_composite(L); d = ImageDraw.Draw(img)
    for label, val, cx in [('П1', m.get('odds_h'), W * 0.40), ('П2', m.get('odds_a'), W * 0.60)]:
        if not val: continue
        _text_center(d, (cx, 622), label + ' · с ОТ', fl, (190, 196, 206))
        _text_center(d, (cx, 652), '%.2f' % val, fo, (255, 255, 255))
    fc = _font('bold', 22)
    d.text((40, H - 50), '🎮 Кто победит? Голосуй в посте ниже'.replace('🎮 ', ''), font=fc, fill=NEON, anchor='lm')
    _watermark(img, W, H)
    img.convert('RGB').save(path, quality=92)
    return path

def render_day(matches, path, title='ОБЫГРАЙ ДЖАРВИСА'):
    W = 1080
    row_h = 170
    H = 300 + row_h * len(matches) + 120
    img = Image.new('RGBA', (W, H), DARK + (255,))
    # фон: пятна фирменных цветов первых матчей
    rnd = random.Random(3)
    for i, m in enumerate(matches):
        for team, cx in [(m['home'], 0.05), (m['away'], 0.95)]:
            c = TEAMS.get(team, (None, (90, 90, 90)))[1]
            blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            cy = 300 + row_h * i + row_h / 2
            ImageDraw.Draw(blob).ellipse((cx * W - 260, cy - 150, cx * W + 260, cy + 150), fill=c + (120,))
            img = Image.alpha_composite(img, blob.filter(ImageFilter.GaussianBlur(90)))
    noise = Image.effect_noise((W, H), 18).convert('L').point(lambda v: int(v * 0.08))
    nz = Image.new('RGBA', (W, H), (255, 255, 255, 0)); nz.putalpha(noise)
    img = Image.alpha_composite(img, nz)
    d = ImageDraw.Draw(img)
    ft = _font('display', 64)
    _text_center(d, (W / 2, 110), title, ft, NEON)
    fs = _font('bold', 30)
    _text_center(d, (W / 2, 185), 'КХЛ  ·  ' + (matches[0]['day_title'] if matches else ''), fs, (220, 226, 234))
    _text_center(d, (W / 2, 235), 'Жми, кто победит, — кнопки под постом', _font('text', 24), (160, 168, 180))
    for i, m in enumerate(matches):
        y = 300 + row_h * i
        L, ld = _layer_draw(img)
        ld.rounded_rectangle((40, y + 10, W - 40, y + row_h - 10), radius=28, fill=(255, 255, 255, 16), outline=(255, 255, 255, 38), width=2)
        img.alpha_composite(L); d = ImageDraw.Draw(img)
        es = 110
        for team, cx in [(m['home'], 120), (m['away'], W - 120)]:
            e = _emblem(team, es)
            _shadowed(img, e, (int(cx - e.width / 2), int(y + row_h / 2 - e.height / 2)), blur=10, off=(0, 6))
        d = ImageDraw.Draw(img)
        fn = _font('display', 30)
        d.text((200, y + row_h / 2 - 18), SHORT.get(m['home'], m['home']).upper(), font=_fit(SHORT.get(m['home'], m['home']).upper(), 'display', 30, 250), fill='white', anchor='lm')
        d.text((W - 200, y + row_h / 2 - 18), SHORT.get(m['away'], m['away']).upper(), font=_fit(SHORT.get(m['away'], m['away']).upper(), 'display', 30, 250), fill='white', anchor='rm')
        fo = _font('bold', 26)
        if m.get('odds_h'): d.text((200, y + row_h / 2 + 26), '%.2f' % m['odds_h'], font=fo, fill=(190, 196, 206), anchor='lm')
        if m.get('odds_a'): d.text((W - 200, y + row_h / 2 + 26), '%.2f' % m['odds_a'], font=fo, fill=(190, 196, 206), anchor='rm')
        _text_center(d, (W / 2, y + row_h / 2 - 14), m['time'], _font('display', 34), NEON)
        _text_center(d, (W / 2, y + row_h / 2 + 26), 'МСК', _font('text', 20), (150, 158, 170))
    _watermark(img, W, H)
    img.convert('RGB').save(path, quality=92)
    return path

if __name__ == '__main__':
    demo = [
        dict(home='Динамо Москва', away='Барыс', time='19:30', day_title='ВТОРНИК, 22 СЕНТЯБРЯ', odds_h=1.62, odds_a=2.45, form_h='WWLWW', form_a='LWLLW'),
        dict(home='Торпедо', away='Авангард', time='19:30', day_title='ВТОРНИК, 22 СЕНТЯБРЯ', odds_h=2.12, odds_a=1.80, form_h='WLWLW', form_a='WWWLW'),
        dict(home='Шанхайские Драконы', away='Автомобилист', time='19:30', day_title='ВТОРНИК, 22 СЕНТЯБРЯ', odds_h=2.55, odds_a=1.55, form_h='LLWLW', form_a='WLWWL'),
    ]
    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    for i, m in enumerate(demo):
        render_match(m, os.path.join(out, 'match_%d.jpg' % (i + 1)))
    render_day(demo, os.path.join(out, 'day.jpg'))
    print('ok')


# ------------------------- минималистичный баннер -------------------------
# Яркий «баннерный» цвет клуба (для фона): где основной цвет тёмный — берём заметный вариант
BANNER = {
    'Авангард': (196, 30, 48), 'Автомобилист': (214, 28, 36), 'Адмирал': (120, 124, 132), 'Ак Барс': (40, 170, 70),
    'Амур': (240, 120, 30), 'Барыс': (40, 170, 190), 'Динамо Москва': (30, 90, 210), 'Динамо Минск': (70, 170, 230),
    'Лада': (40, 100, 170), 'Локомотив': (210, 30, 40), 'Металлург': (238, 118, 12), 'Нефтехимик': (40, 90, 160),
    'Салават Юлаев': (40, 150, 80), 'Северсталь': (240, 190, 0), 'Сибирь': (40, 80, 150), 'СКА': (40, 90, 190),
    'Сочи': (235, 170, 20), 'Спартак': (210, 30, 40), 'Торпедо': (40, 80, 180), 'Трактор': (130, 130, 136),
    'ЦСКА': (205, 25, 40), 'Шанхайские Драконы': (240, 100, 20),
}
DARK_EMBLEMS = set()   # Трактор в новом файле уже с белым контуром   # эмблемы, которым на фоне нужна белая подложка

def _raw_emblem(team, max_w, max_h, plate=False):
    slug = TEAMS.get(team, (None,))[0]
    p = os.path.join(EMB, (slug or '') + '.png')
    if not slug or not os.path.exists(p):
        return _emblem(team, max_h)
    if plate:
        e = _emblem(team, max_h)
        e.thumbnail((max_w, max_h), Image.LANCZOS)
        return e
    im = Image.open(p).convert('RGBA')
    scale = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)

def _minimal_bg(W, H, c1, c2, seed=11):
    rnd = random.Random(seed)
    # горизонтальный градиент: цвет хозяев слева → тёмная середина → цвет гостей справа
    import numpy as np
    x = np.linspace(0, 1, W)[None, :, None]
    y = np.linspace(0, 1, H)[:, None, None]
    a1 = np.array(c1, float); a2 = np.array(c2, float); dk = np.array((22, 20, 18), float)
    wl = np.clip(1 - x / 0.55, 0, 1) ** 1.3
    wr = np.clip((x - 0.45) / 0.55, 0, 1) ** 1.3
    mid = 1 - wl - wr
    col = a1 * wl + a2 * wr + dk * mid
    col = col * (0.82 + 0.18 * (1 - np.abs(y - 0.45) * 1.2))      # чуть светлее по центру по вертикали
    base = Image.fromarray(np.clip(col, 0, 255).astype('uint8').repeat(1, axis=0), 'RGB').convert('RGBA')
    # размытые скруглённые плашки — «боке»
    for side, c in ((0, c1), (1, c2)):
        for i in range(5):
            w = rnd.randint(int(W * 0.10), int(W * 0.22)); h = int(w * rnd.uniform(0.45, 0.7))
            cx = rnd.uniform(0.02, 0.38) if side == 0 else rnd.uniform(0.62, 0.98)
            cy = rnd.uniform(0.05, 0.95)
            bright = tuple(min(255, int(v * rnd.uniform(1.05, 1.45) + 20)) for v in c)
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle((cx * W - w / 2, cy * H - h / 2, cx * W + w / 2, cy * H + h / 2),
                                                    radius=int(h * 0.28), fill=bright + (rnd.randint(70, 150),))
            base = Image.alpha_composite(base, layer.filter(ImageFilter.GaussianBlur(rnd.choice([6, 14, 26]))))
    # тёмные плашки у центра — глубина
    for i in range(3):
        w = rnd.randint(int(W * 0.14), int(W * 0.22)); h = int(w * 0.55)
        cx = rnd.uniform(0.35, 0.65); cy = rnd.choice([rnd.uniform(0.0, 0.2), rnd.uniform(0.8, 1.0)])
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((cx * W - w / 2, cy * H - h / 2, cx * W + w / 2, cy * H + h / 2), radius=int(h * 0.3), fill=(10, 10, 10, 60))
        base = Image.alpha_composite(base, layer.filter(ImageFilter.GaussianBlur(18)))
    # зерно «как на холсте»
    noise = Image.effect_noise((W, H), 40).convert('L')
    grain = Image.merge('RGBA', (noise, noise, noise, Image.new('L', (W, H), 22)))
    base = Image.alpha_composite(base, grain)
    return base

def _brand(img, W, y, size=34):
    d = ImageDraw.Draw(img)
    f = _font('display', size)
    t1, t2 = 'JARVIS', 'BET'
    w = f.getlength(t1 + t2)
    x = W / 2 - w / 2
    d.text((x, y), t1, font=f, fill=(255, 255, 255), anchor='lm')
    d.text((x + f.getlength(t1), y), t2, font=f, fill=NEON, anchor='lm')

def render_minimal(home, away, path, W=1280, H=580, caption=None):
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    img = _minimal_bg(W, H, c1, c2)
    eh = int(H * 0.44); ew = int(W * 0.21)
    e1 = _raw_emblem(home, ew, eh, plate=home in DARK_EMBLEMS)
    e2 = _raw_emblem(away, ew, eh, plate=away in DARK_EMBLEMS)
    gap = int(W * 0.045)
    cy = int(H * 0.53)
    x1 = int(W / 2 - gap / 2 - e1.width); x2 = int(W / 2 + gap / 2)
    _shadowed(img, e1, (x1, cy - e1.height // 2), blur=16, off=(0, 8), color=(0, 0, 0, 110))
    _shadowed(img, e2, (x2, cy - e2.height // 2), blur=16, off=(0, 8), color=(0, 0, 0, 110))
    _brand(img, W, int(H * 0.14))
    if caption:
        f = _font('bold', int(H * 0.042))
        ImageDraw.Draw(img).text((W / 2, int(H * 0.88)), caption, font=f, fill=(255, 255, 255, 230), anchor='mm')
    img.convert('RGB').save(path, quality=93)
    return path


# ----------------- v2: суперсэмплинг, чёткие эмблемы, зерно «холст» -----------------
def _grain(img, strength=1.0, seed=5):
    """Зерно как на исходнике: мелкий монохромный шум + едва заметное «плетение» холста."""
    import numpy as np
    rng = np.random.default_rng(seed)
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    H, W = a.shape[:2]
    n = rng.normal(0, 1, (H, W)).astype(np.float32)
    # чуть смягчаем шум, чтобы он был «плёночным», а не цифровым
    n = np.asarray(Image.fromarray(((n * 40) + 128).clip(0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.55))).astype(np.float32)
    n = (n - 128) / 40
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    weave = 0.5 * (np.sin(2 * np.pi * (xx + yy) / 3.2) + np.sin(2 * np.pi * (xx - yy) / 3.2))
    lum = a.mean(axis=2, keepdims=True) / 255.0
    amp = (0.11 * n + 0.035 * weave)[..., None] * strength
    # на светлом зерно заметнее, на совсем тёмном — мягче
    out = a * (1 + amp * (0.55 + 0.45 * lum)) + amp * 18
    return Image.fromarray(out.clip(0, 255).astype('uint8'), 'RGB')

def _emblem_sharp(team, max_w, max_h, plate=False):
    e = _raw_emblem(team, max_w * 2, max_h * 2, plate=plate)   # на холсте x2
    return e

def render_minimal2(home, away, path, W=1280, H=580, caption=None, grain=1.0):
    S = 2                                   # рисуем в 2 раза крупнее и уменьшаем — гладкие края и градиенты
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    img = _minimal_bg(WW, HH, c1, c2)
    eh = int(H * 0.42); ew = int(W * 0.20)
    e1 = _emblem_sharp(home, ew, eh, plate=home in DARK_EMBLEMS)
    e2 = _emblem_sharp(away, ew, eh, plate=away in DARK_EMBLEMS)
    gap = int(WW * 0.05); cy = int(HH * 0.54)
    x1 = int(WW / 2 - gap / 2 - e1.width); x2 = int(WW / 2 + gap / 2)
    _shadowed(img, e1, (x1, cy - e1.height // 2), blur=28, off=(0, 14), color=(0, 0, 0, 120))
    _shadowed(img, e2, (x2, cy - e2.height // 2), blur=28, off=(0, 14), color=(0, 0, 0, 120))
    _brand(img, WW, int(HH * 0.145), size=int(34 * S))
    if caption:
        f = _font('bold', int(H * 0.042 * S))
        ImageDraw.Draw(img).text((WW / 2, int(HH * 0.885)), caption, font=f, fill=(255, 255, 255), anchor='mm')
    img = img.convert('RGB').resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    img = _grain(img, grain)
    if path.lower().endswith('.png'): img.save(path, optimize=True)
    else: img.save(path, quality=97, subsampling=0)
    return path


# ----------------- v3: фон и текстура ближе к образцу -----------------
def _minimal_bg3(W, H, c1, c2, S=2, seed=11):
    import numpy as np
    rnd = random.Random(seed)
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    a1 = np.array(c1, np.float32); a2 = np.array(c2, np.float32)
    mid = (a1 + a2) / 2 * 0.28 + 12                       # середина — смесь цветов, притушенная, а не «грязная»
    t = x
    wl = np.clip(1 - t / 0.58, 0, 1); wr = np.clip((t - 0.42) / 0.58, 0, 1)
    wl, wr = wl ** 1.15, wr ** 1.15
    col = a1 * wl + a2 * wr + mid * (1 - wl - wr)
    col = col * (0.78 + 0.30 * (1 - y))                   # сверху светлее, к низу темнее
    base = Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')

    def shape(cx, cy, w, h, c, alpha, blur):
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle(box, radius=int(min(w, h) * 0.26), fill=alpha)
        # внутри плашки — лёгкий градиент (светлее к верхнему краю), как у образца
        g = Image.linear_gradient('L').resize((1, max(1, box[3] - box[1])))
        gfull = Image.new('L', (W, H), 0); gfull.paste(g.resize((max(1, box[2] - box[0]), g.height)).point(lambda v: 255 - v // 2), (box[0], box[1]))
        m = ImageChops.multiply(m, gfull.point(lambda v: max(v, 90)))
        layer = Image.new('RGBA', (W, H), c + (0,)); layer.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
        return layer

    for side, c in ((0, c1), (1, c2)):
        bright = tuple(min(255, int(v * 1.25 + 25)) for v in c)
        deep = tuple(int(v * 0.55) for v in c)
        spots = [(0.16, 0.08, 0.20, 0.18, bright, 140, 20), (0.06, 0.36, 0.16, 0.22, bright, 175, 5),
                 (0.03, 0.75, 0.18, 0.30, deep, 110, 28), (0.22, 0.95, 0.12, 0.16, bright, 160, 4)]
        for (sx, sy, sw, sh, cc, al, bl) in spots:
            cx = (sx if side == 0 else 1 - sx) * W + rnd.uniform(-0.02, 0.02) * W
            cy = (sy if side == 0 else 1 - sy * 0.9) * H + rnd.uniform(-0.05, 0.05) * H   # справа — зеркально по вертикали, чтобы не было «копии»
            base = Image.alpha_composite(base, shape(cx, cy, sw * W, sh * H * 1.6, cc, al, bl * S))
    # тёмные плашки у центра внизу и вверху
    for (cx, cy, w, h) in [(0.36, 0.02, 0.16, 0.22), (0.62, 0.95, 0.20, 0.26)]:
        base = Image.alpha_composite(base, shape(cx * W, cy * H, w * W, h * H, (8, 8, 8), 90, 14 * S))
    return base

def _canvas_texture(img, strength=1.0, seed=3):
    """Текстура холста: диагональные «нити» (саржевое плетение) + мелкое зерно."""
    import numpy as np
    rng = np.random.default_rng(seed)
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ang = np.deg2rad(-30)
    u = xx * np.cos(ang) + yy * np.sin(ang)
    v = -xx * np.sin(ang) + yy * np.cos(ang)
    # неровность нитей: плавный шум сдвигает фазу
    low = rng.normal(0, 1, (H // 8 + 2, W // 8 + 2)).astype(np.float32)
    low = np.asarray(Image.fromarray(((low * 30) + 128).clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC)).astype(np.float32)
    phase = (low - 128) / 30 * 0.9
    thread = np.sin(2 * np.pi * u / 4.6 + phase)                       # основные нити
    cross = np.sin(2 * np.pi * v / 3.4) * 0.35                         # поперечное плетение
    weave = np.where(thread > 0, thread, thread * 0.6) + cross
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    tex = (0.055 * weave + 0.045 * fine) * strength
    lum = a.mean(axis=2, keepdims=True) / 255.0
    out = a * (1 + tex[..., None] * (0.6 + 0.8 * lum)) + tex[..., None] * 10
    return Image.fromarray(out.clip(0, 255).astype('uint8'), 'RGB')

def render_minimal3(home, away, path, W=1280, H=580, caption=None, grain=1.0):
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    img = _minimal_bg3(WW, HH, c1, c2, S=S)
    eh = int(H * 0.42); ew = int(W * 0.20)
    e1 = _raw_emblem(home, ew * S, eh * S, plate=home in DARK_EMBLEMS)
    e2 = _raw_emblem(away, ew * S, eh * S, plate=away in DARK_EMBLEMS)
    gap = int(WW * 0.05); cy = int(HH * 0.55)
    x1 = int(WW / 2 - gap / 2 - e1.width); x2 = int(WW / 2 + gap / 2)
    _shadowed(img, e1, (x1, cy - e1.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 120))
    _shadowed(img, e2, (x2, cy - e2.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 120))
    _brand(img, WW, int(HH * 0.145), size=int(34 * S))
    if caption:
        f = _font('bold', int(H * 0.042 * S))
        ImageDraw.Draw(img).text((WW / 2, int(HH * 0.89)), caption, font=f, fill=(255, 255, 255), anchor='mm')
    img = img.convert('RGB').resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))
    img = _canvas_texture(img, grain)
    if path.lower().endswith('.png'): img.save(path, optimize=True)
    else: img.save(path, quality=97, subsampling=0)
    return path


# ----------------- v4: «жидкий» перелив двух цветов, как два моря -----------------
def _fluid_bg(W, H, c1, c2, seed=21):
    import numpy as np
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = xx / W; y = yy / H * (H / W)          # квадратные «единицы», чтобы волны не растягивались

    def flow(px, py, n=5, base=2.2, amp=1.0):
        acc = np.zeros_like(px)
        for k in range(n):
            ang = rng.uniform(0, np.pi)
            f = base * (1.75 ** k) * rng.uniform(0.8, 1.2)
            ph = rng.uniform(0, 2 * np.pi)
            acc += (amp / (1.6 ** k)) * np.sin(2 * np.pi * f * (px * np.cos(ang) + py * np.sin(ang)) + ph)
        return acc

    # спокойные, крупные «течения» — как переливы воды или шёлка
    wx = x + 0.09 * flow(x, y, 3, 0.9); wy = y + 0.09 * flow(x, y, 3, 0.9)
    wx2 = wx + 0.03 * flow(wx, wy, 2, 1.6); wy2 = wy + 0.03 * flow(wx, wy, 2, 1.6)
    # граница «морей»: широкая плавная волна
    edge = (wx2 - 0.5) * 2.4 + 0.45 * flow(wx2 * 0.7, wy2 * 0.7, 2, 0.9)
    m = 1 / (1 + np.exp(-edge * 1.7))
    # баланс: каждый клуб занимает свою половину, волна только «гуляет» у стыка
    base_m = 1 / (1 + np.exp(-(xx / W - 0.5) * 7.5))
    m = 0.35 * m + 0.65 * base_m
    a1 = np.array(c1, np.float32); a2 = np.array(c2, np.float32)
    col = a1[None, None, :] * (1 - m[..., None]) + a2[None, None, :] * m[..., None]
    # переливы яркости: длинные мягкие полосы света и тени
    shade = 0.5 + 0.5 * np.tanh(1.1 * flow(wx2 * 0.9, wy2 * 0.9, 3, 1.1))
    col = col * (0.58 + 0.56 * shade)[..., None]
    sheen = np.exp(-((np.sin(2 * np.pi * (wx2 * 0.9 + 0.35 * flow(wx2, wy2, 2, 0.8))) - 0.9) ** 2) / 0.06)
    col = col + (sheen * 22)[..., None]
    seam = np.exp(-((m - 0.5) ** 2) / 0.03)
    col = col * (1 - 0.18 * seam[..., None])
    # мягкая виньетка к углам и лёгкое затемнение за эмблемами (контраст)
    r = np.sqrt(((xx / W - 0.5) * 1.1) ** 2 + ((yy / H - 0.55) * 0.9) ** 2)
    col = col * (1 - 0.35 * np.clip(r - 0.35, 0, 1)[..., None])
    return Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')

def render_minimal4(home, away, path, W=1280, H=580, caption=None, grain=1.0, seed=None):
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    if seed is None: seed = (sum(map(ord, home + away)) % 997)
    img = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((WW, HH), Image.BICUBIC)   # фон гладкий — считаем в половинном размере
    eh = int(H * 0.42); ew = int(W * 0.20)
    e1 = _raw_emblem(home, ew * S, eh * S, plate=home in DARK_EMBLEMS)
    e2 = _raw_emblem(away, ew * S, eh * S, plate=away in DARK_EMBLEMS)
    gap = int(WW * 0.05); cy = int(HH * 0.55)
    x1 = int(WW / 2 - gap / 2 - e1.width); x2 = int(WW / 2 + gap / 2)
    _shadowed(img, e1, (x1, cy - e1.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    _shadowed(img, e2, (x2, cy - e2.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    _brand(img, WW, int(HH * 0.145), size=int(34 * S))
    if caption:
        f = _font('bold', int(H * 0.042 * S))
        ImageDraw.Draw(img).text((WW / 2, int(HH * 0.89)), caption, font=f, fill=(255, 255, 255), anchor='mm')
    img = img.convert('RGB').resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))
    img = _canvas_texture(img, grain)
    if path.lower().endswith('.png'): img.save(path, optimize=True)
    else: img.save(path, quality=97, subsampling=0)
    return path


# ----------------- v5: баннер с информацией -----------------
def _chip(img, cx, cy, text, font, pad_x=22, pad_y=12, fill=(10, 14, 23, 150), outline=(255, 255, 255, 60), color=(255, 255, 255), radius=None):
    L, ld = _layer_draw(img)
    w = font.getlength(text); bb = font.getbbox('ЁАgy0'); h = bb[3] - bb[1]
    box = (cx - w / 2 - pad_x, cy - h / 2 - pad_y, cx + w / 2 + pad_x, cy + h / 2 + pad_y)
    ld.rounded_rectangle(box, radius=radius or int((box[3] - box[1]) / 2), fill=fill, outline=outline, width=2)
    img.alpha_composite(L)
    ImageDraw.Draw(img).text((cx, cy), text, font=font, fill=color, anchor='mm')
    return box

def _team_block(img, team, info, cx, top, S, align):
    d = ImageDraw.Draw(img)
    name = SHORT.get(team, team).upper()
    fn = _fit(name, 'display', int(38 * S), int(300 * S))
    anchor = 'lm' if align == 'left' else 'rm'
    x = cx
    d.text((x, top), name, font=fn, fill=(255, 255, 255), anchor=anchor, stroke_width=int(1 * S), stroke_fill=(0, 0, 0, 90))
    y = top + int(44 * S)
    fs = _font('text', int(21 * S))
    if info.get('place'):
        d.text((x, y), info['place'], font=fs, fill=(235, 238, 242), anchor=anchor)
        y += int(38 * S)
    form = (info.get('form') or '')[-5:]
    if form:
        r = int(8 * S); gap = int(26 * S)
        xs = [x + i * gap + r for i in range(len(form))] if align == 'left' else [x - (len(form) - 1 - i) * gap - r for i in range(len(form))]
        L, ld = _layer_draw(img)
        for xi, ch in zip(xs, form):
            col = NEON if ch in 'WВ' else (RED if ch in 'LП' else (255, 200, 60))
            ld.ellipse((xi - r, y - r, xi + r, y + r), fill=col + (255,), outline=(0, 0, 0, 90), width=max(1, S))
        img.alpha_composite(L)
        y += int(34 * S)
    if info.get('streak'):
        fb = _font('bold', int(18 * S))
        w = fb.getlength(info['streak'])
        ccx = x + w / 2 + int(16 * S) if align == 'left' else x - w / 2 - int(16 * S)
        _chip(img, ccx, y + int(4 * S), info['streak'], fb, pad_x=int(14 * S), pad_y=int(8 * S), fill=(255, 255, 255, 36), outline=(255, 255, 255, 70))

def render_info(home, away, path, info, W=1280, H=640, grain=1.0, seed=None):
    """info = {when:'ВТ 22.09 · 19:30 МСК', odds:(1.62, 4.10, 2.45), home:{place, form, streak}, away:{...}}"""
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    if seed is None: seed = (sum(map(ord, home + away)) % 997)
    img = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((WW, HH), Image.BICUBIC)
    # мягкое затемнение под текстовыми блоками по бокам и снизу — читаемость без «плашек»
    import numpy as np
    yy, xx = np.mgrid[0:HH, 0:WW].astype(np.float32)
    dim = 0.38 * np.exp(-(((yy / HH) - 0.95) ** 2) / 0.02) + 0.22 * (np.exp(-(((xx / WW) - 0.13) ** 2) / 0.02) + np.exp(-(((xx / WW) - 0.87) ** 2) / 0.02)) * np.exp(-(((yy / HH) - 0.55) ** 2) / 0.06)
    dk = Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L')
    shade = Image.new('RGBA', (WW, HH), (5, 8, 14, 0)); shade.putalpha(dk)
    img = Image.alpha_composite(img, shade)
    # эмблемы в центре
    eh = int(H * 0.36); ew = int(W * 0.17)
    e1 = _raw_emblem(home, ew * S, eh * S, plate=home in DARK_EMBLEMS)
    e2 = _raw_emblem(away, ew * S, eh * S, plate=away in DARK_EMBLEMS)
    gap = int(WW * 0.045); cy = int(HH * 0.47)
    x1 = int(WW / 2 - gap / 2 - e1.width); x2 = int(WW / 2 + gap / 2)
    _shadowed(img, e1, (x1, cy - e1.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    _shadowed(img, e2, (x2, cy - e2.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    _brand(img, WW, int(HH * 0.10), size=int(30 * S))
    # блоки команд по бокам
    top = int(HH * 0.36)
    _team_block(img, home, info.get('home', {}), int(WW * 0.05), top, S, 'left')
    _team_block(img, away, info.get('away', {}), int(WW * 0.95), top, S, 'right')
    # низ: когда + коэффициенты
    fw = _font('bold', int(22 * S))
    if info.get('when'):
        _chip(img, WW / 2, int(HH * 0.80), info['when'], fw, pad_x=int(24 * S), pad_y=int(12 * S), fill=(10, 14, 23, 170), outline=NEON + (170,), color=(255, 255, 255))
    if info.get('odds'):
        fo = _font('bold', int(20 * S))
        labels = ['П1', 'Х', 'П2']
        vals = [v for v in info['odds']]
        step = int(150 * S)
        xs = [WW / 2 + (i - (len(vals) - 1) / 2) * step for i in range(len(vals))]
        for lab, v, x in zip(labels if len(vals) == 3 else ['П1', 'П2'], vals, xs):
            _chip(img, x, int(HH * 0.915), lab + '  ' + ('%.2f' % v), fo, pad_x=int(18 * S), pad_y=int(9 * S), fill=(255, 255, 255, 30), outline=(255, 255, 255, 60))
    img = img.convert('RGB').resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))
    img = _canvas_texture(img, grain)
    img.save(path, optimize=True) if path.lower().endswith('.png') else img.save(path, quality=97, subsampling=0)
    return path


# ----------------- афиша дня: капсулы матчей -----------------
def _circle_emblem(team, d, S):
    """Эмблема в тёмном круге с тонким белым ободком."""
    im = Image.new('RGBA', (d, d), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    e = _raw_emblem(team, int(d * 0.70), int(d * 0.70), plate=False)
    # тёмная эмблема (Динамо, Лада, Сибирь…) — на светлом круге, светлая — на тёмном
    import numpy as np
    ea = np.asarray(e).astype(np.float32); op = ea[..., 3] > 128
    lum = (ea[..., :3][op] @ np.array([0.299, 0.587, 0.114], np.float32)).mean() if op.any() else 128
    dark = lum < 95
    dr.ellipse((0, 0, d - 1, d - 1), fill=(246, 247, 250, 255) if dark else (12, 16, 26, 255),
               outline=(12, 16, 26, 255) if dark else (255, 255, 255, 255), width=max(3, d // 28))
    im.alpha_composite(e, ((d - e.width) // 2, (d - e.height) // 2))
    return im

def _capsule(img, cx, cy, m, S):
    W_, H_ = int(560 * S), int(118 * S)
    x0, y0 = int(cx - W_ / 2), int(cy - H_ / 2)
    c1 = BANNER.get(m['home'], (120, 120, 120)); c2 = BANNER.get(m['away'], (120, 120, 120))
    import numpy as np
    # тело капсулы: цвет хозяев слева → белый центр → цвет гостей справа
    xs = np.linspace(0, 1, W_, dtype=np.float32)[None, :, None]
    a1 = np.array(c1, np.float32); a2 = np.array(c2, np.float32); wh = np.array((246, 247, 250), np.float32)
    left = np.clip(1 - xs / 0.30, 0, 1); right = np.clip((xs - 0.70) / 0.30, 0, 1)
    body = a1 * left + a2 * right + wh * (1 - left - right)
    body = np.repeat(body, H_, axis=0)
    # лёгкие диагональные «волны» в цветных концах
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    waves = (np.sin((xx + yy * 0.8) / (9 * S)) * 0.5 + 0.5) * 0.10 * (left + right)[0][None, :, 0]
    body = body * (1 - waves[..., None])
    cap = Image.fromarray(np.clip(body, 0, 255).astype('uint8'), 'RGB').convert('RGBA')
    mask = Image.new('L', (W_, H_), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W_ - 1, H_ - 1), radius=H_ // 2, fill=255)
    cap.putalpha(mask)
    _shadowed(img, cap, (x0, y0), blur=18 * S, off=(0, 8 * S), color=(0, 0, 0, 120))
    # эмблемы в кругах
    d = int(H_ * 1.08)
    for team, ex in ((m['home'], x0 + int(W_ * 0.20)), (m['away'], x0 + int(W_ * 0.80))):
        ce = _circle_emblem(team, d, S)
        _shadowed(img, ce, (int(ex - d / 2), int(cy - d / 2)), blur=10 * S, off=(0, 4 * S), color=(0, 0, 0, 110))
    dr = ImageDraw.Draw(img)
    dr.text((cx, cy - int(10 * S)), m['time'], font=_font('display', int(46 * S)), fill=(12, 16, 26), anchor='mm')
    dr.text((cx, cy + int(32 * S)), 'МСК', font=_font('bold', int(16 * S)), fill=(110, 116, 128), anchor='mm')
    # коэффициенты под капсулой: самый низкий (фаворит букмекера) — неоновый
    odds = m.get('odds') or ()
    if odds:
        fo = _font('bold', int(19 * S))
        best = min(range(len(odds)), key=lambda i: odds[i])
        step = int(92 * S)
        for i, v in enumerate(odds):
            x = cx + (i - (len(odds) - 1) / 2) * step
            on = i == best
            _chip(img, x, cy + H_ / 2 + int(26 * S), '%.2f' % v, fo, pad_x=int(16 * S), pad_y=int(7 * S),
                  fill=(NEON + (255,)) if on else (22, 28, 40, 235), outline=(NEON + (255,)) if on else (255, 255, 255, 60),
                  color=(10, 14, 23) if on else (235, 238, 242), radius=int(8 * S))

def render_day2(matches, path, date_title, W=1280, grain=1.0):
    S = 2
    rows = (len(matches) + 1) // 2
    H = 500 + rows * 215 + 110
    WW, HH = W * S, H * S
    base = _fluid_bg(WW // 2, HH // 2, (26, 40, 70), (14, 20, 34), seed=5).resize((WW, HH), Image.BICUBIC)
    img = base
    # неоновое свечение сверху
    glow = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((WW * 0.25, -HH * 0.12, WW * 0.75, HH * 0.18), fill=NEON + (46,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(90 * S)))
    dr = ImageDraw.Draw(img)
    _brand(img, WW, int(95 * S), size=int(40 * S))
    dr.text((WW / 2, int(160 * S)), 'ОБЫГРАЙ ДЖАРВИСА', font=_font('display', int(58 * S)), fill=NEON, anchor='mm')
    fd = _font('display', int(34 * S))
    box = _chip(img, WW / 2, int(262 * S), date_title, fd, pad_x=int(46 * S), pad_y=int(22 * S), fill=(255, 255, 255, 22), outline=(255, 255, 255, 50), radius=int(26 * S))
    ImageDraw.Draw(img).text((WW / 2, box[3] + int(26 * S)), 'время московское', font=_font('text', int(19 * S)), fill=(170, 178, 190), anchor='mm')
    # капсулы: по две в ряд, нечётная последняя — по центру
    top = int(455 * S)
    for i, m in enumerate(matches):
        r, c = divmod(i, 2)
        last_single = (len(matches) % 2 == 1) and i == len(matches) - 1
        cx = WW / 2 if last_single else (WW * 0.265 if c == 0 else WW * 0.735)
        cy = top + r * int(215 * S)
        _capsule(img, cx, cy, m, S)
    dr = ImageDraw.Draw(img)
    dr.text((WW / 2, HH - int(80 * S)), 'Кто победит? Жми кнопку под постом', font=_font('bold', int(26 * S)), fill=(255, 255, 255), anchor='mm')
    dr.text((WW / 2, HH - int(44 * S)), 'Коэффициенты — П1 · Х · П2 в основное время', font=_font('text', int(18 * S)), fill=(150, 158, 170), anchor='mm')
    img = img.convert('RGB').resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))
    img = _canvas_texture(img, grain * 0.8)
    img.save(path, optimize=True) if path.lower().endswith('.png') else img.save(path, quality=97, subsampling=0)
    return path


def render_plate(home, away, path, W=1280, H=640, grain=1.0, seed=None):
    """Фон + эмблемы + затемнения под текст, без текста — текст накладывается отдельно."""
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    if seed is None: seed = (sum(map(ord, home + away)) % 997)
    img = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((WW, HH), Image.BICUBIC)
    import numpy as np
    yy, xx = np.mgrid[0:HH, 0:WW].astype(np.float32)
    dim = 0.38 * np.exp(-(((yy / HH) - 0.95) ** 2) / 0.02) + 0.22 * (np.exp(-(((xx / WW) - 0.13) ** 2) / 0.02) + np.exp(-(((xx / WW) - 0.87) ** 2) / 0.02)) * np.exp(-(((yy / HH) - 0.55) ** 2) / 0.06)
    dk = Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L')
    shade = Image.new('RGBA', (WW, HH), (5, 8, 14, 0)); shade.putalpha(dk)
    img = Image.alpha_composite(img, shade)
    eh = int(H * 0.36); ew = int(W * 0.17)
    e1 = _raw_emblem(home, ew * S, eh * S); e2 = _raw_emblem(away, ew * S, eh * S)
    gap = int(WW * 0.045); cy = int(HH * 0.47)
    _shadowed(img, e1, (int(WW / 2 - gap / 2 - e1.width), cy - e1.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    _shadowed(img, e2, (int(WW / 2 + gap / 2), cy - e2.height // 2), blur=30, off=(0, 16), color=(0, 0, 0, 130))
    img = img.convert('RGB').resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))
    img = _canvas_texture(img, grain)
    img.save(path, optimize=True)
    return path


# ----------------- v7: чёткий текст поверх фона, сочетание шрифтов -----------------
_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS7 = {  # (файл, вес для вариативных шрифтов)
    'brand': (_FD + '/Unbounded[wght].ttf', 800),          # широкий гротеск — логотип
    'team': (_FD + '/Montserrat[wght].ttf', 900),          # как счёт в постах КХЛ — названия команд
    'time': (_FD + '/Montserrat[wght].ttf', 900),          # время матча
    'info': (_FD + '/Unbounded[wght].ttf', 400),           # широкие капс-подписи, как в постах КХЛ
    'num': (_FD + '/Montserrat[wght].ttf', 900),           # цифры коэффициентов
    'form': (_FD + '/Montserrat[wght].ttf', 900),          # буквы В/П/О в кружках формы
    'accent': (_FD + '/Montserrat-Italic[wght].ttf', 800), # курсив — акценты
}
FONTS_SIDE = {  # набор шрифтов первого варианта (информация по бокам)
    'brand': (_FD + '/Unbounded[wght].ttf', 800),
    'team': (_FD + '/Oswald[wght].ttf', 700),
    'time': (_FD + '/Unbounded[wght].ttf', 700),
    'info': (_FD + '/Manrope[wght].ttf', 600),
    'num': (_FD + '/Manrope[wght].ttf', 800),
    'form': (_FD + '/Manrope[wght].ttf', 800),
}
_FONTS_CARDS = None
ACC = (255, 194, 61)       # золото — акцент вместо неона
ACC_DARK = (26, 20, 6)
def _f7(kind, size):
    p, w = FONTS7[kind]
    f = ImageFont.truetype(p, size)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f

def _spaced(d, xy, text, font, fill, spacing, anchor='l'):
    """Текст с разрядкой; anchor l/r/m по горизонтали, по вертикали — центр."""
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor == 'r': x -= total
    elif anchor == 'm': x -= total / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=font, fill=fill, anchor='lm')
        x += w + spacing
    return total

def render_clean(home, away, info, path, W=1280, H=640, grain=1.0, seed=None):
    global FONTS7
    saved = FONTS7; FONTS7 = dict(saved, **FONTS_SIDE)
    try:
        return _render_clean(home, away, info, path, W, H, grain, seed)
    finally:
        FONTS7 = saved

def _render_clean(home, away, info, path, W=1280, H=640, grain=1.0, seed=None):
    S = 2
    WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    if seed is None: seed = (sum(map(ord, home + away)) % 997)
    # 1) фон: перелив + затемнения + текстура — текстура только здесь
    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.42 * np.exp(-(((yy / H) - 0.95) ** 2) / 0.02) + 0.26 * (np.exp(-(((xx / W) - 0.13) ** 2) / 0.02) + np.exp(-(((xx / W) - 0.87) ** 2) / 0.02)) * np.exp(-(((yy / H) - 0.55) ** 2) / 0.06)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0)); shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')
    # 2) всё содержимое — на прозрачном слое x2, без шума, потом уменьшаем
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    eh = int(H * 0.36) * S; ew = int(W * 0.17) * S
    def needs_plate(team, col):
        # эмблема почти того же цвета, что фон её половины (Динамо на синем), — даём белый контур
        e = _raw_emblem(team, 200, 200)
        a = np.asarray(e).astype(np.float32); op = a[..., 3] > 128
        if not op.any(): return False
        mean = a[..., :3][op].mean(axis=0)
        return float(np.sqrt(((mean - np.array(col, np.float32)) ** 2).sum())) < 110
    e1 = _raw_emblem(home, ew, eh, plate=needs_plate(home, c1)); e2 = _raw_emblem(away, ew, eh, plate=needs_plate(away, c2))
    gap = int(WW * 0.045); cy = int(HH * 0.47)
    _shadowed(ov, e1, (int(WW / 2 - gap / 2 - e1.width), cy - e1.height // 2), blur=26, off=(0, 14), color=(0, 0, 0, 120))
    _shadowed(ov, e2, (int(WW / 2 + gap / 2), cy - e2.height // 2), blur=26, off=(0, 14), color=(0, 0, 0, 120))
    d = ImageDraw.Draw(ov)
    # логотип: JARVIS | KXL
    fb = _f7('brand', 26 * S)
    sp = 3 * S; bar = 22 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in 'KXL') + sp * 2
    x0 = WW / 2 - (w1 + 2 * bar + w2) / 2; yb = int(58 * S)
    _spaced(d, (x0, yb), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, yb - 14 * S, x0 + w1 + bar + 1.5 * S, yb + 14 * S), radius=S, fill=(255, 255, 255, 150))
    _spaced(d, (x0 + w1 + 2 * bar, yb), 'KXL', fb, ACC + (255,), sp)
    # блоки команд
    def team_block(team, t, x, align):
        anc = 'l' if align == 'left' else 'r'
        name = SHORT.get(team, team).upper()
        size = 66 * S
        ft = _f7('team', size)
        while ft.getlength(name) > 318 * S and size > 34 * S:
            size -= 2 * S; ft = _f7('team', size)
        y = int(250 * S)
        d.text((x, y), name, font=ft, fill=(255, 255, 255, 255), anchor=anc + 'm', stroke_width=0)
        y += int(56 * S)
        d.text((x, y), t['line'], font=_f7('info', 22 * S), fill=(232, 236, 242, 255), anchor=anc + 'm')
        y += int(44 * S)
        form = t.get('form', '')[-5:]
        _form_row(d, x, y, form, S, align=align)
    team_block(home, info['home'], int(64 * S), 'left')
    team_block(away, info['away'], int(WW - 64 * S), 'right')
    # время
    ft = _f7('time', 22 * S)
    tw = ft.getlength(info['when'])
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 486 * S, WW / 2 + tw / 2 + 30 * S, 540 * S), radius=27 * S, fill=(8, 12, 20, 200), outline=ACC + (220,), width=2 * S)
    ov.alpha_composite(L); d = ImageDraw.Draw(ov)
    d.text((WW / 2, 513 * S), info['when'], font=ft, fill=(255, 255, 255, 255), anchor='mm')
    # коэффициенты: подпись + число; фаворит букмекера — неоновая рамка
    odds = info['odds']; labels = ['П1', 'Х', 'П2']
    best = min(range(3), key=lambda i: odds[i])
    fl = _f7('info', 16 * S); fn = _f7('num', 22 * S)
    cw = 132 * S; gapc = 16 * S
    x = WW / 2 - (3 * cw + 2 * gapc) / 2
    L, ld = _layer_draw(ov)
    for i in range(3):
        bx = (x + i * (cw + gapc), 560 * S, x + i * (cw + gapc) + cw, 604 * S)
        ld.rounded_rectangle(bx, radius=22 * S, fill=(8, 12, 20, 170), outline=(ACC + (230,)) if i == best else (255, 255, 255, 70), width=2 * S)
    ov.alpha_composite(L); d = ImageDraw.Draw(ov)
    for i in range(3):
        cx0 = x + i * (cw + gapc)
        d.text((cx0 + 26 * S, 582 * S), labels[i], font=fl, fill=(170, 178, 192, 255), anchor='lm')
        d.text((cx0 + cw - 22 * S, 582 * S), '%.2f' % odds[i], font=fn, fill=(ACC + (255,)) if i == best else (255, 255, 255, 255), anchor='rm')
    d.text((WW / 2, 622 * S), 'коэффициенты в основное время по данным аналитической таблицы', font=_f7('info', 14 * S), fill=(196, 202, 214, 255), anchor='mm')
    ov = ov.resize((W, H), Image.LANCZOS)
    out = Image.alpha_composite(bg, ov).convert('RGB')
    out.save(path, optimize=True) if path.lower().endswith('.png') else out.save(path, quality=97, subsampling=0)
    return path


# ----------------- v8: карточки команд — всё о команде в одном блоке -----------------
def _form_row(d, cx, y, form, S, align='center'):
    """W — победа (зелёный), L — поражение (красный),
    X — победа в ОТ/буллитах (половина белая, половина зелёная), O — поражение в ОТ/буллитах (белый + красный)."""
    r = 14 * S; g = 34 * S
    GREEN = (34, 197, 94, 255); RED_ = (226, 58, 78, 255); WHITE = (240, 243, 248, 255)
    ff = _f7('form', 16 * S); fo = _f7('form', 11 * S)
    if align == 'left': x0 = cx + r
    elif align == 'right': x0 = cx - r - (len(form) - 1) * g
    else: x0 = cx - (len(form) - 1) * g / 2
    for i, ch in enumerate(form):
        xi = x0 + i * g
        box = (xi - r, y - r, xi + r, y + r)
        if ch in 'WL':
            d.ellipse(box, fill=GREEN if ch == 'W' else RED_)
            d.text((xi, y + S), 'В' if ch == 'W' else 'П', font=ff, fill=(255, 255, 255, 255), anchor='mm')
        else:
            col = GREEN if ch == 'X' else RED_
            d.pieslice(box, 90, 270, fill=WHITE)      # левая половина белая
            d.pieslice(box, 270, 450, fill=col)       # правая — итог
            d.text((xi, y + S), 'ОТ', font=fo, fill=(20, 24, 32, 255), anchor='mm', stroke_width=max(1, S), stroke_fill=(255, 255, 255, 255))

def render_cards(home, away, info, path, W=1280, H=640, grain=1.0, seed=None):
    import numpy as np
    S = 2; WW, HH = W * S, H * S
    c1 = BANNER.get(home, (120, 120, 120)); c2 = BANNER.get(away, (120, 120, 120))
    if seed is None: seed = (sum(map(ord, home + away)) % 997)
    bg = _fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dim = 0.40 * np.exp(-(((yy / H) - 0.97) ** 2) / 0.02)
    shade = Image.new('RGBA', (W, H), (5, 8, 14, 0)); shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
    bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
    bg = _canvas_texture(bg, grain).convert('RGBA')
    # стеклянные карточки: размытый фон под ними + тёмная заливка
    cards = [(56, 104, 580, 470), (700, 104, 1224, 470)]
    for (x1, y1, x2, y2) in cards:
        reg = bg.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(18))
        m = Image.new('L', (x2 - x1, y2 - y1), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius=28, fill=255)
        bg.paste(reg, (x1, y1), m)
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
    L, ld = _layer_draw(ov)
    for (x1, y1, x2, y2) in cards:
        ld.rounded_rectangle((x1 * S, y1 * S, x2 * S, y2 * S), radius=28 * S, fill=(8, 12, 20, 150), outline=(255, 255, 255, 46), width=2 * S)
    ov.alpha_composite(L)
    d = ImageDraw.Draw(ov)
    # бренд
    fb = _f7('brand', 26 * S); sp = 3 * S; bar = 22 * S
    w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
    w2 = sum(fb.getlength(c) for c in 'KXL') + sp * 2
    x0 = WW / 2 - (w1 + 2 * bar + w2) / 2; yb = int(56 * S)
    _spaced(d, (x0, yb), 'JARVIS', fb, (255, 255, 255, 255), sp)
    d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, yb - 14 * S, x0 + w1 + bar + 1.5 * S, yb + 14 * S), radius=S, fill=(255, 255, 255, 150))
    _spaced(d, (x0 + w1 + 2 * bar, yb), 'KXL', fb, ACC + (255,), sp)
    def plate_needed(team):
        e = _raw_emblem(team, 200, 200)
        a = np.asarray(e).astype(np.float32); op = a[..., 3] > 128
        if not op.any(): return False
        mean = a[..., :3][op].mean(axis=0)
        return float(0.3 * mean[0] + 0.59 * mean[1] + 0.11 * mean[2]) < 95
    for team, t, (x1, y1, x2, y2) in ((home, info['home'], cards[0]), (away, info['away'], cards[1])):
        cx = (x1 + x2) / 2 * S
        e = _raw_emblem(team, 200 * S, 150 * S, plate=plate_needed(team))
        _shadowed(ov, e, (int(cx - e.width / 2), int(y1 * S + 24 * S + (150 * S - e.height) / 2)), blur=20, off=(0, 10), color=(0, 0, 0, 110))
        d = ImageDraw.Draw(ov)
        name = SHORT.get(team, team).upper()
        size = 54 * S; ft = _f7('team', size)
        while ft.getlength(name) > 440 * S and size > 34 * S:
            size -= 2 * S; ft = _f7('team', size)
        d.text((cx, (y1 + 214) * S), name, font=ft, fill=(255, 255, 255, 255), anchor='mm')
        d.text((cx, (y1 + 260) * S), t['line'].upper(), font=_f7('info', 17 * S), fill=(214, 220, 230, 255), anchor='mm')
        # разделитель + форма
        d.line((cx - 150 * S, (y1 + 284) * S, cx + 150 * S, (y1 + 284) * S), fill=(255, 255, 255, 36), width=S)
        form = t.get('form', '')[-5:]
        _form_row(d, cx, (y1 + 322) * S, form, S)
    # VS между карточками
    d.text((WW / 2, (104 + 470) / 2 * S), 'VS', font=_f7('team', 26 * S), fill=(255, 255, 255, 200), anchor='mm')
    # подписи-акценты (серия) — под карточкой, на одной линии, чтобы не ломать сетку
    # время + коэффициенты
    ft = _f7('time', 24 * S); tw = ft.getlength(info['when'])
    L, ld = _layer_draw(ov)
    ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 490 * S, WW / 2 + tw / 2 + 30 * S, 542 * S), radius=26 * S, fill=(8, 12, 20, 210), outline=ACC + (220,), width=2 * S)
    odds = info['odds']; labels = ['П1', 'Х', 'П2']
    best = min(range(3), key=lambda i: odds[i])
    cw = 132 * S; gapc = 16 * S; xo = WW / 2 - (3 * cw + 2 * gapc) / 2
    for i in range(3):
        bx = (xo + i * (cw + gapc), 558 * S, xo + i * (cw + gapc) + cw, 602 * S)
        ld.rounded_rectangle(bx, radius=22 * S, fill=(8, 12, 20, 180), outline=(ACC + (230,)) if i == best else (255, 255, 255, 70), width=2 * S)
    ov.alpha_composite(L); d = ImageDraw.Draw(ov)
    d.text((WW / 2, 516 * S), info['when'], font=ft, fill=(255, 255, 255, 255), anchor='mm')
    fl = _f7('info', 16 * S); fn = _f7('num', 22 * S)
    for i in range(3):
        cx0 = xo + i * (cw + gapc)
        d.text((cx0 + 26 * S, 580 * S), labels[i], font=_f7('info', 14 * S), fill=(170, 178, 192, 255), anchor='lm')
        d.text((cx0 + cw - 22 * S, 580 * S), '%.2f' % odds[i], font=fn, fill=(ACC + (255,)) if i == best else (255, 255, 255, 255), anchor='rm')
    d.text((WW / 2, 622 * S), 'КОЭФФИЦИЕНТЫ В ОСНОВНОЕ ВРЕМЯ ПО ДАННЫМ АНАЛИТИЧЕСКОЙ ТАБЛИЦЫ', font=_f7('info', 11 * S), fill=(196, 202, 214, 255), anchor='mm')
    ov = ov.resize((W, H), Image.LANCZOS)
    Image.alpha_composite(bg, ov).convert('RGB').save(path, optimize=True)
    return path

def am2dec(a):
    return round(1 + a / 100, 2) if a > 0 else round(1 + 100 / abs(a), 2)

def team_info(gp, pts, form):
    wins = 0
    for ch in reversed(form):
        if ch in 'WX': wins += 1
        else: break
    losses = 0
    for ch in reversed(form):
        if ch not in 'WX': losses += 1
        else: break
    last5 = form[-5:]
    badge = ''
    if wins >= 3: badge = '%d победы подряд' % wins if wins < 5 else '%d побед подряд' % wins
    elif losses >= 3: badge = '%d поражения подряд' % losses if losses < 5 else '%d поражений подряд' % losses
    elif (last5.count('W') + last5.count('X')) >= 4: badge = ('%d победы' if (last5.count('W') + last5.count('X')) < 5 else '%d побед') % (last5.count('W') + last5.count('X')) + ' в 5 последних'
    elif (last5.count('W') + last5.count('X')) <= 1 and len(last5) == 5: badge = 'одна победа в 5 последних'
    ig = 'игр' if gp % 10 in (0, 5, 6, 7, 8, 9) or 11 <= gp % 100 <= 14 else ('игра' if gp % 10 == 1 else 'игры')
    och = 'очков' if pts % 10 in (0, 5, 6, 7, 8, 9) or 11 <= pts % 100 <= 14 else ('очко' if pts % 10 == 1 else 'очка')
    return dict(line='%d %s · %d %s' % (pts, och, gp, ig), form=last5, badge=badge)
