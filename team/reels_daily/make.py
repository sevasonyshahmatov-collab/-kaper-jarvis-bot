# -*- coding: utf-8 -*-
"""Конвейер шортсов КХЛ (docs/handoff/CONVEYOR.md): матчи дня → прогноз по правилу владельца → ролик на утверждённом
шаблоне 14.10 → владельцу в Telegram ролик (со звуком и без) + тексты для YouTube. Запускает .github/workflows/reels-daily.yml.

    python team/reels_daily/make.py plan 2026-10-17 [--max 6] [--per 3]   # матчи и прогнозы → out/reels_daily/<день>/plan.json
    python team/reels_daily/make.py render 2026-10-17 --part 1             # собрать и отправить часть plan.json (по --per роликов)
    python team/reels_daily/make.py render 2026-10-17 --part 1 --frames 1,12,20   # проверка кадрами, без трека и отправки

Треки — render/reels/owner_tracks.py (TRACKS_DIR или секрет TRACKS_KEY); Telegram — TG_BOT_TOKEN (нет — только собирает).
"""
import importlib
import json
import os
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.dirname(os.path.abspath(__file__))):
    sys.path.insert(0, p)

import form  # noqa: E402
import pick  # noqa: E402
import texts  # noqa: E402

CFG = os.path.join(ROOT, 'team', 'out', '2026-10-13', 'reels_cfg')
WEEK = ('ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС')

# утверждённые шаблоны 14.10 (team/reels_selected/README.md): модуль, класс, трек, доля трека (с), дроп в треке (с)
TEMPLATES = [
    ('cinema', 'Cinema', 'withyou', 60 / 73, 52.11),
    ('broadcast', 'Broadcast', 'packs', 60 / 71, 29.59),
    ('dashboard', 'Dashboard', 'truck', 60 / 65, 103.98),
    ('graffiti', 'Graffiti', 'vvs', 60 / 90, 98.69),
    ('jewel', 'Jewel', 'vvs', 60 / 90, 27.47),
    ('kinetic', 'Kinetic', 'packs', 60 / 71, 97.20),
    ('race', 'Race', 'horses', 60 / 76, 37.92),
    ('radar', 'Radar', 'bats', 60 / 73, 39.46),
    ('vhs', 'Vhs', 'downdown', 60 / 61, 78.25),
]
BOTH = 'broadcast'      # прогноз на матч целиком (тотал) — пока только «Эфир» показывает в финале обе команды


def out_dir(day):
    return os.environ.get('OUT') or os.path.join(ROOT, 'out', 'reels_daily', day)


def assign(matches, day):
    """Шаблон каждому матчу: чередование по кругу, начало круга сдвигается по дням; тотал — «Эфир»."""
    n = date.fromisoformat(day).toordinal()
    names = [t[0] for t in TEMPLATES]
    ring = names[n % len(names):] + names[:n % len(names)]
    ring = [x for x in ring if x != BOTH]
    used = set()
    for m in matches:
        if m['g'] == 'tot':
            m['tpl'] = BOTH
            continue
        free = [x for x in ring if x not in used] or ring
        m['tpl'] = free[0]
        used.add(free[0])
    return matches


def plan(day, top, per):
    import khl_data
    import pin
    games, nxt = khl_data.fetch(day)
    fon = {(x['h'], x['a']): x.get('bets') for x in nxt}
    try:
        pins, _ = pin.fetch('khl', day, [(x['h'], x['a']) for x in nxt])
    except Exception as e:  # noqa: BLE001 — без Pinnacle остаётся линия Фонбета
        print('PINERR %r' % e, flush=True)
        pins = {}
    ms = pick.day_picks(games, nxt, pins, fon)
    ms = sorted(sorted(ms, key=lambda m: -m['p'])[:top], key=lambda m: m['d'])    # самые уверенные, по времени начала
    assign(ms, day)
    stats = form.khl(games, day, sorted({t for m in ms for t in (m['h'], m['a'])}))
    parts = [list(range(i, min(i + per, len(ms)))) for i in range(0, len(ms), per)]
    P = dict(day=day, league='KHL', matches=ms, stats=stats, parts=parts, skipped=len(nxt) - len(ms))
    os.makedirs(out_dir(day), exist_ok=True)
    with open(os.path.join(out_dir(day), 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(P, f, ensure_ascii=False, indent=1)
    print('PLAN матчей дня %d, роликов %d, частей %d' % (len(nxt), len(ms), len(parts)), flush=True)
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a') as f:
            f.write('parts=%s\n' % json.dumps(list(range(1, len(parts) + 1))))
    head = ['Шортсы КХЛ на %s.%s: %d' % (day[8:10], day[5:7], len(ms))]
    head += ['%s %s — %s · %s · %s' % (m['d'][11:16], m['h'], m['a'], m['pick'], ('%.2f' % m['odds']).replace('.', ','))
             for m in ms]
    if P['skipped']:
        head.append('Без ролика: %d (нет ставки с кэфом 1,6–2,3 или линии)' % P['skipped'])
    tg_text('\n'.join(head) if ms else 'Шортсы КХЛ на %s: матчей с прогнозом по правилу нет' % day)
    return P


def reel(m, stats):
    mod, cls, key, u, tdrop = next(t for t in TEMPLATES if t[0] == m['tpl'])
    p = os.path.join(CFG, mod + '.json')
    c = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'drop_beats': 20, 'kw': {}}
    drop = c.get('drop_beats', 20) * u
    d = date.fromisoformat(m['d'][:10])
    when = '%s %s · %s МСК' % (WEEK[d.weekday()], d.strftime('%d.%m'), m['d'][11:16])
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    r = Cls(m['h'], m['a'], 'KHL', when, m['pick'], m['odds'], stats.get(m['h'], {}), stats.get(m['a'], {}), u=u, drop=drop,
            line=tuple(m['x1x2']), **c.get('kw', {}))
    return r, key, tdrop - drop


def render(day, part, frames=None):
    from reels import core as C
    from reels import owner_tracks
    with open(os.path.join(out_dir(day), 'plan.json'), encoding='utf-8') as f:
        P = json.load(f)
    idx = P['parts'][part - 1]
    for i in idx:
        m = P['matches'][i]
        t0 = time.time()
        r, key, start = reel(m, P['stats'])
        base = os.path.join(out_dir(day), '%02d_%s' % (i + 1, m['tpl']))
        if frames:
            print(C.render(r, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
            continue
        C.render(r, base + '.mp4', track=owner_tracks.wav(key), start=start, extra_out=base + '_clean.mp4')
        print('REEL %s — %s | %s | трек %s с %.2f с, дроп на %.2f с | %.1f с ролика за %.0f с'
              % (m['h'], m['a'], m['tpl'], key, start, r.drop, r.dur, time.time() - t0), flush=True)
        y = texts.youtube(m)
        tg_reel(base + '.mp4', base + '_clean.mp4', texts.block(m), y['title'])


# ---------- Telegram (как render/team_job.py) ----------

def _tg():
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено', flush=True)
        return None, None
    import team_job as tj
    return tok, os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')


def tg_text(text):
    tok, chat = _tg()
    if tok:
        import team_job as tj
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text=text[:tj.TEXT_MAX], disable_web_page_preview='true'))


def tg_reel(video, clean, caption, title):
    tok, chat = _tg()
    if not tok:
        return
    import team_job as tj
    with open(video, 'rb') as f:
        tj._api(tok, 'sendVideo', dict(chat_id=chat, caption=caption[:tj.CAPTION_MAX], supports_streaming='true'),
                {'video': f}, timeout=300)
    with open(clean, 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption=('Без музыки (если YouTube заявит права на трек): ' + title)[:tj.CAPTION_MAX]),
                {'document': f}, timeout=300)


def main():
    a = sys.argv[1:]
    opt = lambda k, v: a[a.index(k) + 1] if k in a else v  # noqa: E731
    cmd, day = a[0], a[1]
    if cmd == 'plan':
        plan(day, int(opt('--max', 6)), int(opt('--per', 3)))
    elif cmd == 'render':
        render(day, int(opt('--part', 1)), opt('--frames', None))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
