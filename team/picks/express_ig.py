# -*- coding: utf-8 -*-
"""Купон «Экспресс» в Instagram (владелец 31.10, team/picks/EXPRESS.md): пост в ленту (картинка 1080×1350 + подпись)
и сторис (1080×1920, media_type=STORIES). Запуск — задание itogi.yml (team/out/<день>/express_ig.json, kind team):
    team/picks/express_ig.py team/out/2026-10-31/express_ig_plan.json
Замок: публикует, только если в плане "approved": "owner" и "approval" — откуда «да купон» владельца (чат руководителя /
INBOX). Без этого — ничего не публикует и выходит с ошибкой. Секреты IG_TOKEN / IG_USER_ID — из itogi.yml, не выводим.
Картинку Instagram берёт по публичной ссылке: файл на 1 час кладётся на litterbox (как team/mirror/ig_mirror.py)."""
import json
import os
import sys
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'mirror'), os.path.join(ROOT, 'team', 'reels_daily')]
import ig_mirror  # noqa: E402
import instagram  # noqa: E402

API = instagram.API


def _container(data):
    tok, uid = instagram._env()
    r = requests.post(API + uid + '/media', timeout=60, data=dict(data, access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
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


def publish_feed(path, caption):
    """Картинка в ленту с подписью → ссылка."""
    return _container(dict(image_url=ig_mirror.host(path), caption=caption))


def publish_story(path):
    """Картинка в сторис (подписи у сторис нет) → ссылка."""
    return _container(dict(image_url=ig_mirror.host(path), media_type='STORIES'))


def main(plan_path):
    plan = json.load(open(os.path.join(ROOT, plan_path), encoding='utf-8'))
    if str(plan.get('approved', '')).lower() != 'owner' or not plan.get('approval'):
        sys.exit('::error::express_ig: нет одобрения владельца ("approved": "owner" и "approval") — ничего не публикую')
    if not instagram.enabled():
        sys.exit('::error::express_ig: нет секретов IG_TOKEN / IG_USER_ID')
    cap = open(os.path.join(ROOT, plan['caption']), encoding='utf-8').read().strip()
    res = []
    if plan.get('feed'):
        res.append('лента: ' + publish_feed(os.path.join(ROOT, plan['feed']), cap))
    if plan.get('story'):
        res.append('сторис: ' + publish_story(os.path.join(ROOT, plan['story'])))
    for r in res:
        print('::notice title=EXPRESS_IG::%s' % r, flush=True)
    # итог — владельцу в бот: дописываем сообщение в задание (team_job.py перечитывает messages после make)
    job = os.path.join(ROOT, plan['job'])
    j = json.load(open(job, encoding='utf-8'))
    j['messages'] = [{'to': 'owner', 'type': 'text', 'text': 'Экспресс опубликован в Instagram:\n' + '\n'.join(res)}]
    json.dump(j, open(job, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
