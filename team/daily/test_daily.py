# -*- coding: utf-8 -*-
"""Проверка утренних постов без сети: python3 team/daily/test_daily.py [--show]
  1) расчёт ставок совпадает с предикатами team/picks/calc.markets (все ставки конструктора, разные счета, ОТ/Б);
     целые линии — возврат;
  2) INBOX + SENT.md репозитория: какие прогнозы ушли в канал (правки владельца, двойная публикация);
  3) 7 дней подряд на макете API: подача утра и итогов не повторяется в соседние дни и в один день, ни одна фраза
     из банков не повторяется 7 дней, ни одно предложение текста (без цифр и названий) не повторяется 7 дней;
     все посты проходят compose.validate (эмодзи, запретные слова, теги, длина, первая строка без времени матча).
Макет API (mock_api) — тот же вид, что отдают приложение КХЛ и api-web.nhle.com; им же пользуются примеры."""
import os
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'picks')]
os.environ.setdefault('JARVIS_S', '1')

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


if __name__ == '__main__':
    test_settle()
    test_repo_ledger()
    test_run162()
    simulate(date(2026, 10, 17), 7, show='--show' in sys.argv)
    simulate(date(2026, 11, 2), 7, seed=5)
