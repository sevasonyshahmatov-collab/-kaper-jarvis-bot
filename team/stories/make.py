# -*- coding: utf-8 -*-
"""Истории Instagram — 6 в день, без прогнозов (владелец 22.10; docs/handoff/SMM_AGENT.md). Запускает
.github/workflows/stories-daily.yml по расписанию; один запуск — одна история (слот).

  matches  09:00 МСК — «Матчи дня»: КХЛ сегодня + НХЛ ночью (приложение КХЛ, API НХЛ)
  fact     11:30     — «Факт про таблицу»: facts.json по кругу
  win      14:00     — «Вчера зашло»: зашедшие прогнозы канала за вчера (как утренние итоги, team/daily); нет — факт
  question 16:30     — «Вопрос дня»: главный матч вечера, ответ — в Telegram
  video    19:00     — последний рилс аккаунта — историей (видео берём у самого Instagram)
  results  22:30     — «Сегодня зашло»: зашедшие прогнозы канала на сегодняшние матчи; нет — факт

    PYTHONPATH=render python team/stories/make.py <слот> [ГГГГ-ММ-ДД] [--dry]   (--dry — не выкладывать)
    PYTHONPATH=render python team/stories/make.py preview [ГГГГ-ММ-ДД]           все 6 — владельцу в Telegram, не выкладывать
    PYTHONPATH=render python team/stories/make.py auto                           по расписанию: слот по времени (due), без повторов
"""
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily'),
          os.path.join(ROOT, 'team', 'daily'), os.path.join(ROOT, 'team', 'mirror'), HERE):
    sys.path.insert(0, p)

import cards  # noqa: E402

MSK = timezone(timedelta(hours=3))
API = 'https://graph.facebook.com/v21.0/'
OUT = os.path.join(ROOT, 'out', 'stories')


def dm(d):
    return d.strftime('%d.%m')


WD = ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье')
MON = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')


def day_title(d):
    return '%s, %d %s' % (WD[d.weekday()], d.day, MON[d.month - 1])


def fact_card(day, path, shift=0):
    J = json.load(open(os.path.join(HERE, 'facts.json'), encoding='utf-8'))
    F = J['facts']
    i = ((day - date(2026, 10, 23)).days * 2 + shift) % len(F)          # два факта в день не совпадают (fact и запасной)
    return cards.fact(path, F[i]['title'], F[i]['text'], J['label'], swap=i % 2 == 1)   # цвета чередуются


def day_matches(day):
    """→ [('КХЛ', [(время, хоз, гости)]), ('НХЛ', […])]: КХЛ — матчи этого дня, НХЛ — ближайшая ночь (на day+1 по Москве;
    игровой день НХЛ — дата по Нью-Йорку, team/reels_daily/README.md)."""
    import khl_data
    import nhl_data
    groups = []
    for lg, mod, want in (('КХЛ', khl_data, day), ('НХЛ', nhl_data, day + timedelta(days=1))):
        try:
            _, nxt = mod.fetch(day.isoformat())
        except Exception as e:  # noqa: BLE001
            print('STORYERR %s: %r' % (lg, e), flush=True)
            continue
        rows = sorted((x['d'][11:16], x['h'], x['a']) for x in nxt if x['d'][:10] == want.isoformat())
        if lg == 'НХЛ':
            rows = [r for r in rows if r[0] < '12:00']
        if rows:
            groups.append((lg, rows))
    return groups


def hits(t0, t1):
    """Зашедшие прогнозы канала на матчи с началом в [t0, t1) → строки team/daily (для баннера итогов), по убыванию кэфа."""
    import channel
    import data
    import morning
    import settle
    picks, _ = channel.posts(t0, t1)
    found, _ = data.games_for(picks) if picks else ({}, [])
    rows, _, _ = morning.settle_rows(picks, found)
    out = [r for r in rows if r['res'] == settle.WIN]
    out.sort(key=lambda r: -(r.get('kef') or 0))
    return out


def main_match(day):
    """Главный матч вечера для «Вопроса дня»: последний по времени матч КХЛ (прайм-тайм), иначе первый матч НХЛ ночи."""
    g = day_matches(day)
    for lg, rows in g:
        if lg == 'КХЛ':
            tm, h, a = rows[-1]
            return h, a, '%d %s' % (day.day, MON[day.month - 1]), tm, 'KHL'
    for lg, rows in g:
        tm, h, a = rows[0]
        return h, a, '%d %s' % (day.day, MON[day.month - 1]), tm, 'NHL'
    return None


def last_reel():
    """Видео последнего рилса аккаунта (media_url у Instagram) → локальный файл или None."""
    import instagram
    tok, uid = instagram._env()
    j = requests.get(API + uid + '/media', params=dict(fields='media_type,media_product_type,media_url,timestamp', limit=10,
                                                       access_token=tok), timeout=30).json()
    for m in j.get('data') or []:
        if m.get('media_product_type') == 'REELS' and m.get('media_url'):
            p = os.path.join(tempfile.mkdtemp(), 'reel.mp4')
            with open(p, 'wb') as f:
                f.write(requests.get(m['media_url'], timeout=300).content)
            return p
    return None


def _wait_publish(cid, tok, uid):
    for _ in range(60):
        st = requests.get(API + cid, params=dict(fields='status_code', access_token=tok), timeout=30).json()
        if st.get('status_code') in ('FINISHED', None):
            break
        if st.get('status_code') in ('ERROR', 'EXPIRED'):
            raise RuntimeError('обработка: %s' % st)
        time.sleep(5)
    for _ in range(6):
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
        if 'id' in p or (p.get('error') or {}).get('code') != 9007:
            break
        time.sleep(15)
    if 'id' not in p:
        raise RuntimeError('публикация: %s' % (p.get('error') or p))
    return p['id']


def publish_image(path):
    import ig_mirror
    import instagram
    tok, uid = instagram._env()
    r = requests.post(API + uid + '/media', timeout=60,
                      data=dict(image_url=ig_mirror.host(path), media_type='STORIES', access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
    return _wait_publish(r['id'], tok, uid)


def publish_video(path):
    import instagram
    tok, uid = instagram._env()
    r = requests.post(API + uid + '/media', timeout=60,
                      data=dict(media_type='STORIES', upload_type='resumable', access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('контейнер: %s' % (r.get('error') or r))
    with open(path, 'rb') as f:
        data = f.read()
    u = requests.post(r['uri'], data=data, timeout=600,
                      headers={'Authorization': 'OAuth ' + tok, 'offset': '0', 'file_size': str(len(data))}).json()
    if not u.get('success'):
        raise RuntimeError('файл: %s' % u)
    return _wait_publish(r['id'], tok, uid)


def build(slot, day):
    """→ (путь, 'image'|'video', пояснение)."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, '%s_%s.jpg' % (day.isoformat(), slot))
    if slot == 'matches':
        out = []                                         # владелец 22.10: КХЛ и НХЛ — отдельными историями
        for lg, rows in day_matches(day):
            L = 'KHL' if lg == 'КХЛ' else 'NHL'
            p = os.path.join(OUT, '%s_matches_%s.jpg' % (day.isoformat(), L.lower()))
            title = day_title(day) if L == 'KHL' else 'ночь на ' + day_title(day + timedelta(days=1)).split(', ')[1]
            items = [dict(home=h, away=a, time=tm) for tm, h, a in rows]
            out.append((cards.matches(p, title, items, league=L), 'image', '%s: %d матчей' % (lg, len(items))))
        return out or (fact_card(day, path, 1), 'image', 'матчей нет — факт')
    if slot == 'fact':
        return fact_card(day, path), 'image', 'факт'
    if slot in ('win', 'results'):
        y = day - timedelta(days=1) if slot == 'win' else day
        t0 = datetime(y.year, y.month, y.day, 8, 0, tzinfo=MSK)          # КХЛ дня + НХЛ следующей ночи
        try:
            h = hits(t0, t0 + timedelta(days=1)) if slot == 'win' else hits(t0, datetime.now(MSK))
        except Exception as e:  # noqa: BLE001 — канал/счёт недоступны — запасная карточка
            print('STORYERR итоги: %r' % e, flush=True)
            h = []
        if h:
            return cards.win(path, h, day_title(y)), 'image', '%d зашедших' % len(h)
        return fact_card(day, path, 1), 'image', 'зашедших нет — факт'
    if slot == 'question':
        m = main_match(day)
        if m:
            return cards.question(path, *m), 'image', 'вопрос дня: %s — %s' % m[:2]
        return fact_card(day, path, 1), 'image', 'матчей нет — факт'
    if slot == 'video':
        p = last_reel()
        if p:
            return p, 'video', 'последний рилс'
        return fact_card(day, path, 1), 'image', 'рилса нет — факт'
    raise SystemExit(__doc__)


SLOTS = ('matches', 'fact', 'win', 'question', 'video', 'results')
TIMES = dict(matches='09:00', fact='11:30', win='14:00', question='16:30', video='19:00', results='22:30')


WINDOW = timedelta(minutes=150)        # слот ещё можно выложить, если GitHub запустил задание с опозданием


def due(now):
    """Какой слот выкладывать сейчас: последний, чьё время уже наступило, но не раньше чем WINDOW назад (владелец 23.10:
    GitHub запускает задания по расписанию с опозданием или пропускает — поэтому запусков два на слот, и каждый
    проверяет сам). → (слот, день, время слота) или None."""
    for back in (0, 1):                                   # «зашло сегодня» в 22:30 догоняем и после полуночи
        d = now.date() - timedelta(days=back)
        for slot in reversed(SLOTS):
            hh, mm = map(int, TIMES[slot].split(':'))
            t = datetime(d.year, d.month, d.day, hh, mm, tzinfo=MSK)
            if t <= now <= t + WINDOW:
                return slot, d, t
            if t <= now:
                break
    return None


def published_since(t):
    """Есть ли уже история, выложенная после t (активные истории аккаунта — Instagram отдаёт их 24 ч)."""
    import instagram
    tok, uid = instagram._env()
    j = requests.get(API + uid + '/stories', params=dict(fields='timestamp', limit=50, access_token=tok), timeout=30).json()
    if 'error' in j:
        raise RuntimeError('список историй: %s' % j['error'])
    for m in j.get('data') or []:
        ts = datetime.strptime(m['timestamp'], '%Y-%m-%dT%H:%M:%S%z')
        if ts >= t:
            return True
    return False


def to_owner(path, kind, caption):
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('TG_BOT_TOKEN не задан', flush=True)
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    with open(path, 'rb') as f:
        if kind == 'video':
            tj._api(tok, 'sendVideo', dict(chat_id=chat, caption=caption, supports_streaming='true'), {'video': f}, timeout=300)
        else:
            tj._api(tok, 'sendPhoto', dict(chat_id=chat, caption=caption), {'photo': f}, timeout=120)


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    slot = a[0]
    day = date.fromisoformat(next((x for x in a[1:] if x[:2] == '20'), datetime.now(MSK).date().isoformat()))
    if slot == 'auto':                                   # запуск по расписанию: слот по времени, без повторов
        d = due(datetime.now(MSK))
        if not d:
            print('STORY auto: сейчас нет слота', flush=True)
            return
        slot, day, t = d
        import instagram
        if instagram.enabled() and published_since(t):
            print('STORY auto: слот %s %s уже выложен — пропуск' % (slot, TIMES[slot]), flush=True)
            return
        print('STORY auto: слот %s %s' % (slot, TIMES[slot]), flush=True)
    if slot == 'preview':
        for s in SLOTS:
            try:
                res = build(s, day)
            except Exception as e:  # noqa: BLE001
                print('STORYERR %s: %r' % (s, e), flush=True)
                continue
            for path, kind, note in (res if isinstance(res, list) else [res]):
                print('STORY %s %s | %s | %s' % (s, day, kind, note), flush=True)
                to_owner(path, kind, 'ПРОБА истории %s МСК (%s) — не выложено' % (TIMES[s], note))
        return
    import instagram
    res = build(slot, day)
    for path, kind, note in (res if isinstance(res, list) else [res]):
        print('STORY %s %s | %s | %s' % (slot, day, kind, note), flush=True)
        if '--dry' in a:
            continue
        if not instagram.enabled():
            print('STORY нет IG_TOKEN / IG_USER_ID — не выложено', flush=True)
            return
        mid = publish_video(path) if kind == 'video' else publish_image(path)
        print('STORY опубликована %s' % mid, flush=True)


if __name__ == '__main__':
    main()
