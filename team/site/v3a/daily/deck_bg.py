# -*- coding: utf-8 -*-
"""Фоны «Колоды матчей» (matches.html): ТОТ ЖЕ фон, что на баннерах Telegram, — render/poster.py: _fluid_bg (перелив двух цветов,
складки света и тени) + _canvas_texture (диагональное плетение холста и зерно). Слева цвет хозяев, справа — гостей.
Цвета: хоккей — как у баннеров (КХЛ poster.BANNER, НХЛ render/nhl.py BANNER; близкие пары разводятся вторым цветом гостей,
как в versus.pair_colors); футбол — цвета клуба из football-lite (c), приведённые к «баннерной» яркости.
Результат: data/deckbg/<ключ матча>.webp (2560×1440, компьютер) и <ключ>-m.webp (1170×2010, телефон) + data/deckbg/index.json.
Фоны матчей, которых больше нет в окне today.json, удаляются. Seed стабилен от ключа матча — файл не меняется между запусками.
    python team/site/v3a/daily/deck_bg.py [ключ …]   (без аргументов — все матчи окна)
"""
import colorsys, json, os, re, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
V3A = os.path.abspath(os.path.join(HERE, '..'))
REPO = os.path.abspath(os.path.join(V3A, '..', '..', '..'))
RENDER = os.path.join(REPO, 'render')
sys.path.insert(0, RENDER)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import poster  # noqa: E402
import nhl  # noqa: E402

OUT = os.path.join(V3A, 'data', 'deckbg')
SIZES = {'': (2560, 1440), '-m': (1170, 2010)}  # чётко на экранах высокой плотности (владелец 04.11: «фон размытый»)
QUALITY = {'': 80, '-m': 70}  # телефон 70: файл 320 → 77 КБ при том же размере (аудит 08.11, скорость matches.html)
DIM = 0.84            # лёгкое затемнение: под колонкой «О встрече» мелкий белый текст читается (подложка плюс это)
# правки цветов, которые применялись на баннерах (render/fix_pairs.py)
FIX = {'sochi': (28, 58, 116), 'avtomobilist': (38, 42, 48)}


def jload_js(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))


def _maps():
    """slug → (основной, второй) цвета хоккейных клубов по реестрам баннеров."""
    m = {}
    for ru, v in poster.TEAMS.items():
        m[v[0]] = (poster.BANNER.get(ru, v[1]), v[2])
    for ru, v in nhl.TEAMS.items():
        m[v[0]] = (nhl.BANNER[ru], nhl.SECOND[ru])
    for k, c in FIX.items():
        if k in m:
            m[k] = (c, m[k][1])
    return m


def _hex(h):
    h = str(h).lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _banner_color(cands):
    """Футбол и клубы без записи в реестре: берём самый насыщенный цвет и приводим к «баннерным» (яркий, не белый, не чёрный)."""
    best, bs = None, -1
    for c in cands:
        h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])
        sc = s * (0.4 + v) if v > 0.12 and s > 0.2 else -1
        if sc > bs:
            best, bs = (h, s, v), sc
    if best is None:                       # белый / чёрный / серый клуб — нейтральный стальной
        return (120, 124, 132)
    h, s, v = best
    s = min(0.85, max(0.6, s))
    v = min(0.82, max(0.68, v))
    return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** .5


def colors_for(m, HM, FB, TL):
    """(c1, c2): хозяева слева, гости справа; близкие — гостям второй цвет."""
    def one(slug):
        if m['lg'] in ('khl', 'nhl'):
            if slug in HM:
                return HM[slug][0], HM[slug][1]
            t = (TL.get(slug) or {}).get('colors') or []
            cs = [_hex(x) for x in t]
            return _banner_color(cs), _banner_color(cs[::-1])
        t = FB.get(slug) or {}
        cs = [_hex(x) for x in (t.get('c') or [])]
        return _banner_color(cs), _banner_color(cs[::-1])
    c1, s1 = one(m['h'])
    c2, s2 = one(m['a'])
    if _dist(c1, c2) < (60 if m['lg'] == 'khl' else 110):      # КХЛ — как на баннерах (цвета как есть), НХЛ и футбол — как versus.pair_colors
        chroma = lambda c: max(c) - min(c)
        if chroma(s2) > 40 and _dist(c1, s2) >= 110:
            c2 = s2
        elif chroma(s1) > 40 and _dist(s1, c2) >= 110:
            c1 = s1
        else:
            c2 = (34, 62, 118) if _dist(c1, (34, 62, 118)) >= 110 else (200, 40, 50)
    return c1, c2


def render(c1, c2, seed, W, H):
    """Как баннеры: фон считается в половинном размере и растягивается (гладкий), затем текстура холста."""
    bg = poster._fluid_bg(W // 2, H // 2, c1, c2, seed=seed).resize((W, H), Image.BICUBIC).convert('RGB')
    bg = poster._canvas_texture(bg, 1.0)
    a = np.asarray(bg).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx / W - 0.5) * 1.15) ** 2 + ((yy / H - 0.5) * 1.0) ** 2)
    a *= (DIM * (1 - 0.42 * np.clip(r - 0.30, 0, 1)))[..., None]            # виньетка к краям
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGB')


def safe(key):
    return re.sub(r'[^A-Za-z0-9_-]+', '_', key).strip('_')


def main(only=None):
    today = json.load(open(os.path.join(V3A, 'data', 'today.json'), encoding='utf-8'))
    HM = _maps()
    FB = (jload_js(os.path.join(V3A, 'football', 'data', 'football-lite.js')) or {}).get('teams', {})
    try:
        TL = jload_js(os.path.join(V3A, 'assets', 'data', 'teams-lite.js')).get('teams', {})
    except Exception:  # noqa: BLE001
        TL = {}
    os.makedirs(OUT, exist_ok=True)
    idx, want = {}, set()
    for m in today.get('matches', []):
        key = m['key']
        name = safe(key)
        want.update([name + '.webp', name + '-m.webp'])
        c1, c2 = colors_for(m, HM, FB, TL)
        seed = zlib.crc32(key.encode()) % 997
        if only and key not in only:
            idx[key] = {'f': name, 'c': ['#%02x%02x%02x' % c1, '#%02x%02x%02x' % c2]}
            continue
        for suf, (W, H) in SIZES.items():
            render(c1, c2, seed, W, H).save(os.path.join(OUT, name + suf + '.webp'), 'WEBP', quality=QUALITY[suf], method=5)
        idx[key] = {'f': name, 'c': ['#%02x%02x%02x' % c1, '#%02x%02x%02x' % c2]}
    for f in os.listdir(OUT):
        if f.endswith('.webp') and f not in want:
            os.remove(os.path.join(OUT, f))
    json.dump({'built': today.get('built'), 'bg': idx}, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    sz = [os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith('.webp')]
    return 'фонов %d, средний %d КБ, всего %.1f МБ' % (len(sz), sum(sz) / max(1, len(sz)) / 1024, sum(sz) / 1048576)


if __name__ == '__main__':
    print(main(sys.argv[1:] or None))
