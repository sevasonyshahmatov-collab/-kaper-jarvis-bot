# -*- coding: utf-8 -*-
"""Очередь роликов в Instagram (владелец 26.10: не пачкой ночью, а по одному днём).

Запуски (владелец 27.10: внешний будильник утром не сработал — очередь не должна от него зависеть): ночной конвейер
в конце запускает ig-queue.yml; запуск сам ждёт время следующего ролика (не дольше RUN_FOR) и, если задания остались,
запускает себя снова (workflow_dispatch с GITHUB_TOKEN — разрешённое исключение). Тики соцсетей — запасной путь.

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
GAP, RUN_FOR, LATE = 25 * 60, 5 * 3600, timedelta(minutes=30)     # запуск — до 5 ч (предел задания GitHub — 6 ч)
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


def live(items, now):
    """Задания, которые ещё можно выложить (матч не начался), — по одному на матч (последнее); по времени выхода."""
    seen, out = set(), []
    for q in sorted(items, key=lambda q: -q['created']):
        first = instagram.key_line(q['text'])
        if first in seen:
            continue
        seen.add(first)
        if now < q['start'] - LATE:
            out.append(q)
    return sorted(out, key=lambda q: (q['at'], q['start']))


def due(items, now):
    """Подошло время и матч ещё не начался; сначала те, чей матч раньше."""
    return sorted((q for q in live(items, now) if q['at'] <= now), key=lambda q: (q['start'], q['at']))


def again():
    """Запустить себя снова (остались задания на потом)."""
    r = requests.post('https://api.github.com/repos/%s/actions/workflows/ig-queue.yml/dispatches' % os.environ['GITHUB_REPOSITORY'],
                      json={'ref': os.environ.get('GITHUB_REF_NAME') or 'main'}, timeout=60,
                      headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'})
    print('IGQ следующий запуск: %s' % ('запрошен' if r.status_code == 204 else 'ошибка %s %s' % (r.status_code, r.text[:200])),
          flush=True)


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
    t0, last = time.time(), None
    rest = [q for q in live(items, datetime.now(timezone.utc)) if not instagram.posted(instagram.key_line(q['text']))]
    print('IGQ заданий %d, ждут выкладки %d' % (len(items), len(rest)), flush=True)
    while rest:
        now = datetime.now(timezone.utc)
        rest = live(rest, now)
        todo = due(rest, now)
        if not todo:
            if not rest:
                break
            wait = (min(q['at'] for q in rest) - now).total_seconds()
            if dry or time.time() - t0 + wait > RUN_FOR:
                break
            print('IGQ жду %d мин до следующего ролика' % (wait // 60 + 1), flush=True)
            time.sleep(wait + 5)
            continue
        q = todo[0]
        first = instagram.key_line(q['text'])
        if dry:
            print('IGQ выложил бы: %s (по плану %s МСК)' % (first[:80], q['at'].astimezone(MSK).strftime('%H:%M')))
            rest.remove(q)
            continue
        if last and time.time() - last < GAP:                      # между роликами — не меньше 25 мин
            if time.time() - t0 + GAP > RUN_FOR:
                break
            time.sleep(GAP - (time.time() - last))
        url, note = put(q, videos)
        print('IGQ %s: %s %s' % (first[:80], note, url or ''), flush=True)
        print('::notice title=IGQ::%s — %s' % (first[:80], note[:120]), flush=True)   # видно из облака (api.github.com)
        rest.remove(q)
        if url:
            last = time.time()
            instagram._state.setdefault('captions', []).insert(0, q['text'])   # posted() видит только что выложенное
    rest = live(rest, datetime.now(timezone.utc))
    if rest and not dry:
        again()


if __name__ == '__main__':
    main('--dry' in sys.argv)
