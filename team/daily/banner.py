# -*- coding: utf-8 -*-
"""Баннер итогов прогнозов — шаблон «Матчи дня» (render/matchday_vs.py, results=True, макет strips), та же семья, что
«Итоги дня»: только матчи наших вчерашних прогнозов, у каждого счёт, внизу полосы — знак вердикта (✅ / ❌ / ↩️,
нарисованы — в шрифтах постера эмодзи нет), наша ставка и «ОТ»/«Б». До 8 матчей — одна высокая картинка: 1080×1350 (4:5) до
4 матчей, дальше выше, до 1080×1920 при 8 (в ленте Telegram крупно). Больше 8 — альбом (подпись к первой), у всех один
размер, со второй — продолжение (cont=True). Шапка — «JARVIS | КХЛ · НХЛ» кириллицей. JPG шириной 1080 (рисуем в 2×)."""
import os
import sys

os.environ.setdefault('JARVIS_S', '2')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))

PER_IMAGE = 8                 # владелец 16.10: одна картинка до 8 матчей (альбом из узких картинок в ленте мелкий)
H_BASE, H_TOP, ROWS_BASE = 1350, 1920, 4   # до 4 матчей — 1080×1350 (4:5), дальше выше, до 1080×1920 при 8


def height(n):
    """Высота постера под n матчей: 4:5 до 4, затем ровно до 1920 к 8."""
    if n <= ROWS_BASE:
        return H_BASE
    return min(H_TOP, H_BASE + round((H_TOP - H_BASE) * (n - ROWS_BASE) / (PER_IMAGE - ROWS_BASE)))


SHORT = (('индивидуальный тотал', 'инд. тотал'), ('в основное время', 'в осн. время'), ('тотал матча', 'тотал'),
         ('не проиграет', 'не проиграет'), (' (с ОТ и Б)', ''))


def bet_label(r):
    t = r['bet']
    for a, b in SHORT:
        t = t.replace(a, b)
    if len(t) > 30:                                  # не влезает крупно — без «в осн. время» (правило — в подписи поста)
        t = t.replace(' в осн. время', '').replace('индивидуальный', 'инд.')
    return t + (' · %s' % ('%.2f' % r['kef']).replace('.', ',') if r.get('kef') else '')


def groups(n):
    """8 → [8]; 9 → [5, 4]; 17 → [6, 6, 5] — поровну, не больше PER_IMAGE."""
    k = -(-n // PER_IMAGE)
    base, extra = divmod(n, k)
    return [base + (1 if i < extra else 0) for i in range(k)]


def render(rows, out_dir, date_title):
    """rows — рассчитанные прогнозы (compose); → список путей JPG."""
    if not rows:
        return []
    from PIL import Image
    import matchday_vs as mv
    leagues = {r['league'] for r in rows}
    league = 'KHL+NHL' if len(leagues) > 1 else leagues.pop() + '-RU'      # шапка «JARVIS | КХЛ · НХЛ» — кириллицей
    items = [dict(home=r['home'], away=r['away'], sh=r['g']['hg'], sa=r['g']['ag'], mark=r['g'].get('end') or '',
                  league=r['league'], verdict=r['res'], bet=bet_label(r)) for r in rows]
    sizes = groups(len(items))
    paths, i = [], 0
    os.makedirs(out_dir, exist_ok=True)
    for k, n in enumerate(sizes):
        p = os.path.join(out_dir, 'recap_%d.jpg' % (k + 1))
        mv.render(items[i:i + n], p, league=league, title='ИТОГИ ПРОГНОЗОВ', date_title=date_title, cont=k > 0,
                  rows=max(sizes), results=True, style='strips', h_max=height(max(sizes)))
        with Image.open(p) as im:
            if im.width != mv.W:
                im.convert('RGB').resize((mv.W, round(im.height * mv.W / im.width)), Image.LANCZOS).save(p, quality=92, optimize=True)
        paths.append(p)
        i += n
    return paths
