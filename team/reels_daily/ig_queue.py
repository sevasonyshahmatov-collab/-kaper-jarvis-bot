# -*- coding: utf-8 -*-
"""Очередь роликов в Instagram (владелец 26.10: не пачкой ночью, а по одному днём).

Ночной конвейер (make.py → instagram.queue) загружает ролик в контейнер и кладёт задание <ролик>.igq в маленький
артефакт igq-<лига>-<день>-<часть> запуска «Шортсы — конвейер» (сами ролики — в videos-…, их качаем, только если
контейнер не вышел и ролик надо загрузить заново). Тик соцсетей (social-tick.yml) запускает этот скрипт: берёт артефакты запусков
за последние 30 ч, выкладывает задания, у которых подошло время (at), пока матч не начался (за 30 мин до начала —
уже нет). Несколько заданий за тик — с паузой GAP, не дольше MAX_TICK; остальное — следующему тику.
Уже выложенное (та же первая строка подписи в Instagram) не повторяется. Контейнер истёк или не создался —
ролик загружается заново из артефакта.

    python team/reels_daily/ig_queue.py [--dry]     # --dry — только показать, что подошло
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instagram  # noqa: E402

MSK = timezone(timedelta(hours=3))
GAP, MAX_TICK, LATE = 25 * 60, 95 * 60, timedelta(minutes=30)
WINDOW = timedelta(hours=30)                     # артефакты живут 2 дня, контейнеры — 24 ч
ROOT, FETCHED = tempfile.mkdtemp(), set()


def gh(path, **params):
    r = requests.get('https://api.github.com/repos/%s/actions/%s' % (os.environ['GITHUB_REPOSITORY'], path),
                     params=params, timeout=60, headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                                                         'Accept': 'application/vnd.github+json'})
    r.raise_for_status()
    return r


def fetch(root):
    """Скачать задания igq-* свежих запусков конвейера в root/<запуск>-<артефакт>/; → {каталог: id артефакта роликов}."""
    since, videos = datetime.now(timezone.utc) - WINDOW, {}
    for run in gh('workflows/reels-daily.yml/runs', per_page=10).json()['workflow_runs']:
        if datetime.fromisoformat(run['created_at'].replace('Z', '+00:00')) < since:
            continue
        arts = {a['name']: a for a in gh('runs/%d/artifacts' % run['id']).json()['artifacts'] if not a['expired']}
        for name, a in arts.items():
            if not name.startswith('igq-'):
                continue
            d = os.path.join(root, '%d-%s' % (run['id'], name))
            unzip(a['id'], d)
            v = arts.get('videos-' + name[4:])
            if v:
                videos[d] = v['id']
    return videos


def unzip(aid, d):
    zipfile.ZipFile(io.BytesIO(gh('artifacts/%d/zip' % aid).content)).extractall(d)


def jobs(root):
    out = []
    for p in glob.glob(os.path.join(root, '**', '*.igq'), recursive=True):
        with open(p, encoding='utf-8') as f:
            q = json.load(f)
        q['dir'] = os.path.dirname(p)
        q['at'] = datetime.fromisoformat(q['at'])
        q['start'] = datetime.strptime(q['start'], '%Y-%m-%d %H:%M').replace(tzinfo=MSK)
        out.append(q)
    return out


def due(items, now):
    """Подошло время и матч ещё не начался; сначала те, чей матч раньше. Один матч — одно задание (последнее)."""
    seen, out = set(), []
    for q in sorted(items, key=lambda q: -q['created']):
        first = q['text'].split('\n')[0]
        if first in seen:
            continue
        seen.add(first)
        if q['at'] <= now < q['start'] - LATE:
            out.append(q)
    return sorted(out, key=lambda q: (q['start'], q['at']))


def put(q, videos):
    """Выложить: готовый контейнер (живёт 24 ч), иначе — загрузить заново из артефакта роликов."""
    if q.get('cid') and time.time() - q['created'] < 23 * 3600:
        try:
            return instagram.publish(q['cid'])
        except Exception as e:  # noqa: BLE001
            print('IGQ контейнер не вышел (%s) — загружаю заново' % str(e)[:150], flush=True)
    top = os.path.relpath(q['dir'], ROOT).split(os.sep)[0]
    if top not in FETCHED and os.path.join(ROOT, top) in videos:      # ролики этой части — один раз
        unzip(videos[os.path.join(ROOT, top)], os.path.join(ROOT, top))
        FETCHED.add(top)
    if not shutil.which('ffmpeg'):                                     # zoomed() — копия для Instagram
        subprocess.run('timeout 300 sudo apt-get install -y -qq ffmpeg >/dev/null 2>&1 || '
                       '{ timeout 600 sudo apt-get update -qq && timeout 300 sudo apt-get install -y -qq ffmpeg >/dev/null; }',
                       shell=True)
    cover = os.path.join(q['dir'], q['cover']) if q.get('cover') else None
    return instagram.upload(os.path.join(q['dir'], q['video']), q['text'], cover)


def main(dry=False):
    if not instagram.enabled():
        print('IGQ нет IG_TOKEN / IG_USER_ID')
        return
    videos = fetch(ROOT)
    items = jobs(ROOT)
    now = datetime.now(timezone.utc)
    todo = due(items, now)
    print('IGQ заданий %d, подошло %d' % (len(items), len(todo)), flush=True)
    t0, done = time.time(), 0
    for q in todo:
        first = q['text'].split('\n')[0]
        if instagram.posted(first):
            print('IGQ уже выложен: %s' % first[:80], flush=True)
            continue
        if dry:
            print('IGQ выложил бы: %s (по плану %s МСК)' % (first[:80], q['at'].astimezone(MSK).strftime('%H:%M')))
            continue
        if done:
            if time.time() - t0 + GAP > MAX_TICK:
                print('IGQ остальное — следующему тику', flush=True)
                break
            time.sleep(GAP)
        url, note = put(q, videos)
        print('IGQ %s: %s %s' % (first[:80], note, url or ''), flush=True)
        if url:
            done += 1
            instagram._state.setdefault('captions', []).insert(0, q['text'])   # posted() видит только что выложенное


if __name__ == '__main__':
    main('--dry' in sys.argv)
