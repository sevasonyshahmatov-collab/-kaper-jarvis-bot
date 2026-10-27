# -*- coding: utf-8 -*-
"""Загрузка ролика в Instagram Reels (владелец 19.10): Instagram Graph API через вход Facebook — аккаунт jarvisbet_
привязан к странице «Jarvis Прогнозы на хоккей», маркер страницы бессрочный (docs/channel/instagram/ПОДКЛЮЧЕНИЕ.md).
Секреты: IG_TOKEN (маркер страницы), IG_USER_ID (ID аккаунта Instagram). Нет секретов — ничего не делаем.
Загрузка: контейнер REELS (resumable) → файл на rupload.facebook.com → ждём FINISHED → media_publish.
Лимит Instagram — 50 публикаций через API за сутки."""
import os
import time
from datetime import timedelta, timezone

import requests

API = 'https://graph.facebook.com/v21.0/'
_state = {'stop': None}


def enabled():
    return all(os.environ.get(k) for k in ('IG_TOKEN', 'IG_USER_ID'))


def _env():
    return ''.join(os.environ['IG_TOKEN'].split()), os.environ['IG_USER_ID'].strip()


def posted(first_line):
    """Ролик на этот матч уже есть в Instagram — подпись начинается с той же первой строки (владелец 20.10: ролики выкладываем
    вечером накануне, ночной запуск того же дня не должен их дублировать). Последние 50 публикаций, один запрос за запуск."""
    if not enabled() or not first_line:
        return False
    if _state.get('captions') is None:
        tok, uid = _env()
        try:
            j = requests.get(API + uid + '/media', params=dict(fields='caption', limit=50, access_token=tok), timeout=30).json()
            _state['captions'] = [str(x.get('caption') or '') for x in j.get('data') or []]
        except Exception as e:  # noqa: BLE001 — не удалось проверить — собираем как обычно
            print('INSTAGRAMERR список публикаций: %r' % e, flush=True)
            _state['captions'] = []
    import yt_texts                                   # до 24.10 подпись начиналась сразу с матча, без «Прогноз на матч»
    lines = {first_line, first_line[len(yt_texts.HEAD):] if first_line.startswith(yt_texts.HEAD) else first_line}
    return any(c.startswith(x) for c in _state['captions'] for x in lines)


CTA = 'Полный разбор и итоги — в Telegram @jarvibet (ссылка в шапке профиля)'   # владелец 22.10: цель — переход в канал
CTA_B = 'Разбор и итог матча — в Telegram @jarvibet (ссылка в шапке профиля)'      # вариант Б сравнения заставок (27.10)


def caption(m, y, ab=None):
    """Подпись: описание для YouTube (матч, прогноз, Telegram) + хэштеги; ≤ 2200 знаков, хэштегов ≤ 30.
    Сразу после первой строки — призыв в Telegram (первая строка не меняется: по ней posted() ищет повторы).
    ab='B' — другой призыв: по нему снимок Instagram (team/social/ig_snapshot.py) отличает вариант заставки."""
    first, _, rest = y['description'].partition('\n')
    return (first + '\n' + (CTA_B if ab == 'B' else CTA) + '\n' + rest)[:2100]


def zoomed(path, cover=None):
    """Копия для Instagram (владелец 19.10): Instagram закрывает низ меньше, чем Shorts, и под бегущей строкой оставалась
    пустая полоса. Кадр сдвигается вниз на 110 px без увеличения (сверху — тёмная полоса под значками Instagram, снизу
    уходит пустое место). Не увеличиваем: на длинных экранах Instagram сам срезает края ролика, и поля 3 % по бокам
    (core.INSET) нужны как запас — ×1,12 и ×1,06 резали края у шаблонов во всю ширину («Северсталь», 19.10).
    Обложка (render/vk_covers.py): Instagram берёт обложку только по общедоступной ссылке или кадром ролика, поэтому
    последние 0,3 с копии — кадр обложки, а thumb_offset указывает на него (в ленте — обложка, а не чёрный первый кадр).
    → (файл, thumb_offset в мс | None). Не вышло — исходный ролик."""
    import subprocess
    out = path[:-4] + '_ig.mp4'
    vf, inputs, thumb = '[0:v]pad=1080:2030:0:110:color=0x08080a,crop=1080:1920:0:0[v]', ['-i', path], None
    if cover and os.path.exists(cover):
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                   capture_output=True, text=True).stdout.strip() or 0)
        if dur > 1:
            t0 = dur - 0.3
            inputs += ['-loop', '1', '-t', '%.2f' % dur, '-i', cover]
            vf += ';[1:v]scale=1080:1920,setsar=1[c];[v][c]overlay=0:0:enable=\'gte(t,%.3f)\'[v]' % t0
            vf = vf.replace('[v];[1:v]', '[z];[1:v]').replace('[v][c]', '[z][c]')
            thumb = int((t0 + 0.1) * 1000)
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + inputs + [
        '-filter_complex', vf, '-map', '[v]', '-map', '0:a?', '-shortest',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy', out])
    if r.returncode == 0 and os.path.exists(out):
        return out, thumb
    return path, None


def upload(path, text, cover=None, tries=3):
    """→ (ссылка на ролик | None, пояснение для владельца). Instagram иногда отвечает ProcessingFailedError на загрузку
    файла (19–20.10: со второй попытки проходило) — повторяем загрузку с новым контейнером до tries раз."""
    for k in range(tries):
        url, note = _upload(path, text, cover)
        if url or 'ProcessingFailedError' not in note or k == tries - 1:
            return url, note
        print('INSTAGRAM повтор %d: %s' % (k + 2, note[:120]), flush=True)
        time.sleep(20)
    return url, note


def _upload(path, text, cover=None):
    if not enabled():
        return None, ''
    if _state['stop']:
        return None, _state['stop']
    try:
        return publish(prepare(path, text, cover))
    except Exception as e:  # noqa: BLE001 — ролик всё равно уходит в Telegram и на YouTube
        return _fail(e)


def _fail(e):
    msg = str(e)[:300]
    if 'limit' in msg.lower():
        _state['stop'] = 'не загружен: дневной лимит Instagram — загрузите вручную'
    print('INSTAGRAMERR %s' % msg, flush=True)
    return None, _state['stop'] or 'не загружен (%s) — загрузите вручную' % msg[:150]


def prepare(path, text, cover=None):
    """Контейнер REELS с загруженным и обработанным видео, без публикации → id контейнера (живёт 24 ч)."""
    tok, uid = _env()
    video, thumb = zoomed(path, cover)
    meta = dict(media_type='REELS', upload_type='resumable', caption=text, share_to_feed='true', access_token=tok)
    if thumb is not None:
        meta['thumb_offset'] = str(thumb)
    r = requests.post(API + uid + '/media', timeout=60, data=meta).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
    cid, uri = r['id'], r['uri']
    with open(video, 'rb') as f:
        data = f.read()
    u = requests.post(uri, data=data, timeout=600, headers={
        'Authorization': 'OAuth ' + tok, 'offset': '0', 'file_size': str(len(data))}).json()
    if not u.get('success'):
        raise RuntimeError('файл: %s' % u)
    for _ in range(60):                                              # обработка видео — обычно 20–60 с
        st = requests.get(API + cid, params=dict(fields='status_code,status', access_token=tok), timeout=30).json()
        if st.get('status_code') == 'FINISHED':
            return cid
        if st.get('status_code') in ('ERROR', 'EXPIRED'):
            raise RuntimeError('обработка: %s' % st.get('status'))
        time.sleep(5)
    raise RuntimeError('Instagram не обработал видео за 5 минут')


def publish(cid):
    """Опубликовать готовый контейнер → (ссылка, 'опубликован'); ошибка — исключение."""
    tok, uid = _env()
    for _ in range(6):            # FINISHED бывает раньше, чем медиа готово к публикации (код 9007 / 2207027) — ждём
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
        if 'id' in p or (p.get('error') or {}).get('code') != 9007:
            break
        time.sleep(15)
    if 'id' not in p:
        raise RuntimeError('публикация: %s' % (p.get('error') or p))
    link = requests.get(API + p['id'], params=dict(fields='permalink', access_token=tok), timeout=30).json()
    url = link.get('permalink') or 'https://www.instagram.com/'
    print('INSTAGRAM опубликован %s %s' % (p['id'], url), flush=True)
    return url, 'опубликован'


def deferred():
    """Владелец 26.10: ролики — не пачкой ночью, а по одному днём. В Actions ролик ставится в очередь (queue), выкладывает
    тик соцсетей (team/reels_daily/ig_queue.py). Выключить: IG_QUEUE=0 — сразу, как раньше."""
    return enabled() and os.environ.get('IG_QUEUE', '1') != '0' and os.environ.get('GITHUB_ACTIONS') == 'true'


def queue(base, text, cover, at, start):
    """Загрузить ролик в контейнер и записать задание <base>.igq (JSON) для ig_queue.py: at — время выхода (UTC, как
    у YouTube, make.publish_time), start — начало матча (МСК, 'ГГГГ-ММ-ДД ЧЧ:ММ'). Время уже прошло — публикуем сразу.
    Контейнер не создался — задание без cid: тик загрузит ролик заново из артефакта."""
    if at is None:
        return upload(base + '.mp4', text, cover)
    cid = None
    try:
        cid = prepare(base + '.mp4', text, cover)
    except Exception as e:  # noqa: BLE001
        print('INSTAGRAMERR контейнер для очереди: %s' % str(e)[:200], flush=True)
    import json
    with open(base + '.igq', 'w', encoding='utf-8') as f:
        json.dump(dict(cid=cid, created=time.time(), at=at.isoformat(), start=start, text=text,
                       video=os.path.basename(base) + '.mp4', cover=os.path.basename(cover) if cover else None),
                  f, ensure_ascii=False)
    hm = at.astimezone(timezone(timedelta(hours=3))).strftime('%H:%M')
    print('INSTAGRAM в очереди на %s МСК (%s)' % (hm, 'контейнер готов' if cid else 'загрузка при выкладке'), flush=True)
    return None, 'в очереди на %s МСК' % hm
