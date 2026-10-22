# -*- coding: utf-8 -*-
"""Серия «Как работает JARVIS» (владелец 22.10): один эпизод в день → Instagram Reels (+ YouTube по флагу) и владельцу
в Telegram. Эпизоды — episodes.json по кругу от "start"; ролик — render/reels/explainer.py; треки — те же, что у
конвейера шортсов (по очереди). Запускает .github/workflows/series-daily.yml.

    PYTHONPATH=render python team/series/make.py [ГГГГ-ММ-ДД] [--ep N] [--frames 1.5,8,15]

YouTube: SERIES_YT=1 — загрузить и туда. По умолчанию нет: квота YouTube ~6 загрузок в сутки уходит на прогнозы,
ролик серии владелец получает в Telegram и выкладывает в Studio вручную (квоту не тратит).
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily')):
    sys.path.insert(0, p)

MSK = timezone(timedelta(hours=3))
EP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'episodes.json')
TAGS = ['#хоккей', '#КХЛ', '#НХЛ', '#прогнозы', '#JARVIS']


def tracks():
    """Треки конвейера с простыми параметрами: (ключ, доля, дроп в треке)."""
    import make
    return [(v[2], v[3], v[4]) for v in make.TEMPLATES.values() if len(v) == 5]


def texts(ep):
    title = 'Как работает JARVIS · %d. %s' % (ep['n'], ep['title'])
    body = '\n'.join([
        ep['hook'], '',
        '— ' + ep['s2'],
        '— ' + ep['s3'],
        '— ' + ep['drop'], '',
        'Прогнозы на КХЛ и НХЛ каждый день — в Telegram: https://t.me/jarvibet',
        'Прогноз — мнение автора, не совет.', '',
        ' '.join(TAGS + ['#какработаетjarvis'])])
    return title, body


def main():
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None  # noqa: E731
    day = date.fromisoformat(next((x for x in a if x[:2] == '20'), datetime.now(MSK).date().isoformat()))
    S = json.load(open(EP, encoding='utf-8'))
    eps = S['episodes']
    idx = (day - date.fromisoformat(S['start'])).days
    if opt('--ep'):
        ep = next(e for e in eps if e['n'] == int(opt('--ep')))
    elif idx < 0:
        raise SystemExit('серия начинается %s' % S['start'])
    else:
        ep = eps[idx % len(eps)]
    TR = tracks()
    key, u, tdrop = TR[(ep['n'] - 1 + idx // len(eps)) % len(TR)]

    from reels import core as C
    from reels.explainer import Explainer
    r = Explainer(ep, u=u)
    base = os.path.join(ROOT, 'out', 'series', '%s_ep%02d' % (day.isoformat(), ep['n']))
    if opt('--frames'):
        print(C.render(r, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in opt('--frames').split(',')]))
        return

    import instagram
    import youtube
    import make
    from reels import owner_tracks
    title, body = texts(ep)
    if instagram.posted(ep['hook']):
        print('SERIESSKIP эпизод %d уже в Instagram' % ep['n'], flush=True)
        return
    C.render(r, base + '.mp4', track=owner_tracks.wav(key), start=tdrop - r.drop, extra_out=base + '_clean.mp4')
    print('SERIES эп. %d | трек %s | %.1f с' % (ep['n'], key, r.dur), flush=True)
    cover = base + '_cover.jpg' if os.path.exists(base + '_cover.jpg') else None
    head = ''
    if os.environ.get('SERIES_YT') == '1':
        url, note = youtube.upload(base + '.mp4', title, body, [t.lstrip('#') for t in TAGS])
        head += 'YouTube: %s\n\n' % (url or note)
    else:
        head += 'YouTube: загрузите вручную (название и описание ниже)\n\n'
    ig, ignote = instagram.upload(base + '.mp4', body, cover)
    head += 'Instagram: %s\n\n' % (ig or ignote or 'не выложен (нет IG_TOKEN)')
    make.tg_reel(base + '.mp4', base + '_clean.mp4', head + title + '\n\n' + body, title, cover)


if __name__ == '__main__':
    main()
