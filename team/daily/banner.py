# -*- coding: utf-8 -*-
"""Баннер итогов прогнозов — шаблон «Матчи дня» (render/matchday_vs.py, results=True, макет strips), та же семья, что
«Итоги дня»: только матчи наших вчерашних прогнозов, у каждого счёт, внизу полосы — знак вердикта (✅ / ❌ / ↩️,
нарисованы — в шрифтах постера эмодзи нет), наша ставка и «ОТ»/«Б». До 5 матчей на картинку; больше — несколько картинок
(альбом, подпись к первой), у всех один размер, со второй — продолжение (cont=True), как альбомы «Итогов дня».
JPG шириной 1080 (рисуем в 2× и уменьшаем)."""
import os
import sys

os.environ.setdefault('JARVIS_S', '2')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))

PER_IMAGE = 5
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
    """5 → [5]; 7 → [4, 3]; 11 → [4, 4, 3] — поровну, не больше PER_IMAGE."""
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
    league = 'KHL+NHL' if len(leagues) > 1 else leagues.pop()
    items = [dict(home=r['home'], away=r['away'], sh=r['g']['hg'], sa=r['g']['ag'], mark=r['g'].get('end') or '',
                  league=r['league'], verdict=r['res'], bet=bet_label(r)) for r in rows]
    sizes = groups(len(items))
    paths, i = [], 0
    os.makedirs(out_dir, exist_ok=True)
    for k, n in enumerate(sizes):
        p = os.path.join(out_dir, 'recap_%d.jpg' % (k + 1))
        mv.render(items[i:i + n], p, league=league, title='ИТОГИ ПРОГНОЗОВ', date_title=date_title, cont=k > 0,
                  rows=max(sizes), results=True, style='strips')
        with Image.open(p) as im:
            if im.width != mv.W:
                im.convert('RGB').resize((mv.W, round(im.height * mv.W / im.width)), Image.LANCZOS).save(p, quality=92, optimize=True)
        paths.append(p)
        i += n
    return paths
