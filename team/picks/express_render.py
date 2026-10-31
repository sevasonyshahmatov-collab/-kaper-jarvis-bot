# -*- coding: utf-8 -*-
"""Картинки купонов «Экспресс» из JSON team/picks/express.py: для купона k — e<k>_feed.jpg (1080×1350),
e<k>_story.jpg (1080×1920), e<k>_anim.mp4 (лента, ≤ 5 с, ноги выезжают по очереди, затем общий кэф) и
e<k>_story.mp4 (сторис-видео). Без шанса модели и пояснений (владелец 31.10: «просто сам экспресс и снизу общий кэф»). Рисовать в Actions (jpg/mp4 в team/out
не коммитятся): в задании "make": ["team/picks/express_render.py <coupons.json> <папка>"].
    PYTHONPATH=render python3 team/picks/express_render.py team/out/2026-10-31/express_coupons.json out/express/2026-10-31"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'render'))
import express_card as ec  # noqa: E402

MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
WORD = {2: 'на два матча', 3: 'на три матча'}


def ru_date(d):
    y, m, dd = d.split('-')
    return '%d %s' % (int(dd), MON[int(m) - 1])


def date_title(legs):
    ds = sorted({x['date'] for x in legs if x.get('date')})
    if not ds:
        return ''
    return ru_date(ds[0]) if len(ds) == 1 else '%s – %s' % (ru_date(ds[0]), ru_date(ds[-1]))


def main(src, out):
    sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
    import banners
    banners.ensure_ffmpeg()                           # на раннере ffmpeg может не быть (как у баннеров прогнозов)
    cs = json.load(open(os.path.join(ROOT, src), encoding='utf-8'))['coupons']
    out = os.path.join(ROOT, out)
    os.makedirs(out, exist_ok=True)
    done = []
    for k, c in enumerate(cs, 1):
        if not c.get('legs'):
            continue
        legs = [dict(home=x['home'], away=x['away'], time=x['time'], bet=x['bet_short'], kef=x['kef'], league=x['league'])
                for x in c['legs']]
        kw = dict(date_title=date_title(c['legs']), total=c['kef'])     # владелец 31.10: только события и общий кэф
        for fmt in ('feed', 'story'):
            p = ec.render(legs, os.path.join(out, 'e%d_%s.jpg' % (k, fmt)), fmt=fmt,
                          cta='Все прогнозы — в Telegram @jarvibet' if fmt == 'story' else None, **kw)
            done.append('%s %d КБ' % (os.path.basename(p), os.path.getsize(p) // 1024))
        p = ec.animate(legs, os.path.join(out, 'e%d_anim.mp4' % k), **kw)
        done.append('%s %d КБ' % (os.path.basename(p), os.path.getsize(p) // 1024))
        p = ec.animate(legs, os.path.join(out, 'e%d_story.mp4' % k), fmt='story', cta='Все прогнозы — в Telegram @jarvibet', **kw)
        done.append('%s %d КБ' % (os.path.basename(p), os.path.getsize(p) // 1024))


    # одна пометка на все файлы: в шаге Actions — не больше 10 пометок, остальные нужны отправке (EXSEND_<i>)
    print('::notice title=EXRENDER::%s' % ' · '.join(done), flush=True)


if __name__ == '__main__':
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:  # noqa: BLE001 — логи из облака закрыты: причина — пометкой
        import traceback
        print('::notice title=EXRENDER::%s' % traceback.format_exc()[-900:].replace('\n', ' | '), flush=True)
        raise
