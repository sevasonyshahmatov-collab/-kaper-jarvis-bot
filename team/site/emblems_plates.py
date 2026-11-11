"""Подложка под эмблему клуба (владелец 11.11: «плохо видно логотип» — тёмная эмблема на тёмной плашке цвета клуба).

Для каждой эмблемы team/site/v3a/assets/em/<клуб>.webp считаем, какая доля её точек сливается с плашкой, и выбираем первую
подложку: тёмную первого цвета клуба, если на ней теряется меньше LIMIT точек; иначе ту, где теряется меньше всего
(тёмная другого цвета клуба или светлая с ободком цвета клуба).
Результат — assets/em/plates.js: window.JV_EMPL = {клуб: ['d'|'l', '#цвет']}. Запуск: python3 team/site/emblems_plates.py
"""
import glob
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V3A = os.path.join(ROOT, 'team', 'site', 'v3a')
EM = os.path.join(V3A, 'assets', 'em')
NAVY, LIGHT, NEAR, LIMIT = (9, 21, 43), (238, 242, 249), 100, 0.30


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dark(c):   # середина градиента плашки: около трети цвета клуба на тёмно-синем
    return tuple(round(c[i] * .33 + NAVY[i] * .67) for i in range(3))


def lost(px, plate):
    n = sum(1 for p in px if sum((p[i] - plate[i]) ** 2 for i in range(3)) ** .5 < NEAR)
    return n / max(1, len(px))


def main():
    s = open(os.path.join(V3A, 'assets', 'data', 'teams-lite.js'), encoding='utf-8').read()
    teams = json.loads(s[s.index('{'):s.rindex('}') + 1])['teams']
    out, rep = {}, []
    for p in sorted(glob.glob(os.path.join(EM, '*.webp'))):
        slug = os.path.splitext(os.path.basename(p))[0]
        im = Image.open(p).convert('RGBA').resize((72, 72), Image.LANCZOS)
        px = [q[:3] for q in im.get_flattened_data() if q[3] > 140]
        cols = [c for c in (teams.get(slug, {}).get('colors') or []) if isinstance(c, str) and len(c.lstrip('#')) == 6] or ['#2a3f6b']
        cand = []
        for c in dict.fromkeys(cols):
            cand.append(('d', c, lost(px, dark(rgb(c)))))
        cand.append(('l', cols[0], lost(px, LIGHT)))
        pick = cand[0] if cand[0][2] < LIMIT else min(cand, key=lambda c: (round(c[2], 2), c[0] != 'l'))   # первый цвет клуба, иначе где теряется меньше всего
        out[slug] = [pick[0], pick[1]]
        if pick is not cand[0]:
            rep.append('%s: %s %s (на первом цвете терялось %d %%)' % (slug, 'светлая' if pick[0] == 'l' else 'тёмная', pick[1], round(cand[0][2] * 100)))
    open(os.path.join(EM, 'plates.js'), 'w', encoding='utf-8').write(
        '/* подложки под эмблемы; генерирует team/site/emblems_plates.py */\nwindow.JV_EMPL=%s;\n' % json.dumps(out, separators=(',', ':'), sort_keys=True))
    print('эмблем: %d; не первый цвет клуба — %d:' % (len(out), len(rep)))
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
