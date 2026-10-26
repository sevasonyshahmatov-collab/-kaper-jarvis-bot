# -*- coding: utf-8 -*-
"""Снимок Instagram для скиллов /ig-profile и /ig-audit (владелец 26.10: «начинаем пользоваться скиллами»).

Только чтение, ничего не публикует. Graph API (IG_TOKEN, IG_USER_ID — секреты itogi.yml): профиль и последние посты
со статистикой. Печатает строки IGSNAP_PROFILE {...} и IGSNAP_MEDIA {...} в лог — сессия читает их по метке.

    python team/social/ig_snapshot.py [постов=40]
"""
import json
import os
import sys

import requests

API = 'https://graph.facebook.com/v21.0/'
METRICS = ('views', 'reach', 'saved', 'shares', 'total_interactions')


def get(path, **params):
    params['access_token'] = os.environ['IG_TOKEN'].strip()
    r = requests.get(API + path, params=params, timeout=30).json()
    if 'error' in r:
        # текст ошибки без токена: в ответе Graph API его нет
        print('IGSNAP_ERR %s: %s' % (path.split('/')[-1] or path, str(r['error'].get('message', r['error']))[:200]))
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
        print('IGSNAP_MEDIA ' + json.dumps(m, ensure_ascii=False))
    print('IGSNAP_DONE %d' % len(media))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
