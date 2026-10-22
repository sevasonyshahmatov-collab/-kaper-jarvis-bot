# -*- coding: utf-8 -*-
"""Посты для блога на sports.ru (владелец 22.10: «проработаем шаблоны, попробуем писать посты»).
У sports.ru нет API для публикации — пост собирается здесь, приходит владельцу в Telegram (заголовок и текст отдельными
сообщениями, чтобы удобно копировать), владелец вставляет его в редактор блога сам.

Три вида (README рядом):
  match — разбор одного матча: форма команд, 10 000 розыгрышей модели, «цифра дня», прогноз и кэф;
  day   — прогнозы на все матчи дня одной лиги, по абзацу на матч;
  week  — честные итоги недели по постам канала: каждый прогноз со счётом и знаком, сколько зашло.

Данные — plan.json конвейера шортсов (team/reels_daily/make.py plan) и посты канала (team/daily/channel.py).
Правила текстов — как у постов канала (compose.validate): без «Джарвис», букмекеров, промокодов, гарантий и слова «таблица»;
«ставь» не пишем. Запуск:
    python team/sportsru/post.py match out/reels_daily/khl-2026-10-23/plan.json [--team Сибирь]
    python team/sportsru/post.py day   out/reels_daily/khl-2026-10-23/plan.json
    python team/sportsru/post.py week  2026-10-27            # итоги недели, которая закончилась к утру этого понедельника
"""
import json
import os
import random
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in ('team/daily', 'team/picks', 'team/reels_daily', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))

from compose import MONTHS, WD, kef_s, plural, validate  # noqa: E402
from settle import gen  # noqa: E402

TG = 'https://t.me/jarvibet'
WD_ON = ('в понедельник', 'во вторник', 'в среду', 'в четверг', 'в пятницу', 'в субботу', 'в воскресенье')
LG = {'khl': 'КХЛ', 'nhl': 'НХЛ', 'KHL': 'КХЛ', 'NHL': 'НХЛ'}


def day_words(d):
    """date → «23 октября, четверг»."""
    return '%d %s, %s' % (d.day, MONTHS[d.month - 1], WD[d.weekday()])


def pct(x):
    return ('%.0f' % (100 * x)) + '%'


def lower1(s):
    return s if ' не проиграет ' in s else s[0].lower() + s[1:]


def when(m):
    d = date.fromisoformat(m['d'][:10])
    return d, m['d'][11:16]


def form_block(team, st):
    """Абзац формы клуба: место, очки, разница шайб, последние 3 игры."""
    if not st:
        return None
    games = st.get('last3') or []
    lines = ['%s %s %s — %s%s' % ('✅' if g['res'] == 'В' else '❌', g['date'], 'дома' if g['home'] else 'в гостях',
                                   g['opp'], ' ' + g['score']) for g in games]
    head = '%s: %s, %s %s, разница шайб %s%d.' % (
        team, st.get('place') or 'место уточняется', plural(st.get('points', 0), 'очко', 'очка', 'очков'),
        'за ' + plural(st.get('games', 0), 'матч', 'матча', 'матчей'), '+' if st.get('gd', 0) > 0 else '−' if st.get('gd', 0) < 0 else '', abs(st.get('gd', 0)))
    return '\n'.join([head, 'Последние игры:'] + lines)


def sim_line(m):
    s = m.get('sim')
    if not s:
        return None
    top = ', '.join('%d:%d' % (h, a) for h, a, _ in s['top'])
    return ('Модель разыграла матч %s раз. Наш прогноз сыграл в %s розыгрышей. Самые частые счета: %s.'
            % ('{:,}'.format(s['n']).replace(',', ' '), pct(s['hits'] / s['n']), top))


def fact_line(m):
    f = m.get('fact')
    if not f or not f.get('n'):
        return None
    return 'Цифра матча: у %s такое событие было в %d из %d игр сезона.' % (gen(f['team']), f['k'], f['n'])


OPEN = [
    '{wd} {H} играет дома против {A_gen}. Разбираю матч по цифрам: форма, очки и что говорит модель.',
    '{H} и {A} играют {wdl}. Смотрю на форму обеих команд и на расчёт модели.',
    '{wd} матч {H} — {A}. Ниже всё, на чём держится прогноз: последние игры, очки и розыгрыши модели.',
]
CLOSE = [
    'Посмотрим, как сыграет. Итоги — каждое утро в Telegram, и зашедшие, и нет: ' + TG,
    'Свои прогнозы на матч пишите в комментариях. Все прогнозы и честные итоги — в Telegram: ' + TG,
    'Ролик по матчу и прогнозы на остальные игры дня — в Telegram: ' + TG,
]


def match_post(P, m):
    """Разбор матча. → dict(title, body)."""
    lg = LG[P['league']]
    d, hm = when(m)
    rnd = random.Random(m['d'] + m['h'])
    title = '%s — %s: прогноз на матч %d %s %d' % (m['h'], m['a'], d.day, MONTHS[d.month - 1], d.year)
    wdl = '%s, %d %s' % (WD_ON[d.weekday()], d.day, MONTHS[d.month - 1])
    ctx = dict(H=m['h'], A=m['a'], A_gen=gen(m['a']), wd=wdl[0].upper() + wdl[1:] + ',', wdl=wdl)
    x = m.get('x1x2') or []
    line = 'Линия на основное время: П1 %s · Х %s · П2 %s.' % tuple(kef_s(v) for v in x[:3]) if len(x) >= 3 and all(x[:3]) else None
    parts = [
        '%s, %s МСК%s.' % (lg, hm, (', ' + m['arena']) if m.get('arena') else ''),
        rnd.choice(OPEN).format(**ctx),
        line,
        'Форма команд',
        form_block(m['h'], P['stats'].get(m['h'])),
        form_block(m['a'], P['stats'].get(m['a'])),
        'Что говорит модель',
        ' '.join(s for s in (
            'Модель считает вероятность событий по форме команд и сравнивает её с линией. Выбираю самое вероятное событие '
            'с кэфом от 1,6 до 2,3.', sim_line(m), fact_line(m)) if s),
        'Прогноз: %s, кэф %s. Вероятность по модели — %s.' % (lower1(m['pick']), kef_s(m['odds']), pct(m['p'])),
        rnd.choice(CLOSE),
    ]
    return dict(title=title, body=join(parts), tags=[lg, m['h'], m['a'], 'прогнозы'])


def day_post(P):
    """Все матчи дня одной лиги. → dict(title, body)."""
    lg = LG[P['league']]
    ms = sorted(P['matches'], key=lambda m: m['d'])
    if not ms:
        return None
    d = date.fromisoformat(P['day'])
    night = P['league'] == 'nhl'
    title = ('Прогнозы на матчи %s в ночь на %d %s' if night else 'Прогнозы на матчи %s %d %s') % (lg, d.day, MONTHS[d.month - 1])
    parts = ['%s: %s. Ниже по каждому матчу — форма команд и прогноз модели.' % (
        'Ночь на ' + day_words(d) if night else day_words(d).capitalize(),
        plural(len(ms), 'матч с прогнозом', 'матча с прогнозом', 'матчей с прогнозом'))]
    for m in ms:
        st_h, st_a = P['stats'].get(m['h']) or {}, P['stats'].get(m['a']) or {}
        form = lambda st: '-'.join(g['res'] for g in reversed(st.get('last3') or [])) or '—'  # noqa: E731
        parts.append('%s %s — %s' % (m['d'][11:16], m['h'], m['a']))
        parts.append(' '.join(s for s in (
            'Форма за 3 игры (от ранней к последней): %s %s, %s %s.' % (m['h'], form(st_h), m['a'], form(st_a)),
            fact_line(m),
            'Прогноз: %s, кэф %s (по модели %s).' % (lower1(m['pick']), kef_s(m['odds']), pct(m['p']))) if s))
    if P.get('skipped'):
        parts.append('Ещё %s без прогноза: нет события с кэфом 1,6–2,3, которое модель считает самым вероятным.'
                     % plural(P['skipped'], 'матч', 'матча', 'матчей'))
    parts.append('Утром — честные итоги, и зашедшие прогнозы, и нет. Всё в Telegram: ' + TG)
    return dict(title=title, body=join(parts), tags=[lg, 'прогнозы'])


def week_post(monday, rows):
    """Итоги недели. rows — рассчитанные прогнозы канала (morning.settle_rows). → dict(title, body)."""
    import compose
    import settle
    d0, d1 = monday - timedelta(days=7), monday - timedelta(days=1)
    t = compose.tally(rows)
    title = 'Итоги прогнозов за неделю: %d–%d %s' % (d0.day, d1.day, MONTHS[d1.month - 1]) if d0.month == d1.month else \
        'Итоги прогнозов за неделю: %d %s — %d %s' % (d0.day, MONTHS[d0.month - 1], d1.day, MONTHS[d1.month - 1])
    parts = ['Показываю все прогнозы недели — и зашедшие, и нет. Счёт, событие и кэф по каждому.']
    blocks = {}
    for r in sorted(rows, key=lambda r: r['g']['start']):      # раздел «КХЛ · 20 октября» — строки подряд, без пустых
        blocks.setdefault(compose.section(r), []).append('%s %s — %s %s (%s%s)' % (
            {settle.WIN: '✅', settle.LOSS: '❌'}.get(r['res'], '↩️'), r['home'], r['away'], compose.score_s(r['g']), r['bet'],
            ', кэф ' + kef_s(r['kef']) if r.get('kef') else ''))
    parts += ['\n'.join([k] + v) for k, v in blocks.items()]
    tail = 'Итого: зашло %s.' % compose.score_line(t)
    if t.get('units') is not None:
        tail += ' В единицах ставки по кэфам из постов: %s' % compose.units_s(t['units'])
    parts += [tail, 'Новая неделя — новые прогнозы. Каждый день в Telegram: ' + TG]
    return dict(title=title, body=join(parts), tags=['КХЛ', 'НХЛ', 'прогнозы', 'итоги'])


def join(parts):
    return '\n\n'.join(p for p in parts if p)


def best_match(P, team=None):
    """Матч для разбора: по клубу (если задан) или самый уверенный прогноз дня."""
    ms = P['matches']
    if team:
        ms = [m for m in ms if team in (m['h'], m['a'])]
    return max(ms, key=lambda m: m['p']) if ms else None


def check(post):
    """Правила текстов канала; эмодзи можно (знаки ✅/❌ в форме и итогах)."""
    return validate(post['title'] + '\n' + post['body'], emoji=True) if post else ['нет матчей']


def as_messages(kind, post):
    """Для Telegram владельцу: служебная строка, заголовок, текст — тремя сообщениями."""
    errs = check(post)
    head = 'Пост для sports.ru · %s. Скопируйте заголовок и текст в редактор блога; теги: %s.%s' % (
        {'match': 'разбор матча', 'day': 'прогнозы дня', 'week': 'итоги недели'}[kind], ', '.join(post['tags']),
        ('\nПроверьте: ' + '; '.join(errs)) if errs else '')
    return [head, post['title'], post['body']]


def send(msgs):
    """Владельцу в личку бота, как ролики конвейера (TG_BOT_TOKEN, OWNER_CHAT или создатель @jarvibet)."""
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено', flush=True)
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    for t in msgs:
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text=t[:tj.TEXT_MAX], disable_web_page_preview='true'))


def main(argv=None):
    a = [x for x in (argv if argv is not None else sys.argv[1:]) if x != '--send']
    kind = a.pop(0)
    team = None
    if '--team' in a:
        i = a.index('--team')
        team = a[i + 1]
        del a[i:i + 2]
    if kind in ('match', 'day'):
        with open(a[0], encoding='utf-8') as f:
            P = json.load(f)
        post = match_post(P, best_match(P, team)) if kind == 'match' and best_match(P, team) else day_post(P) if kind == 'day' else None
    else:
        import morning
        monday = date.fromisoformat(a[0]) if a else date.today()
        try:
            import channel
            from data import MSK
            t1 = datetime(monday.year, monday.month, monday.day, 8, 0, tzinfo=MSK)
            picks, chan = channel.posts(t1 - timedelta(days=7), t1)
            import data
            found, _ = data.games_for(picks) if picks else ({}, [])
            rows, pending, bad = morning.settle_rows(picks, found)
            for p, why in pending + bad:
                print('WEEKSKIP %s — %s: %s' % (p['home'], p['away'], why), flush=True)
        except Exception as e:  # noqa: BLE001
            print('WEEKERR %r' % e, flush=True)
            rows = []
        post = week_post(monday, rows) if rows else None
    if not post:
        print('SPORTSRU нечего публиковать (нет матчей с прогнозом или итогов)', flush=True)
        return 0
    msgs = as_messages(kind, post)
    out = os.environ.get('OUT')
    if out:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, 'sportsru_%s.txt' % kind), 'w', encoding='utf-8') as f:
            f.write('\n\n-----\n\n'.join(msgs))
    if '--send' in sys.argv:
        send(msgs)
    print('\n\n-----\n\n'.join(msgs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
