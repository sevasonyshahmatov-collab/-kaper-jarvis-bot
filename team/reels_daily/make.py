# -*- coding: utf-8 -*-
"""Конвейер шортсов КХЛ и НХЛ (docs/handoff/CONVEYOR.md): матчи дня → прогноз по правилу владельца → ролик на утверждённом
шаблоне 14.10 → владельцу в Telegram ролик (со звуком и без) + тексты для YouTube. Запускает .github/workflows/reels-daily.yml.

    python team/reels_daily/make.py plan khl 2026-10-17 [--max N] [--per 3]   # матчи и прогнозы → out/reels_daily/khl-<день>/plan.json
    python team/reels_daily/make.py render khl 2026-10-17 --part 1           # собрать и отправить часть plan.json (по --per роликов)
    python team/reels_daily/make.py render khl 2026-10-17 --part 1 --frames 1,12,20   # проверка кадрами, без трека и отправки

Один матч — один ролик (владелец 17.10): шаблоны по очереди, прошли все — круг заново. Матчи НХЛ — игровой день НХЛ
(дата по Нью-Йорку, у нас ночь на следующее число). --max 0 (по умолчанию) — ролик на каждый матч с прогнозом.

Треки — render/reels/owner_tracks.py (TRACKS_DIR или секрет TRACKS_KEY); Telegram — TG_BOT_TOKEN (нет — только собирает).
"""
import importlib
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.dirname(os.path.abspath(__file__))):
    sys.path.insert(0, p)

import form  # noqa: E402
import pick  # noqa: E402
import youtube  # noqa: E402
import instagram  # noqa: E402
import yt_texts  # noqa: E402

CFG = os.path.join(ROOT, 'team', 'out', '2026-10-13', 'reels_cfg')
MSK = timezone(timedelta(hours=3))
WEEK = ('ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС')

# Все утверждённые шаблоны (team/reels_selected/README.md) — по очереди, независимо от вида ставки (владелец 19.10).
# 14.10 и их варианты с треками 16–17.10 (владелец 17.10: «с новой музыкой пойдёт» — отдельные шаблоны; быстрые треки —
# на половинном темпе): параметры сцен — reels_cfg/<модуль>.json.
# 12.10 («Сравнение», «Терминал», «Карточка», «Состав» на трёх треках): параметры — как в team/out/2026-10-12/*_make.py.
# код: модуль, класс, трек, доля трека (с), дроп в треке (с)[, доли до дропа, аргументы класса]
TEMPLATES = {
    'cinema': ('cinema', 'Cinema', 'withyou', 60 / 73, 52.11),
    'broadcast': ('broadcast', 'Broadcast', 'packs', 60 / 71, 29.59),
    'dashboard': ('dashboard', 'Dashboard', 'truck', 60 / 65, 103.98),
    # 'graffiti': ('graffiti', 'Graffiti', 'vvs', 60 / 90, 98.69),   # владелец 19.10: «Граффити» больше не берём
    'jewel': ('jewel', 'Jewel', 'vvs', 60 / 90, 27.47),
    'kinetic': ('kinetic', 'Kinetic', 'packs', 60 / 71, 97.20),
    'race': ('race', 'Race', 'horses', 60 / 76, 37.92),
    'radar': ('radar', 'Radar', 'bats', 60 / 73, 39.46),
    'vhs': ('vhs', 'Vhs', 'downdown', 60 / 61, 78.25),
    'cinema_vampire': ('cinema', 'Cinema', 'vampire', 60 / 73, 92.101),
    # 'graffiti_demons': ('graffiti', 'Graffiti', 'demons', 0.6522, 86.296),   # владелец 19.10: «Граффити» больше не берём
    'dashboard_doomsday': ('dashboard', 'Dashboard', 'doomsday', 2 * 0.4444, 43.181),
    'race_cant_say': ('race', 'Race', 'cant_say', 2 * 0.3871, 49.161),
    'vhs_two_faced': ('vhs', 'Vhs', 'two_faced', 2 * 0.4839, 33.871),
    'tape': ('tape', 'Tape', 'rotten', 60 / 72, 28.20, 2.5 + 2 * 6 + 1.5, dict(per=1, pre=1.5, hold=4, cta=2.5)),
    'jarvis': ('jarvis', 'Jarvis', 'north', 120 / 142, 57.50, 19, dict(team=7, pre=2, hold=5, cta=2.5)),
    'card': ('card', 'Card', 'jefe', 60 / 81, 20.80, 21, dict(team=8, rush=2, hold=5.5, cta=3)),
    'lineup_slx': ('lineup', 'Lineup', 'slx', 60 / 95, 35.42, None, dict(ni=4, nt=9, nv=3, nh=6, nf=4)),
    'lineup_kizaru': ('lineup', 'Lineup', 'kizaru', 60 / 60, 40.08, None, dict(ni=3, nt=6, nv=2, nh=4, nf=2)),
    'lineup_vace': ('lineup', 'Lineup', 'vace', 60 / 64, 36.08, None, dict(ni=3, nt=6, nv=2, nh=4, nf=3)),
}


LG = {'khl': ('KHL', 'КХЛ'), 'nhl': ('NHL', 'НХЛ')}


def out_dir(league, day):
    return os.environ.get('OUT') or os.path.join(ROOT, 'out', 'reels_daily', '%s-%s' % (league, day))


# Сначала — шаблоны, которых в автозагрузке ещё не было (владелец 19.10: «начать с них»), потом остальные.
FIRST = ('lineup_slx', 'tape', 'jarvis', 'card', 'jewel', 'kinetic', 'lineup_kizaru', 'lineup_vace')
RING_START = date(2026, 10, 20)
PER_DAY = 12                      # мест очереди на день: НХЛ 0–5, КХЛ 6–11 (раньше обе лиги начинали с одного места)


LAST = ('cinema', 'broadcast', 'dashboard')                # шли почти каждую ночь до 19.10 — в конец очереди


def ring():
    return list(FIRST) + [t for t in TEMPLATES if t not in FIRST + LAST] + list(LAST)


def assign(matches, day, league='khl'):
    """Шаблон каждому матчу: одна сквозная очередь на все дни и обе лиги — шаблон повторяется, только когда прошли все."""
    r = ring()
    k = (date.fromisoformat(day) - RING_START).days * PER_DAY + (6 if league == 'khl' else 0)
    for m in matches:
        m['tpl'] = r[k % len(r)]
        k += 1
    return matches


def plan(league, day, top, per):
    import pin
    if league == 'khl':
        import khl_data
        games, nxt = khl_data.fetch(day)
        fon = {(x['h'], x['a']): x.get('bets') for x in nxt}
    else:
        import nhl_data
        games, nxt = nhl_data.fetch(day)
        fon = {}
    try:
        pins, _ = pin.fetch(league, day, [(x['h'], x['a']) for x in nxt])
    except Exception as e:  # noqa: BLE001 — без Pinnacle в КХЛ остаётся линия Фонбета
        print('PINERR %r' % e, flush=True)
        pins = {}
    ms = pick.day_picks(games, nxt, pins, fon, league)
    soon = (datetime.now(MSK) + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M')   # уже начавшиеся матчи — без ролика
    ms = [m for m in ms if m['d'] >= soon]
    only = [x for x in os.environ.get('REELS_ONLY', '').split(',') if x]     # только эти клубы (ручной запуск)
    if only:
        ms = [m for m in ms if m['h'] in only or m['a'] in only]
    if top:
        ms = sorted(ms, key=lambda m: -m['p'])[:top]                                # самые уверенные
    ms.sort(key=lambda m: m['d'])
    assign(ms, day, league)
    names = sorted({t for m in ms for t in (m['h'], m['a'])})
    stats = (form.khl if league == 'khl' else form.nhl)(games, day, names)
    parts = [list(range(i, min(i + per, len(ms)))) for i in range(0, len(ms), per)]
    P = dict(day=day, league=league, matches=ms, stats=stats, parts=parts, skipped=len(nxt) - len(ms),
             all=[dict(d=x['d'], h=x['h'], a=x['a']) for x in sorted(nxt, key=lambda x: x['d'])])
    os.makedirs(out_dir(league, day), exist_ok=True)
    with open(os.path.join(out_dir(league, day), 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(P, f, ensure_ascii=False, indent=1)
    print('PLAN матчей дня %d, роликов %d, частей %d' % (len(nxt), len(ms), len(parts)), flush=True)
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a') as f:
            f.write('parts=%s\n' % json.dumps(list(range(1, len(parts) + 1))))
    lg = LG[league][1]
    head = ['Шортсы %s на %s.%s: %d' % (lg, day[8:10], day[5:7], len(ms))]
    head += ['%s %s — %s · %s · %s' % (m['d'][11:16], m['h'], m['a'], m['pick'], ('%.2f' % m['odds']).replace('.', ','))
             for m in ms]
    if P['skipped']:
        head.append('Без ролика: %d (нет ставки с кэфом 1,6–2,3 или линии)' % P['skipped'])
    tg_text('\n'.join(head) if ms else 'Шортсы %s на %s: матчей с прогнозом по правилу нет' % (lg, day))
    return P


def reel(m, stats, code):
    mod, cls, key, u, tdrop, *rest = TEMPLATES[m['tpl']]
    d = date.fromisoformat(m['d'][:10])
    when = '%s %s · %s МСК' % (WEEK[d.weekday()], d.strftime('%d.%m'), m['d'][11:16])
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    line = tuple(m['x1x2'])
    if mod == 'lineup':                       # «Состав»: дроп считает сам шаблон
        from reels import form as F
        from reels import core as C
        h, a = C.match(m['h'], m['a'], code)
        r = Cls(m['h'], m['a'], code, m['pick'], m['odds'], when, stats, side=F.fav_side(h, a, m['pick']), u=u, line=line,
                **rest[1])
        return r, key, tdrop - r.drop
    if rest:                                  # 12.10: доли до дропа и аргументы — свои
        beats, kw = rest
    else:                                     # 14.10: reels_cfg/<модуль>.json
        p = os.path.join(CFG, mod + '.json')
        c = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'drop_beats': 20, 'kw': {}}
        beats, kw = c.get('drop_beats', 20), c.get('kw', {})
    drop = beats * u
    r = Cls(m['h'], m['a'], code, when, m['pick'], m['odds'], stats.get(m['h'], {}), stats.get(m['a'], {}), u=u, drop=drop,
            line=line, **kw)
    return r, key, tdrop - drop


def render(league, day, part, frames=None):
    code, lg = LG[league]
    if code == 'NHL':
        import nhl
        nhl.register()
    with open(os.path.join(out_dir(league, day), 'plan.json'), encoding='utf-8') as f:
        P = json.load(f)
    errors = []
    for i in P['parts'][part - 1]:
        try:
            one(P, i, league, day, code, lg, frames)
        except Exception as e:  # noqa: BLE001 — остальные ролики всё равно собираем
            m = P['matches'][i]
            errors.append('%s — %s: %r' % (m['h'], m['a'], e))
            print('REELERR', errors[-1], flush=True)
    if errors:
        tg_text('Шортсы: не собрались\n' + '\n'.join(errors))
        raise SystemExit('; '.join(errors))


def ticker(P, lg):
    """Бегущая строка внизу ролика (core.ticker, владелец 18.10): ярлык «МАТЧИ ДНЯ · дата» стоит на месте (дата
    в ленте уезжала под ярлык), в ленте — лига и все матчи дня по времени МСК. → (ярлык, пункты ленты)."""
    ms = P.get('all') or P['matches']
    d = ms[0]['d']
    return 'МАТЧИ ДНЯ · %s.%s' % (d[8:10], d[5:7]), ['%s · время МСК' % lg] + ['%s — %s %s' % (m['h'], m['a'], m['d'][11:16]) for m in ms]


def one(P, i, league, day, code, lg, frames):
    """Один ролик: собрать (со звуком и без) и отправить владельцу."""
    from reels import core as C
    from reels import owner_tracks
    m = P['matches'][i]
    t0 = time.time()
    r, key, start = reel(m, P['stats'], code)
    r.ticker_tag, r.ticker = ticker(P, lg)
    base = os.path.join(out_dir(league, day), '%02d_%s' % (i + 1, m['tpl']))
    if frames:
        print(C.render(r, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
        return
    C.render(r, base + '.mp4', track=owner_tracks.wav(key), start=start, extra_out=base + '_clean.mp4')
    print('REEL %s — %s | %s | трек %s с %.2f с, дроп на %.2f с | %.1f с ролика за %.0f с'
          % (m['h'], m['a'], m['tpl'], key, start, r.drop, r.dur, time.time() - t0), flush=True)
    y = yt_texts.youtube(m, lg)
    url, note = youtube.upload(base + '.mp4', y['title'], y['description'], y['tags'])
    cover = cover_for(m, code, base)
    tnote = youtube.thumbnail(url, cover) if cover else ''
    note = '\n'.join(x for x in (note, tnote) if x)
    head = ('YouTube: %s\n%s\n\n' % (url, note)) if url else ('YouTube: %s\n\n' % note) if note else ''
    ig, ignote = instagram.upload(base + '.mp4', instagram.caption(m, y), cover)
    head += ('Instagram: %s\n\n' % ig) if ig else ('Instagram: %s\n\n' % ignote) if ignote else ''
    tg_reel(base + '.mp4', base + '_clean.mp4', head + yt_texts.block(m, lg), y['title'], cover)


def cover_for(m, code, base):
    """Обложка 1080×1920 для YouTube и клипов VK (render/vk_covers.py, владелец 19.10). Не нарисовалась — None."""
    try:
        import vk_covers
        p = base + '_vk_cover.jpg'
        vk_covers.cover(dict(league=code, h=m['h'], a=m['a'], d=m['d'])).save(p, quality=90)
        return p
    except Exception as e:  # noqa: BLE001 — без обложки ролик всё равно уходит
        print('COVERERR %r' % e, flush=True)
        return None


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


def tg_reel(video, clean, caption, title, cover=None):
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
    if cover:
        with open(cover, 'rb') as f:
            tj._api(tok, 'sendDocument', dict(chat_id=chat, caption=('Обложка для YouTube и клипа VK: ' + title)[:tj.CAPTION_MAX]),
                    {'document': f}, timeout=120)


def main():
    a = sys.argv[1:]
    opt = lambda k, v: a[a.index(k) + 1] if k in a else v  # noqa: E731
    cmd, league, day = a[0], a[1].lower(), a[2]
    if league not in LG:
        raise SystemExit(__doc__)
    if cmd == 'plan':
        plan(league, day, int(opt('--max', 0)), int(opt('--per', 3)))
    elif cmd == 'render':
        render(league, day, int(opt('--part', 1)), opt('--frames', None))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
