# -*- coding: utf-8 -*-
"""Загрузка ролика в Instagram Reels (владелец 19.10): Instagram Graph API через вход Facebook — аккаунт jarvisbet_
привязан к странице «Jarvis Прогнозы на хоккей», маркер страницы бессрочный (docs/channel/instagram/ПОДКЛЮЧЕНИЕ.md).
Секреты: IG_TOKEN (маркер страницы), IG_USER_ID (ID аккаунта Instagram). Нет секретов — ничего не делаем.
Загрузка: контейнер REELS (resumable) → файл на rupload.facebook.com → ждём FINISHED → media_publish.
Лимит Instagram — 50 публикаций через API за сутки."""
import os
import time

import requests

API = 'https://graph.facebook.com/v21.0/'
_state = {'stop': None}


def enabled():
    return all(os.environ.get(k) for k in ('IG_TOKEN', 'IG_USER_ID'))


def _env():
    return ''.join(os.environ['IG_TOKEN'].split()), os.environ['IG_USER_ID'].strip()


def caption(m, y):
    """Подпись: описание для YouTube (матч, прогноз, Telegram) + хэштеги; ≤ 2200 знаков, хэштегов ≤ 30."""
    return y['description'][:2100]


def zoomed(path):
    """Копия для Instagram (владелец 19.10): ×1,12 и обрезка — Instagram закрывает низ меньше, чем Shorts, и под бегущей
    строкой оставалась пустая полоса. Картинка крупнее, строка ниже, к подписи Instagram. Не вышло — исходный ролик."""
    import subprocess
    out = path[:-4] + '_ig.mp4'
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', path, '-vf', 'scale=1210:2150,crop=1080:1920:65:70',
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy', out])
    return out if r.returncode == 0 and os.path.exists(out) else path


def upload(path, text):
    """→ (ссылка на ролик | None, пояснение для владельца)."""
    if not enabled():
        return None, ''
    if _state['stop']:
        return None, _state['stop']
    tok, uid = _env()
    try:
        r = requests.post(API + uid + '/media', timeout=60, data=dict(
            media_type='REELS', upload_type='resumable', caption=text, share_to_feed='true', access_token=tok)).json()
        if 'id' not in r:
            raise RuntimeError('контейнер: %s' % (r.get('error') or r))
        cid, uri = r['id'], r['uri']
        with open(zoomed(path), 'rb') as f:
            data = f.read()
        u = requests.post(uri, data=data, timeout=600, headers={
            'Authorization': 'OAuth ' + tok, 'offset': '0', 'file_size': str(len(data))}).json()
        if not u.get('success'):
            raise RuntimeError('файл: %s' % u)
        for _ in range(60):                                              # обработка видео — обычно 20–60 с
            st = requests.get(API + cid, params=dict(fields='status_code,status', access_token=tok), timeout=30).json()
            if st.get('status_code') == 'FINISHED':
                break
            if st.get('status_code') in ('ERROR', 'EXPIRED'):
                raise RuntimeError('обработка: %s' % st.get('status'))
            time.sleep(5)
        else:
            raise RuntimeError('Instagram не обработал видео за 5 минут')
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
        if 'id' not in p:
            raise RuntimeError('публикация: %s' % (p.get('error') or p))
        link = requests.get(API + p['id'], params=dict(fields='permalink', access_token=tok), timeout=30).json()
        url = link.get('permalink') or 'https://www.instagram.com/'
        print('INSTAGRAM опубликован %s %s' % (p['id'], url), flush=True)
        return url, 'опубликован'
    except Exception as e:  # noqa: BLE001 — ролик всё равно уходит в Telegram и на YouTube
        msg = str(e)[:300]
        if 'limit' in msg.lower():
            _state['stop'] = 'не загружен: дневной лимит Instagram — загрузите вручную'
        print('INSTAGRAMERR %s' % msg, flush=True)
        return None, _state['stop'] or 'не загружен (%s) — загрузите вручную' % msg[:150]
