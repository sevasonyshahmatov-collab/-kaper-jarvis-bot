# -*- coding: utf-8 -*-
"""Снимок Instagram для скиллов /ig-profile и /ig-audit (владелец 26.10: «начинаем пользоваться скиллами»).

Только чтение, ничего не публикует. Graph API (IG_TOKEN, IG_USER_ID — секреты itogi.yml): профиль и последние посты
со статистикой. Печатает строки IGSNAP_PROFILE {...} и IGSNAP_MEDIA {...} в лог и те же данные пометками запуска
(::notice:: — облачная сессия читает их через api.github.com check-runs annotations: хранилище логов из облака закрыто).

    python team/social/ig_snapshot.py [постов=40]
"""
import json
import os
import sys

import requests

API = 'https://graph.facebook.com/v21.0/'
SAID = []
METRICS = ('views', 'reach', 'saved', 'shares', 'total_interactions')


def get(path, **params):
    params['access_token'] = os.environ['IG_TOKEN'].strip()
    r = requests.get(API + path, params=params, timeout=30).json()
    if 'error' in r:
        # текст ошибки без токена: в ответе Graph API его нет
        err = '%s: %s' % (path.split('/')[-1] or path, str(r['error'].get('message', r['error']))[:200])
        print('IGSNAP_ERR ' + err)
        if '/insights' not in path or not SAID:  # ошибку статистики — один раз, а не на каждый пост
            SAID.append(1)
            print('::notice title=IGSNAP_ERR::' + err.replace('\n', ' '), flush=True)
    return r


def insights(mid):
    r = get('%s/insights' % mid, metric=','.join(METRICS))
    if 'data' not in r:  # одна недоступная метрика роняет весь запрос — тогда по одной
        r = {'data': sum((get('%s/insights' % mid, metric=m).get('data', []) for m in METRICS), [])}
    out = {}
    for d in r['data']:
        v = d['values'][0]['value'] if d.get('values') else d.get('total_value', {}).get('value')
        out[d['name']] = v
    return out


def notice(title, obj):
    msg = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    msg = msg.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=%s::%s' % (title, msg), flush=True)


def mark(m):
    """Метки роликов конвейера для сравнения (по подписи, team/reels_daily/instagram.caption): ab — заставка А/Б (27.10),
    fmt — short (10–15 с, владелец 30.10) | long, card — карточка-призыв короткого ролика: protocol | share."""
    c = m.get('caption') or ''
    if 'в Telegram @jarvibet' not in c:
        return
    m['ab'] = 'B' if c.startswith('Разбор и итог матча') or '\nРазбор и итог матча' in c else 'A'
    first = c.split('\n')[0]
    m['fmt'] = 'short' if first.startswith(('Сохрани.', 'Отправь тому')) else 'long'
    if m['fmt'] == 'short':
        m['card'] = 'protocol' if first.startswith('Сохрани.') else 'share'


def main(n=40):
    if not os.environ.get('IG_TOKEN') or not os.environ.get('IG_USER_ID'):
        print('IGSNAP_ERR нет IG_TOKEN / IG_USER_ID')
        return
    uid = os.environ['IG_USER_ID'].strip()
    prof = get(uid, fields='username,name,biography,website,followers_count,follows_count,media_count')
    print('IGSNAP_PROFILE ' + json.dumps(prof, ensure_ascii=False))
    media = get('%s/media' % uid, limit=n, fields='id,caption,media_type,media_product_type,timestamp,permalink,'
                                                 'like_count,comments_count').get('data', [])
    for m in media:
        m.update(insights(m['id']))
        m['caption'] = (m.get('caption') or '')[:300]
        mark(m)
        print('IGSNAP_MEDIA ' + json.dumps(m, ensure_ascii=False))
    print('IGSNAP_DONE %d' % len(media))
    # пометок не больше 10 на шаг — профиль и посты пачками по 8
    notice('IGSNAP_PROFILE', prof)
    short = [{k: (v[:150] if k == 'caption' else v) for k, v in m.items() if k not in ('id', 'media_type')} for m in media]
    for i in range(0, len(short), 8):
        notice('IGSNAP_MEDIA_%d' % (i // 8), short[i:i + 8])


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
