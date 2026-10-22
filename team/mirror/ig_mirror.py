# -*- coding: utf-8 -*-
"""Зеркало канала в Instagram (владелец 22.10: «всё то же самое, что делаем для Телеграма, — постами в Инстаграм»; вариант
1 — пост-картинка). Поводом остаётся кнопка «Опубликовать» в Telegram: что вышло в канале, то через несколько минут
выходит и в Instagram — отдельно ничего не одобряется.

- Лента канала t.me/s/jarvibet (team/daily/channel.py): посты с видео/гифкой/фото, вышедшие после START и за последние
  HOURS часов. Текстовые посты и альбомы пропускаются (Instagram требует картинку).
- Картинка: последний кадр баннера (там прогноз/итог уже на месте), под ленту Instagram — от 4:5 до 1,91:1; вертикальный
  баннер садится на 1080×1350 поверх размытого себя же.
- Instagram берёт картинку только по публичной ссылке (репозиторий закрытый) — файл кладётся на litterbox.catbox.moe на
  1 час (запасной — tmpfiles.org), Instagram забирает его при создании контейнера. Картинка и так уходит в публичный пост.
- Подпись — текст поста из Telegram без разметки + строка про Telegram в шапке профиля; до 2200 знаков.
- Повторов нет: номера уже выложенных постов — .ig_mirror/done.json (кэш Actions между запусками), и подпись с теми же
  первыми двумя строками в последних 50 публикациях Instagram (instagram.posted).
- YouTube: постов сообщества нет в API — владельцу в бота та же картинка с текстом, чтобы вставить в приложении.

    python team/mirror/ig_mirror.py [--dry]      (--dry — ничего не выкладывать, владельцу превью картинки и подписи)
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

import requests
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
for p in ('team/daily', 'team/reels_daily', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import channel  # noqa: E402
import instagram  # noqa: E402

START = datetime(2026, 10, 22, 12, 0, tzinfo=channel.MSK)     # раньше этого — не зеркалим (запуск зеркала)
HOURS = int(os.environ.get('MIRROR_HOURS', '12'))
STATE = os.path.join(ROOT, '.ig_mirror', 'done.json')
FOOTER = 'Полные разборы и таблица — в Telegram, ссылка в шапке профиля.'
TAGS = '#хоккей #кхл #нхл #прогнозы'
API = instagram.API


def load_done():
    try:
        with open(STATE, encoding='utf-8') as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def save_done(done):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w', encoding='utf-8') as f:
        json.dump(sorted(done)[-300:], f)


def caption(post):
    lines = [t for t, _ in post['text']]
    tags = [t for t in lines if t.startswith('#')]
    body = [t for t in lines if not t.startswith('#')]
    head = '\n'.join(body[:2])
    rest = body[2:]
    txt = '\n'.join(body) + '\n\n' + FOOTER + '\n\n' + (' '.join(tags) or TAGS)
    if len(txt) > 2200:
        keep = 2200 - len(head) - len(FOOTER) - 60
        txt = head + '\n' + '\n'.join(rest)[:keep].rsplit(' ', 1)[0] + '…\n\n' + FOOTER + '\n\n' + TAGS
    return head, txt


def picture(post, tmp):
    """Файл поста → JPEG для ленты Instagram (последний кадр видео), путь."""
    src = os.path.join(tmp, 'src')
    r = requests.get(post['media_url'], timeout=120, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    with open(src, 'wb') as f:
        f.write(r.content)
    png = os.path.join(tmp, 'frame.png')
    if post['media'] in ('видео', 'гифка'):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-sseof', '-0.4', '-i', src, '-frames:v', '1', png], check=True)
        im = Image.open(png).convert('RGB')
    else:
        im = Image.open(src).convert('RGB')
    w, h = im.size
    if 0.8 <= w / h <= 1.91:
        out = im.resize((1080, round(1080 * h / w)), Image.LANCZOS)
    else:                                                  # вертикальный (9:16) или слишком широкий — на 1080×1350
        W, H = 1080, 1350 if w / h < 0.8 else 566
        bg = im.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new('RGB', (W, H), (0, 0, 0)), 0.35)
        k = min(W / w, H / h)
        fg = im.resize((round(w * k), round(h * k)), Image.LANCZOS)
        bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
        out = bg
    path = os.path.join(tmp, 'post_%d.jpg' % post['id'])
    out.save(path, quality=92)
    return path


def host(path):
    """Публичная ссылка на файл на 1 час (Instagram забирает картинку по ссылке)."""
    try:
        with open(path, 'rb') as f:
            r = requests.post('https://litterbox.catbox.moe/resources/internals/api.php', timeout=120,
                              data=dict(reqtype='fileupload', time='1h'), files=dict(fileToUpload=f))
        if r.ok and r.text.startswith('https://'):
            return r.text.strip()
        print('MIRRORERR litterbox: %s %s' % (r.status_code, r.text[:200]), flush=True)
    except requests.RequestException as e:
        print('MIRRORERR litterbox: %r' % e, flush=True)
    with open(path, 'rb') as f:
        r = requests.post('https://tmpfiles.org/api/v1/upload', timeout=120, files=dict(file=f))
    url = r.json()['data']['url']
    return url.replace('tmpfiles.org/', 'tmpfiles.org/dl/', 1)


def publish(url, text):
    tok, uid = instagram._env()
    r = requests.post(API + uid + '/media', timeout=60, data=dict(image_url=url, caption=text, access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
    import time
    for _ in range(24):
        st = requests.get(API + r['id'], params=dict(fields='status_code', access_token=tok), timeout=30).json()
        if st.get('status_code') in ('FINISHED', None):
            break
        if st.get('status_code') in ('ERROR', 'EXPIRED'):
            raise RuntimeError('обработка: %s' % st)
        time.sleep(5)
    for _ in range(6):
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=r['id'], access_token=tok), timeout=60).json()
        if 'id' in p or (p.get('error') or {}).get('code') != 9007:
            break
        time.sleep(10)
    if 'id' not in p:
        raise RuntimeError('публикация: %s' % (p.get('error') or p))
    link = requests.get(API + p['id'], params=dict(fields='permalink', access_token=tok), timeout=30).json()
    return link.get('permalink') or 'https://www.instagram.com/'


def to_owner(path, text):
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    with open(path, 'rb') as f:
        tj._api(tok, 'sendPhoto', dict(chat_id=chat, caption=text[:1024]), {'photo': f})


def main(dry=False):
    now = datetime.now(channel.MSK)
    since = max(START, now - timedelta(hours=HOURS))
    posts, pages = channel.feed(since)
    done = load_done()
    todo = [p for p in posts if p['posted'] and p['posted'] >= since and p['id'] not in done and p['text']
            and p['media'] in ('видео', 'гифка', 'фото') and p.get('media_url')]
    if dry:                                       # превью: два последних поста с картинкой, без даты запуска
        todo = [p for p in posts if p['media'] in ('видео', 'гифка', 'фото') and p.get('media_url') and p['text']][-2:]
    print('MIRROR лента: постов %d (страниц %d), к выкладке %d: %s' % (len(posts), pages, len(todo),
                                                                       ', '.join('№%d' % p['id'] for p in todo)), flush=True)
    for post in todo:
        head, text = caption(post)
        tmp = tempfile.mkdtemp()
        try:
            path = picture(post, tmp)
            if dry:
                to_owner(path, 'Превью зеркала в Instagram (пост №%d, никуда не выложен):\n\n%s' % (post['id'], text))
                print('MIRRORDRY №%d\n%s' % (post['id'], text), flush=True)
                continue
            if instagram.posted(head):
                print('MIRROR №%d уже в Instagram' % post['id'], flush=True)
            else:
                link = publish(host(path), text)
                print('MIRROR №%d → %s' % (post['id'], link), flush=True)
                if os.environ.get('MIRROR_YT', '1') == '1':
                    to_owner(path, 'Пост для YouTube (вкладка «Сообщество» в приложении) — скопируйте текст и картинку:\n\n'
                             + text.replace('ссылка в шапке профиля', 'ссылка в описании канала'))
            done.add(post['id'])
            save_done(done)
        except Exception as e:  # noqa: BLE001 — один пост не должен остановить остальные
            print('MIRRORERR №%d: %r' % (post['id'], e), flush=True)


if __name__ == '__main__':
    main('--dry' in sys.argv)
