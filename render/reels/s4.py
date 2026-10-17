# -*- coding: utf-8 -*-
"""Серия 4 (17.10): новые шаблоны под треки владельца с драматургией утверждённых 12.10 / 14.10:
матч и линия П1 · Х · П2 → команда 1 (последние 3 игры, очки, место, разница) → команда 2 → прогноз ровно на дроп
(только выбранная команда) → плашка Telegram. Без процентов шанса и без заголовков-рубрик.

Тайминг в долях трека: сцена команды ~6 с, подводка к дропу ~1,5 с, прогноз ~4 с, Telegram ~2,8 с — ролик ~22–24 с.
Шаблон рисует только своё оформление; данные и общие блоки — здесь (Base.*). Данные клубов — form.norm.
"""
import math

from PIL import Image

from reels import core as C
from reels import form as F

W, H = C.W, C.H
WHITE = (255, 255, 255)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def beats(u, intro=2.4, team=6.0, pre=1.5, hold=4.2, cta=2.8):
    """Доли сцен по темпу трека: dict(intro, team, pre, hold, cta, drop) — drop = доли от начала ролика до дропа."""
    r = dict(intro=max(3, round(intro / u)), team=max(5, round(team / u)), pre=max(2, round(pre / u)),
             hold=max(4, round(hold / u)), cta=max(3, round(cta / u)))
    r['drop'] = r['intro'] + 2 * r['team'] + r['pre']
    return r


class Base(C.Reel):
    """Общее для шаблонов серии 4. Наследник задаёт STYLE и рисует сцены (intro / team / pre / pick)."""
    STYLE = dict(font='mont', title='unb', ink=WHITE, sub=(176, 182, 196), accent=(222, 186, 110), panel=(14, 15, 19),
                 panel_a=215, line=(255, 255, 255), line_a=40, radius=26)

    def __init__(self, home, away, league, when, pick, coef, sh, sa, u, drop=None, line=None, seed=7, **kw):
        bt = beats(u, **kw)
        super().__init__(u, bt['drop'] * u if drop is None else drop, seed)
        self.bt = bt
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef, self.line, self.pick_txt = league, when, coef, line, pick
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.st = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.t1 = self.b(-(2 * bt['team'] + bt['pre']))
        self.t2 = self.b(-(bt['team'] + bt['pre']))
        self.tp = self.b(-bt['pre'])
        self.t_cta = self.b(bt['hold'])
        self.dur = self.b(bt['hold'] + bt['cta'])
        self.cover_t = self.b(1.5)
        self.tg = C.tg_plate(960, 170, font='unb')

    # ── сцены по времени ──
    def scene(self, t):
        if t < self.t1:
            return 'intro', 0.0, self.t1
        if t < self.t2:
            return 'h', self.t1, self.t2
        if t < self.tp:
            return 'a', self.t2, self.tp
        if t < self.drop:
            return 'pre', self.tp, self.drop
        return 'pick', self.drop, self.dur

    def team_of(self, key):
        return self.h if key == 'h' else self.a

    # ── блоки данных (оформление — из STYLE) ──
    def sty(self, **over):
        s = dict(self.STYLE)
        s.update(over)
        return s

    def panel(self, w, h, sty=None):
        s = sty or self.STYLE
        im = C.rrect(w, h, s['radius'], s['panel'], s['panel_a'])
        if s.get('line_a'):
            ol = C.rrect(w, h, s['radius'], None, outline=s['line'], width=2)
            ol.putalpha(ol.getchannel('A').point(lambda v: int(v * s['line_a'] / 255)))
            im.alpha_composite(ol)
        return im

    def game_row(self, g, w=940, h=112, sty=None):
        """Строка игры: кружок В/П, соперник (эмблема + имя), дата; справа — счёт и ОТ/Б."""
        s = sty or self.STYLE
        im = self.panel(w, h, s)
        ch = F.chip(g['res'], 58)
        C.put(im, ch, 30 + 29, h / 2)
        x = 30 + 58 + 22
        if g.get('opp_key'):
            try:
                em = C.fit(C.Team(g['opp_key']).emb(120), 58, 58)
                C.put(im, em, x + 29, h / 2)
                x += 58 + 16
            except Exception:
                pass
        sc = C.text(g['score'], s['font'], 54, s['ink'], 800)
        note = C.text(g['note'], s['font'], 26, s['sub'], 700) if g['note'] else None
        right = sc.width + (note.width + 10 if note else 0)
        where = ('дома' if g.get('home') else 'в гостях') if g.get('home') is not None else ''
        nm = C.text(g['opp'].upper(), s['font'], 36, s['ink'], 800, max_w=w - x - right - 60)
        C.put(im, nm, x, h / 2 - 20 - nm.height / 2, anchor='tl')
        meta = ' · '.join(v for v in (g['date'], where) if v)
        if meta:
            C.put(im, C.text(meta, s['font'], 24, s['sub'], 600), x, h / 2 + 22 - 12, anchor='tl')
        rx = w - 30
        if note:
            C.put(im, note, rx - note.width, h / 2 + sc.height / 2 - note.height - 4, anchor='tl')
            rx -= note.width + 10
        C.put(im, sc, rx - sc.width, h / 2 - sc.height / 2, anchor='tl')
        return im

    def stat_tiles(self, st, w=940, h=150, sty=None):
        """До трёх плиток: очки (за N матчей), место, разница шайб."""
        s = sty or self.STYLE
        items = []
        if st['points'] is not None:
            sub = ('за %d %s' % (st['gp'], plural(st['gp'], 'матч', 'матча', 'матчей'))) if st['gp'] is not None else ''
            items.append(('ОЧКИ', '%d' % st['points'], sub, s['ink']))
        if st['place'] is not None:
            items.append(('МЕСТО', '%d' % st['place'], st['place_scope'], s['ink']))
        if st['gd'] is not None:
            items.append(('РАЗНИЦА', F.gd_txt(st['gd']), 'шайб', F.WIN if st['gd'] > 0 else F.LOSS if st['gd'] < 0 else s['ink']))
        if not items:
            return None
        gap = 20
        tw = (w - gap * (len(items) - 1)) / len(items)
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for k, (lab, val, sub, vc) in enumerate(items):
            p = self.panel(int(tw), h, s)
            C.put(p, C.text(lab, s['font'], 24, s['sub'], 800, track=0.16, max_w=tw - 24), tw / 2, 30)
            C.put(p, C.text(val, s['title'], 62, vc, 800, max_w=tw - 24), tw / 2, 80)
            if sub:
                C.put(p, C.text(sub, s['font'], 22, s['sub'], 600, max_w=tw - 20), tw / 2, 124)
            C.put(out, p, k * (tw + gap), 0, anchor='tl')
        return out

    def team_blocks(self, key, sty=None):
        """→ [(картинка, высота)] — 3 строки игр и плитки: появляются по очереди на доли."""
        st = self.st[key]
        out = [self.game_row(g, sty=sty) for g in st['games'][:3]]
        tl = self.stat_tiles(st, sty=sty)
        if tl is not None:
            out.append(tl)
        return out

    def odds(self, sty=None, w=940, h=170):
        s = sty or self.STYLE
        return C.odds_row(self.line, w=w, h=h, font=s['title'], lab_font=s['font'], fill=s['panel'], fill_a=s['panel_a'],
                          val_col=s['ink'], lab_col=s['sub'], outline=s['line'] if s.get('line_a') else None)

    def when_txt(self):
        return '%s · %s' % (F.lg_ru(self.league), self.when)

    def pick_block(self, kef_q=1.0, sty=None, w=960):
        """Прогноз: подпись, ставка крупно (2 строки), «в основное время», плашка кэфа."""
        s = sty or self.STYLE
        p1 = C.lines(self.pick1, s['title'], 92, w, s['ink'], 800, gap=0.04, max_lines=2)
        p2 = C.text(self.pick2, s['font'], 34, s['sub'], 800, track=0.14) if self.pick2 else None
        hh = 60 + p1.height + (60 if p2 else 0) + 150
        im = Image.new('RGBA', (w, hh), (0, 0, 0, 0))
        C.put(im, C.text('ПРОГНОЗ', s['font'], 32, s['accent'], 800, track=0.35), w / 2, 22)
        y = 60
        C.put(im, p1, w / 2, y + p1.height / 2)
        y += p1.height
        if p2:
            C.put(im, p2, w / 2, y + 36)
            y += 60
        if kef_q > 0:
            pill = C.rrect(420, 112, 56, s['accent'])
            C.put(pill, C.text('КЭФ ' + C.fmt_k(self.coef).replace('.', ','), s['title'], 52, (20, 16, 8), 800), 210, 56)
            C.put(im, C.scale(pill, 0.8 + 0.2 * kef_q), w / 2, y + 30 + 56, min(1.0, kef_q * 1.5))
        return im

    def stack(self, fr, blocks, t, t0, x, y, gap=18, dy=40, step=None, a=1.0):
        """Блоки столбиком от (x, y) по центру x; каждый следующий въезжает на свою долю."""
        step = step or self.u
        for k, im in enumerate(blocks):
            q = C.out_expo(C.seg(t, t0 + k * step, t0 + k * step + 0.45))
            if q > 0:
                C.put(fr, im, x, y + im.height / 2 + dy * (1 - q), q * a)
            y += im.height + gap
        return y

    def cta(self, fr, t, y=1374):
        if t >= self.t_cta:
            q = C.out_expo(C.seg(t, self.t_cta + 0.05, self.t_cta + 0.5))
            C.put(fr, self.tg, W / 2, y + 50 * (1 - q), q)

    def camera(self, fr, t, cx=W / 2, cy=H / 2, amp=10):
        """Толчки на склейках, наезд на подводке, удар на дропе."""
        z, dx, dy = 1.0, 0.0, 0.0
        for th in (self.t1, self.t2, self.tp):
            if t >= th:
                z += 0.025 * (1 - C.seg(t, th, th + 0.3)) ** 2
            sx, sy = C.shake(t, th, 6, 0.22)
            dx, dy = dx + sx, dy + sy
        if self.tp <= t < self.drop:
            z += 0.04 * C.in_cubic(C.seg(t, self.tp, self.drop))
        if t >= self.drop:
            z += 0.05 * math.exp(-(t - self.drop) * 5)
            sx, sy = C.shake(t, self.drop, amp * 1.6, 0.45)
            dx, dy = dx + sx, dy + sy
        return C.zoom(fr.convert('RGB'), z, cx=cx, cy=cy, dx=dx, dy=dy)
