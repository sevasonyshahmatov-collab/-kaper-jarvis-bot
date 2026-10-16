# -*- coding: utf-8 -*-
"""Проверка утренних постов без сети: python3 team/daily/test_daily.py [--show]
  1) расчёт ставок совпадает с предикатами team/picks/calc.markets (все ставки конструктора, разные счета, ОТ/Б);
     целые линии — возврат;
  2) INBOX + SENT.md репозитория: какие прогнозы ушли в канал (правки владельца, двойная публикация);
  3) 7 дней подряд на макете API: подача утра и итогов не повторяется в соседние дни и в один день, ни одна фраза
     из банков не повторяется 7 дней, ни одно предложение текста (без цифр и названий) не повторяется 7 дней;
     все посты проходят compose.validate (эмодзи, запретные слова, теги, длина, первая строка без времени матча);
  4) утренний опрос бота (ask.py, morning.py --ask): свои строки «Прогноз: …» обеих лиг → матч, ставка, кэф; непонятные
     и «Динамо» без уточнения — владельцу «не понял»; итоги по отмеченным номерам с правками владельца, недоигранные —
     в итоги следующего утра (и не дважды); выбор из INBOX и из payload; render/team_job.py: заготовка и переменные.
Макет API (mock_api) — тот же вид, что отдают приложение КХЛ и api-web.nhle.com; им же пользуются примеры."""
import os
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'picks')]
os.environ.setdefault('JARVIS_S', '1')

import ask  # noqa: E402
import calc  # noqa: E402
import compose  # noqa: E402
import data  # noqa: E402
import ledger  # noqa: E402
import morning  # noqa: E402
import settle  # noqa: E402
import teams  # noqa: E402
from data import MSK  # noqa: E402

KHL_ID = {v: k for k, v in teams.KHL_IDS.items()}
NHL_AB = {v: k for k, v in teams.NHL_RU.items()}
KHL_TEAMS = sorted(KHL_ID)
NHL_TEAMS = sorted(NHL_AB)


# ---------------------------------------------------------------- макет API

def game(league, start, home, away, hg=None, ag=None, end='', no_outcome=False):
    """start — 'YYYY-MM-DD HH:MM' МСК. Счёт None — матч ещё не сыгран (на момент now — live/future).
    no_outcome=True — НХЛ отдаёт матч в состоянии FINAL без gameOutcome и periodDescriptor (ОТ видно только по голам) —
    так в run 162 матч Чикаго — Виннипег с ОТ посчитали как в основное время."""
    return dict(league=league, start=datetime.strptime(start, '%Y-%m-%d %H:%M').replace(tzinfo=MSK), home=home, away=away,
                hg=hg, ag=ag, end=end, no_outcome=no_outcome)


def _periods(g):
    """Голы по периодам основного времени [(х, г)]×3 под итоговый счёт (ОТ/Б — +1 победителю сверху)."""
    m = min(g['hg'], g['ag'])
    rh, ra = (m, m) if g['end'] else (g['hg'], g['ag'])
    per = [[0, 0], [0, 0], [0, 0]]
    for k in range(rh):
        per[k % 3][0] += 1
    for k in range(ra):
        per[(k + 1) % 3][1] += 1
    return per


def mock_api(games, now, leaders=()):
    """Ответы API на момент now: сыгранные (конец по оценке до now и есть счёт) — finished/OFF, остальные — нет."""
    khl = {'data.json': {'current_stage_id': 1369, 'stages_v2': [{'id': 1369, 'season': '2026/2027', 'title': 'Регулярный чемпионат'}]},
           'events': [], 'details': {}}
    nhl = {}
    for i, g in enumerate(sorted(games, key=lambda x: x['start']), 1):
        done = g['hg'] is not None and morning.est_end(g) <= now
        if g['league'] == 'KHL':
            eid = 900000 + i
            khl['events'].append({'event': {
                'id': eid, 'type_id': 18, 'start_at': int(g['start'].timestamp() * 1000),
                'game_state_key': 'finished' if done else ('in_progress' if g['start'] <= now else 'not_yet_started'),
                'team_a': {'id': KHL_ID[g['home']], 'name': g['home']}, 'team_b': {'id': KHL_ID[g['away']], 'name': g['away']},
                'score': '%d:%d' % (g['hg'], g['ag']) if done else ''}})
            if done:
                per = _periods(g)
                win_h = g['hg'] > g['ag']
                khl['details'][str(eid)] = {'id': eid, 'score': '%d:%d' % (g['hg'], g['ag']), 'scores': {
                    'first_period': '%d:%d' % tuple(per[0]), 'second_period': '%d:%d' % tuple(per[1]),
                    'third_period': '%d:%d' % tuple(per[2]),
                    'overtime': ('1:0' if win_h else '0:1') if g['end'] == 'ОТ' else '0:0',     # как в приложении: «0:0», если ОТ не было
                    'bullitt': ('1:0' if win_h else '0:1') if g['end'] == 'Б' else ''}}
        else:
            day = data.nhl_game_day(g['start'])
            st = ('FINAL' if g.get('no_outcome') else 'OFF') if done else ('LIVE' if g['start'] <= now else 'FUT')
            row = {'id': 2026020000 + i, 'gameType': 2, 'gameState': st,
                   'startTimeUTC': g['start'].astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   'homeTeam': {'abbrev': NHL_AB[g['home']], 'score': g['hg'] if done else None},
                   'awayTeam': {'abbrev': NHL_AB[g['away']], 'score': g['ag'] if done else None}}
            if done:
                hab, aab = NHL_AB[g['home']], NHL_AB[g['away']]
                goals = []
                for n, (x, y) in enumerate(_periods(g), 1):
                    goals += [{'periodDescriptor': {'number': n, 'periodType': 'REG'}, 'teamAbbrev': {'default': hab}}] * x
                    goals += [{'periodDescriptor': {'number': n, 'periodType': 'REG'}, 'teamAbbrev': {'default': aab}}] * y
                if g['end']:
                    n, t = (4, 'OT') if g['end'] == 'ОТ' else (5, 'SO')
                    goals.append({'periodDescriptor': {'number': n, 'periodType': t},
                                  'teamAbbrev': {'default': hab if g['hg'] > g['ag'] else aab}})
                row['goals'] = goals
                if not g.get('no_outcome'):
                    row['gameOutcome'] = {'lastPeriodType': {'ОТ': 'OT', 'Б': 'SO'}.get(g['end'], 'REG')}
                    row['periodDescriptor'] = {'number': {'ОТ': 4, 'Б': 5}.get(g['end'], 3),
                                               'periodType': {'ОТ': 'OT', 'Б': 'SO'}.get(g['end'], 'REG')}
            nhl.setdefault('score/' + day, {'games': []})['games'].append(row)
    nhl['standings/now'] = {'standings': [{'teamAbbrev': {'default': NHL_AB.get(t, t)}, 'leagueSequence': i + 1, 'gamesPlayed': 9}
                                          for i, t in enumerate(leaders)]}
    return {'khl': khl, 'nhl': nhl}


def sent_row(pid, p):
    lg = 'КХЛ' if p['league'] == 'KHL' else 'НХЛ'
    return '| %s | %s | %s — %s, %s | %s | %s | 60,0 %% | тест |' % (
        pid, lg, p['home'], p['away'], p['start'].strftime('%d.%m %H:%M'), p['bet'], compose.kef_s(p['kef']) or '—')


def ledger_texts(picks, published=True):
    """picks — [{pid, league, home, away, start, bet, kef}] → тексты SENT.md и INBOX.md как у бота."""
    sent = ['| Номер | Лига | Матч | Ставка | Кэф | «Что заходит» | Отправлено |', '|---|---|---|---|---|---|---|']
    inbox = []
    for p in picks:
        sent.append(sent_row(p['pid'], p))
        if published:
            ts = p['start'] - timedelta(minutes=90)
            inbox.append('- [x] %s · опубликовано владельцем (по расписанию): %s «%s · %s · %s МСК»' % (
                ts.strftime('%d.%m %H:%M'), p['pid'], 'КХЛ' if p['league'] == 'KHL' else 'НХЛ', compose.dm(p['start']),
                p['start'].strftime('%H:%M')))
    return '\n'.join(sent), '\n'.join(inbox)


# ---------------------------------------------------------------- случайный, но правдоподобный мир для симуляции

KHL_SLOTS = ['12:30', '14:30', '16:30', '17:00', '19:00', '19:00', '19:30', '19:30']
NHL_SLOTS = ['02:00', '02:00', '02:30', '03:00', '03:00', '03:30', '04:00', '05:00', '05:30']
BETS = [('победа {G} в основное время', 'win'), ('итоговая победа {G}', 'fin'), ('{N} не проиграет в основное время', 'dc'),
        ('фора {G} +1,5', 'hc'), ('тотал матча меньше 5,5', 'tu'), ('тотал матча больше 4,5', 'to'),
        ('индивидуальный тотал {G} больше 2,5 в основное время', 'it'), ('тотал матча меньше 6', 'tu6')]


def world(d0, d1, seed=7):
    """Матчи с d0 по d1: КХЛ — по датам МСК, НХЛ — ночи на эти даты; у каждого счёт (сыгран ли — решает mock_api по now)."""
    rnd = random.Random(seed)
    out = []
    d = d0
    while d <= d1:
        wd = d.weekday()
        nk = [5, 6, 4, 7, 6, 8, 7][wd] + rnd.choice([-2, -1, 0, 0, 1])
        nn = [9, 6, 11, 5, 13, 12, 8][wd] + rnd.choice([-3, -1, 0, 2])
        if d.day % 9 == 0:
            nn = 0                                     # бывает: НХЛ не играет
        if d.day % 11 == 0:
            nk = 0
        for lg, n, slots, pool, base in (('KHL', nk, KHL_SLOTS, KHL_TEAMS, d), ('NHL', nn, NHL_SLOTS, NHL_TEAMS, d)):
            tm = rnd.sample(pool, min(len(pool) // 2 * 2, 2 * max(0, n)))
            for k in range(0, len(tm), 2):
                hh = rnd.choice(slots)
                hg, ag = rnd.choice([(3, 2), (2, 4), (1, 0), (4, 1), (2, 3), (5, 2), (1, 3), (3, 3), (2, 2), (0, 2), (6, 3)])
                end = ''
                if hg == ag:
                    end = rnd.choice(['ОТ', 'Б'])
                    hg += rnd.choice([0, 1])
                    ag += 1 if hg == ag else 0
                out.append(game(lg, '%s %s' % (base.isoformat(), hh), tm[k], tm[k + 1], hg, ag, end))
        d += timedelta(days=1)
    return out


def world_picks(games, rnd):
    """Прогнозы на часть матчей (как будто отправлены и опубликованы): номера ММДД-N по дню отправки."""
    picks, cnt = [], {}
    for g in sorted(games, key=lambda x: x['start']):
        if rnd.random() > 0.35:
            continue
        sent_day = g['start'].date() if g['league'] == 'KHL' else (g['start'] - timedelta(days=1)).date()
        cnt[sent_day] = cnt.get(sent_day, 0) + 1
        tpl, _ = rnd.choice(BETS)
        side = rnd.choice([g['home'], g['away']])
        bet = tpl.format(G=settle.gen(side), N=side)
        picks.append(dict(pid='%s-%d' % (sent_day.strftime('%d%m'), cnt[sent_day]), league=g['league'], home=g['home'],
                          away=g['away'], start=g['start'], bet=bet, kef=round(rnd.uniform(1.6, 2.2), 2)))
    return picks


def run_day(d, games, picks, published=True, leaders=(), card=False, out_dir=None, variant=0):
    """Одно утро на макете: → (сообщения, сводка, внутренности build)."""
    now = morning.cutoff(d) + timedelta(minutes=10)
    os.environ['DAILY_NOW'] = now.strftime('%Y-%m-%d %H:%M')
    data.set_mock(mock_api(games, now, leaders))
    sent, inbox = ledger_texts(picks, published)
    led = ledger.Ledger(morning.cutoff(d), inbox=inbox, sent=sent, picks='')
    return morning.build(d, variant=variant, card=card, out_dir=out_dir, led=led)


# ---------------------------------------------------------------- проверки

def test_settle():
    n = 0
    for H, A in (('Спартак', 'ЦСКА'), ('Динамо Москва', 'Динамо Минск'), ('Тампа-Бэй', 'Сиэтл')):
        for mk in calc.markets(H, A):
            for hg, ag, end in ((3, 2, ''), (2, 3, 'ОТ'), (4, 1, ''), (1, 1, ''), (0, 5, ''), (3, 2, 'Б'), (5, 4, ''), (2, 1, ''), (6, 0, '')):
                m = min(hg, ag)
                o = dict(h=m if end else hg, a=m if end else ag, fh=hg, fa=ag)
                want = settle.WIN if mk['f'](o) else settle.LOSS
                got = settle.settle(mk['t'], H, A, dict(hg=hg, ag=ag, end=end))[0]
                assert got == want, (mk['t'], hg, ag, end, want, got)
                n += 1
    g = lambda hg, ag, end='': dict(hg=hg, ag=ag, end=end)        # noqa: E731
    cases = [('тотал меньше 6', 'Лада', 'СКА', g(2, 4), settle.PUSH), ('тотал матча меньше 6', 'Лада', 'СКА', g(2, 3, 'ОТ'), settle.WIN),
             ('тотал матча меньше 6', 'Лада', 'СКА', g(3, 4, 'ОТ'), settle.PUSH),     # осн. время 3:3
             ('тотал матча больше 6,5 с учётом ОТ', 'Лада', 'СКА', g(3, 4, 'ОТ'), settle.WIN),
             ('победа Каролины с форой −1', 'Филадельфия', 'Каролина', g(2, 3), settle.PUSH),
             ('победа Каролины с форой −1', 'Филадельфия', 'Каролина', g(1, 4), settle.WIN),
             ('итоговая победа Торпедо', 'Торпедо', 'Динамо Москва', g(3, 2, 'Б'), settle.WIN),
             ('победа Торпедо', 'Торпедо', 'Динамо Москва', g(3, 2, 'Б'), settle.LOSS),
             ('Айлендерс не проиграют в основное время', 'Оттава', 'Айлендерс', g(3, 2, 'ОТ'), settle.WIN),
             ('П1 и тотал меньше 5,5', 'Локомотив', 'Динамо Минск', g(6, 1), settle.LOSS),
             ('индивидуальный тотал Сиэтла больше 2,5 (по основному времени)', 'Филадельфия', 'Сиэтл', g(2, 3, 'Б'), settle.LOSS),
             ('ИТБ Барыса больше 2,5', 'Барыс', 'Авангард', g(5, 1), settle.WIN)]
    for bet, h, a, sc, want in cases:
        got = settle.settle(bet, h, a, sc)[0]
        assert got == want, (bet, sc, want, got)
    print('расчёт ставок: %d сверок с calc.markets и %d случаев с возвратом/ОТ — ок' % (n, len(cases)))


def test_repo_ledger():
    d = date(2026, 10, 16)
    led = ledger.Ledger(morning.cutoff(d))
    c0, c1 = morning.cutoff(d - timedelta(days=1)), morning.cutoff(d)
    pub, notes = led.published(c0 - timedelta(hours=12), c1)
    ids = [p['pid'] for p in pub if p.get('pid')]
    print('репозиторий, утро 16.10: опубликовано %s' % ', '.join(ids))
    by = {p['pid']: p for p in pub if p.get('pid')}
    if '1510-15' in by:
        assert by['1510-15']['bet'] == 'тотал матча меньше 5,5' and by['1510-15']['kef'] == 1.78, by['1510-15']
    for n in notes:
        print('  заметка:', n)


def test_run162():
    """Утро 16.10 как в run 162: Чикаго — Виннипег закончился в ОТ, а НХЛ отдал его как FINAL без gameOutcome;
    1510-2 и 1510-15 — один матч Северсталь — Локомотив. Ждём: 5 прогнозов (1510-1 Лада — СКА на месте),
    Виннипег «в основное время» — минус, Северсталь — один раз."""
    d = date(2026, 10, 16)
    G = [game('KHL', '2026-10-15 18:00', 'Лада', 'СКА', 2, 4), game('KHL', '2026-10-15 19:00', 'Северсталь', 'Локомотив', 5, 2),
         game('NHL', '2026-10-16 02:00', 'Тампа-Бэй', 'Сиэтл', 4, 3, 'ОТ'), game('NHL', '2026-10-16 03:00', 'Миннесота', 'Сент-Луис', 5, 4),
         game('NHL', '2026-10-16 03:00', 'Чикаго', 'Виннипег', 3, 4, 'ОТ', no_outcome=True),
         game('NHL', '2026-10-16 04:00', 'Эдмонтон', 'Юта', 5, 2), game('NHL', '2026-10-16 05:00', 'Вегас', 'Калгари', 3, 2)]
    now = morning.cutoff(d) + timedelta(minutes=5)
    os.environ['DAILY_NOW'] = now.strftime('%Y-%m-%d %H:%M')
    data.set_mock(mock_api(G, now))
    msgs, s, inner = morning.build(d, card=False, recap_only=True, led=ledger.Ledger(morning.cutoff(d)))
    rows = {r['home']: r for r in inner['rd']['rows']}
    assert sorted(r.get('pid') for r in rows.values()) == ['1510-1', '1510-10', '1510-12', '1510-15', '1510-6'], rows.keys()
    assert rows['Чикаго']['g']['end'] == 'ОТ' and rows['Чикаго']['res'] == settle.LOSS, rows['Чикаго']
    assert rows['Тампа-Бэй']['res'] == settle.WIN and rows['Северсталь']['res'] == settle.LOSS
    print('run 162 (16.10): 5 прогнозов, ОТ у Чикаго — Виннипег найден по голам, «победа Виннипега в осн. время» — минус — ок')
    return msgs, inner


def sentences(text):
    plain = re.sub(r'<[^>]+>', '', text)
    for t in KHL_TEAMS + NHL_TEAMS + [settle.gen(x) for x in KHL_TEAMS + NHL_TEAMS]:
        plain = plain.replace(t, 'К')
    plain = re.sub(r'\d+([:,.]\d+)?', '0', plain)
    out = []
    for line in plain.split('\n'):
        if line.startswith('#') or line[:1] in '✅❌↩' or re.match(r'^0 К — К|^(КХЛ|НХЛ)( ·|$)|^Главное:', line) or \
                re.search(r'→|ЗАШЛО|МИНУС|ВОЗВРАТ', line) or \
                ' — К' in line[:40] and re.search(r'\b0\b', line):
            continue                                      # строки матчей, подзаголовки лиг, табло и хэштеги — данные, а не фразы
        out += [s.strip() for s in re.split(r'(?<=[.!?])(?<!ед\.)\s+', line) if len(s.strip()) > 12]
    return out


def simulate(d0, days=7, show=False, seed=11):
    games = world(d0 - timedelta(days=9), d0 + timedelta(days=days + 1), seed)
    picks = world_picks([g for g in games if g['start'] < morning.cutoff(d0 + timedelta(days=days))], random.Random(seed))
    eng = morning.engine()
    seen_bank, seen_sent, prev, problems, report = {}, {}, None, [], []
    for k in range(days):
        d = d0 + timedelta(days=k)
        msgs, summary, inner = run_day(d, games, picks)
        plan = inner['plan']
        lay = (plan.layout('m'), 'шаблон')
        if prev:
            assert lay[0] != prev[0], 'макет утра повторился день в день: %s %s %s' % (d, prev, lay)
        prev = lay
        rec = inner['recap']
        if rec:                                           # строк прогнозов столько же, сколько в строке «ставили на N»
            n_lines = sum(1 for x in rec['text'].split('\n') if x and x[0] in '✅❌↩')
            assert n_lines == rec['tally']['n'] == len(inner['rd']['rows']), (d, n_lines, rec['tally'])
        for bank, items in plan.picks.items():
            if bank.endswith('.layout') or bank == 'addr':
                continue
            for it in items:
                last = seen_bank.get((bank, it))
                w = eng.banks[bank].window
                assert last is None or (d - last).days >= min(7, w), 'фраза повторилась: %s «%s» %s и %s' % (bank, it, last, d)
                seen_bank[(bank, it)] = d
        for m in msgs[1:]:
            if m.get('buttons') != 'post':
                continue
            errs = compose.validate(m['text'], photo=m['type'] == 'photo')
            problems += ['%s %s: %s' % (d, m['pid'], e) for e in errs]
            for s in sentences(m['text']):
                last = seen_sent.get(s)
                if last and last[0] != d and (d - last[0]).days < 7:
                    problems.append('%s %s: предложение повторилось (было %s %s): «%s»' % (d, m['pid'], last[0], last[1], s))
                seen_sent.setdefault(s, (d, m['pid']))
        report.append((d, summary, msgs))
        if show:
            print('\n######## %s (%s): утро «%s», прогнозов в итогах %d' % (d, compose.WD[d.weekday()], lay[0], summary['picks']))
            for m in msgs:
                print('--- %s ---\n%s' % (m.get('pid', 'владельцу'), m['text']))
    assert not problems, '\n'.join(problems)
    print('симуляция %s … %s: макет утра не повторяется подряд, строки прогнозов = «ставили на N», фразы банков и '
          'предложения — без повторов 7 дней, проверки постов — ок'
          % (d0, d0 + timedelta(days=days - 1)))
    return report


# ---------------------------------------------------------------- утренний опрос «на что ставили»

ASK_GAMES = [
    game('KHL', '2026-10-15 17:00', 'Салават Юлаев', 'Шанхайские Драконы', 4, 1), game('KHL', '2026-10-15 17:00', 'Трактор', 'Металлург', 2, 3, 'Б'),
    game('KHL', '2026-10-15 18:00', 'Лада', 'СКА', 2, 4), game('KHL', '2026-10-15 19:00', 'Северсталь', 'Локомотив', 5, 2),
    game('KHL', '2026-10-15 19:30', 'Динамо Москва', 'Спартак', 3, 2, 'ОТ'), game('KHL', '2026-10-15 19:30', 'Динамо Минск', 'Ак Барс', 1, 3),
    game('NHL', '2026-10-16 02:00', 'Тампа-Бэй', 'Сиэтл', 4, 3, 'ОТ'), game('NHL', '2026-10-16 02:00', 'Нью-Джерси', 'Рейнджерс', 2, 3),
    game('NHL', '2026-10-16 02:30', 'Питтсбург', 'Филадельфия', 1, 4), game('NHL', '2026-10-16 03:00', 'Чикаго', 'Виннипег', 3, 4, 'ОТ'),
    game('NHL', '2026-10-16 04:00', 'Эдмонтон', 'Юта', 5, 2), game('NHL', '2026-10-16 05:00', 'Вегас', 'Калгари', 3, 2),
    game('KHL', '2026-10-16 16:30', 'Авангард', 'Автомобилист', 1, 2), game('KHL', '2026-10-16 19:00', 'Нефтехимик', 'Сибирь', 3, 1),
    game('NHL', '2026-10-17 02:00', 'Бостон', 'Баффало', 2, 5),
]

# строка владельца → (хозяева матча, ставка в итогах, кэф) или (None, начало причины «не понял»)
FREE_CASES = [
    ('Прогноз: победа СКА в основное время, кэф 1,85', 'Лада', 'победа СКА в основное время', 1.85),
    ('Прогноз: Лада — СКА П2 1.85', 'Лада', 'победа СКА в основное время', 1.85),
    ('прогноз: тотал больше 5,5 в матче Вегас — Калгари 1.66', 'Вегас', 'тотал матча больше 5,5', 1.66),
    ('Прогноз: фора Сиэтла +1,5', 'Тампа-Бэй', 'фора Сиэтла +1,5', None),
    ('Прогноз: Тампа-Бэй — Сиэтл Ф2(+1.5) @1.83', 'Тампа-Бэй', 'фора Сиэтла +1,5', 1.83),
    ('Прогноз: ИТБ Юты 2,5', 'Эдмонтон', 'индивидуальный тотал Юты больше 2,5', None),
    ('Прогноз: Рейнджерс не проиграют, коэф. 1,77', 'Нью-Джерси', 'Рейнджерс не проиграет в основное время', 1.77),
    ('Прогноз: итоговая победа Виннипега 2.21', 'Чикаго', 'итоговая победа Виннипега', 2.21),
    ('Прогноз: Салават тотал меньше 4,5', 'Салават Юлаев', 'тотал матча меньше 4,5', None),
    ('Прогноз: победа Трактора с учётом ОТ кф 2,10', 'Трактор', 'итоговая победа Трактора', 2.1),
    ('Прогноз: Динамо Мн — Ак Барс ТМ 5', 'Динамо Минск', 'тотал матча меньше 5', None),
    ('Прогноз: Питсбург Филадельфия П1 и ТБ 4,5', 'Питтсбург', 'победа Питтсбурга в основное время и тотал матча больше 4,5', None),
    ('Прогноз: Динамо — Спартак П1', 'Динамо Москва', 'победа Динамо Москва в основное время', None),
    ('Прогноз: Динамо Москва - Спартак X2 кэф 1.9', 'Динамо Москва', 'Спартак не проиграет в основное время', 1.9),
    ('Прогноз: ставка на Ладу с форой +1,5', 'Лада', 'фора Лады +1,5', None),
    ('Прогноз: победа Сиэтла над Тампой 2,4', 'Тампа-Бэй', 'победа Сиэтла в основное время', 2.4),
    ('Прогноз: тотал меньше 6 Северсталь Локомотив', 'Северсталь', 'тотал матча меньше 6', None),
    ('Прогноз: победа Динамо', None, 'непонятно, какая команда: Динамо Минск или Динамо Москва'),
    ('Прогноз: победа Бостона', None, 'вчера не играли: Бостон'),
    ('Прогноз: что-то хорошее', None, 'не нашёл команду'),
    ('Прогноз: СКА фора -1,25', None, 'ставка: азиатская линия'),
    ('Прогноз: Вегас нормально сыграет', None, 'ставка: не понял ставку'),
]


def ask_mock(now):
    os.environ['DAILY_NOW'] = now
    data.set_mock(mock_api(ASK_GAMES, datetime.strptime(now, '%Y-%m-%d %H:%M').replace(tzinfo=MSK)))


def test_ask_free():
    ask_mock('2026-10-16 05:10')
    games, errs = ask.window_games(date(2026, 10, 16))
    assert not errs and len(games) == 12, (errs, [(g['home'], g['start']) for g in games])   # 16.10 16:30 и позже — не вчера
    for case in FREE_CASES:
        line, home = case[0], case[1]
        p, why = ask.parse_line(line, games)
        if home is None:
            assert p is None and why.startswith(case[2]), (line, p, why)
            continue
        assert p, (line, why)
        assert (p['home'], p['bet'], p['kef']) == (home, case[2], case[3]), (line, p['home'], p['bet'], p['kef'])
        legs = settle.parse(p['bet'], p['home'], p['away'])                     # форма для поста разбирается так же
        assert legs == settle.parse(p['bet'], p['home'], p['away']) and p['league'] in ('KHL', 'NHL')
    ok, bad = ask.parse_free([c[0] for c in FREE_CASES] + ['Прогноз:   '], games)
    assert len(ok) == sum(1 for c in FREE_CASES if c[1]) and len(bad) == sum(1 for c in FREE_CASES if not c[1])
    # только одно Динамо играло вчера — «Динамо» без уточнения понятно
    one = [g for g in games if g['home'] != 'Динамо Минск']
    p, why = ask.parse_line('Прогноз: победа Динамо', one)
    assert p and p['home'] == 'Динамо Москва' and p['bet'] == 'победа Динамо Москва в основное время', (p, why)
    print('свои строки «Прогноз: …»: %d формулировок КХЛ и НХЛ — матч, ставка, кэф; %d непонятных (в т. ч. «Динамо» при двух '
          'Динамо) — владельцу «не понял» — ок' % (sum(1 for c in FREE_CASES if c[1]), sum(1 for c in FREE_CASES if not c[1])))


ASK_SENT = [dict(pid='1510-1', league='KHL', home='Лада', away='СКА', start=game('KHL', '2026-10-15 18:00', '', '')['start'],
                 bet='победа СКА в осн. время', kef=1.64),
            dict(pid='1510-2', league='KHL', home='Северсталь', away='Локомотив', start=game('KHL', '2026-10-15 19:00', '', '')['start'],
                 bet='тотал матча меньше 4,5', kef=2.05),
            dict(pid='1510-6', league='NHL', home='Тампа-Бэй', away='Сиэтл', start=game('NHL', '2026-10-16 02:00', '', '')['start'],
                 bet='фора Сиэтла +1,5', kef=1.83),
            dict(pid='1510-13', league='NHL', home='Эдмонтон', away='Юта', start=game('NHL', '2026-10-16 04:00', '', '')['start'],
                 bet='индивидуальный тотал Юты больше 2,5 в основное время', kef=1.62),
            dict(pid='1610-2', league='KHL', home='Авангард', away='Автомобилист', start=game('KHL', '2026-10-16 16:30', '', '')['start'],
                 bet='Автомобилист не проиграет в основное время', kef=1.71)]


def test_ask_recap():
    sent, _ = ledger_texts(ASK_SENT, published=False)
    inbox = ['- [x] 15.10 12:00 · правка владельца в боте: 1510-1 — новый текст поста; Прогноз: победа СКА в осн. время; Кэф: 1,70',
             '- [x] 16.10 00:30 · опубликовано владельцем (по расписанию): 1510-6 «НХЛ · 16 октября · 02:00 МСК»']
    d = date(2026, 10, 16)
    env = dict(RECAP_DAY='2026-10-16', RECAP_PIDS='1510-1,1510-6,1510-13,1599-9', RECAP_AT='2026-10-16 05:10',
               RECAP_FREE='["Прогноз: победа Трактора с учётом ОТ кф 2,10", "Прогноз: победа Динамо", "Прогноз: Бостон молодцы"]')
    led = ledger.Ledger(morning.cutoff(d), inbox='\n'.join(inbox), sent=sent, picks='')
    sel = ask.selection(d, led.inbox_text, env=env)
    assert sel['src'] == 'payload' and sel['pids'] == ['1510-1', '1510-6', '1510-13', '1599-9'] and len(sel['free']) == 3
    ask_mock('2026-10-16 05:12')
    msgs, summary, inner = morning.build(d, card=False, led=led, recap_only=True, sel=sel)
    rd = inner['rd']
    got = {(r.get('pid') or 'свой', r['home']): r for r in rd['rows']}
    assert sorted(got) == [('1510-1', 'Лада'), ('1510-6', 'Тампа-Бэй'), ('свой', 'Трактор')], sorted(got)
    assert got[('1510-1', 'Лада')]['kef'] == 1.70 and got[('1510-1', 'Лада')]['res'] == settle.WIN       # правка владельца
    assert got[('1510-6', 'Тампа-Бэй')]['res'] == settle.WIN and got[('свой', 'Трактор')]['res'] == settle.LOSS
    assert [p['pid'] for p in rd['carry']] == ['1510-13']                                              # Эдмонтон ещё играет
    rec = inner['recap']['text']
    assert sum(1 for x in rec.split('\n') if x and x[0] in '✅❌↩') == 3 and '(итоговая победа Трактора)' in rec, rec
    intro = msgs[0]['text']
    for want in ('по вашему выбору', 'Источник: ваш выбор в утреннем опросе (16.10 05:10) — свой, 1510-1, 1510-6',
                 'Свой: «Прогноз: победа Трактора с учётом ОТ кф 2,10» → Трактор — Металлург, итоговая победа Трактора, кэф 2,10',
                 'не понял: «Прогноз: победа Динамо» — непонятно, какая команда', 'не понял: «Прогноз: Бостон молодцы»',
                 'В завтрашние итоги: Эдмонтон — Юта (1510-13', '1599-9 нет в SENT.md'):
        assert want in intro, (want, intro)
    assert [m.get('pid') for m in msgs] == [None, '1610-r1'] and all(m.get('buttons') == 'post' for m in msgs[1:])
    # утро 17.10: выбор из INBOX (без payload) — Эдмонтон из вчерашнего опроса доигран и входит; Лада — СКА второй раз не входит
    inbox += ['- [x] 16.10 05:10 · итоги ставок 16.10: выбрано 1510-1, 1510-6, 1510-13; свои: "Прогноз: победа Трактора с учётом ОТ кф 2,10"',
              '- [x] 17.10 05:20 · итоги ставок 17.10: выбрано 1610-2']
    d2 = date(2026, 10, 17)
    led2 = ledger.Ledger(morning.cutoff(d2), inbox='\n'.join(inbox), sent=sent, picks='')
    sel2 = ask.selection(d2, led2.inbox_text, env={})
    assert sel2['src'] == 'inbox' and sel2['pids'] == ['1610-2'] and sel2['at'].strftime('%d.%m %H:%M') == '17.10 05:20'
    ask_mock('2026-10-17 05:22')
    msgs2, _, inner2 = morning.build(d2, card=False, led=led2, recap_only=True, sel=sel2)
    got2 = sorted((r['pid'], r['res']) for r in inner2['rd']['rows'])
    assert got2 == [('1510-13', settle.LOSS), ('1610-2', settle.WIN)], got2
    assert 'Из вчерашнего опроса (доигрались позже): Эдмонтон — Юта' in msgs2[0]['text'], msgs2[0]['text']
    # «Сегодня без итогов» и разбор строки INBOX
    sels = ask.parse_selections('- [x] 18.10 05:30 · итоги ставок 18.10: сегодня без итогов\n' + '\n'.join(inbox), datetime(2026, 10, 18, tzinfo=MSK))
    assert sels[date(2026, 10, 18)]['none'] and sels[date(2026, 10, 16)]['free'] == ['Прогноз: победа Трактора с учётом ОТ кф 2,10']
    print('итоги по выбору владельца: номера с правкой кэфа, свой прогноз, «не понял», Эдмонтон (ещё играл в 05:10) — в итогах '
          '17.10 один раз; выбор из payload и из INBOX — ок')


def test_team_job_ask():
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))
    import team_job
    env = team_job.recap_env({'kind': 'team', 'job': 'team/out/2026-10-16/recap_ask.json', 'day': '2026-10-16', 'at': '2026-10-16 05:10',
                              'pids': ['1510-1', '1510-6', 'x; rm -rf /'], 'free': ['Прогноз: победа СКА\nвторая строка', ' ']})
    assert env == {'RECAP_DAY': '2026-10-16', 'RECAP_PIDS': '1510-1,1510-6', 'RECAP_AT': '2026-10-16 05:10',
                   'RECAP_FREE': '["Прогноз: победа СКА вторая строка"]'}, env
    assert team_job.recap_env({'job': 'team/out/2026-10-16/morning.json'}) == {}
    job = 'team/out/2099-01-02/recap_ask.json'
    path = os.path.join(team_job.ROOT, job)
    try:
        assert team_job.from_template(job) and not team_job.from_template(job)        # второй раз — уже есть
        import json
        with open(path, encoding='utf-8') as f:
            j = json.load(f)
        assert j['day'] == '2099-01-02' and j['make'] == ['team/daily/morning.py 2099-01-02 --ask --recap-only --no-wait '
                                                          '--job-file team/out/2099-01-02/recap_ask.json'], j
        assert not team_job.from_template('team/out/2099-01-02/../x.json') and not team_job.from_template('team/out/2099-01-02/nope.json')
    finally:
        if os.path.exists(path):
            os.remove(path)
            os.rmdir(os.path.dirname(path))
    print('team_job: задание из заготовки team/daily/jobs/recap_ask.json, выбор владельца → RECAP_* (только проверенное) — ок')


if __name__ == '__main__':
    test_ask_free()
    test_ask_recap()
    test_team_job_ask()
    test_settle()
    test_repo_ledger()
    test_run162()
    simulate(date(2026, 10, 17), 7, show='--show' in sys.argv)
    simulate(date(2026, 11, 2), 7, seed=5)
