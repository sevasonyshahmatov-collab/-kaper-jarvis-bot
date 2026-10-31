# -*- coding: utf-8 -*-
"""Посты купонов «Экспресс» для владельца (формат владельца 31.10: «просто сам экспресс и снизу общий кэф»):
шапка «НХЛ · 31 октября · экспресс», события (матч, время МСК, ставка, кэф), «Общий кэф: X», хэштеги. Без процентов
модели и пояснений — расчёт только в служебной записи (team/picks/EXPRESS_LOG.md) и руководителю.

    python3 team/picks/express_post.py 2026-10-31 [--static 2] [--no-stories]
Из team/out/D/express_coupons.json (team/picks/express.py) пишет:
  team/out/D/express_posts.json — подписи купонов {k: {pid, html}} (их же берёт team/picks/express_ig.py для Instagram);
  team/out/D/express_msgs.json  — сообщения владельцу: на купон — гифка (animation e<k>_anim.mp4; --static k — картинкой
                                  e<k>_feed.jpg) + подпись + кнопки «Опубликовать / Редактировать / Не надо» (pid ДДММ-e<k>),
                                  затем альбом сторис (картинки; в Instagram сторис уходит видео);
  team/out/D/express.json       — задание itogi.yml: make — картинки (express_render.py), отправка (express_send.py).
Шапка без времени: бот публикует купон сразу по кнопке (не за 1,5 / 4 ч до матча, как одиночные прогнозы)."""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import express_render as er  # noqa: E402

TAG = {'НХЛ': '#нхл', 'КХЛ': '#кхл', 'Футбол': '#футбол'}
ORDER = ['КХЛ', 'НХЛ', 'Футбол']


def _k(v):
    return ('%.2f' % v).replace('.', ',')


def caption(c):
    legs = c['legs']
    lgs = [x for x in ORDER if any(l['league'] == x for l in legs)]
    first = min(l['date'] for l in legs if l.get('date')) if any(l.get('date') for l in legs) else ''
    lines = ['%s · %s · экспресс' % (' · '.join(lgs), er.date_title(legs)), '']
    for i, x in enumerate(legs, 1):
        when = ('%s, ' % er.ru_date(x['date']) if x.get('date') and x['date'] != first else '') + '%s МСК' % x['time']
        lines.append('%d. <b>%s — %s</b>, %s' % (i, x['home'], x['away'], when))
        lines.append('%s · %s' % (x['bet_full'], _k(x['kef'])))
    lines += ['', 'Общий кэф: <b>%s</b>' % _k(c['kef']), '', ' '.join([TAG[x] for x in lgs] + ['#экспресс', '#jarvibet'])]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('day')
    ap.add_argument('--static', default='', help='номера купонов картинкой вместо гифки, через запятую')
    ap.add_argument('--no-stories', action='store_true')
    a = ap.parse_args()
    D = a.day
    dd = D[8:10] + D[5:7]                                   # ДДММ — как у номеров прогнозов (3110-1)
    base = 'team/out/%s/' % D
    X = 'out/express/%s/' % D
    cs = json.load(open(os.path.join(ROOT, base + 'express_coupons.json'), encoding='utf-8'))['coupons']
    static = {int(s) for s in a.static.split(',') if s.strip()}
    posts, msgs, stories = {}, [], []
    for k, c in enumerate(cs, 1):
        if not c.get('legs'):
            continue
        pid = '%s-e%d' % (dd, k)
        html = caption(c)
        if len(html) > 1024:
            sys.exit('купон %d: подпись %d знаков > 1024' % (k, len(html)))
        posts[str(k)] = dict(pid=pid, html=html)
        if k in static:
            msgs.append(dict(to='owner', type='photo', html=True, files=[X + 'e%d_feed.jpg' % k], text=html, buttons='post', pid=pid))
        else:
            msgs.append(dict(to='owner', type='animation', html=True, files=[X + 'e%d_anim.mp4' % k], text=html,
                             buttons='post', pid=pid))
        stories.append(X + 'e%d_story.jpg' % k)
    if stories and not a.no_stories:
        msgs.append(dict(to='owner', type='album', files=stories[:10], text='Сторис для Instagram (там уйдут видео)'))
    json.dump(posts, open(os.path.join(ROOT, base + 'express_posts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(day=D, messages=msgs), open(os.path.join(ROOT, base + 'express_msgs.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    job = dict(day=D, make=['team/picks/express_render.py %sexpress_coupons.json %s' % (base, X.rstrip('/')),
                            'team/picks/express_send.py %sexpress_msgs.json' % base], messages=[])
    json.dump(job, open(os.path.join(ROOT, base + 'express.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, p in posts.items():
        print('--- купон %s (%s), %d знаков\n%s' % (k, p['pid'], len(p['html']), p['html']))


if __name__ == '__main__':
    main()
