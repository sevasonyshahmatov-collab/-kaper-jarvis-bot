# -*- coding: utf-8 -*-
"""Купон «Экспресс» в Instagram после кнопки «Опубликовать» в боте (владелец 31.10, team/picks/EXPRESS.md).
Цепочка: владелец жмёт «Опубликовать» под купоном ДДММ-eN → бот публикует его в канал и запускает itogi.yml
(payload {kind: team, job: team/out/<D>/express_ig.json, express: {pid}}; задание — из заготовки
team/daily/jobs/express_ig.json) → render/team_job.py ставит EXPRESS_PID и EXPRESS_BY=owner-button → этот скрипт:
  лента — картинка последнего кадра купона (e<k>_feed.jpg) с подписью (надёжнее видео; по ссылке litterbox, как
          team/mirror/ig_mirror.py);
  сторис — видео e<k>_story.mp4 (media_type=STORIES, загрузка resumable); не вышло — картинка e<k>_story.jpg.
Итог (ссылки или причина отказа) — владельцу в бот: скрипт дописывает сообщение в задание (team_job перечитывает
messages после make). Канал не откатываем.
Замок: без EXPRESS_BY=owner-button (нажатие кнопки) — ничего не публикует. Запасной ручной путь — план
team/out/<D>/express_ig_plan.json с "approved": "owner", "approval" (где и когда владелец разрешил) и "pid".
    python team/picks/express_ig.py 2026-10-31
Секреты IG_TOKEN / IG_USER_ID — из itogi.yml, не выводим."""
import json
import os
import re
import sys
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'mirror'), os.path.join(ROOT, 'team', 'reels_daily')]
import ig_mirror  # noqa: E402
import instagram  # noqa: E402

API = instagram.API
TAGS = {'#нхл': '#нхл', '#кхл': '#кхл', '#футбол': '#футбол'}


def _wait_publish(cid, tries=60, pause=5):
    tok, uid = instagram._env()
    for _ in range(tries):
        st = requests.get(API + cid, params=dict(fields='status_code,status', access_token=tok), timeout=30).json()
        if st.get('status_code') in ('FINISHED', None):
            break
        if st.get('status_code') in ('ERROR', 'EXPIRED'):
            raise RuntimeError('обработка: %s' % st.get('status'))
        time.sleep(pause)
    else:
        raise RuntimeError('Instagram не обработал файл за %d с' % (tries * pause))
    for _ in range(6):
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
        if 'id' in p or (p.get('error') or {}).get('code') != 9007:
            break
        time.sleep(15)
    if 'id' not in p:
        raise RuntimeError('публикация: %s' % (p.get('error') or p))
    link = requests.get(API + p['id'], params=dict(fields='permalink', access_token=tok), timeout=30).json()
    return link.get('permalink') or 'https://www.instagram.com/'


def _container(data):
    tok, uid = instagram._env()
    r = requests.post(API + uid + '/media', timeout=60, data=dict(data, access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
    return r


def publish_feed(path, caption):
    """Картинка в ленту с подписью → ссылка."""
    return _wait_publish(_container(dict(image_url=ig_mirror.host(path), caption=caption))['id'], 24)


def publish_story_image(path):
    return _wait_publish(_container(dict(image_url=ig_mirror.host(path), media_type='STORIES'))['id'], 24)


def publish_story_video(path):
    """Видео-сторис: контейнер STORIES (resumable) → файл на rupload.facebook.com → обработка → публикация."""
    tok, _ = instagram._env()
    r = _container(dict(media_type='STORIES', upload_type='resumable'))
    data = open(path, 'rb').read()
    u = requests.post(r['uri'], data=data, timeout=600, headers={
        'Authorization': 'OAuth ' + tok, 'offset': '0', 'file_size': str(len(data))}).json()
    if not u.get('success'):
        raise RuntimeError('файл: %s' % u)
    return _wait_publish(r['id'])


def ig_caption(html):
    """Подпись Telegram → Instagram: без HTML, призыв в Telegram, 3 хэштега (голос .claude/instagram/voice.md)."""
    t = re.sub(r'<[^>]+>', '', html).strip()
    body, _, tags = t.rpartition('\n\n')
    lg = [x for x in tags.split() if x in TAGS] or ['#хоккей']
    tags3 = (lg + ['#хоккей', '#экспресс', '#прогнозынахоккей'])
    seen = []
    for x in tags3:
        if x not in seen:
            seen.append(x)
    return '%s\n\nВсе прогнозы — в Telegram @jarvibet, ссылка в шапке профиля.\n\n%s' % (body, ' '.join(seen[:3]))


def approved_pid(day):
    """→ (pid, откуда разрешение) или (None, причина)."""
    pid = os.environ.get('EXPRESS_PID', '')
    if os.environ.get('EXPRESS_BY') == 'owner-button' and re.fullmatch(r'\d{4}-e\d{1,2}', pid):
        return pid, 'кнопка «Опубликовать» в боте'
    plan = os.path.join(ROOT, 'team/out/%s/express_ig_plan.json' % day)
    if os.path.exists(plan):
        j = json.load(open(plan, encoding='utf-8'))
        if str(j.get('approved', '')).lower() == 'owner' and j.get('approval') and re.fullmatch(r'\d{4}-e\d{1,2}', str(j.get('pid', ''))):
            return j['pid'], 'план: ' + str(j['approval'])
    return None, 'нет нажатия кнопки «Опубликовать» (EXPRESS_BY) и одобренного плана'


def report(day, text):
    """Сообщение владельцу: дописать в задание (team_job перечитывает messages после make)."""
    job = os.path.join(ROOT, 'team/out/%s/express_ig.json' % day)
    try:
        j = json.load(open(job, encoding='utf-8'))
    except (OSError, ValueError):
        return
    j['messages'] = (j.get('messages') or []) + [{'to': 'owner', 'type': 'text', 'text': text}]
    json.dump(j, open(job, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main(day):
    pid, why = approved_pid(day)
    if not pid:
        print('::notice title=EXPRESS_IG::не публикую: %s' % why, flush=True)
        sys.exit('express_ig: %s' % why)
    k = pid.split('-e')[1]
    posts = json.load(open(os.path.join(ROOT, 'team/out/%s/express_posts.json' % day), encoding='utf-8'))
    if k not in posts or posts[k]['pid'] != pid:
        report(day, 'Instagram: купон %s не найден в express_posts.json — не опубликован.' % pid)
        sys.exit('express_ig: нет купона %s' % pid)
    if not instagram.enabled():
        report(day, 'Instagram: нет ключей IG_TOKEN / IG_USER_ID — купон %s не опубликован.' % pid)
        sys.exit('express_ig: нет секретов')
    X = os.path.join(ROOT, 'out/express/%s/e%s_' % (day, k))
    res, errs = [], []
    try:
        res.append('лента: ' + publish_feed(X + 'feed.jpg', ig_caption(posts[k]['html'])))
    except Exception as e:  # noqa: BLE001
        errs.append('лента: %s' % str(e)[:200])
    try:
        res.append('сторис (видео): ' + publish_story_video(X + 'story.mp4'))
    except Exception as e:  # noqa: BLE001
        try:
            res.append('сторис (картинка; видео не прошло: %s): ' % str(e)[:80] + publish_story_image(X + 'story.jpg'))
        except Exception as e2:  # noqa: BLE001
            errs.append('сторис: %s' % str(e2)[:200])
    for r in res + errs:
        print('::notice title=EXPRESS_IG::%s %s' % (pid, r.replace('\n', ' ')), flush=True)
    report(day, 'Экспресс %s — Instagram (%s):\n%s' % (pid, why, '\n'.join(res + ['не вышло — ' + e for e in errs])))
    if errs:
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1])
