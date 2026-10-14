# -*- coding: utf-8 -*-
"""Итоговые счета НХЛ за игровой день (ET) из официального API и табло ESPN (два источника) — для послематчевых баннеров.
Печатает в лог строки «NHLSCORE {json}»: команды, счёт, как закончился (REG / OT / SO), голы по периодам.
Запуск: python team/out/2026-10-14/nhl_scores.py [YYYY-MM-DD по ET, по умолчанию 2026-10-13]"""
import json
import sys

import requests

DAY = sys.argv[1] if len(sys.argv) > 1 else '2026-10-13'
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'


def main():
    for g in S.get('https://api-web.nhle.com/v1/score/' + DAY, timeout=30).json().get('games', []):
        per = {}
        for gl in g.get('goals') or []:
            p = (gl.get('periodDescriptor') or {}).get('number') or gl.get('period')
            ab = gl.get('teamAbbrev')
            ab = ab.get('default') if isinstance(ab, dict) else ab
            side = 'h' if ab == g['homeTeam']['abbrev'] else 'a'
            per.setdefault(str(p), {'h': 0, 'a': 0})[side] += 1
        out = dict(id=g.get('id'), state=g.get('gameState'), home=g['homeTeam']['abbrev'], away=g['awayTeam']['abbrev'],
                   sh=g['homeTeam'].get('score'), sa=g['awayTeam'].get('score'),
                   end=(g.get('gameOutcome') or {}).get('lastPeriodType'), periods=per)
        print('NHLSCORE ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')), flush=True)


def espn():
    """Второй источник — табло ESPN: счёт, статус и голы по периодам."""
    url = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=' + DAY.replace('-', '')
    for ev in S.get(url, timeout=30).json().get('events', []):
        c = ev['competitions'][0]
        side = {t['homeAway']: t for t in c['competitors']}
        out = dict(name=ev.get('shortName'), status=(c.get('status') or ev.get('status', {})).get('type', {}).get('detail'),
                   home=side['home']['team'].get('abbreviation'), away=side['away']['team'].get('abbreviation'),
                   sh=side['home'].get('score'), sa=side['away'].get('score'),
                   lh=[x.get('value') for x in side['home'].get('linescores') or []],
                   la=[x.get('value') for x in side['away'].get('linescores') or []])
        print('ESPNSCORE ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    for f in (main, espn):
        try:
            f()
        except Exception as e:                      # noqa: BLE001
            print('NHLERR %s %r' % (f.__name__, e), flush=True)
