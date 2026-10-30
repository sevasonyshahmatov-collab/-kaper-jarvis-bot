"""Эмблемы и цвета футбольных клубов: ESPN teams API → render/emblems/football/<id>.png (500 px) + teams.json.

Запускает .github/workflows/team-emblems-football.yml (из облачной сессии сайты закрыты). Турниры — как в
docs/handoff/FOOTBALL_SOURCES.md; id клуба — id ESPN (один и тот же во всех турнирах).
"""
import io
import json
import os
import sys
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'render', 'emblems', 'football')
LEAGUES = ['eng.1', 'esp.1', 'ita.1', 'ger.1', 'fra.1', 'por.1', 'uefa.champions', 'uefa.europa', 'uefa.europa.conf']
API = 'https://site.api.espn.com/apis/site/v2/sports/soccer/%s/teams?limit=200'
LOGO = 'https://a.espncdn.com/i/teamlogos/soccer/500/%s.png'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'teams.json')
    table = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    log = []
    for lg in LEAGUES:
        try:
            data = json.loads(get(API % lg))
            teams = [t['team'] for t in data['sports'][0]['leagues'][0]['teams']]
        except Exception as e:
            log.append('%s: ошибка %r' % (lg, e)); continue
        log.append('%s: клубов %d' % (lg, len(teams)))
        for t in teams:
            tid = str(t['id'])
            row = table.setdefault(tid, {'leagues': []})
            row.update({'name': t.get('displayName'), 'short': t.get('shortDisplayName'), 'abbr': t.get('abbreviation'),
                        'location': t.get('location'), 'color': t.get('color'), 'alt': t.get('alternateColor')})
            if lg not in row['leagues']:
                row['leagues'].append(lg)
            png = os.path.join(OUT, tid + '.png')
            if os.path.exists(png):
                continue
            try:
                im = Image.open(io.BytesIO(get(LOGO % tid))).convert('RGBA')
                box = im.getchannel('A').getbbox()
                (im.crop(box) if box else im).save(png, optimize=True)
            except Exception as e:
                log.append('  нет логотипа %s %s: %r' % (tid, t.get('displayName'), e))
    json.dump(table, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    log.append('всего клубов: %d' % len(table))
    print('\n'.join(log))
    open(os.path.join(OUT, 'fetch_report.txt'), 'w', encoding='utf-8').write('\n'.join(log) + '\n')
    return 0 if table else 1


if __name__ == '__main__':
    sys.exit(main())
