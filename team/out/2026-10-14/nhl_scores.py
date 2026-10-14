# -*- coding: utf-8 -*-
"""Итоговые счета НХЛ за игровой день (ET) из официального API — для послематчевых баннеров.
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
            side = 'h' if gl.get('teamAbbrev', {}).get('default', gl.get('teamAbbrev')) == g['homeTeam']['abbrev'] else 'a'
            per.setdefault(str(p), {'h': 0, 'a': 0})[side] += 1
        out = dict(id=g.get('id'), state=g.get('gameState'), home=g['homeTeam']['abbrev'], away=g['awayTeam']['abbrev'],
                   sh=g['homeTeam'].get('score'), sa=g['awayTeam'].get('score'),
                   end=(g.get('gameOutcome') or {}).get('lastPeriodType'), periods=per)
        print('NHLSCORE ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:                          # noqa: BLE001
        print('NHLERR %r' % (e,), flush=True)
