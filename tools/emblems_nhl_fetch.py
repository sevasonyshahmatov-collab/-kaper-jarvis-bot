"""Эмблемы НХЛ в 4К: официальные SVG лиги (assets.nhle.com) → PNG 2048 px, обрезка по прозрачности.

Запускает .github/workflows/team-emblems.yml (из облачной сессии сайт лиги закрыт). Список клубов —
render/emblems/nhl_fetch.txt (имя файла и код лиги через пробел). Меняет только файлы, где новый больше старого.
"""
import io
import os
import subprocess
import sys
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMB = os.path.join(ROOT, 'render', 'emblems')
URL = 'https://assets.nhle.com/logos/nhl/svg/%s_light.svg'
SIDE = 2048


def fetch(code):
    req = urllib.request.Request(URL % code, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def to_png(svg):
    png = subprocess.run(['rsvg-convert', '-w', str(SIDE), '-h', str(SIDE), '--keep-aspect-ratio'],
                         input=svg, capture_output=True, check=True).stdout
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    box = im.getchannel('A').getbbox()
    return im.crop(box) if box else im


def main():
    report, bad = [], 0
    for line in open(os.path.join(EMB, 'nhl_fetch.txt'), encoding='utf-8'):
        line = line.split('#')[0].strip()
        if not line:
            continue
        name, code = line.split()
        path = os.path.join(EMB, name + '.png')
        old = Image.open(path).size if os.path.exists(path) else (0, 0)
        try:
            im = to_png(fetch(code))
        except Exception as e:                      # нет файла у лиги — оставляем старый
            report.append('%s %s: ошибка %s' % (name, code, e)); bad += 1
            continue
        if max(im.size) <= max(old):
            report.append('%s: новый %dx%d не больше старого %dx%d — оставлен старый' % ((name,) + im.size + old))
            continue
        im.save(path, optimize=True)
        report.append('%s: %dx%d → %dx%d' % ((name,) + old + im.size))
    print('\n'.join(report))
    with open(os.path.join(EMB, 'nhl_fetch_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    return 1 if bad == len(report) else 0


if __name__ == '__main__':
    sys.exit(main())
