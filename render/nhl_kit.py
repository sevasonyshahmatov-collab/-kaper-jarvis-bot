# -*- coding: utf-8 -*-
"""Полный набор баннеров НХЛ — те же семь типов, что и для КХЛ.

Одиночные матчи рисуются в «Боках» (утверждённый шаблон НХЛ), сводные — той же
вёрсткой, что в КХЛ, но с ледяным акцентом и шапкой «JARVIS | NHL».

    import nhl, nhl_kit
    nhl.register()
    nhl_kit.preview('Бостон', 'Торонто', info, 'out/nhl/card.png')

Функции сами разводят похожие клубные цвета (nhl.pair_colors) и сами
переключают оформление на НХЛ — отдельный вызов nhl.skin() не нужен.
"""
import os

from PIL import Image, ImageDraw

import nhl
import poster
import quality
import recap
from nhl import ICE

GREEN = (36, 200, 88)
RED = (226, 58, 78)

FOOT_ODDS = 'коэффициенты в основное время на момент публикации'
FOOT_PICK = 'прогноз канала · коэффициент на момент публикации'


def _prep(home, away):
    if all(t in poster.TEAMS and t not in nhl.TEAMS for t in (home, away)):
        return home, away                     # клубы КХЛ — как есть, цвета из poster.BANNER
    h, a = nhl.resolve(home), nhl.resolve(away)
    nhl.pair_colors(h, a)
    return h, a


def _jpg(path, quality=95):
    """PNG → JPEG рядом, PNG удаляется. Автору отдаём только jpg."""
    if not path.lower().endswith('.png'):
        return path
    out = path[:-4] + '.jpg'
    Image.open(path).convert('RGB').save(out, quality=quality, subsampling=0, optimize=True)
    os.remove(path)
    return out


# ── единый рендер «Бока» для одиночного матча ────────────────────────────────
def _side(home, away, path, mode, home_info=None, away_info=None, when=None,
          odds=None, pred=None, coef=None, score=None, verdict=None, verdict_color=None,
          foot=None, tag='NHL', accent=ICE, handle='@jarvibet',
          W=1280, H=640, grain=1.0, seed=None, scale=2):
    """mode: 'odds' — линия П1/Х/П2 | 'pick' — прогноз и кэф | 'score' — счёт матча.
    scale — во сколько раз крупнее рисовать: 2 — 2560×1280 (обычно), 3 — 3840×1920 («4К»)."""
    import numpy as np
    h, a = _prep(home, away)
    c1, c2 = poster.BANNER[h], poster.BANNER[a]
    saved = poster.FONTS7
    poster.FONTS7 = dict(saved, **poster.FONTS_SIDE)
    try:
        S = scale
        WW, HH = W * S, H * S
        if seed is None:
            seed = sum(map(ord, h + a)) % 997

        # фон: перелив клубных цветов, затемнения по бокам и снизу, текстура
        bg = poster._fluid_bg(WW // 2, HH // 2, c1, c2, seed=seed).resize((W, H), Image.LANCZOS)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dim = (0.42 * np.exp(-(((yy / H) - 0.95) ** 2) / 0.02)
               + 0.26 * (np.exp(-(((xx / W) - 0.13) ** 2) / 0.02)
                         + np.exp(-(((xx / W) - 0.87) ** 2) / 0.02))
               * np.exp(-(((yy / H) - 0.55) ** 2) / 0.06))
        if mode == 'score':
            dim = dim + 0.30 * np.exp(-(((xx / W) - 0.5) ** 2) / 0.012) \
                              * np.exp(-(((yy / H) - 0.45) ** 2) / 0.05)
        shade = Image.new('RGBA', (W, H), (5, 8, 14, 0))
        shade.putalpha(Image.fromarray((np.clip(dim, 0, 1) * 255).astype('uint8'), 'L'))
        bg = Image.alpha_composite(bg.convert('RGBA'), shade).convert('RGB')
        bg = poster._canvas_texture(bg, grain).convert('RGBA')

        ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
        # в режиме счёта эмблемы чуть меньше и разведены шире — между ними цифры
        if mode == 'score':
            eh, ew, gap = int(H * 0.30) * S, int(W * 0.14) * S, int(WW * 0.215)
        else:
            eh, ew, gap = int(H * 0.36) * S, int(W * 0.17) * S, int(WW * 0.045)
        cy = int(HH * (0.45 if mode == 'score' else 0.47))

        def needs_plate(team, col):
            e = poster._raw_emblem(team, 200, 200)
            arr = np.asarray(e).astype(np.float32)
            op = arr[..., 3] > 128
            if not op.any():
                return False
            mean = arr[..., :3][op].mean(axis=0)
            return float(np.sqrt(((mean - np.array(col, np.float32)) ** 2).sum())) < 110

        e1 = poster._raw_emblem(h, ew, eh, plate=needs_plate(h, c1))
        e2 = poster._raw_emblem(a, ew, eh, plate=needs_plate(a, c2))
        poster._shadowed(ov, e1, (int(WW / 2 - gap / 2 - e1.width), cy - e1.height // 2),
                         blur=13 * S, off=(0, 7 * S), color=(0, 0, 0, 125))
        poster._shadowed(ov, e2, (int(WW / 2 + gap / 2), cy - e2.height // 2),
                         blur=13 * S, off=(0, 7 * S), color=(0, 0, 0, 125))
        d = ImageDraw.Draw(ov)

        # шапка JARVIS | NHL
        fb = poster._f7('brand', 26 * S)
        sp, bar = 3 * S, 22 * S
        w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
        w2 = sum(fb.getlength(c) for c in tag) + sp * max(0, len(tag) - 1)
        x0 = WW / 2 - (w1 + 2 * bar + w2) / 2
        yb = int(58 * S)
        poster._spaced(d, (x0, yb), 'JARVIS', fb, (255, 255, 255, 255), sp)
        d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, yb - 14 * S, x0 + w1 + bar + 1.5 * S, yb + 14 * S),
                            radius=S, fill=(255, 255, 255, 150))
        poster._spaced(d, (x0 + w1 + 2 * bar, yb), tag, fb, accent + (255,), sp)

        # счёт между эмблемами
        if mode == 'score':
            sh, sa = score
            fsc = poster._f7('num', 92 * S)
            d.text((WW / 2 - 46 * S, cy), str(sh), font=fsc, anchor='rm',
                   fill=((255, 255, 255, 255) if sh > sa else (198, 208, 224, 255)))
            d.text((WW / 2, cy), ':', font=poster._f7('num', 58 * S), fill=accent + (235,), anchor='mm')
            d.text((WW / 2 + 46 * S, cy), str(sa), font=fsc, anchor='lm',
                   fill=((255, 255, 255, 255) if sa > sh else (198, 208, 224, 255)))

        # блоки команд по бокам — посередине между краем картинки и эмблемой, по высоте — на центре эмблемы;
        # ширина считается от настоящего края эмблемы, чтобы длинные названия («Нью-Йорк Айлендерс») не наезжали на логотип
        def block(team, t, emb, side):
            if side == 'left':
                x0, x1 = 64 * S, WW / 2 - gap / 2 - emb.width - 18 * S
            else:
                x0, x1 = WW / 2 + gap / 2 + emb.width + 18 * S, WW - 64 * S
            x = int((x0 + x1) / 2)
            name = poster.SHORT.get(team, team).upper()
            size = 66 * S
            ft = poster._f7('team', size)
            while ft.getlength(name) > x1 - x0 and size > 26 * S:
                size -= 2 * S
                ft = poster._f7('team', size)
            steps = ([int(56 * S)] if t else []) + ([int(44 * S)] if t and t.get('form') else [])
            y = int(cy - sum(steps) / 2)
            d.text((x, y), name, font=ft, fill=(255, 255, 255, 255), anchor='mm')
            if t:
                y += steps[0]
                d.text((x, y), t.get('line', ''), font=poster._f7('info', 22 * S),
                       fill=(232, 236, 242, 255), anchor='mm')
                if t.get('form'):
                    y += steps[1]
                    poster._form_row(d, x, y, t['form'][-5:], S, align='center')

        block(h, home_info, e1, 'left')
        block(a, away_info, e2, 'right')

        # время
        if when:
            ft = poster._f7('time', 22 * S)
            tw = ft.getlength(when)
            L, ld = poster._layer_draw(ov)
            ld.rounded_rectangle((WW / 2 - tw / 2 - 30 * S, 486 * S, WW / 2 + tw / 2 + 30 * S, 540 * S),
                                 radius=27 * S, fill=(8, 12, 20, 200), outline=accent + (220,), width=2 * S)
            ov.alpha_composite(L)
            d = ImageDraw.Draw(ov)
            d.text((WW / 2, 513 * S), when, font=ft, fill=(255, 255, 255, 255), anchor='mm')

        y0, y1 = 558 * S, 604 * S

        if mode == 'odds' and odds:                     # линии ещё нет — без строки кэфов
            labels = ['П1', 'Х', 'П2']
            best = min(range(3), key=lambda i: odds[i])
            fl, fn = poster._f7('info', 16 * S), poster._f7('num', 22 * S)
            cw, gc = 132 * S, 16 * S
            x = WW / 2 - (3 * cw + 2 * gc) / 2
            L, ld = poster._layer_draw(ov)
            for i in range(3):
                ld.rounded_rectangle((x + i * (cw + gc), y0, x + i * (cw + gc) + cw, y1), radius=22 * S,
                                     fill=(8, 12, 20, 170),
                                     outline=(accent + (230,)) if i == best else (255, 255, 255, 70), width=2 * S)
            ov.alpha_composite(L)
            d = ImageDraw.Draw(ov)
            for i in range(3):
                cx0 = x + i * (cw + gc)
                d.text((cx0 + 26 * S, 582 * S), labels[i], font=fl, fill=(170, 178, 192, 255), anchor='lm')
                d.text((cx0 + cw - 22 * S, 582 * S), '%.2f' % odds[i], font=fn,
                       fill=(accent + (255,)) if i == best else (255, 255, 255, 255), anchor='rm')

        elif mode != 'odds':
            # 'pick' и 'score' делят одну строку: вердикт | ставка | кэф
            cells = []
            if verdict:
                vc = verdict_color or (GREEN if verdict.lower().startswith(('заш', 'выигр')) else RED)
                cells.append(('fill', verdict.upper(), vc, (8, 20, 12), 19 * S, 50 * S))
            if pred:
                size = 20 * S
                fp = poster._f7('num', size)
                while fp.getlength(pred) > 560 * S and size > 13 * S:
                    size -= 1
                    fp = poster._f7('num', size)
                cells.append(('ghost', pred, None, (255, 255, 255), size, 52 * S))
            if coef:
                cells.append(('coef', '%.2f' % coef, accent, (16, 18, 24), 22 * S, 96 * S))
            if cells:
                widths = [poster._f7('num', s).getlength(t) + pad for _, t, _, _, s, pad in cells]
                gp = 12 * S
                xs = WW / 2 - (sum(widths) + gp * (len(cells) - 1)) / 2
                L, ld = poster._layer_draw(ov)
                x = xs
                for (kind, _t, col, _fg, _s, _p), w in zip(cells, widths):
                    if kind == 'ghost':
                        ld.rounded_rectangle((x, y0, x + w, y1), radius=23 * S,
                                             fill=(8, 12, 20, 180), outline=(255, 255, 255, 70), width=2 * S)
                    else:
                        ld.rounded_rectangle((x, y0, x + w, y1), radius=23 * S, fill=col + (255,))
                    x += w + gp
                ov.alpha_composite(L)
                d = ImageDraw.Draw(ov)
                x = xs
                for (kind, t, _c, fg, s, _p), w in zip(cells, widths):
                    if kind == 'coef':
                        d.text((x + 34 * S, 581 * S), 'КЭФ', font=poster._f7('info', 13 * S),
                               fill=fg + (255,), anchor='mm')
                        d.text((x + w - 34 * S, 581 * S), t, font=poster._f7('num', s),
                               fill=fg + (255,), anchor='mm')
                    else:
                        d.text((x + w / 2, 581 * S), t, font=poster._f7('num', s), fill=fg + (255,), anchor='mm')
                    x += w + gp

        if foot is None:
            foot = (FOOT_ODDS if odds else '') if mode == 'odds' else (FOOT_PICK if mode == 'pick' else '')
        if foot:
            d.text((WW / 2, 624 * S), foot, font=poster._f7('info', 14 * S),
                   fill=(196, 202, 214, 255), anchor='mm')
        elif handle:
            poster._spaced(d, (WW / 2, 624 * S), handle, poster._f7('info', 13 * S),
                           accent + (255,), 1.6 * S, anchor='m')

        out = quality.compose(bg, ov).convert('RGB')                 # SCALE = 2 — без уменьшения, 2560×1280
        if path.lower().endswith('.png'):
            out.save(path, optimize=True)
        else:
            out.save(path, quality=96, subsampling=0)
        return path
    finally:
        poster.FONTS7 = saved


# ── 1. предматчевая карточка ─────────────────────────────────────────────────
def preview(home, away, info, path, **kw):
    """info = dict(when, odds=(П1, Х, П2), home=team_info(...), away=team_info(...))"""
    return _side(home, away, path, 'odds', when=info['when'], odds=info['odds'],
                 home_info=info.get('home'), away_info=info.get('away'), **kw)


# ── 2. постер прогноза ───────────────────────────────────────────────────────
def pick(m, path, **kw):
    """m = dict(when, pred, coef, home=dict(team=..., **team_info), away=...)"""
    return _side(m['home']['team'], m['away']['team'], path, 'pick',
                 when=m.get('when'), pred=m['pred'], coef=m.get('coef'),
                 home_info=m['home'], away_info=m['away'], foot=m.get('foot'), **kw)


# ── 3. постер результата ─────────────────────────────────────────────────────
def result(home, away, sh, sa, path, verdict=None, verdict_color=None, when=None,
           pred=None, coef=None, home_info=None, away_info=None, **kw):
    return _side(home, away, path, 'score', score=(sh, sa), when=when,
                 verdict=verdict, verdict_color=verdict_color, pred=pred, coef=coef,
                 home_info=home_info, away_info=away_info, **kw)


# ── 4–7. сводные баннеры ─────────────────────────────────────────────────────
def _pairs(items):
    for it in items:
        it['home'], it['away'] = _prep(it['home'], it['away'])
    return items


def slate(items, path, date_title=None, title='МАТЧИ ДНЯ', **kw):
    items = _pairs(items)
    with nhl.skin():
        return recap.render_slate(items, path, title=title, date_title=date_title, **kw)


def picks(items, path, date_title=None, express=None, title='ПРОГНОЗЫ ДНЯ', **kw):
    items = _pairs(items)
    with nhl.skin():
        return recap.render_picks(items, path, date_title, express=express, title=title, **kw)


def hits(items, path, date_title=None, express=None, **kw):
    items = _pairs(items)
    with nhl.skin():
        return recap.render_hits(items, path, date_title, express=express, **kw)


def results_day(items, path, date_title=None, title='ИТОГИ ДНЯ', **kw):
    items = _pairs(items)
    with nhl.skin():
        return recap.render_results_day(items, path, title=title, date_title=date_title, **kw)


team_info = poster.team_info
