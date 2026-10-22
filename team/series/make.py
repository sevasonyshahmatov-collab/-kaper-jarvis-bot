# -*- coding: utf-8 -*-
"""Серия «Как работает JARVIS» (владелец 22.10): ролики про таблицу на матчах следующего игрового дня →
Instagram Reels (+ YouTube по флагу) и владельцу в Telegram. Эпизоды — episodes.json по кругу от "start"; форматы —
render/reels/explainer.py (текст) и explainer_viz.py (sheet / scale / case); треки — как у конвейера шортсов.
Запускает .github/workflows/series-daily.yml.

    PYTHONPATH=render python team/series/make.py preview [ГГГГ-ММ-ДД] [khl|nhl]   # 3 формата на пробу — только владельцу
    PYTHONPATH=render python team/series/make.py publish [ГГГГ-ММ-ДД] [khl|nhl]   # эпизод дня — в Instagram и владельцу
    ... --frames 1.5,8,15 — проверка кадрами (без сети — пример КХЛ 22.10)

День — матчи этого дня (по умолчанию — завтра по Москве). YouTube: SERIES_YT=1 — загрузить и туда. По умолчанию нет:
квота YouTube ~6 загрузок в сутки уходит на прогнозы; ролик серии владелец выкладывает в Studio вручную.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily'), HERE):
    sys.path.insert(0, p)

MSK = timezone(timedelta(hours=3))
EP = os.path.join(HERE, 'episodes.json')
TAGS = ['#хоккей', '#КХЛ', '#НХЛ', '#прогнозы', '#JARVIS']
PREVIEW = [('sheet', 1), ('scale', 4), ('case', 2)]          # формат на пробу → эпизод
FMT_NAME = {'text': 'Текст', 'sheet': 'Таблица', 'scale': 'Инфографика', 'case': 'Разбор матча'}


def conveyor():
    """team/reels_daily/make.py (тот же файл называется make.py — грузим по пути)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location('reels_make', os.path.join(ROOT, 'team', 'reels_daily', 'make.py'))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def tracks():
    """Треки конвейера с простыми параметрами: (ключ, доля, дроп в треке)."""
    make = conveyor()
    return [(v[2], v[3], v[4]) for v in make.TEMPLATES.values() if len(v) == 5]


def texts(ep, D=None):
    title = 'Как работает JARVIS · %d. %s' % (ep['n'], ep['title'])
    lines = [ep['hook'], '', '— ' + ep['s2'], '— ' + ep['s3'], '— ' + ep['drop'], '']
    if D:
        lines += ['Прогнозы %s на %s:' % (D['lg'], D['day'])] + \
                 ['%s %s — %s: %s · %s' % (r[0], r[1], r[2], r[6], r[7].replace('.', ',')) for r in D['rows']] + ['']
    lines += ['Все прогнозы на КХЛ и НХЛ — в Telegram: https://t.me/jarvibet', 'Прогноз — мнение автора, не совет.', '',
              ' '.join(TAGS + ['#какработаетjarvis'])]
    return title, '\n'.join(lines)


def reel(fmt, ep, u, D):
    if fmt == 'text':
        from reels.explainer import Explainer
        return Explainer(ep, u=u)
    from reels import explainer_viz as V
    return getattr(V, fmt.capitalize())(ep, u=u, D=D)


def main():
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None  # noqa: E731
    mode = a[0] if a and a[0] in ('preview', 'publish') else 'publish'
    day = next((x for x in a if x[:2] == '20'), (datetime.now(MSK).date() + timedelta(days=1)).isoformat())
    league = next((x for x in a if x in ('khl', 'nhl')), 'khl')
    S = json.load(open(EP, encoding='utf-8'))
    eps = {e['n']: e for e in S['episodes']}
    idx = max(0, (date.fromisoformat(day) - date.fromisoformat(S['start'])).days)
    TR = tracks()

    if opt('--frames'):                                          # без сети — пример
        from reels import core as C
        for fmt, n in PREVIEW:
            r = reel(fmt, eps[n], TR[0][1], None)
            print(C.render(r, os.path.join(ROOT, 'out', 'series', fmt + '.mp4'),
                           frames=[int(round(float(x) * C.FPS)) for x in opt('--frames').split(',')]))
        return

    import data
    D = data.build(day, league)
    if not D:
        print('SERIES %s %s: матчей с прогнозом нет' % (league, day), flush=True)
        return
    if mode == 'preview':
        jobs = [(fmt, eps[n], TR[i % len(TR)]) for i, (fmt, n) in enumerate(PREVIEW)]
    else:
        fmt = S.get('fmt')
        if not fmt:
            print('SERIES формат не выбран (episodes.json → "fmt") — ничего не публикуем', flush=True)
            return
        n = sorted(eps)[idx % len(eps)]
        jobs = [(fmt, eps[n], TR[(n - 1 + idx // len(eps)) % len(TR)])]

    import instagram
    import youtube
    make = conveyor()
    from reels import core as C
    from reels import owner_tracks
    for fmt, ep, (key, u, tdrop) in jobs:
        r = reel(fmt, ep, u, D)
        base = os.path.join(ROOT, 'out', 'series', '%s_%s_ep%02d' % (day, fmt, ep['n']))
        title, body = texts(ep, D)
        if mode == 'publish' and instagram.posted(ep['hook']):
            print('SERIESSKIP эпизод %d уже в Instagram' % ep['n'], flush=True)
            continue
        C.render(r, base + '.mp4', track=owner_tracks.wav(key), start=tdrop - r.drop, extra_out=base + '_clean.mp4')
        print('SERIES %s | эп. %d | трек %s | %.1f с' % (fmt, ep['n'], key, r.dur), flush=True)
        cover = base + '_cover.jpg' if os.path.exists(base + '_cover.jpg') else None
        if mode == 'preview':
            head = 'ПРОБА формата «%s» (никуда не выложено). Матчи %s %s.\n\n' % (FMT_NAME[fmt], D['lg'], D['day'])
        else:
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
