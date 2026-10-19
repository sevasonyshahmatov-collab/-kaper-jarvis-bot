# -*- coding: utf-8 -*-
"""«Кинетика» — кинетическая типографика в энергии UK-дрилла (трек «PACKS», 71 BPM половинным темпом).

Каждая доля трека — жёсткая склейка и ОДНА мысль на весь экран огромным тяжёлым шрифтом (Dela Gothic One, Oswald):
надпись влетает с «ударом» (масштаб 1,4 → 1 и лёгкий доворот), за ней — контурная копия со сдвигом и два контурных
«эха», разлетающиеся от удара; камера чуть вздрагивает на каждом ударе, на полудолях — микро-толчок и шаг бегущих строк.
База — чёрное / белое, акцент — цвет клуба на экране; эмблема — крупный графический элемент. Фон — бегущие строки
контурных названий клуба и плёночное зерно. Сверху на всё время — тонкая полоса матча (JARVIS | NHL, обе команды,
текущая — в плашке цвета клуба), снизу — @jarvibet на чёрной полосе (одинаково во всех сценах до плашки Telegram).

Сцены (u — доля трека; все склейки и акценты — на долях от дропа; число долей — reels_cfg/kinetic.json):
  интро (до b(−2·team−build), 4 доли при drop_beats = 20) — обе эмблемы влетают с краёв, названия, на полдоли —
            «наклейка» с днём и временем МСК, на долю — линия П1 · Х · П2 тремя крупными плашками (основное время);
  клуб ×2 (team долей, ~5,9 с) — по доле на мысль: название огромными буквами на цвете клуба с большой эмблемой
            (хозяева / гости, серия побед, если есть) → три последние игры, по игре на долю: соперник (эмблема и имя)
            и дата сверху, счёт во весь экран, плашка ПОБЕДА / ПОРАЖЕНИЕ, отметка ОТ / буллиты; внизу копится
            строка формы из трёх квадратов В / П → очки за матчи → место в конференции → разница шайб
            (забито / пропущено). Пустые поля не показываются, освободившиеся доли получает название клуба;
  разгон (build долей) — названия обеих команд чередуются всё чаще (полдоли → четверть → восьмая), камера наезжает,
            расслоение цвета растёт;
  ДРОП (hold долей, ~4,2 с) — вспышка и ударная волна: только выбранная команда — одна эмблема, ПОБЕДА …,
            В ОСНОВНОЕ ВРЕМЯ и кэф (form.split_pick); на каждую следующую долю — кольцо-волна и толчок;
  финал (cta долей, ~2,3 с) — прогноз коротко и плашка Telegram (C.tg_plate, текст по центру плашки).
Никаких шансов и процентов. Кадр — чистая функция t; все надписи, фоны и спрайты готовятся в конструкторе
(до разветвления процессов) и кешируются на уровне модуля.
"""
import math

from PIL import Image, ImageDraw

from reels import core as C
from reels import form as F
from reels import fresh
from reels.core import W, H

INK = (10, 10, 12)
PAPER = (242, 240, 234)
WHITE = (255, 255, 255)
GREY = (178, 180, 186)
WIN_D = (22, 156, 80)
LOSS_D = (214, 38, 44)
WIN_L = (60, 222, 124)
LOSS_L = (255, 74, 74)
OT_Y = (255, 214, 64)

STRIP_Y, STRIP_H = 264, 60                 # полоса матча (верх безопасной зоны)
HAND_Y, HAND_H = 1440, 72                   # полоса @jarvibet (низ безопасной зоны, до 1476)
TOP, BOT = 312, 1392                        # поле надписей между полосами
X0, X1 = 60, 1020
CHIP_Y = 1322

_SPR, _BG, _MQ = {}, {}, {}


# ─────────────────────────────── мелочи ───────────────────────────────
def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def streak_txt(s):
    """«В4» → «4 ПОБЕДЫ ПОДРЯД»; короче двух и прочее — пусто."""
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


def note_txt(n):
    n = str(n or '').upper()
    if not n:
        return ''
    if n == 'ОТ':
        return 'В ОВЕРТАЙМЕ'
    if n == 'Б':
        return 'ПО БУЛЛИТАМ'
    return 'ОВЕРТАЙМ / БУЛЛИТЫ' if 'ОТ' in n and 'Б' in n else n


def fit_size(s, name, size, max_w, wght=700):
    """Кегль, при котором строка влезает в max_w."""
    size = int(size)
    while size > 16 and C.font(name, size, wght).getlength(s) > max_w:
        size = max(16, int(size * max_w / C.font(name, size, wght).getlength(s) * 0.995))
    return size


def best_lines(s, name, size, max_w, maxn=3):
    """Разбивка строки на 1…maxn строк с самым крупным кеглем (владелец 19.10: длинный прогноз не мельчить)."""
    import itertools
    w = s.split()
    best = ([s], fit_size(s, name, size, max_w))
    for n in range(2, min(maxn, len(w)) + 1):
        for cut in itertools.combinations(range(1, len(w)), n - 1):
            ls = [' '.join(w[a:b]) for a, b in zip((0,) + cut, cut + (len(w),))]
            sz = min(fit_size(x, name, size, max_w) for x in ls)
            if sz > best[1] * 1.08:                           # лишняя строка — только если заметно крупнее
                best = (ls, sz)
    return best


def name_lines(up):
    """Длинное название — в две строки по дефису / пробелу («ЛОС-» / «АНДЖЕЛЕС»)."""
    if len(up) > 9:
        if '-' in up:
            a, b = up.split('-', 1)
            return [a + '-', b]
        if ' ' in up:
            return up.split(' ', 1)
    return [up]


def accents(team):
    """(акцент на чёрном, фон-акцент, цвет текста на фоне-акценте, акцент на белом)."""
    c = fresh.club(team)
    if max(c) - min(c) < 40:                                     # монохромный клуб (Лос-Анджелес) — светлое серебро
        on_ink = (206, 212, 216)
        bg = (190, 197, 202)
        on_paper = (24, 24, 28)
    else:
        on_ink = c
        while lum(on_ink) < 105:
            on_ink = fresh.bright(on_ink, 0.22)
        bg = c if lum(c) >= 60 else on_ink
        on_paper = c if lum(c) < 170 else C.mix(c, (0, 0, 0), 0.4)
    txt = INK if lum(bg) > 105 else WHITE
    return dict(ink=tuple(on_ink), bg=tuple(bg), txt=txt, paper=tuple(on_paper))


def T(s, size, col=WHITE, name='dela', max_w=None, stroke=0, stroke_fill=INK, wght=800, track=0.0):
    return C.text(s, name, size, col, wght, track=track, max_w=max_w, stroke=stroke, stroke_fill=stroke_fill)


def O(s, size, col, sw, name='dela', max_w=None, wght=800, track=0.0):
    """Только контур надписи (толщина sw)."""
    return C.text(s, name, size, col, wght, track=track, max_w=max_w, stroke=sw, outline=True)


def stack(ims, gap=0, align='c'):
    """Строки картинок одна под другой."""
    w = max(i.width for i in ims)
    h = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    y = 0
    for i in ims:
        x = (w - i.width) // 2 if align == 'c' else 0 if align == 'l' else w - i.width
        out.alpha_composite(i, (x, y))
        y += i.height + gap
    return out


def row(ims, gap=0):
    """Картинки в строку, по центру по вертикали."""
    w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    h = max(i.height for i in ims)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    x = 0
    for i in ims:
        out.alpha_composite(i, (x, (h - i.height) // 2))
        x += i.width + gap
    return out


def boxed(im, fill, padx=26, pady=14, r=6):
    bx = C.rrect(im.width + 2 * padx, im.height + 2 * pady, r, fill)
    C.put(bx, im, bx.width / 2, bx.height / 2)
    return bx


def chip(r, d, ring=None):
    key = ('chip', r, d, ring)
    if key not in _SPR:
        col = WIN_D if r == 'В' else LOSS_D if r == 'П' else (120, 120, 128)
        im = Image.new('RGBA', (d + 12, d + 12), (0, 0, 0, 0))
        if ring:
            im.alpha_composite(C.rrect(d + 12, d + 12, 10, ring), (0, 0))
        im.alpha_composite(C.rrect(d, d, 7, col), (6, 6))
        C.put(im, T(r or '?', int(d * 0.6), WHITE), im.width / 2, im.height / 2)
        _SPR[key] = im
    return _SPR[key]


def chip_empty(d, col):
    key = ('chip0', d, col)
    if key not in _SPR:
        im = Image.new('RGBA', (d + 12, d + 12), (0, 0, 0, 0))
        im.alpha_composite(C.rrect(d, d, 7, None, outline=col, width=3), (6, 6))
        _SPR[key] = C.fade(im, 0.45)
    return _SPR[key]


# ─────────────────────────────── ролик ───────────────────────────────
class Kinetic(C.Reel):
    def __init__(self, home, away, league, when, pick, coef, sh, sa, u=60 / 71, drop=20 * 60 / 71, line=None, team=7,
                 build=2, hold=5, cta=2.75, seed=23, **kw):
        super().__init__(u, drop, seed)
        self.line = tuple(line) if line else None
        self.h, self.a = C.match(home, away, league)
        self.league, self.when, self.coef = league, when, coef
        self.tag = F.tag(league)
        self.pick1, self.pick2 = F.split_pick(pick)
        self.side = F.fav_side(self.h, self.a, pick)
        self.fav = self.h if self.side == 'h' else self.a
        self.rec = {'h': sh or {}, 'a': sa or {}}
        self.s = {'h': F.norm(sh), 'a': F.norm(sa)}
        self.team_n, self.build_n = int(team), float(build)
        self.T1 = self.b(-(2 * team + build))
        if self.T1 < 2.4:
            raise ValueError('мало времени до дропа для интро')
        self.T2 = self.b(-(team + build))
        self.TB = self.b(-build)
        self.TC = self.b(hold)
        self.dur = self.b(hold + cta)
        self.cover_t = self.T1 - 0.5                                   # интро целиком: обе команды, время, линия
        self.key = (home, away, league, when, pick, coef, self.line, team, build, hold, cta, round(u, 5), round(drop, 4))
        self.acc = {'h': accents(self.h), 'a': accents(self.a)}
        self.tm = {'h': self.h, 'a': self.a}
        self._prep()

    # ── заготовки ──
    def _el(self, im, x, y, d=0.0, kind='slam', rot=0.0, z0=1.4, kick=0.0, echo=None, off=(0, 0), dur=0.16, dx0=0,
            pulse=0.0):
        if kind == 'slam' and z0 > 1:                                  # удар не выносит надпись за край кадра
            z0 = max(1.0, min(z0, (W - 100) / im.width, 2 * (x - 30) / im.width, 2 * (W - 30 - x) / im.width))
        e = dict(im=im, x=x, y=y, d=d, kind=kind, rot=rot, z0=z0, kick=kick, echo=echo, off=off, dur=dur, dx0=dx0,
                 pulse=pulse)
        e['rest'] = C.rotate(im, rot)
        e['echo_rest'] = C.rotate(echo, rot) if echo is not None else None
        return e

    def _strip(self, mode):
        """Полоса матча сверху: тег слева; справа обе команды (текущая — в плашке цвета клуба) или время."""
        key = ('strip', self.key, mode)
        if key in _SPR:
            return _SPR[key]
        im = Image.new('RGBA', (W, STRIP_H), INK + (255,))
        tg = T(self.tag, 44, WHITE, 'osw', wght=700, track=0.06)
        C.put(im, tg, X0 + tg.width / 2, STRIP_H / 2)
        room = X1 - X0 - tg.width - 40
        if mode == 'time':
            rt = T(self.when.upper(), 44, WHITE, 'osw', wght=700, max_w=room)
        else:
            parts = []
            for side in ('h', 'a'):
                nm = T(self.tm[side].up, 44, WHITE if mode != side else self.acc[side]['txt'], 'osw', wght=700)
                if mode == side:
                    nm = boxed(nm, self.acc[side]['bg'], 12, 6, 4)
                parts.append(nm)
                if side == 'h':
                    parts.append(T('—', 44, GREY, 'osw', wght=700))
            rt = row(parts, 14)
            if rt.width > room:
                rt = C.fit(rt, room, STRIP_H)
        C.put(im, rt, X1 - rt.width / 2, STRIP_H / 2)
        _SPR[key] = im
        return im

    def _handle(self):
        key = ('handle',)
        if key not in _SPR:
            im = Image.new('RGBA', (W, HAND_H), INK + (255,))
            C.put(im, T(C.HANDLE, 50, WHITE, 'dela'), W / 2, HAND_H / 2)
            _SPR[key] = im
        return _SPR[key]

    def _marquee(self, s, col, a, size=150, sw=3):
        """Длинная полоса контурного текста для бегущих строк → (картинка, период)."""
        key = ('mq', s, col, a, size, sw)
        if key not in _MQ:
            unit = O(s + ' —', size, col, sw)
            gap = int(size * 0.35)
            per = unit.width + gap
            n = int(math.ceil((W + per) / per)) + 1
            im = Image.new('RGBA', (per * n, unit.height), (0, 0, 0, 0))
            for k in range(n):
                im.alpha_composite(unit, (k * per, 0))
            _MQ[key] = (C.fade(im, a), per)
        return _MQ[key]

    def _bg(self, kind, side=None, wm=None):
        """Неподвижный фон карточки: заливка (+ водяной знак эмблемы) → RGBA."""
        key = (self.key, kind, side, wm)
        if key in _BG:
            return _BG[key]
        if kind == 'ink':
            col = INK
        elif kind == 'paper':
            col = PAPER
        else:
            col = self.acc[side]['bg']
        im = Image.new('RGBA', (W, H), col + (255,))
        if kind == 'acc':                                          # лёгкий объём: светлее в центре
            im = C.add_light(im.convert('RGB'), C.radial(1500, 1500, (255, 255, 255), 46, 1.6), W / 2, 760).convert('RGBA')
        if kind == 'glow':
            im = Image.new('RGBA', (W, H), INK + (255,))
            c = self.acc[side]['ink']
            im = C.add_light(im.convert('RGB'), C.radial(1500, 1500, c, 120, 1.7), W / 2, 560).convert('RGBA')
        if wm:
            tm = self.tm[side]
            e = tm.emb(1250)
            g = e.convert('LA').convert('RGBA') if kind != 'glow' else e
            g = C.rotate(g, -12)
            C.put(im, C.fade(g, 0.09 if kind == 'ink' else 0.12), W * 0.86, H * 0.52)
        _BG[key] = im
        return im

    def _mq_spec(self, kind, side, txt=None):
        """Бегущие строки фона: (полоса, период) для каждой строки."""
        rows = []
        if kind == 'ink':
            sides = [side] if side else ['h', 'a']
            for k in range(8):
                sd = sides[k % len(sides)]
                rows.append(self._marquee(txt or self.tm[sd].up, self.acc[sd]['ink'], 0.13))
        elif kind == 'glow':
            for k in range(8):
                rows.append(self._marquee(txt or self.tm[side].up, self.acc[side]['ink'], 0.16))
        elif kind == 'paper':
            for k in range(8):
                rows.append(self._marquee(txt or self.tm[side].up, (150, 150, 156), 0.22))
        else:
            c = self.acc[side]['bg']
            dark = C.mix(c, (0, 0, 0), 0.32) if lum(c) > 105 else C.mix(c, (255, 255, 255), 0.3)
            for k in range(8):
                rows.append(self._marquee(txt or self.tm[side].up, dark, 0.55))
        return rows

    # ── карточки клуба ──
    def _name_block(self, side, mw=920):
        """Название клуба огромными буквами (1–2 строки) → (сплошное, контур)."""
        tm, ac = self.tm[side], self.acc[side]
        ls = name_lines(tm.up)
        size = min(fit_size(s, 'dela', 200, mw) for s in ls)
        blk = stack([T(s, size, ac['txt'], max_w=mw + 10) for s in ls], int(size * 0.02))
        blk_o = stack([O(s, size, WHITE if ac['txt'] == INK else INK, 5, max_w=mw + 10) for s in ls], int(size * 0.02))
        return blk, blk_o

    def _emb_fit(self, side, w, h):
        """Эмблема клуба, вписанная по видимым пикселям в w×h."""
        key = ('embfit', self.tm[side].name, int(w), int(h))
        if key not in _SPR:
            e = self.tm[side].emb(900)
            bb = e.getchannel('A').getbbox()
            e = e.crop(bb) if bb else e
            _SPR[key] = C.fit(e, w, h)
        return _SPR[key]

    def _name_card(self, side, t0, t1, sub=True, build_k=None):
        """Название клуба на цвете клуба + большая эмблема (сцена клуба; в разгоне — без подписи)."""
        els = []
        blk, blk_o = self._name_block(side, 860 if build_k is not None else 920)
        role = 'ХОЗЯЕВА' if side == 'h' else 'ГОСТИ'
        stk = streak_txt(self.rec[side].get('streak'))
        sb = boxed(T(role + (' · ' + stk if stk else ''), 52, WHITE, 'osw', wght=700, track=0.04, max_w=900), INK, 22, 10, 4)
        bottom = 1366 - (sb.height + 26 if sub else 0)
        cy = bottom - blk.height / 2
        top = cy - blk.height / 2
        emb = self._emb_fit(side, 820, top - 40 - 330)
        ey = 330 + (top - 40 - 330) / 2
        bk = build_k is not None
        rk = (-5 if build_k % 2 else 5) if bk else -4
        els.append(self._el(emb if bk else C.with_shadow(emb, 26, 0.45, 18), W / 2, ey + (0 if bk else 9), kind='slam',
                            z0=1.35 if bk else 1.55, kick=0 if bk else -9, rot=rk, dur=0.1 if bk else 0.16))
        els.append(self._el(blk, W / 2, cy, d=0.0 if bk else 0.02, kind='slam', z0=1.25 if bk else 1.35, kick=0 if bk else 3,
                            rot=(2 if build_k % 2 else -2) if bk else -2, echo=blk_o, off=(12, 12), dur=0.1 if bk else 0.16))
        if sub:
            els.append(self._el(sb, W / 2, bottom + 26 + sb.height / 2 - 6, d=0.1, kind='drop', rot=1.5))
        return dict(t0=t0, t1=t1, bg='acc', side=side, els=els, chips=None, hit=10 if bk else 12, wm=False)

    def _game_card(self, side, g, k, t0, t1):
        tm, ac = self.tm[side], self.acc[side]
        els = []
        # соперник: эмблема + имя, дата и дома / в гостях
        opp = T(g['opp'].upper(), 84, WHITE, max_w=700)
        parts = []
        if g.get('opp_key'):
            try:
                parts.append(C.Team(g['opp_key']).emb(118))
            except Exception:
                pass
        parts.append(opp)
        orow = row(parts, 24)
        els.append(self._el(orow, W / 2, 404, d=0.03, kind='slide', dx0=-260))
        meta = []
        if g.get('date'):
            meta.append(g['date'])
        if g.get('home') is not None:
            meta.append('ДОМА' if g['home'] else 'В ГОСТЯХ')
        if meta:
            els.append(self._el(T(' · '.join(meta), 54, GREY, 'osw', wght=600, track=0.05), W / 2, 500, d=0.06,
                                kind='slide', dx0=260))
        # счёт во весь экран
        sc = g['score']
        size = fit_size(sc, 'dela', 400, 860)
        col = WHITE
        els.append(self._el(T(sc, size, col), W / 2, 764, kind='slam', z0=1.5, kick=-5, rot=-2,
                            echo=O(sc, size, ac['ink'], 6), off=(14, 14)))
        # плашка результата
        word = 'ПОБЕДА' if g['res'] == 'В' else 'ПОРАЖЕНИЕ' if g['res'] == 'П' else '—'
        bc = WIN_D if g['res'] == 'В' else LOSS_D if g['res'] == 'П' else (90, 90, 96)
        bar = Image.new('RGBA', (1240, 172), bc + (255,))
        C.put(bar, T(word, 112, WHITE, max_w=960), bar.width / 2, bar.height / 2)
        els.append(self._el(bar, W / 2, 1072, d=0.08, kind='wipe', rot=-3, dur=0.14))
        nt = note_txt(g.get('note'))
        if nt:
            st = boxed(T(nt, 58, INK, max_w=860), OT_Y, 24, 12, 4)
            els.append(self._el(st, W / 2 + 120, 1206, d=0.14, kind='slam', z0=1.6, kick=6, rot=2.5))
        return dict(t0=t0, t1=t1, bg='ink', side=side, els=els, chips=(k, True), hit=9, wm=True)

    def _stat_card(self, side, kind, s, t0, t1, bg):
        ac = self.acc[side]
        fg = INK if bg in ('paper',) else ac['txt'] if bg == 'acc' else WHITE
        sec = ac['paper'] if bg == 'paper' else fg if bg == 'acc' else ac['ink']
        oc = ac['paper'] if bg == 'paper' else (WHITE if fg == INK else INK) if bg == 'acc' else ac['ink']
        els = []
        if kind == 'pts':
            n = s['points']
            big, w1 = '%d' % n, plural(n, 'ОЧКО', 'ОЧКА', 'ОЧКОВ')
            sub = ('ЗА %d %s' % (s['gp'], plural(s['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))) if s['gp'] is not None else ''
            bcol = fg
        elif kind == 'place':
            big, w1 = '%d-Е' % s['place'], 'МЕСТО'
            sub = (s['place_scope'] or '').upper()
            bcol = fg
        elif kind == 'gd':
            big, w1 = F.gd_txt(s['gd']), 'РАЗНИЦА ШАЙБ'
            r = self.rec[side]
            gf, ga = r.get('gf'), r.get('ga')
            sub = ('ЗАБИТО %d · ПРОПУЩЕНО %d' % (gf, ga)) if isinstance(gf, int) and isinstance(ga, int) else ''
            bcol = (WIN_L if s['gd'] > 0 else LOSS_L if s['gd'] < 0 else fg) if bg == 'ink' else \
                   (WIN_D if s['gd'] > 0 else LOSS_D if s['gd'] < 0 else fg)
        else:                                                     # серия / рекорд
            big, w1, sub, bcol = s
        size = fit_size(big, 'dela', 470, 880)
        els.append(self._el(T(big, size, bcol), W / 2, 650, kind='slam', z0=1.55, kick=-6, rot=-3,
                            echo=O(big, size, oc, 6), off=(16, 16)))
        s1 = fit_size(w1, 'dela', 150, 960)
        els.append(self._el(T(w1, s1, sec if kind != 'gd' else fg, max_w=980), W / 2, 978, d=0.05, kind='slam', z0=1.3,
                            kick=3, rot=-1.5))
        if sub:
            sb = boxed(T(sub, 58, PAPER if bg != 'ink' else INK, 'osw', wght=700, track=0.04, max_w=880),
                       INK if bg != 'ink' else PAPER, 22, 10, 4)
            els.append(self._el(sb, W / 2, 1128, d=0.1, kind='drop', rot=1.5))
        return dict(t0=t0, t1=t1, bg=bg, side=side, els=els, chips=(3, False), hit=9, wm=(bg == 'ink'))

    def _team_cards(self, side, T0):
        u, s = self.u, self.s[side]
        r = self.rec[side]
        ideas = [('name', None)]
        for k, g in enumerate(s['games']):
            ideas.append(('game', (k, g)))
        if s['points'] is not None:
            ideas.append(('pts', None))
        if s['place'] is not None:
            ideas.append(('place', None))
        if s['gd'] is not None:
            ideas.append(('gd', None))
        extra = []                                                   # запас фактов, если чего-то нет
        stk = str(r.get('streak') or '').strip().upper()
        if stk[:1] in ('В', 'W') and stk[1:].isdigit() and int(stk[1:]) >= 2:
            n = int(stk[1:])
            extra.append(('x', ('%d' % n, plural(n, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'), 'ПОДРЯД', None)))
        rc = str(r.get('record') or '')
        if rc.count('-') == 2 and all(x.isdigit() for x in rc.split('-')):
            w_, l_, o_ = (int(x) for x in rc.split('-'))
            if w_ + l_ + o_:
                extra.append(('x', ('%d' % w_, plural(w_, 'ПОБЕДА', 'ПОБЕДЫ', 'ПОБЕД'),
                                    'В %d %s' % (w_ + l_ + o_, plural(w_ + l_ + o_, 'МАТЧЕ', 'МАТЧАХ', 'МАТЧАХ')), None)))
        while len(ideas) < self.team_n and extra:
            ideas.append(extra.pop(0))
        ideas = ideas[:self.team_n]
        beats = [1] * len(ideas)
        beats[0] += self.team_n - sum(beats)                          # лишние доли — названию клуба
        cards, t = [], T0
        bgs = {'pts': 'paper', 'place': 'acc', 'gd': 'ink'}
        xi = 0
        for (kind, data), nb in zip(ideas, beats):
            t1 = t + nb * u
            if kind == 'name':
                cards.append(self._name_card(side, t, t1))
            elif kind == 'game':
                cards.append(self._game_card(side, data[1], data[0], t, t1))
            elif kind == 'x':
                big, w1, sub, _ = data
                cards.append(self._stat_card(side, 'x', (big, w1, sub, WHITE if xi % 2 == 0 else INK), t, t1,
                                             'ink' if xi % 2 == 0 else 'paper'))
                xi += 1
            else:
                cards.append(self._stat_card(side, kind, s, t, t1, bgs[kind]))
            cards[-1]['beats'] = nb
            t = t1
        return cards

    # ── интро ──
    def _intro(self):
        els = []
        for side, x in (('h', 272), ('a', 808)):
            tm = self.tm[side]
            els.append(self._el(C.with_shadow(tm.emb(300), 20, 0.5, 12), x, 520, d=0.0, kind='slam', z0=1.6,
                                kick=-10 if side == 'h' else 10, rot=-3 if side == 'h' else 3, dur=0.2))
        size = min(fit_size(self.h.up, 'dela', 66, 470), fit_size(self.a.up, 'dela', 66, 470))
        for side, x in (('h', 272), ('a', 808)):
            nm = T(self.tm[side].up, size, WHITE)
            bar = Image.new('RGBA', (min(nm.width, 300), 10), self.acc[side]['ink'] + (255,))
            els.append(self._el(stack([nm, bar], 14), x, 742, d=0.06 + 0.04 * (side == 'a'), kind='slam', z0=1.3))
        sl = Image.new('RGBA', (12, 250), WHITE + (255,))
        els.append(self._el(sl, W / 2, 540, d=0.1, kind='slam', rot=-18, z0=1.6))
        st = boxed(T(self.when.upper(), 60, INK, max_w=880), PAPER, 30, 16, 4)
        els.append(self._el(st, W / 2, 878, d=self.u / 2, kind='slam', z0=1.5, kick=-5, rot=-2))
        if self.line:
            gap = 24
            bw = (X1 - X0 - 2 * gap) // 3
            bh = 262
            for k, (lab, v) in enumerate(zip(('П1', 'Х', 'П2'), self.line)):
                bx = C.rrect(bw, bh, 18, INK, outline=WHITE, width=4)
                lc = self.acc['h']['ink'] if k == 0 else self.acc['a']['ink'] if k == 2 else WHITE
                C.put(bx, T(lab, 60, lc, 'dela'), bw / 2, 68)
                C.put(bx, T(C.fmt_k(v), 104, WHITE, max_w=bw - 30), bw / 2, 172)
                x = X0 + k * (bw + gap) + bw / 2
                els.append(self._el(bx, x, 1110, d=self.u + 0.07 * k, kind='slam', z0=1.45, kick=(k - 1) * 4))
            els.append(self._el(T('ОСНОВНОЕ ВРЕМЯ', 48, GREY, 'osw', wght=700, track=0.12), W / 2, 1296,
                                d=self.u + 0.25, kind='slide', dx0=0))
        return dict(t0=0.0, t1=self.T1, bg='ink', side=None, els=els, chips=None, hit=0, wm=False)

    # ── разгон перед дропом ──
    def _build_cards(self):
        u = self.u
        offs = [0, 0.5, 1.0, 1.25, 1.5, 1.75, 1.875]
        offs = [o * self.build_n / 2 for o in offs]
        other = 'h' if self.side == 'a' else 'a'
        seq = [other if k % 2 == 0 else self.side for k in range(len(offs))]
        cards = []
        for k, (o, sd) in enumerate(zip(offs, seq)):
            t0 = self.TB + o * u
            t1 = self.TB + (offs[k + 1] * u if k + 1 < len(offs) else self.build_n * u)
            c = self._name_card(sd, t0, t1, sub=False, build_k=k)
            c['build'] = True
            cards.append(c)
        return cards

    # ── прогноз и финал ──
    def _pick_card(self):
        D, ac, sd = self.drop, self.acc[self.side], self.side
        p, size = best_lines(self.pick1, 'dela', 130 if len(self.pick1) > 20 else 150, 900)
        size = min(size, 150)
        gap = int(size * 0.32)                                 # строки не налезают друг на друга (обводка-эхо ниже на 12 px)
        blk = stack([T(s_, size, WHITE, max_w=910) for s_ in p], gap)
        blk_o = stack([O(s_, size, ac['ink'], 6, max_w=910) for s_ in p], gap)
        es = 450 if blk.height < 240 else 340                 # высокий прогноз — эмблема меньше
        els = [self._el(C.with_shadow(self.fav.emb(es), 30, 0.6, 18), W / 2, 540 - (450 - es) / 2, kind='slam', z0=2.3,
                        kick=-14, dur=0.2, pulse=0.05)]
        y_txt = 540 + 450 / 2 - (450 - es) + 60 + blk.height / 2
        els.append(self._el(blk, W / 2, y_txt, d=0.0, kind='slam', z0=1.6, kick=2, rot=-2, echo=blk_o, off=(12, 12),
                            dur=0.18))
        y = y_txt + blk.height / 2 + 12
        if self.pick2:
            st = boxed(T(self.pick2, 60, INK, max_w=880), PAPER, 26, 14, 4)
            y += 44 + st.height / 2
            els.append(self._el(st, W / 2, y, d=0.06, kind='slam', z0=1.5, kick=-4, rot=1.5))
            y += st.height / 2
        if self.coef:
            lab = T('КЭФ', 64, ac['txt'], 'dela')
            val = T(C.fmt_k(self.coef), 132, ac['txt'], 'dela')
            pw = lab.width + val.width + 110
            pl = C.rrect(pw, 190, 16, ac['bg'])
            C.put(pl, lab, 40 + lab.width / 2, 95 + 4)
            C.put(pl, val, pw - 40 - val.width / 2, 95)
            y += 40 + 95
            els.append(self._el(pl, W / 2, y, d=0.12, kind='slam', z0=1.7, kick=6, rot=-2, pulse=0.035))
        if y > 1300:                                           # высокий блок — всё выше, а не кэф поверх прогноза
            for e in els:
                e['y'] -= y - 1300
        return dict(t0=D, t1=self.TC, bg='glow', side=sd, els=els, chips=None, hit=26, wm=False, pick=True)

    def _end_card(self):
        TC, ac = self.TC, self.acc[self.side]
        els = [self._el(self._emb_fit(self.side, 520, 420), W / 2, 570, kind='slam', z0=1.5, rot=-3)]
        p, size = best_lines(self.pick1, 'dela', 96, 940, 2)
        blk = stack([T(s_, size, WHITE) for s_ in p], int(size * 0.3))
        y_p = 880 + (blk.height - T(p[0], size, WHITE).height) / 2 - (40 if len(p) > 1 else 0)
        els.append(self._el(blk, W / 2, y_p, d=0.04, kind='slam', z0=1.3, rot=-1.5,
                            echo=stack([O(s_, size, ac['ink'], 4) for s_ in p], int(size * 0.3)), off=(8, 8)))
        sub = []
        if self.pick2:
            sub.append(self.pick2)
        if self.coef:
            sub.append('КЭФ ' + C.fmt_k(self.coef))
        if sub:
            els.append(self._el(T(' · '.join(sub), 64, ac['ink'], 'osw', wght=700, track=0.03, max_w=960), W / 2, max(984, y_p + blk.height / 2 + 64),
                                d=0.08, kind='slide', dx0=200))
        els.append(self._el(C.tg_plate(980, 220, font='unb'), W / 2, 1250, d=0.12, kind='slam', z0=1.4, kick=-3))
        return dict(t0=TC, t1=self.dur + 1, bg='ink', side=self.side, els=els, chips=None, hit=12, wm=False, end=True)

    def _prep(self):
        cards = [self._intro()]
        cards += self._team_cards('h', self.T1)
        cards += self._team_cards('a', self.T2)
        cards += self._build_cards()
        cards.append(self._pick_card())
        cards.append(self._end_card())
        for c in cards:
            _ = self._bg(c['bg'], c['side'], c['wm'])
            c['mq'] = self._mq_spec(c['bg'], c['side'],
                                    txt=(self.pick1 if c.get('pick') else None))
        self.cards = cards
        for m in ('none', 'h', 'a', 'time'):
            self._strip(m)
        self._handle()
        self.hits = sorted({round(c['t0'], 4) for c in cards})
        # строка формы (три квадрата) для каждой команды
        for sd in ('h', 'a'):
            for g in self.s[sd]['games']:
                for ring in (None, WHITE, INK):
                    chip(g['res'], 84, ring)
        for col in (WHITE, INK):
            chip_empty(84, col)

    # ── кадр ──
    def _card(self, t):
        for c in self.cards:
            if c['t0'] <= t < c['t1']:
                return c
        return self.cards[-1] if t >= self.cards[-1]['t0'] else self.cards[0]

    def _draw_el(self, fr, e, t, t0, pulse=0.0):
        lt = t - t0 - e['d']
        if lt < 0:
            return
        q = C.seg(lt, 0, e['dur'])
        k = C.out_expo(q)
        x, y = e['x'], e['y']
        kind = e['kind']
        a = 1.0
        if q >= 1 and not pulse:
            im, imo = e['rest'], e['echo_rest']
            s = 1.0
        else:
            s, r = 1.0, e['rot']
            if q < 1:
                if kind == 'slam':
                    s = e['z0'] + (1 - e['z0']) * k
                    r = e['rot'] + e['kick'] * (1 - k)
                elif kind == 'slide':
                    x += e['dx0'] * (1 - k)
                    a = min(1.0, 0.25 + lt / 0.08)
                elif kind == 'drop':
                    y -= 120 * (1 - k)
                    a = min(1.0, 0.2 + lt / 0.08)
            s *= 1 + pulse
            if kind == 'wipe' and q < 1:
                src = e['im']
                ww = max(1, int(src.width * C.out_cubic(q)))
                im = C.rotate(src.crop((0, 0, ww, src.height)), r)
                x -= (src.width - ww) / 2 * math.cos(math.radians(r))
                y += (src.width - ww) / 2 * math.sin(math.radians(r))
                imo = None
            elif abs(s - 1) < 0.003 and abs(r - e['rot']) < 0.05:
                im, imo = e['rest'], e['echo_rest']
            else:
                im = C.rotate(C.scale(e['im'], s), r)
                imo = C.rotate(C.scale(e['echo'], s), r) if e['echo'] is not None else None
        if e['echo'] is not None:
            if lt < 0.34:                                                # разлетающееся эхо от удара
                p = lt / 0.34
                for ds, a0 in ((0.16, 0.7), (0.34, 0.45)):
                    eo = C.scale(e['echo_rest'], s * (1 + ds * C.out_cubic(p)))
                    C.put(fr, eo, x, y, a0 * (1 - p))
            if imo is not None:
                C.put(fr, imo, x + e['off'][0], y + e['off'][1], a)
        C.put(fr, im, x, y, a)

    def _chips(self, fr, c, t):
        side = c['side']
        g = self.s[side]['games']
        if not g:
            return
        cur, live = c['chips']
        n = len(g)
        d, gap = 84, 22
        x0 = W / 2 - (n * (d + 12) + (n - 1) * gap) / 2 + (d + 12) / 2
        ring = INK if c['bg'] in ('paper', 'acc') else WHITE
        for k in range(n):
            x = x0 + k * (d + 12 + gap)
            if k < cur or (k == cur and not live):
                C.put(fr, chip(g[k]['res'], d, None), x, CHIP_Y)
            elif k == cur:
                lt = t - c['t0']
                s = 1.0 + 0.35 * (1 - C.out_expo(C.seg(lt, 0, 0.16)))
                C.put(fr, C.scale(chip(g[k]['res'], d, ring), s * 1.12), x, CHIP_Y)
            else:
                C.put(fr, chip_empty(d, ring), x, CHIP_Y)

    def _mq(self, fr, c, t):
        u = self.u
        rows = c['mq']
        if not rows:
            return
        h = rows[0][0].height
        n = len(rows)
        y0 = TOP - 40
        step = (BOT - y0 + 40) / n
        beats = (t - self.drop) / u
        bi = math.floor(beats)
        frac = beats - bi
        jump = bi + C.out_expo(frac / 0.35)                            # шаг на каждую долю
        for k, (im, per) in enumerate(rows):
            dirn = 1 if k % 2 == 0 else -1
            off = (dirn * (t * 38 + jump * 64) + k * 173) % per
            y = int(y0 + k * step + (step - h) / 2)
            crop = im.crop((int(off), 0, int(off) + W, h))
            fr.alpha_composite(crop, (0, y))

    def _ring(self, fr, cx, cy, p, col, width, rmax):
        r = 40 + rmax * C.out_cubic(p)
        a = int(255 * (1 - p) ** 1.5)
        if a < 4:
            return
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse((cx - r, cy - r, cx + r, cy + r), outline=tuple(col) + (a,),
                                    width=max(2, int(width * (1 - 0.6 * p))))
        fr.alpha_composite(lay)

    def frame(self, t):
        u, D = self.u, self.drop
        c = self._card(t)
        t0 = c['t0']
        fr = self._bg(c['bg'], c['side'], c['wm']).copy()
        self._mq(fr, c, t)
        pulse_k = 0.0
        if c.get('pick'):
            for n in range(1, 8):                                      # кольца и пульс на доли
                tb = self.b(n)
                if tb <= t < tb + 0.5:
                    self._ring(fr, W / 2, 540, C.seg(t, tb, tb + 0.5), self.acc[self.side]['ink'], 16, 700)
                if tb <= t:
                    pulse_k = max(pulse_k, (1 - C.seg(t, tb, tb + 0.3)) ** 2)
            if t < D + 0.7:                                            # ударная волна дропа
                for dl, col, wd in ((0.0, WHITE, 30), (0.08, self.acc[self.side]['ink'], 22), (0.18, WHITE, 10)):
                    if t >= D + dl:
                        self._ring(fr, W / 2, 540, C.seg(t, D + dl, D + dl + 0.55), col, wd, 1100)
        for e in c['els']:
            self._draw_el(fr, e, t, t0, pulse=e['pulse'] * pulse_k if e['pulse'] else 0.0)
        if c.get('chips'):
            self._chips(fr, c, t)
        # камера: толчок на склейке, микро-толчок на полудоле, разгон перед дропом, удар на дропе
        z, dx, dy, rot = 1.0, 0.0, 0.0, 0.0
        if c['hit']:
            sx, sy = C.shake(t, t0, c['hit'], 0.26 if not c.get('pick') else 0.5)
            dx, dy = dx + sx, dy + sy
            z += 0.035 * (1 - C.out_cubic(C.seg(t, t0, t0 + 0.3)))
        nb = (t - D) / u
        half = math.floor(nb * 2) / 2
        th = D + half * u
        if abs(half - round(half)) > 0.1 and th >= t0 + 0.2:            # полудоля внутри сцены
            z += 0.012 * (1 - C.seg(t, th, th + 0.2)) ** 2
        if c.get('pick'):
            k = 1 - C.seg(t, D, D + 0.5)
            z += 0.07 * k ** 2 + 0.012 * pulse_k
            rot = 1.6 * k ** 2 * math.sin((t - D) * 38)
            for n in range(1, 8):
                sx, sy = C.shake(t, self.b(n), 6, 0.22)
                dx, dy = dx + sx, dy + sy
        if c.get('build'):
            q = C.seg(t, self.TB, D)
            z += 0.08 * C.in_cubic(q)
        fr = fr.convert('RGB')
        if z > 1.001 or abs(dx) + abs(dy) > 0.5 or abs(rot) > 0.02:
            fr = C.zoom(fr, z, dx=dx, dy=dy, rot=rot)
        # расслоение цвета: разгон и дроп
        rs = 0
        if c.get('build'):
            rs = 3 + 13 * C.in_cubic(C.seg(t, self.TB, D))
        if D <= t < D + 0.35:
            rs = 18 * (1 - C.seg(t, D, D + 0.35))
        if rs >= 1:
            fr = C.rgb_split(fr, rs)
        fr = fr.convert('RGBA')
        # вспышка на дропе
        if D <= t < D + 0.1:
            a = 1 - C.seg(t, D, D + 0.1)
            fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(235 * a))))
        # полосы матча и @jarvibet
        mode = 'time' if t >= D else (c['side'] if c['side'] and t >= self.T1 else 'none')
        fr.alpha_composite(self._strip(mode), (0, STRIP_Y - STRIP_H // 2))
        if t < self.TC:
            if C.HANDLE_BOTTOM:
                fr.alpha_composite(self._handle(), (0, HAND_Y - HAND_H // 2))
        return C.grain(fr, t, 9)
