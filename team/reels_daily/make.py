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
    # треки, которых раньше не было (пробы 19.10, run 268; владелец 19.10: «все ролики берём по очереди»)
    'broadcast_depto': ('broadcast', 'Broadcast', 'depto', 0.621762, 39.219),                        # 1
    'kinetic_kilo': ('kinetic', 'Kinetic', 'kilo', 0.9375, 60.082),                                   # 2
    'radar_quantum': ('radar', 'Radar', 'quantum', 1.0, 55.147),                                      # 3
    'race_militant': ('race', 'Race', 'militant', 0.952381, 29.733),                                  # 4
    'dashboard_too_fast': ('dashboard', 'Dashboard', 'too_fast', 1.061946, 33.576),                   # 5
    'card_two_face': ('card', 'Card', 'two_face', 0.731707, 23.336, 21, dict(team=8, rush=2, hold=5.5, cta=3)),   # 6
    'tape_demons': ('tape', 'Tape', 'demons', 0.869565, 85.438, 16.0, dict(per=1, pre=1.5, hold=4, cta=2.5)),     # 7
    # 20.10 — по трендам шортсов (владелец 20.10: «давай попробуем»): данные — pick.simulate / pick.fact; в очередь VIEWS
    # встают после одобрения превью. Треки — Mixkit (владелец 20.10: «берём»; tools/assets_fetch.py, tracks/mixkit.json)
    'simulate': ('simulate', 'Simulate', 'mx_614', 0.857143, 27.191, 12, dict(intro=8, hold=7, cta=3)),
    'numday': ('numday', 'NumDay', 'mx_318', 0.631579, 19.563, 16, dict(num=8, pre=3, hold=8, cta=4)),
}


LG = {'khl': ('KHL', 'КХЛ'), 'nhl': ('NHL', 'НХЛ')}


def out_dir(league, day):
    return os.environ.get('OUT') or os.path.join(ROOT, 'out', 'reels_daily', '%s-%s' % (league, day))


# Очередь шаблонов (владелец 20.10: «каждый раз другой шаблон, чтобы не повторялись один за одним; когда закончатся все —
# по кругу заново, и так всегда, без исключения»). Шаблон = вид ролика (модуль): 12 разных видов идут подряд без повторов,
# потом круг заново; внутри вида от круга к кругу меняется трек (варианты ниже — в порядке очереди).
VIEWS = [
    ['tape', 'tape_demons'],                                         # «Лента»
    ['jarvis'],                                                      # «Джарвис»
    ['card', 'card_two_face'],                                       # «Карточка»
    ['jewel'],                                                       # «Ювелир»
    ['kinetic', 'kinetic_kilo'],                                     # «Кинетик»
    ['radar_quantum', 'radar'],                                      # «Радар»
    ['race_militant', 'race', 'race_cant_say'],                      # «Гонка»
    ['vhs_two_faced', 'vhs'],                                        # «VHS»
    ['cinema_vampire', 'cinema'],                                    # «Кино»
    ['broadcast_depto', 'broadcast'],                                # «Эфир»
    ['dashboard_too_fast', 'dashboard_doomsday', 'dashboard'],       # «Дашборд»
    ['lineup_slx', 'lineup_kizaru', 'lineup_vace'],                  # «Состав» — в конце круга: 20.10 уже вышли два
]
RING_START = date(2026, 10, 20)
PER_DAY = len(VIEWS)                  # на день — один полный круг: НХЛ места 0–5, КХЛ 6–11


OWNER_PICKS = os.path.join(ROOT, 'team', 'reels_daily', 'owner_picks.json')


def owner_picks(ms):
    """Решения владельца по матчам (team/reels_daily/owner_picks.json, ключ «ГГГГ-ММ-ДД Хозяева — Гости»):
    null — без ролика; {"pick": "…", "odds": 1.95[, "tpl": "broadcast_depto"]} — ролик с прогнозом владельца вместо прогноза
    модели (и, если задан, этим шаблоном из TEMPLATES)."""
    try:
        with open(OWNER_PICKS, encoding='utf-8') as f:
            o = json.load(f)
    except (OSError, ValueError):
        return ms
    out = []
    for m in ms:
        k = '%s %s — %s' % (m['d'][:10], m['h'], m['a'])
        if k not in o:
            out.append(m)
        elif o[k]:
            out.append(dict(m, pick=o[k]['pick'], odds=float(o[k]['odds']), sim=None, fact=None))   # данные модели — не к этому прогнозу
            if o[k].get('tpl') in TEMPLATES:
                out[-1]['tpl_owner'] = o[k]['tpl']
            print('OWNERPICK %s: %s %s' % (k, o[k]['pick'], o[k]['odds']), flush=True)
        else:
            print('OWNERSKIP %s' % k, flush=True)
    return out


# Владелец 22.10: квоты YouTube хватает на ~6 загрузок в сутки (НХЛ 02:00 и КХЛ 02:30 МСК — одни сутки квоты), поэтому
# автозагрузка — только самым ценным матчам; остальные ролики приходят владельцу одним пакетом (pack.py) для ручной загрузки.
YT_SLOTS = {'khl': int(os.environ.get('YT_SLOTS_KHL', '4')), 'nhl': int(os.environ.get('YT_SLOTS_NHL', '2'))}
TOP_CLUBS = {'СКА', 'ЦСКА', 'Спартак', 'Динамо Москва', 'Ак Барс', 'Локомотив', 'Авангард', 'Металлург', 'Трактор',
             'Салават Юлаев', 'Торонто', 'Монреаль', 'Рейнджерс', 'Бостон', 'Эдмонтон', 'Вашингтон', 'Питтсбург',
             'Чикаго', 'Детройт', 'Тампа-Бэй', 'Флорида', 'Колорадо', 'Вегас'}


def yt_priority(ms, league):
    """m['yt'] = True — ролик грузится на YouTube автоматически: прайм-тайм (КХЛ с 18:00 МСК, НХЛ — до 04:00 МСК,
    пока Россия не спит), топ-клубы, затем более уверенный прогноз."""
    def score(m):
        hm = m['d'][11:16]
        prime = hm >= '18:00' if league == 'khl' else hm <= '04:00'
        return (prime, (m['h'] in TOP_CLUBS) + (m['a'] in TOP_CLUBS), m.get('p') or 0)
    for m in ms:
        m['yt'] = False
    for m in sorted(ms, key=score, reverse=True)[:YT_SLOTS.get(league, 3)]:
        m['yt'] = True


def slot(k):
    """Шаблон k-го места сквозной очереди: вид — по кругу, трек вида — по номеру круга."""
    v = VIEWS[k % len(VIEWS)]
    return v[(k // len(VIEWS)) % len(v)]


def assign(matches, day, league='khl'):
    """Шаблон каждому матчу дня: одна сквозная очередь на все дни и обе лиги, соседние ролики — всегда разные виды."""
    k = (date.fromisoformat(day) - RING_START).days * PER_DAY + (6 if league == 'khl' else 0)
    for m in matches:
        m['tpl'] = m.get('tpl_owner') or slot(k)                 # шаблон, выбранный владельцем, — вместо очереди
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
    backup = set()
    if league == 'nhl' and any((x['h'], x['a']) not in pins for x in nxt):
        try:                                        # владелец 20.10: нет матча у Pinnacle — линия DraftKings с ESPN
            import espn
            for k, mk in espn.fetch(day, [x for x in nxt if (x['h'], x['a']) not in pins]).items():
                pins[k] = mk
                backup.add(k)
        except Exception as e:  # noqa: BLE001
            print('ESPNERR %r' % e, flush=True)
    ms = pick.day_picks(games, nxt, pins, fon, league, backup=backup)
    soon = (datetime.now(MSK) + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M')   # уже начавшиеся матчи — без ролика
    ms = [m for m in ms if m['d'] >= soon]
    ms = owner_picks(ms)
    ms.sort(key=lambda m: m['d'])
    assign(ms, day, league)                         # место в очереди — по всему дню, и при ручном запуске части матчей
    only = [x for x in os.environ.get('REELS_ONLY', '').split(',') if x]     # только эти клубы (ручной запуск)
    if only:
        ms = [m for m in ms if m['h'] in only or m['a'] in only]
    if top:
        ms = sorted(ms, key=lambda m: -m['p'])[:top]                                # самые уверенные
    ms.sort(key=lambda m: m['d'])
    yt_priority(ms, league)
    names = sorted({t for m in ms for t in (m['h'], m['a'])})
    stats = (form.khl if league == 'khl' else form.nhl)(games, day, names)
    parts = [list(range(i, min(i + per, len(ms)))) for i in range(0, len(ms), per)]
    yd = (date.fromisoformat(day) - timedelta(days=1)).isoformat()     # вчера со счётом — слайд «Расписание» на сайте
    P = dict(day=day, league=league, matches=ms, stats=stats, parts=parts, skipped=len(nxt) - len(ms),
             all=[dict(d=x['d'], h=x['h'], a=x['a']) for x in sorted(nxt, key=lambda x: x['d'])],
             yday=[dict(d=g['d'], h=g['h'], a=g['a'], sc='%d:%d%s' % (g['hg'], g['ag'], ' ' + g['e'] if g.get('e') else ''))
                   for g in sorted(games, key=lambda g: g['d']) if str(g.get('d', ''))[:10] == yd])
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
    head += ['%s %s — %s · %s · %s%s' % (m['d'][11:16], m['h'], m['a'], m['pick'], ('%.2f' % m['odds']).replace('.', ','),
                                         ' · YouTube авто' if m.get('yt') else '') for m in ms]
    if P['skipped']:
        head.append('Без ролика: %d (нет ставки с кэфом 1,6–2,3 или линии)' % P['skipped'])
    tg_text('\n'.join(head) if ms else 'Шортсы %s на %s: матчей с прогнозом по правилу нет' % (lg, day))
    return P


DATA = {'simulate': ('sim',), 'numday': ('fact',)}     # шаблонам — данные прогноза из plan.json


def reel(m, stats, code):
    mod, cls, key, u, tdrop, *rest = TEMPLATES[m['tpl']]
    d = date.fromisoformat(m['d'][:10])
    when = '%s %s · %s МСК' % (WEEK[d.weekday()], d.strftime('%d.%m'), m['d'][11:16])
    Cls = getattr(importlib.import_module('reels.' + mod), cls)
    line = tuple(m['x1x2']) if m.get('x1x2') else None       # запасная линия (ESPN) — без П1 · Х · П2
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
    kw = dict(kw, **{k: m.get(k) for k in DATA.get(mod, ())})
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
    if not frames and instagram.posted(yt_texts.youtube(m, lg)['description'].split('\n')[0]):
        print('REELSKIP %s — %s: ролик уже выложен (Instagram)' % (m['h'], m['a']), flush=True)
        return
    from reels import intro
    t0 = time.time()
    r, key, start = reel(m, P['stats'], code)
    r.ticker_tag, r.ticker = ticker(P, lg)
    base = os.path.join(out_dir(league, day), '%02d_%s' % (i + 1, m['tpl']))
    if frames:
        r = intro.wrap(r, m['h'], m['a'], code, *ab_lines(m, i))
        print(C.render(r, base + '.mp4', frames=[int(round(float(x) * C.FPS)) for x in frames.split(',')]))
        return
    track = owner_tracks.wav(key)
    if os.environ.get('REELS_TTS') == '1':          # владелец 20.10: озвучка и субтитры (пока по флагу, на пробу)
        import voice
        r, mix = voice.voiced(r, m, TEMPLATES[m['tpl']][0], track, start, base)
        if mix:
            track, start = mix, 0.0
    # владелец 24.10: перед каждым роликом на 1 с — «ПРОГНОЗ НА МАТЧ» и команды; трек — на столько же раньше, дроп на месте
    # владелец 27.10: сравнение заставок — чётные ролики дня А (прогноз и кэф), нечётные Б (вопрос, ответ на дропе)
    r = intro.wrap(r, m['h'], m['a'], code, *ab_lines(m, i))
    start -= getattr(r, 'intro', 0.0)
    C.render(r, base + '.mp4', track=track, start=start, extra_out=base + '_clean.mp4')
    print('REEL %s — %s | %s | заставка %s | трек %s с %.2f с, дроп на %.2f с | %.1f с ролика за %.0f с'
          % (m['h'], m['a'], m['tpl'], ab(i) or '-', key, start, r.drop, r.dur, time.time() - t0), flush=True)
    y = yt_texts.youtube(m, lg)
    cover = cover_for(m, code, base)
    if m.get('yt', True):
        url, note = youtube.upload(base + '.mp4', y['title'], y['description'], y['tags'] + ['tpl_' + m['tpl']],
                                   publish_at=publish_time(P, i))
        tnote = youtube.thumbnail(url, cover) if cover else ''
        note = '\n'.join(x for x in (note, tnote) if x)
    else:
        url, note = None, 'загрузите вручную (автозагрузка — только приоритетным матчам)' if youtube.enabled() else ''
    yt_url, yt_note = url, note
    head = ('YouTube: %s\n%s\n\n' % (url, note)) if url else ('YouTube: %s\n\n' % note) if note else ''
    if instagram.deferred():       # владелец 26.10: в Instagram — по одному днём, по расписанию YouTube (team/reels_daily/ig_queue.py)
        ig, ignote = instagram.queue(base, instagram.caption(m, y, ab(i)), cover, publish_time(P, i), m['d'][:16])
    else:
        ig, ignote = instagram.upload(base + '.mp4', instagram.caption(m, y, ab(i)), cover)
    head += ('Instagram: %s\n\n' % ig) if ig else ('Instagram: %s\n\n' % ignote) if ignote else ''
    with open(base + '.json', 'w', encoding='utf-8') as f:          # для пакета владельцу (pack.py)
        json.dump(dict(i=i, ab=ab(i), d=m['d'], h=m['h'], a=m['a'], lg=lg, video=os.path.basename(base) + '.mp4', yt=yt_url,
                       yt_note=yt_note, ig=ig, title=y['title'], description=y['description']), f, ensure_ascii=False)
    if os.environ.get('REELS_TG_EACH') == '1':                       # прежний режим: каждый ролик отдельно
        tg_reel(base + '.mp4', base + '_clean.mp4', head + yt_texts.block(m, lg), y['title'], cover)


AB_DUR = 1.5                         # заставка сравнения: строк больше — 1,5 с вместо 1 с (у обоих вариантов одинаково)


def ab(i):
    """Вариант заставки ролика i дня (владелец 27.10): 'A' — прогноз и кэф сразу, 'B' — вопрос, ответ на дропе.
    REELS_AB=0 — прежняя заставка «ПРОГНОЗ НА МАТЧ» (None)."""
    if os.environ.get('REELS_AB', '1') == '0':
        return None
    return 'A' if i % 2 == 0 else 'B'


def ask(m):
    """Вопрос без ответа по виду прогноза: тотал матча / тотал команды / исход."""
    from settle import gen
    p = m['pick'].lower()
    if p.startswith('тотал матча'):
        return 'Сколько шайб будет в матче?'
    if p.startswith('тотал'):
        t = next((x for x in (m['h'], m['a']) if gen(x).lower() in p), None)
        if t:
            return 'Сколько шайб у %s?' % gen(t)
    if any(w in p for w in ('победа', 'фора', 'не проиграет', 'ничья')):
        return 'Кто заберёт матч?'
    return 'Какой прогноз на матч?'


def ab_lines(m, i):
    """→ (строки заставки, длительность) для intro.wrap; без сравнения — (None, None)."""
    v = ab(i)
    teams = '%s — %s' % (m['h'], m['a'])
    if v == 'A':
        return [m['pick'], teams, 'кэф ' + ('%.2f' % m['odds']).replace('.', ',')], AB_DUR
    if v == 'B':
        return [ask(m), teams, 'Ответ — в конце'], AB_DUR
    return None, None


SPREAD_FROM, SPREAD_STEP, SPREAD_LEAD = 9, 90, 120     # МСК: с 09:00, шаг 90 мин, не позже чем за 2 ч до матча


def publish_time(P, i):
    """Время выхода ролика на YouTube (UTC) — владелец 20.10: не пачкой ночью, а с интервалами. Ролик i дня выходит
    в 09:00 МСК + i × 90 мин (КХЛ — со сдвигом 45 мин), но не позже чем за 2 ч до начала своего матча; время уже прошло — None (сразу).
    Выключить: REELS_SPREAD=0."""
    if os.environ.get('REELS_SPREAD', '1') == '0':
        return None
    m = P['matches'][i]
    start = datetime.strptime(m['d'][:16], '%Y-%m-%d %H:%M').replace(tzinfo=MSK)
    now = datetime.now(MSK)
    day0 = (start - timedelta(minutes=SPREAD_LEAD)).replace(hour=SPREAD_FROM, minute=0, second=0, microsecond=0)
    if day0 > start - timedelta(minutes=SPREAD_LEAD):
        day0 -= timedelta(days=1)
    off = 45 if P.get('league') == 'khl' else 0          # КХЛ — между роликами НХЛ того же утра
    t = min(day0 + timedelta(minutes=SPREAD_STEP * i + off), start - timedelta(minutes=SPREAD_LEAD))
    if t <= now + timedelta(minutes=20):
        return None
    return t.astimezone(timezone.utc)


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
