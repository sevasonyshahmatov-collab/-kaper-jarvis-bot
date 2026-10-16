# -*- coding: utf-8 -*-
"""Карточка «Итоги прогнозов» к посту итогов: тот же язык, что «Итоги дня» в render/matchday_vs.py (results=True,
макет strips) — тёмный фон, панели клубов с эмблемами, крупный счёт, проигравший в матче приглушён; но только матчи
наших прогнозов и вместо «ПОБЕДА» — строка ставки и плашка вердикта: ЗАШЛО (залитая цветом акцента), МИНУС (тёмная,
серая), ВОЗВРАТ (контур акцента). Статичный JPG шириной 1080 (рисуем в 2× и уменьшаем).

    import card
    card.render(rows, 'out/daily/2026-10-16/recap.jpg', title_date='15 октября', score='3 из 5')
rows — как в compose.recap_post: {league, home, away, g: {hg, ag, end}, short, res}. До 8 матчей; больше — None.
"""
import os
import sys

os.environ.setdefault('JARVIS_S', '2')                        # matchday_vs рисует в quality.S; нам хватит 2× и 1080 на выходе
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))

MAX_ROWS = 8


def render(rows, path, title_date, score):
    if not rows or len(rows) > MAX_ROWS:
        return None
    from PIL import Image, ImageDraw

    import brand_kit
    import matchday_vs as mv
    import nhl
    import poster
    import quality

    S = mv.S
    leagues = {r['league'] for r in rows}
    if 'NHL' in leagues:
        nhl.register()
    acc = poster.ACC if 'KHL' in leagues else nhl.ICE
    R, top, H = mv._layout(len(rows), len(rows))
    g = mv._geom(R)
    F = mv._res_fonts(g['ab'], min(66, R * 0.32), g['ph'])
    F['bet'] = mv._cap(mv.MAN, 800, max(12, min(23, R * 0.10)) * S)
    F['badge'] = mv._cap(mv.OSW, 600, g['ph'] * 0.40 * S)

    img = mv._background(H)
    d = ImageDraw.Draw(img)
    # шапка: марка (обе лиги — «KXL · NHL»), заголовок, дата и счёт дня
    tag = ' · '.join(mv.TAG[x] for x in ('KHL', 'NHL') if x in leagues)
    fm = brand_kit.font(mv.OSW, 26 * S, 700)
    wj, wt = fm.getlength('JARVIS'), fm.getlength(tag)
    gx, bar = 26 * 0.58 * S, 3.25 * S
    x = mv.W / 2 * S - (wj + 2 * gx + bar + wt) / 2
    _, t_, _, b_ = fm.getbbox('J', anchor='ls')
    base = 50 * S - (t_ + b_) / 2
    d.text((x, base), 'JARVIS', font=fm, fill=(245, 245, 245), anchor='ls')
    d.rectangle((x + wj + gx, base + t_ * 1.08, x + wj + gx + bar, base + 1.5 * S), fill=(220, 220, 225))
    d.text((x + wj + 2 * gx + bar, base), tag, font=fm, fill=acc, anchor='ls')
    ft = mv._fit_w('ИТОГИ ПРОГНОЗОВ', mv.ALU, 900, 80 * S, (mv.W - 2 * mv.MX) * S)
    mv._txt(d, mv.W / 2 * S, 124 * S, 'ИТОГИ ПРОГНОЗОВ', ft, (245, 245, 245))
    mv._spaced(d, mv.W / 2 * S, 196 * S, ('%s · зашло %s' % (title_date, score)).upper(), mv._cap(mv.OSW, 600, 21 * S), acc, 3 * S)

    for i, r in enumerate(rows):
        _row(img, r, top + i * (R + mv.GAP), R, g, acc, F, i, mv, S)

    d = ImageDraw.Draw(img)
    note = 'ФИНАЛЬНЫЙ СЧЁТ' + (' · ' + mv.RES_FOOT if any(r['g'].get('end') for r in rows) else '')
    mv._spaced(d, mv.W / 2 * S, (H - 66) * S, note, mv._cap(mv.MAN, 700, 10 * S), mv.GREY, 1.2 * S)
    mv._spaced(d, mv.W / 2 * S, (H - 32) * S, '@jarvibet', mv._cap(mv.OSW, 600, 19 * S), acc, 2 * S)
    out = quality.texture(img, 2).convert('RGB')
    if out.width != mv.W:
        out = out.resize((mv.W, round(out.height * mv.W / out.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    out.save(path, quality=92, optimize=True)
    return path


def _row(img, r, y0, R, g, acc, F, i, mv, S):
    from PIL import ImageDraw
    league = r['league']
    (hn, hc, ha), (an, ac, aa) = mv._pair(r, league)
    it = dict(sh=r['g']['hg'], sa=r['g']['ag'], mark=r['g'].get('end') or '')
    sh, sa, mark, win = mv._res(it)
    pw, off, ph = g['pw'], g['off'], g['ph']
    for k, (x0, top, col, team, ab, seed, fade) in enumerate(((mv.MX, y0, hc, hn, ha, 11 + 7 * i, 'down'),
                                                               (mv.W - mv.MX - pw, y0 + off, ac, an, aa, 23 + 7 * i, 'up'))):
        lose = mv._lost(win, k)
        box = (x0 * S, top * S, (x0 + pw) * S, (top + R - off) * S)
        mv._panel(img, box, mv._dim(col) if lose else col, seed, fade, (0.5, 0.52))
        es = min((R - off) * 0.84, pw * 0.76) * (0.92 if lose else 1)
        mv._emblem(img, team, (x0 + pw / 2) * S, (top + (R - off) * 0.52) * S, es * S, ab, col, dim=lose)
    d = ImageDraw.Draw(img)
    zc = (g['zx0'] + g['zx1']) / 2
    ya = y0 + R * 0.34
    sw = mv._score(d, zc * S, ya * S, sh, sa, F['sc'], win) / S
    room = ((g['zx1'] - g['zx0']) / 2 - sw / 2 - 18) * S
    for k, (abbr, col, x, anchor) in enumerate(((ha, hc, g['zx0'], 'l'), (aa, ac, g['zx1'], 'r'))):
        c = mv._dim_ink(col) if mv._lost(win, k) else mv._readable(col)
        mv._txt(d, x * S, ya * S, abbr, mv._fit_room(abbr, mv.ALU, 900, F['ab'], room), c + (255,), anchor)
    # нижняя строка: ставка слева, ОТ/Б в середине, вердикт справа
    yp = y0 + R * 0.78
    label = {'win': 'ЗАШЛО', 'loss': 'МИНУС', 'push': 'ВОЗВРАТ'}[r['res']]
    bw = mv._spaced_w(label, F['badge'], 2 * S) / S + ph * 0.95
    bx = g['zx1'] - bw / 2
    box = (bx - bw / 2) * S, (yp - ph / 2) * S, (bx + bw / 2) * S, (yp + ph / 2) * S
    if r['res'] == 'win':
        d.rounded_rectangle(box, radius=int(ph * .28 * S), fill=acc)
        mv._spaced(d, bx * S, yp * S, label, F['badge'], mv.INK, 2 * S)
    elif r['res'] == 'loss':
        d.rounded_rectangle(box, radius=int(ph * .28 * S), fill=(46, 44, 52), outline=(92, 90, 100), width=max(2, int(ph * 0.05 * S)))
        mv._spaced(d, bx * S, yp * S, label, F['badge'], (170, 168, 178), 2 * S)
    else:
        d.rounded_rectangle(box, radius=int(ph * .28 * S), fill=mv.BG, outline=mv._over(acc, 0.85), width=max(2, int(ph * 0.05 * S)))
        mv._spaced(d, bx * S, yp * S, label, F['badge'], acc, 2 * S)
    left = g['zx0']
    if mark:
        mw = mv._mark_w(F, ph * 0.8 * S, mark) / S
        mv._mark_pill(d, (left + mw / 2) * S, yp * S, ph * 0.8 * S, mark, F, acc)
        left += mw + 10
    room_b = (bx - bw / 2 - 14 - left) * S
    label = r['short'] + (' · %s' % ('%.2f' % r['kef']).replace('.', ',') if r.get('kef') else '')
    f = mv._fit_room(label, mv.MAN, 800, F['bet'], room_b)
    mv._txt(d, left * S, yp * S, label, f, (236, 234, 242) + (255,), 'l')
