# -*- coding: utf-8 -*-
"""«Состав» — интро команд в духе представления игроков (Team OG, The International 2019), кульминация — прогноз на дроп.

Палитра: тёмно-синий, монохром и один акцент (цвет клуба), дымчатый серый фон с плывущими частицами и боке.
Сцены (время — в долях трека u; дроп ровно на стыке «напряжения» и «прогноза»):
  интро (ni долей)   — тёмно-синий: лига, день и время, «хозяева — гости» (без заголовков-рубрик — сразу матч) и линия
                       кэфов основного времени П1 / Х / П2 крупными плашками (line);
  клуб (nt долей) ×2 — 1) жёсткая склейка на тёмно-синюю плашку: полное название клуба огромными белыми заглавными
                       в две строки, с обрезкой по краям, строки едут в разные стороны;
                       2) эмблема «въезжает» поверх плашки (у хозяев справа, у гостей слева), текст продолжает ехать за ней;
                       3) удержание: дымчатый фон, эмблема монохромом по центру, медленный наезд; короткое имя крупно
                       цветом клуба, ниже мелкими белыми заглавными — «ХОЗЯЕВА · КХЛ», последние 3 игры строками
                       (дата · соперник · счёт · В/П цветом; появляются спокойно — по строке на долю) и сезон: очки · игры ·
                       место · разница шайб; команда на экране 6–8 с;
  напряжение (nv)    — обе эмблемы монохромом съезжаются к центру, «VS», кадр темнеет, дрожь нарастает (без подписей);
  ДРОП (nh долей)    — вспышка, удар камеры, ударная волна и осколки; только команда прогноза — одна эмблема крупно
                       (без второй и без «VS»), огромный «ПРОГНОЗ: ПОБЕДА …», кэф; на каждую долю — пульс; ~4 с;
  финал (nf долей)   — «Все прогнозы» + плашка Telegram (текст по центру плашки, C.tg_plate), ~2–2,5 с.
@jarvibet во всех сценах — у низа безопасной зоны Shorts (y 1560); нижние блоки — чуть левее центра (кнопки справа).
Никаких процентов/шансов. stats = {"Клуб": {"last3": [{date, opp, home, score, res}], "points", "games", "place", "gd"}};
пустые (None) поля не показываются.
"""
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

import poster
from reels import core as C
from reels.core import W, H

NAVY = (7, 27, 78)
NAVY_D = (3, 12, 38)
WHITE = (255, 255, 255)
GRAY = (176, 182, 196)
BLUE = (88, 150, 255)          # фирменный голубой (как ник в референсе) — подписи «ПРОГНОЗ», Telegram
WIN = (60, 200, 120)
LOSS = (232, 70, 70)
XC = W / 2 - 20                # центр нижних блоков: чуть левее — справа кнопки интерфейса Shorts

# полное название клуба для плашки (две строки); нет в словаре — короткое имя + лига
FULL = {
    'Ак Барс': ('АК БАРС', 'КАЗАНЬ'), 'Сочи': ('ХОККЕЙНЫЙ КЛУБ', 'СОЧИ'), 'Торпедо': ('ТОРПЕДО', 'НИЖНИЙ НОВГОРОД'),
    'Металлург': ('МЕТАЛЛУРГ', 'МАГНИТОГОРСК'), 'Нью-Джерси': ('НЬЮ-ДЖЕРСИ', 'ДЕВИЛЗ'), 'Оттава': ('ОТТАВА', 'СЕНАТОРЗ'),
    'Барыс': ('БАРЫС', 'АСТАНА'), 'Сибирь': ('СИБИРЬ', 'НОВОСИБИРСК'), 'Трактор': ('ТРАКТОР', 'ЧЕЛЯБИНСК'),
    'Локомотив': ('ЛОКОМОТИВ', 'ЯРОСЛАВЛЬ'), 'Авангард': ('АВАНГАРД', 'ОМСК'), 'Северсталь': ('СЕВЕРСТАЛЬ', 'ЧЕРЕПОВЕЦ'),
    'Динамо Минск': ('ДИНАМО', 'МИНСК'), 'Миннесота': ('МИННЕСОТА', 'УАЙЛД'), 'Вегас': ('ВЕГАС', 'ГОЛДЕН НАЙТС'),
}


def _sat(c):
    return (max(c) - min(c)) / 255.0


def _lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def club(t, avoid=None):
    """Акцент клуба для тёмного фона: цветной (не серый/чёрный); если avoid близок — следующий цвет клуба."""
    cand = [c for c in (t.c1, t.c0, t.c2) if _sat(c) > 0.2 and 40 < _lum(c) < 235] or [t.c1]
    if avoid is not None:
        far = [c for c in cand if sum((a - b) ** 2 for a, b in zip(c, avoid)) ** 0.5 > 110]
        if far:
            return tuple(far[0])
    return tuple(cand[0])


def bright(c, k=0.3):
    a = np.array(c, float)
    a = a + (255 - a) * k
    m = a.mean()
    a = m + (a - m) * 1.2
    return tuple(int(v) for v in np.clip(a, 0, 255))


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def place_parts(s):
    """'12 в лиге (конференция …)' → ('12', 'В ЛИГЕ'); '11 на Востоке (общее 25 в лиге)' → ('11', 'НА ВОСТОКЕ')."""
    if s is None:
        return None
    s = re.sub(r'\(.*?\)', '', str(s)).strip()
    m = re.match(r'(\d+)\s*(.*)', s)
    return (m.group(1), m.group(2).strip().upper()) if m else None


def season_lines(st):
    """→ ['23 ОЧКА · 15 ИГР', '1 МЕСТО В ЛИГЕ · РАЗНИЦА ШАЙБ +20'] (только непустые поля)."""
    a, b = [], []
    if st.get('points') is not None:
        a.append('%s %s' % (st['points'], plural(st['points'], 'ОЧКО', 'ОЧКА', 'ОЧКОВ')))
    if st.get('games') is not None:
        a.append('%s %s' % (st['games'], plural(st['games'], 'ИГРА', 'ИГРЫ', 'ИГР')))
    pl = place_parts(st.get('place'))
    if pl:
        b.append(('%s МЕСТО %s' % pl).strip())
    gd = st.get('gd')
    if gd is not None and str(gd) != '':
        gd = str(gd).replace('−', '-')
        b.append('РАЗНИЦА ШАЙБ ' + ('0' if gd in ('+0', '-0', '0') else gd.replace('-', '−')))
    return [' · '.join(x) for x in (a, b) if x]


def mono_emb(im, k=1.0):
    """Эмблема монохромом (как ч/б фото в референсе): серое с повышенным контрастом, альфа своя."""
    g = ImageOps.autocontrast(ImageOps.grayscale(im.convert('RGB')), cutoff=1)
    g = g.point(lambda v: int(40 + v * 0.84))
    out = Image.merge('RGBA', (g, g, g, im.getchannel('A')))
    return out if k >= 1 else Image.blend(im, out, k)


class Lineup(C.Reel):
    def __init__(self, home, away, league, pick, coef, when, stats, side='h', u=0.8, ni=1, nt=6, nv=2, nh=None, nf=None,
                 seed=12, line=None):
        """pick — 'Победа Ак Барса в основное время'; when — 'ПН 12.10 · 19:00 МСК'; side — за кого прогноз ('h'/'a').
        Дроп в ролике = (ni + 2·nt + nv)·u — трек ставить со start = дроп_трека − self.drop."""
        self.ni, self.nt, self.nv = ni, nt, nv
        # строки удержания ложатся на доли трека: быстрый трек — по строке на долю, иначе — на каждую половину доли
        self.r0, self.rs = (2.0, 1.0) if u < 0.8 else (1.5, 0.5)
        super().__init__(u, (ni + 2 * nt + nv) * u, seed)
        self.h, self.a = C.match(home, away, league)
        self.lg = 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'
        self.tag = 'JARVIS | NHL' if self.lg == 'НХЛ' else 'JARVIS | KXL'
        self.coef, self.when, self.side, self.line = coef, when, side, line
        m = re.match(r'(?i)\s*(победа)\s+(.*?)(\s+в основное время)?\s*$', pick)
        if m:
            self.p1, self.p2, self.p3 = 'ПОБЕДА', m.group(2).upper(), ('В ОСНОВНОЕ ВРЕМЯ' if m.group(3) else '')
        else:
            self.p1, self.p2, self.p3 = '', pick.upper(), ''
        self.ch = club(self.h)
        self.ca = club(self.a, avoid=self.ch)
        self.cf = self.ch if side == 'h' else self.ca
        self.st = {'h': stats.get(self.h.name) or stats.get(home) or {}, 'a': stats.get(self.a.name) or stats.get(away) or {}}
        self.nh = nh or max(4, int(math.ceil(3.9 / u)))        # прогноз держим ~4 с (поправка 12.10: на 10–20 % быстрее)
        self.nf = nf or int(math.ceil(2.1 / u))                # плашка Telegram 2–2,5 с
        self.t_home = ni * u
        self.t_away = (ni + nt) * u
        self.t_vs = (ni + 2 * nt) * u
        self.t_end = self.drop + self.nh * u
        self.dur = self.t_end + self.nf * u
        self.cover_t = self.drop + min(2.4, self.nh * u - 0.4)
        self._prep()

    # ── заготовки ──
    def _prep(self):
        rnd = np.random.default_rng(self.seed)
        self.smoke = self._smoke(rnd)
        self.plate_bg = self._plate_bg(rnd)
        # частицы: мелкие искры и крупные размытые «боке»
        self.dots = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.5, 3.8), rnd.uniform(-14, 14), rnd.uniform(-40, -8),
                      rnd.uniform(0.35, 1.0), rnd.uniform(0, 6.28)) for _ in range(110)]
        self.bokeh = []
        for _ in range(9):
            r = int(rnd.uniform(26, 70))
            b = C.radial(r * 2, r * 2, WHITE, int(rnd.uniform(90, 170)), 0.7)
            self.bokeh.append((b, rnd.uniform(0, W), rnd.uniform(200, H - 200), rnd.uniform(-18, 18), rnd.uniform(-22, 8)))
        self.halo = C.radial(1100, 1100, (200, 210, 230), 70, 1.6)
        # осколки взрыва: белый, голубой, акцент фаворита
        self.shards = []
        for i in range(150):
            col = [WHITE, BLUE, bright(self.cf, 0.2), (190, 200, 220)][i % 4]
            self.shards.append(dict(ang=rnd.uniform(0, 2 * math.pi), sp=rnd.uniform(500, 2600), size=rnd.uniform(10, 34),
                                    spin=rnd.uniform(-14, 14), rot0=rnd.uniform(0, 6.28), col=col, drag=rnd.uniform(2.0, 4.0),
                                    life=rnd.uniform(1.0, 2.6), k=rnd.uniform(0.35, 0.8)))
        self.sparks = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(900, 3200), rnd.uniform(0.25, 0.7)) for _ in range(90)]
        self.S = {}
        for key, tm, col, mir in (('h', self.h, self.ch, False), ('a', self.a, self.ca, True)):
            emb = tm.emb(560)
            full = FULL.get(tm.name, (tm.up, self.lg))
            self.S[key] = dict(tm=tm, col=col, acc=bright(col, 0.28), mir=mir, emb=emb, mono=mono_emb(emb),
                               plate_lines=[self._big(s) for s in full], **self._info(key, tm, col))
        self.odds = C.odds_row(self.line, 940, 220, fill=WHITE, fill_a=26, outline=(120, 150, 210)) if self.line else None
        self.odds_lab = C.text('ОСНОВНОЕ ВРЕМЯ', 'mont', 36, GRAY, 800, track=0.25)

    def _smoke(self, rnd):
        """Дымчатый серый «космос»: многооктавный шум с косыми прядями, чуть больше кадра (для наезда/сдвига)."""
        w, h = W + 240, H + 240
        acc = np.zeros((h, w), np.float32)
        for cell, amp in ((360, 1.0), (170, 0.55), (80, 0.3), (36, 0.14)):
            g = rnd.normal(0, 1, (h // cell + 3, w // cell + 3)).astype(np.float32)
            im = Image.fromarray(g).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
            acc += np.asarray(im, np.float32)[:h, :w] * amp
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        streak = np.sin((xx * 0.8 + yy * 0.6) / 70 + acc * 1.4)            # косые пряди тумана
        v = 0.5 + 0.22 * acc + 0.12 * streak
        v = np.clip(v, 0, 1)
        v = 30 + v * 120
        dist = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.38) / (h * 0.55)) ** 2)
        v *= np.clip(1.15 - 0.6 * dist, 0.35, 1.15)
        rgb = np.stack([v * 0.93, v * 0.96, v * 1.06], -1)                  # чуть холодный серый
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(2))
        return im.convert('RGBA')

    def _plate_bg(self, rnd):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        k = np.clip(1 - np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 1.2, 0, 1)[..., None]
        arr = np.array(NAVY_D, np.float32) + (np.array(NAVY, np.float32) - np.array(NAVY_D, np.float32)) * k
        return Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')

    def _big(self, s):
        """Строка плашки: кегль такой, чтобы строка была шире кадра (обрезка по краям), но не выше 330."""
        base = C.text(s, 'mont', 100, WHITE, 900)
        size = int(C.clamp(100 * W * 1.12 / base.width, 150, 330))
        return C.text(s, 'mont', size, WHITE, 900)

    def _info(self, key, tm, col):
        """Подписи удержания: короткое имя (акцент), роль, 3 игры строками, сезон."""
        st = self.st[key]
        acc = bright(col, 0.28)
        name = C.text(tm.up, 'mont', 190, acc, 900, max_w=980)
        role = C.text('%s · %s' % ('ХОЗЯЕВА' if key == 'h' else 'ГОСТИ', self.lg), 'mont', 40, WHITE, 800, track=0.18)
        rows = []
        for g in (st.get('last3') or [])[:3]:
            res = str(g.get('res') or '')
            win = res.startswith('В')
            rw, rh = 920, 84
            row = Image.new('RGBA', (rw, rh), (0, 0, 0, 0))
            C.put(row, C.rrect(rw, rh, 18, NAVY_D, 150), 0, 0, anchor='tl')
            dt = C.text(str(g.get('date') or ''), 'mont', 38, GRAY, 700)
            C.put(row, dt, 22, rh / 2 - dt.height / 2, anchor='tl')
            opp = poster.SHORT.get(str(g.get('opp') or ''), str(g.get('opp') or ''))
            where = '' if g.get('home') is None else (' (Д)' if g['home'] else ' (Г)')
            ot = C.text((opp + where).upper(), 'mont', 44, WHITE, 800, max_w=440)
            C.put(row, ot, 170, rh / 2 - ot.height / 2, anchor='tl')
            sc = str(g.get('score') or '').replace('ОТ/Б', 'ОТ')
            stx = C.text(sc.upper(), 'mont', 48, WHITE, 900)
            C.put(row, stx, rw - 112 - stx.width, rh / 2 - stx.height / 2, anchor='tl')
            bd = C.rrect(70, 62, 14, WIN if win else LOSS)
            C.put(bd, C.text('В' if win else 'П', 'mont', 40, WHITE, 900), 35, 31)
            C.put(row, bd, rw - 52, rh / 2)
            rows.append(row)
        head = C.text('ПОСЛЕДНИЕ 3 ИГРЫ', 'mont', 34, GRAY, 800, track=0.25)
        season = [C.text(s, 'mont', 46, WHITE, 800, track=0.04, max_w=900) for s in season_lines(st)]
        return dict(name=name, role=role, rows=rows, head=head, season=season)

    # ── общие слои ──
    def header(self, fr, a=1.0):
        C.put(fr, C.text(self.tag, 'unb', 34, WHITE, 700, track=0.12), W / 2, 262, a * 0.92)

    def handle(self, fr, a=1.0):
        C.put(fr, C.text(C.HANDLE, 'unb', 38, WHITE, 600), W / 2, 1560, a * 0.85 * C.HANDLE_BOTTOM)     # у низа безопасной зоны Shorts

    def particles(self, fr, t, a=1.0, bokeh=True):
        if bokeh:
            for b, x0, y0, vx, vy in self.bokeh:
                C.put(fr, b, (x0 + vx * t) % (W + 200) - 100, y0 + vy * t, 0.55 * a)
        d = ImageDraw.Draw(fr)
        for x0, y0, r, vx, vy, al, ph in self.dots:
            x = (x0 + vx * t) % W
            y = (y0 + vy * t) % H
            tw = 0.6 + 0.4 * math.sin(t * 3 + ph)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(255 * al * a * tw * 0.8)))

    def smoky(self, fr, t, t0):
        """Дымчатый фон, медленно плывёт."""
        lt = t - t0
        x0 = 120 + 70 * math.sin(lt * 0.25) - lt * 14
        y0 = 120 - lt * 10
        fr.alpha_composite(self.smoke.crop((int(x0), int(y0), int(x0) + W, int(y0) + H)))

    # ── сцены ──
    def intro(self, fr, t):
        """Матч: обе эмблемы, лига и время, «хозяева — гости», линия кэфов основного времени крупными плашками."""
        fr.alpha_composite(self.plate_bg)
        self.particles(fr, t, 0.6, bokeh=False)
        for key, sg, d0 in (('h', -1, 0.0), ('a', 1, 0.12)):          # обе эмблемы в цвете — сразу матч
            qe = C.out_expo(C.seg(t, d0, d0 + 0.5))
            e = C.scale(self.S[key]['emb'], 0.66)
            C.put(fr, C.shadow(e, 24, 0.6 * qe), W / 2 + sg * (240 + 160 * (1 - qe)), 590 + 20)
            C.put(fr, e, W / 2 + sg * (240 + 160 * (1 - qe)), 590, qe)
        q = C.seg(t, 0.03, 0.3)
        C.put(fr, C.text('%s · %s' % (self.lg, self.when), 'mont', 46, BLUE, 800, track=0.1, max_w=980), W / 2, 860, q)
        q2 = C.out_expo(C.seg(t, 0.15, 0.5))
        C.put(fr, C.text('%s — %s' % (self.h.up, self.a.up), 'mont', 84, WHITE, 900, max_w=1000), W / 2, 970 + 20 * (1 - q2), q2)
        if self.odds is not None:
            q3 = C.out_expo(C.seg(t, 0.35, 0.75))
            C.put(fr, self.odds_lab, W / 2, 1110, q3)
            C.put(fr, self.odds, XC, 1265 + 40 * (1 - q3), q3)

    def team(self, fr, key, t, t0):
        u = self.u
        S = self.S[key]
        sg = -1 if S['mir'] else 1               # хозяева: эмблема въезжает справа; гости — слева
        lt = t - t0
        tA, tB = 0.6 * u, 1.45 * u               # плашка → въезд эмблемы → удержание
        if lt < tB:
            # 1–2) тёмно-синяя плашка, огромное полное название в две строки, строки едут в разные стороны
            fr.alpha_composite(self.plate_bg)
            self.particles(fr, t, 0.5, bokeh=False)
            l1, l2 = S['plate_lines']
            sp = 70 + 380 * C.in_cubic(C.seg(lt, tA, tB))
            off = lt * sp
            y1 = 900 - (l1.height + 40) / 2
            y2 = y1 + l1.height + 40
            C.put(fr, l1, W / 2 - sg * off, y1)
            C.put(fr, l2, W / 2 + sg * off, y2)
            if lt >= tA:
                q = C.out_expo(C.seg(lt, tA, tB - 0.05))
                e = C.scale(S['mono'], 1.08)
                x = W / 2 + sg * C.lerp(W, 60, q)
                C.put(fr, C.shadow(e, 30, 0.7), x, 900 + 30)
                C.put(fr, e, x, 900)
            return fr
        # 3) удержание: дым, частицы, эмблема монохромом, имя акцентом, данные мелкими заглавными
        th = t0 + tB
        self.smoky(fr, t, t0)
        self.particles(fr, t, 0.9)
        C.put(fr, self.halo, W / 2, 600)
        e = C.scale(S['mono'], 0.76 + 0.008 * (lt - tB))      # медленный наезд, но без наезда на подпись
        C.put(fr, C.shadow(e, 26, 0.55), W / 2, 615)
        C.put(fr, e, W / 2, 595)
        q = C.out_expo(C.seg(t, th, th + 0.3 * u))
        nm = S['name']
        C.put(fr, C.with_shadow(nm, 14, 0.55, 6), W / 2 + sg * 60 * (1 - q), 910, q)
        C.put(fr, S['role'], W / 2, 345, C.seg(t, th, th + 0.25 * u))
        y = 1040
        if S['rows']:
            C.put(fr, S['head'], W / 2, y, C.seg(t, th + 0.3 * u, th + 0.55 * u))
            y += 44
        n_rows = len(S['rows'])
        for i, row in enumerate(S['rows']):
            ti = t0 + (self.r0 + self.rs * i) * u              # строки — по очереди (r0, шаг rs долей)
            q = C.out_expo(C.seg(t, ti, ti + 0.3 * u))
            if q > 0:
                C.put(fr, row, XC - sg * 120 * (1 - q), y + row.height / 2, min(1.0, q * 1.5))
            y += row.height + 10
        y += 26
        for j, s in enumerate(S['season']):
            ti = t0 + (self.r0 + self.rs * (n_rows + j)) * u
            q = C.out_expo(C.seg(t, ti, ti + 0.3 * u))
            C.put(fr, s, XC, y + s.height / 2 + 14 * (1 - q), q)
            y += s.height + 22
        return fr

    def versus(self, fr, t):
        """Напряжение: монохромные эмблемы съезжаются, «VS», затемнение к дропу."""
        u, t0, D = self.u, self.t_vs, self.drop
        q = C.seg(t, t0, D)
        self.smoky(fr, t, t0)
        self.particles(fr, t, 0.8)
        k = C.in_cubic(q) * 0.7 + 0.3 * C.out_cubic(q)
        C.put(fr, C.text('VS', 'mont', 300, WHITE, 900), W / 2, 880, min(1.0, q * 3) * 0.9)
        for key, sg in (('h', -1), ('a', 1)):
            e = C.scale(self.S[key]['mono'], 0.78 + 0.08 * q)
            C.put(fr, e, W / 2 + sg * C.lerp(720, 190, k), 880)
        dim = 0.12 + 0.55 * C.in_cubic(q) + 0.28 * C.seg(t, D - 0.2 * u, D)
        fr.alpha_composite(Image.new('RGBA', (W, H), NAVY_D + (int(255 * min(0.95, dim)),)))
        return fr

    def burst(self, fr, t):
        """Ударная волна, осколки и искры после дропа."""
        dt = t - self.drop
        if dt < 0 or dt > 2.8:
            return fr
        cx, cy = W / 2, 880
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for r0, wd, al in ((0, 26, 230), (-160, 12, 160)):
            r = r0 + 2600 * (1 - math.exp(-3.0 * dt))
            a = int(al * max(0.0, 1 - dt / 0.9))
            if r > 0 and a > 0:
                d.ellipse((cx - r, cy - r * 0.92, cx + r, cy + r * 0.92), outline=(220, 232, 255, a), width=wd)
        for s in self.shards:
            if dt > s['life']:
                continue
            dist = s['sp'] * (1 - math.exp(-s['drag'] * dt)) / s['drag']
            x = cx + math.cos(s['ang']) * dist
            y = cy + math.sin(s['ang']) * dist + 240 * dt * dt
            if not (-60 < x < W + 60 and -60 < y < H + 60):
                continue
            a = int(255 * (1 - dt / s['life']) ** 0.7)
            r = s['size'] * (1 - 0.4 * dt / s['life'])
            rt = s['rot0'] + s['spin'] * dt
            pts = [(x + r * math.cos(rt), y + r * math.sin(rt)),
                   (x + r * s['k'] * math.cos(rt + 2.3), y + r * s['k'] * math.sin(rt + 2.3)),
                   (x + r * 0.7 * math.cos(rt + 4.0), y + r * 0.7 * math.sin(rt + 4.0))]
            d.polygon(pts, fill=tuple(s['col']) + (a,))
        for ang, sp, life in self.sparks:
            if dt > life:
                continue
            dist = sp * (1 - math.exp(-3.2 * dt)) / 3.2
            x, y = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
            tail = min(160, sp * 0.06 * (1 - dt / life))
            d.line((x, y, x - math.cos(ang) * tail, y - math.sin(ang) * tail), fill=(235, 242, 255, int(255 * (1 - dt / life))), width=4)
        fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
        fr.alpha_composite(lay)
        return fr

    def pulse(self, t):
        """1 — в момент доли после дропа, затем затухает."""
        if t < self.drop:
            return 0.0
        return math.exp(-(((t - self.drop) / self.u) % 1.0) * 9)

    def verdict(self, fr, t):
        """Дроп: только команда, на которую прогноз, — одна эмблема крупно, под ней огромный прогноз (без «VS»)."""
        u, D = self.u, self.drop
        fr.alpha_composite(self.plate_bg)
        self.smoky_tint(fr, t)
        self.particles(fr, t, 0.9)
        k = C.out_expo(C.seg(t, D, D + 0.45 * u))
        fav = self.S[self.side]['emb']
        e = C.scale(fav, C.lerp(1.0, 0.8, k) * (1 + 0.03 * self.pulse(t)))
        C.put(fr, C.glow(e, 18, 0.6, (200, 215, 255)) if k > 0.98 else e, W / 2, C.lerp(880, 545, k))
        q = C.out_expo(C.seg(t, D, D + 0.22 * u))
        lab = C.text('ПРОГНОЗ', 'mont', 58, BLUE, 900, track=0.35)
        C.put(fr, C.scale(lab, 1.6 - 0.6 * q), W / 2, 840, min(1.0, q * 2))
        y = 950
        if self.p1:
            im = C.with_shadow(C.text(self.p1, 'mont', 150, WHITE, 900, max_w=1000), 14, 0.6, 8)
            C.put(fr, C.scale(im, 2.2 - 1.2 * q), W / 2, y, min(1.0, q * 2))
            y += 150
        q2 = C.out_expo(C.seg(t, D + 0.04, D + 0.3 * u))
        nm = C.glow(C.text(self.p2, 'mont', 180, bright(self.cf, 0.3), 900, max_w=980), 18, 0.8, self.cf)
        C.put(fr, C.scale(nm, (2.4 - 1.4 * q2) * (1 + 0.025 * self.pulse(t))), W / 2, y + 10, min(1.0, q2 * 2))
        y += 135
        if self.p3:
            q3 = C.out_expo(C.seg(t, D + 0.5 * u, D + 0.9 * u))
            C.put(fr, C.text(self.p3, 'mont', 58, WHITE, 800, track=0.12, max_w=980), W / 2, y + 30 * (1 - q3), q3)
            y += 95
        if self.coef:
            q4 = C.out_back(C.seg(t, D + 1.0 * u, D + 1.35 * u), 1.8)
            if q4 > 0.01:
                kt = C.text('КЭФ ' + C.fmt_k(self.coef), 'mont', 92, NAVY_D, 900)
                kp = C.rrect(kt.width + 120, 150, 75, WHITE)
                C.put(kp, kt, kp.width / 2, 75)
                C.put(fr, C.scale(kp, 0.4 + 0.6 * q4), W / 2, y + 75, min(1.0, q4 * 1.5))
            y += 175
        self.burst(fr, t)
        return fr

    def smoky_tint(self, fr, t):
        """Дым поверх синего — полупрозрачно (дроп и финал)."""
        sm = self.smoke.crop((120, 120, 120 + W, 120 + H))
        sm.putalpha(110)
        fr.alpha_composite(sm)

    def final(self, fr, t):
        """Плашка Telegram: «ВСЕ / ПРОГНОЗЫ» крупно, плашка (текст по центру плашки), подпись — блоком по центру кадра."""
        u, t0 = self.u, self.t_end
        fr.alpha_composite(self.plate_bg)
        self.smoky_tint(fr, t)
        self.particles(fr, t, 0.8)
        q = C.out_expo(C.seg(t, t0, t0 + 0.4 * u))
        C.put(fr, C.text('ВСЕ', 'mont', 200, WHITE, 900), W / 2, 630 + 40 * (1 - q), q)
        C.put(fr, C.text('ПРОГНОЗЫ', 'mont', 200, WHITE, 900, max_w=1000), W / 2, 830 + 40 * (1 - q), q)
        q = C.out_expo(C.seg(t, t0 + 0.3 * u, t0 + 0.75 * u))
        if q > 0:
            pl = C.tg_plate(1000, 210)
            C.put(fr, C.scale(pl, 0.8 + 0.2 * q), W / 2, 1105, q)
        q = C.seg(t, t0 + 0.7 * u, t0 + 1.1 * u)
        C.put(fr, C.text('КАЖДЫЙ ДЕНЬ · КХЛ И НХЛ', 'mont', 46, GRAY, 800, track=0.15, max_w=1000), W / 2, 1305, q)

    # ── кадр ──
    def frame(self, t):
        u, D = self.u, self.drop
        fr = Image.new('RGBA', (W, H), NAVY_D + (255,))
        if t < self.t_home:
            self.intro(fr, t)
        elif t < self.t_away:
            self.team(fr, 'h', t, self.t_home)
        elif t < self.t_vs:
            self.team(fr, 'a', t, self.t_away)
        elif t < D:
            self.versus(fr, t)
        elif t < self.t_end:
            self.verdict(fr, t)
        else:
            self.final(fr, t)
        hdr = 1.0 if (t < D or t >= D + 0.25) else C.seg(t, D, D + 0.25)
        self.header(fr, hdr)
        self.handle(fr, hdr)
        # камера: медленный наезд в удержании, толчки на склейках, удар на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        for t0 in (self.t_home, self.t_away):
            if t0 <= t < t0 + self.nt * u:
                z += 0.035 * C.seg(t, t0 + 1.45 * u, t0 + self.nt * u)
            for tb in (t0, t0 + 1.45 * u):
                if t >= tb:
                    z += 0.04 * (1 - C.seg(t, tb, tb + 0.35)) ** 2
                sx, sy = C.shake(t, tb, 10, 0.28)
                dx, dy = dx + sx, dy + sy
        if self.t_vs <= t < D:
            q = C.seg(t, self.t_vs, D)
            z += 0.08 * C.in_cubic(q)
            dx += 7 * q * math.sin(t * 71)
            dy += 7 * q * math.cos(t * 53)
        if t >= D:
            k = 1 - C.seg(t, D, D + 0.5)
            z += 0.16 * k ** 2
            sx, sy = C.shake(t, D, 34, 0.55)
            dx, dy = dx + sx, dy + sy
            rot = 2.0 * k ** 2 * math.sin((t - D) * 40)
            if t < self.t_end:
                z += 0.012 * self.pulse(t)
        fr = C.zoom(fr.convert('RGB'), z, dx=dx, dy=dy, rot=rot)
        if D <= t < D + 0.18:
            fr = C.rgb_split(fr, 18 * (1 - C.seg(t, D, D + 0.18)))
        if D <= t < D + 0.4:                          # вспышка на дроп
            a = 1.0 if t < D + 1 / 30 else (1 - C.seg(t, D + 1 / 30, D + 0.4)) ** 1.6
            fr = Image.blend(fr, Image.new('RGB', fr.size, (245, 248, 255)), 0.92 * a)
        fr = C.vignette(fr, 0.4)
        return C.grain(fr, t, 5)
