# -*- coding: utf-8 -*-
"""Баннеры «Versus» для постов-прогнозов прямо из задания: у сообщения поле "vs" — баннер рисуется в его files[0].
  "vs": {"league": "KHL" | "NHL", "home": "Торпедо", "away": "Динамо Москва", "date": "16 октября", "time": "19:00",
         "odds": [2.12, 3.76, 3.00]}       # П1/Х/П2 основного времени (Pinnacle; КХЛ без линии — Фонбет); null — без плашек
У сообщения "type": "animation" баннер анимированный («гифка», files[0] — .mp4): собирается из плашек клубов
(render/versus_anim.py, compose; плашки — в out/anim/plates, нет — рисуются, ~1 мин на клуб).
Задание: "make": ["team/picks/banners.py team/out/<день>/picks_khl.json"] (из корня, PYTHONPATH=render — так запускает team_job.py).
В сессии для проверки: PYTHONPATH=render python team/picks/banners.py <задание> → картинки в out/picks/… (в git не класть)."""
import json
import os
import sys

import versus


def main(job_path):
    job = json.load(open(job_path, encoding='utf-8'))
    n = 0
    for m in job.get('messages') or []:
        vs = m.get('vs')
        if not vs or not m.get('files'):
            continue
        path = m['files'][0]
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        odds = vs.get('odds')
        odds = tuple(odds) if odds and all(odds) else None
        if m.get('type') == 'animation':
            import versus_anim
            versus_anim.compose(vs['home'], vs['away'], path, date=vs.get('date', ''), time=vs.get('time', ''), odds=odds,
                                league=vs.get('league', 'KHL'), plates_dir='out/anim/plates')
        else:
            versus.render(vs['home'], vs['away'], path, date=vs.get('date', ''), time=vs.get('time', ''), odds=odds,
                          league=vs.get('league', 'KHL'))
        n += 1
        print('баннер:', path, flush=True)
    print('баннеров: %d' % n, flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
