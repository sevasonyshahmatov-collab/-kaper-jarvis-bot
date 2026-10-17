# -*- coding: utf-8 -*-
"""Загрузка ролика на YouTube (YouTube Data API v3, videos.insert) — секреты YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.

Пока приложение Google не прошло проверку (YouTube API Services Audit), ролики загружаются закрытыми — владелец открывает
доступ в YouTube Studio; квота — около 6 загрузок в день, кончилась (quotaExceeded) — остальные ролики только в Telegram.
Режим «Testing» в Google Cloud: refresh token живёт 7 дней — потом обновить YT_REFRESH_TOKEN (OAuth Playground)."""
import json
import os

import requests

TOKEN_URL = 'https://oauth2.googleapis.com/token'
UPLOAD_URL = 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status'
SPORTS = '17'
_state = {'token': None, 'stop': None}      # stop — причина, по которой в этом запуске больше не загружаем


def enabled():
    return all(os.environ.get(k) for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN'))


def _token():
    if not _state['token']:
        env = {k: ''.join(os.environ[k].split()) for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN')}   # без пробелов из вставки
        r = requests.post(TOKEN_URL, data=dict(client_id=env['YT_CLIENT_ID'], client_secret=env['YT_CLIENT_SECRET'],
                                               refresh_token=env['YT_REFRESH_TOKEN'], grant_type='refresh_token'), timeout=30)
        if r.status_code != 200:
            err = r.json().get('error', r.status_code)
            fix = {'invalid_client': 'проверьте секреты YT_CLIENT_ID и YT_CLIENT_SECRET (тот ли Client secret и включён ли он)',
                   'unauthorized_client': 'проверьте секреты YT_CLIENT_ID и YT_CLIENT_SECRET',
                   'invalid_grant': 'токен истёк или отозван — получите новый в OAuth Playground и обновите YT_REFRESH_TOKEN'}
            raise RuntimeError('доступ к YouTube не обновился (%s) — %s' % (err, fix.get(err, 'проверьте секреты YT_*')))
        _state['token'] = r.json()['access_token']
    return _state['token']


def upload(path, title, description, tags):
    """→ (ссылка на ролик | None, пояснение для владельца)."""
    if not enabled():
        return None, ''
    if _state['stop']:
        return None, _state['stop']
    try:
        meta = {'snippet': {'title': title[:100], 'description': description[:4900], 'categoryId': SPORTS,
                            'tags': [t.lstrip('#') for t in tags], 'defaultLanguage': 'ru', 'defaultAudioLanguage': 'ru'},
                'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}}
        h = {'Authorization': 'Bearer ' + _token()}
        r = requests.post(UPLOAD_URL, headers=dict(h, **{'Content-Type': 'application/json; charset=UTF-8',
                                                         'X-Upload-Content-Type': 'video/mp4',
                                                         'X-Upload-Content-Length': str(os.path.getsize(path))}),
                          data=json.dumps(meta, ensure_ascii=False).encode('utf-8'), timeout=60)
        if r.status_code == 200:
            with open(path, 'rb') as f:
                r = requests.put(r.headers['Location'], headers=dict(h, **{'Content-Type': 'video/mp4'}), data=f, timeout=600)
        if r.status_code in (200, 201):
            vid = r.json()['id']
            print('YOUTUBE загружен %s: %s' % (vid, title), flush=True)
            return 'https://youtu.be/%s' % vid, 'загружен закрытым — открыть доступ в YouTube Studio'
        reason = ''
        try:
            reason = r.json()['error']['errors'][0].get('reason', '')
        except (ValueError, KeyError, IndexError):
            pass
        if reason in ('quotaExceeded', 'uploadLimitExceeded', 'rateLimitExceeded'):
            _state['stop'] = 'не загружен: дневной лимит YouTube исчерпан — загрузите вручную'
        else:
            _state['stop'] = 'не загружен (YouTube %s %s) — загрузите вручную' % (r.status_code, reason)
        print('YOUTUBEERR %s %s' % (r.status_code, r.text[:500]), flush=True)
        return None, _state['stop']
    except Exception as e:  # noqa: BLE001 — ролик всё равно уходит в Telegram
        _state['stop'] = 'не загружен: %s' % e
        print('YOUTUBEERR %r' % e, flush=True)
        return None, _state['stop']
