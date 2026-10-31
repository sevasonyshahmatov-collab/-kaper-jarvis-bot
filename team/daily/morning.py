# -*- coding: utf-8 -*-
"""Утренние посты владельцу (team/daily/README.md): «Начало игрового дня» и «Итоги вчерашних ставок», каждый — с кнопками
«Опубликовать» / «Редактировать» / «Не надо», перед ними — служебная строка владельцу.

  python3 team/daily/morning.py --job 2026-10-16        заготовка задания team/out/2026-10-16/morning.json
  python3 team/daily/morning.py 2026-10-16              (make задания, в Actions) данные → посты → сообщения в то же задание
  python3 team/daily/morning.py 2026-10-16 --dry        то же без записи в задание: тексты в консоль
  python3 team/daily/morning.py --history 2026-10-16    какие подачи и фразы выпали за 7 дней до даты (без сети)
  ключи: --variant N — другой вариант текстов этого дня; --no-card — итоги без баннера; --recap-only — только итоги;
         --no-wait — не ждать CUTOFF+5 мин; --job-file — куда писать сообщения (с --job: --name morning2 → morning2.json)

Номера постов — ММДД-m1 (утро) и ММДД-r1 (итоги; баннер отдельно, если подпись не влезла, — ММДД-r2): бот принимает
любой номер без «|» (tm|pub|<номер>), а буква не попадает под ММДД-N, по которому check.py --next считает номера
прогнозов, и под ММДД-N, по которому итоги ищут опубликованные прогнозы в INBOX.

Итоги за утро D — прогнозы, матчи которых закончились (по оценке: начало + 2:30, ОТ +0:15, буллиты +0:25) между
CUTOFF дня D−1 и CUTOFF дня D (06:00 МСК; другое — переменная DAILY_CUTOFF=ЧЧ:ММ). Матч НХЛ, что доигрывается после
CUTOFF (обычно начало в 04:00 и позже), уходит в итоги следующего утра — так каждый прогноз попадает в итоги ровно один
раз, а повторный запуск дня даёт то же самое. Запущено раньше CUTOFF+5 мин — в Actions ждёт (не дольше 35 мин).

--ask — итоги по выбору владельца из утреннего опроса бота (team/daily/ask.py): отмеченные номера (SENT.md с правками
из INBOX) и свои строки «Прогноз: …». Граница — момент его ответа (RECAP_AT, иначе время строки «итоги ставок» в INBOX):
в итоги — матчи, которые к этому моменту закончились (по той же оценке конца); остальные выбранные — в итоги следующего
утра (берутся из вчерашнего выбора). Задание — team/daily/jobs/recap_ask.json (render/team_job.py создаёт его сам).
Опрос с 16.10 не используется (решение владельца), режим оставлен для ручного перезапуска.

Источник итогов по умолчанию (--source channel, решение владельца 16.10) — сам канал: посты-прогнозы с публичной ленты
t.me/s/jarvibet (team/daily/channel.py) на матчи с началом с 08:00 вчера до 08:00 сегодня (МСК), текст канала — окончательный
(с правками владельца), один матч в двух постах — последний пост. Лента не прочиталась — запасной источник: записи бота
(INBOX «опубликовано владельцем» + SENT.md) на те же матчи; какой источник взят — во вступлении владельцу. В Actions ждёт,
пока по оценке доиграет последний матч (не дольше 35 мин). --source ledger — прежний режим (INBOX + SENT.md, граница CUTOFF).
Бот запускает сам, без опроса: 06:00 МСК — team/daily/jobs/morning_greet.json (--greet-only: только «Начало игрового дня»),
08:30 МСК — team/daily/jobs/recap_auto.json (--recap-only: итоги из канала).
"""
import argparse
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [HERE, os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')]

import ask  # noqa: E402
import channel  # noqa: E402
import compose  # noqa: E402
import data  # noqa: E402
import ledger  # noqa: E402
import settle  # noqa: E402
import texts  # noqa: E402
import variety  # noqa: E402
from data import MSK  # noqa: E402

CUTOFF = tuple(int(x) for x in os.environ.get('DAILY_CUTOFF', '06:00').split(':'))   # МСК: граница «суток» для итогов
WAIT_MAX_MIN = 35                      # запустили раньше CUTOFF+5 мин — подождать (в Actions), но не дольше
GAME_LEN = timedelta(minutes=150)
EXTRA = {'ОТ': timedelta(minutes=15), 'Б': timedelta(minutes=25)}


def cutoff(d):
    return datetime(d.year, d.month, d.day, CUTOFF[0], CUTOFF[1], tzinfo=MSK)


def est_end(g):
    return g['start'] + GAME_LEN + EXTRA.get(g.get('end') or '', timedelta(0))


def mmdd(d):
    return d.strftime('%d%m')


def job_path(d):
    return os.path.join(ROOT, 'team', 'out', d.isoformat(), 'morning.json')


_ENGINE = None


def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = variety.Engine(texts.banks())
    return _ENGINE


# ---------------------------------------------------------------- прогнозы → расчёт

def settle_rows(picks, found):
    """→ (рассчитанные, не доиграны/нет счёта, не разобрал ставку)."""
    rows, pending, bad = [], [], []
    for p in picks:
        g = data.match_game(found, p)
        if not g:
            pending.append((p, 'матч не найден в данных лиги'))
            continue
        if g['state'] != 'final':
            pending.append((p, 'перенесён' if g['state'] == 'off' else 'не доигран'))
            continue
        try:
            res, legs, why = settle.settle(p['bet'], p['home'], p['away'], g)
        except ValueError as e:
            bad.append((p, str(e)))
            continue
        leg_res = [settle.settle_leg(x, g) for x in legs]
        rows.append(dict(p, g=g, res=res, legs=legs, why=why, short=settle.short(legs, p['home'], p['away']),
                         leg_push=len(legs) > 1 and settle.PUSH in leg_res))
    return rows, pending, bad


def recap_data(d, led):
    """Прогнозы для итогов утра d и недели. → dict(rows, week, src, notes, pending, bad, carry)."""
    c0, c1 = cutoff(d - timedelta(days=1)), cutoff(d)
    monday = (d - timedelta(days=1)) - timedelta(days=(d - timedelta(days=1)).weekday())
    w0 = cutoff(monday)
    span0 = min(c0, w0) - timedelta(hours=12)            # начало матча — не раньше, чем за полсуток до окна
    pub, notes = led.published(span0, c1, note_from=c0 - timedelta(hours=3))
    src = 'inbox'
    in_day = lambda r: c0 <= est_end(r['g']) < c1                        # noqa: E731

    def split(picks):
        found, errs_ = data.games_for(picks) if picks else ({}, [])
        rows_all_, pending_, bad_ = settle_rows(picks, found)
        # не доигран и по оценке закончится после CUTOFF — войдёт в итоги завтра; раньше — владельцу «не вошёл»
        carry_ = [p for p, why in pending_ if why == 'не доигран' and p['start'] + GAME_LEN >= c1]
        pending_ = [(p, why) for p, why in pending_ if p['start'] < c1 and p['start'] + GAME_LEN >= c0]
        bad_ = [(p, why) for p, why in bad_ if c0 - timedelta(hours=12) <= p['start'] < c1]
        return rows_all_, pending_, bad_, carry_, errs_

    rows_all, pending, bad, carry, errs = split(pub)
    rows = [r for r in rows_all if in_day(r)]
    week = [r for r in rows_all if w0 <= est_end(r['g']) < c1]
    if not rows and not pending and not bad:          # из опубликованного на эти сутки — ничего: берём отправленные владельцу
        sent = led.sent_only(c0 - timedelta(hours=12), c1)
        if sent:
            r2, p2, b2, c2, e2 = split(sent)
            if [r for r in r2 if in_day(r)] or p2:
                src, week, rows_all = 'sent', None, r2
                rows, pending, bad, carry, errs = [r for r in r2 if in_day(r)], p2, b2, c2, errs + e2
    late = [r for r in rows_all if est_end(r['g']) >= c1]                # закончились позже CUTOFF — в завтрашние итоги
    rows.sort(key=lambda r: r['g']['start'])                             # по времени: ночь НХЛ, день КХЛ, следующая ночь
    if week is not None:
        week.sort(key=lambda r: r['g']['start'])
    return dict(rows=rows, week=week, src=src, notes=notes + errs, pending=pending, bad=bad, carry=carry, late=late)


def recap_ask_data(d, led, sel):
    """Итоги по выбору владельца (утренний опрос). → dict как у recap_data + ask: свои строки, «не понял», перенос."""
    at = sel['at']
    picks, notes = led.chosen(sel['pids'])
    games, gerr = ask.window_games(d) if sel['free'] else ([], [])
    free, unparsed = ask.parse_free(sel['free'], games)
    picks += free
    prev = ask.selection(d - timedelta(days=1), led.inbox_text, env={})   # вчерашний выбор: что тогда ещё не доиграли
    prev_picks = []
    if prev and not prev['none']:
        pp, _ = led.chosen(prev['pids'])
        if prev['free']:
            g2, _ = ask.window_games(d - timedelta(days=1))
            pp += ask.parse_free(prev['free'], g2)[0]
        mine = {(p['league'], p['home'], p['away'], p['start'].date()) for p in picks}
        prev_picks = [dict(p, carried=True) for p in pp if (p['league'], p['home'], p['away'], p['start'].date()) not in mine]
    allp = picks + prev_picks
    found, errs = data.games_for(allp) if allp else ({}, [])
    rows_all, pending, bad = settle_rows(allp, found)
    # вчерашние: вошли во вчерашние итоги (закончились до вчерашнего ответа) — второй раз не берём
    rows_all = [r for r in rows_all if not r.get('carried') or est_end(r['g']) >= prev['at']]
    pending = [(p, why) for p, why in pending if not p.get('carried') or p['start'] + GAME_LEN >= prev['at']]
    bad = [(p, why) for p, why in bad if not p.get('carried')]
    rows = sorted([r for r in rows_all if est_end(r['g']) < at], key=lambda r: r['g']['start'])
    late = [r for r in rows_all if est_end(r['g']) >= at]
    carry = [p for p, why in pending if why == 'не доигран' and p['start'] + GAME_LEN >= at]
    return dict(rows=rows, week=None, src='ask', notes=notes + gerr + errs, pending=pending, bad=bad, carry=carry, late=late,
                ask=dict(at=at, pids=sel['pids'], free=free, unparsed=unparsed, prev=[r for r in rows if r.get('carried')],
                         src=sel.get('src', '')))


def wait_games(picks):
    """В Actions: подождать, пока по оценке (начало + 2:30 + 10 мин) доиграет последний матч прогнозов (не дольше 35 мин)."""
    if not os.environ.get('GITHUB_ACTIONS') or not picks:
        return
    now = data.now_msk()
    target = max(p['start'] for p in picks) + GAME_LEN + timedelta(minutes=10)
    if now < target:
        sec = min((target - now).total_seconds(), WAIT_MAX_MIN * 60)
        print('DAILY жду %d мин (последний матч прогнозов по оценке заканчивается к %02d:%02d МСК)' % (
            sec // 60, target.hour, target.minute), flush=True)
        time.sleep(sec)


def recap_channel_data(d, led, wait=False):
    """Итоги по постам канала (channel.py): прогнозы на матчи с началом в окне ask.window(d) — с 08:00 вчера до 08:00 утра d.
    Ленту не прочитать — те же матчи по записям бота: INBOX «опубликовано владельцем» + SENT.md (src='ledger').
    → dict как у recap_data + chan (сводка ленты или ошибка), window."""
    t0, t1 = ask.window(d)
    notes = []
    try:
        picks, chan = channel.posts(t0, t1)
        src = 'channel'
        notes += chan['notes']
        for line in chan['log']:
            print(line, flush=True)
    except channel.Unavailable as e:
        print('DAILY_SOURCE канал недоступен: %s → запасной источник: INBOX «опубликовано владельцем» + SENT.md' % e, flush=True)
        picks, n2 = led.published(t0, t1)
        notes += n2
        src, chan = 'ledger', dict(error=str(e))
        for p in picks:
            print('DAILY_SOURCE запасной | %s | %s | %s — %s | начало %s | %s | кэф %s' % (
                src_label(p), p['league'], p['home'], p['away'], p['start'].strftime('%d.%m %H:%M'), p['bet'],
                compose.kef_s(p['kef']) or '—'), flush=True)
    if wait:
        wait_games(picks)
    found, errs = data.games_for(picks) if picks else ({}, [])
    rows, pending, bad = settle_rows(picks, found)
    rows.sort(key=lambda r: r['g']['start'])
    return dict(rows=rows, week=None, src=src, notes=notes + errs, pending=pending, bad=bad, carry=[], late=[], chan=chan,
                window=(t0, t1))


# ---------------------------------------------------------------- сообщения

def src_label(p):
    """Как назвать прогноз владельцу: номер, «свой» (строка «Прогноз: …» из опроса) или PICKS.md."""
    return p.get('pid') or ('свой' if p.get('src') == 'free' else 'PICKS.md')


def intro(d, morning, recap, rd, merr, card_note, recap_only=False):
    pid_m, pid_r = '%s-m1' % mmdd(d), '%s-r1' % mmdd(d)
    out = ['<b>Утренние посты на %s</b> — проверьте и опубликуйте' % compose.dm(d), '']
    if morning:
        i = morning['info']
        parts = []
        if i['khl']:
            parts.append('КХЛ %s (%s)' % (compose.plural(i['khl'], 'матч', 'матча', 'матчей'), i['khl_when']))
        if i['nhl']:
            parts.append('НХЛ %s (ночь на %s, %s)' % (compose.plural(i['nhl'], 'матч', 'матча', 'матчей'),
                                                     compose.dm(d + timedelta(days=1)), i['nhl_when']))
        out.append('1. Начало игрового дня (%s): %s. Подача «%s».' % (pid_m, ', '.join(parts), texts.LAYOUT_RU[morning['layout']]))
    elif rd and (rd['src'] == 'ask' or recap_only):
        out[0] = '<b>Итоги вчерашних ставок на %s</b> — %sпроверьте и опубликуйте' % (
            compose.dm(d), 'по вашему выбору, ' if rd['src'] == 'ask' else '')
    else:
        out.append('1. Начало игрового дня: матчей сегодня нет — поста нет.')
    for e in merr:
        out.append('   ' + compose.esc(e))
    if rd is None:                                     # только «Начало игрового дня» (06:00): итоги — отдельным запуском
        out.append('2. Итоги вчерашних ставок — отдельным сообщением позже утром, когда доиграет НХЛ (по постам канала).')
        out += ['', '«Опубликовать» — пост выйдет сразу (в первой строке нет времени матча). «Редактировать» — поправить текст.']
        return '\n'.join(out)
    solo = not morning and (rd['src'] == 'ask' or recap_only)          # в сообщении только итоги — без нумерации
    ids = ', '.join(src_label(r) for r in rd['rows'])
    if rd['src'] in ('channel', 'ledger'):
        w0, w1 = rd['window']
        win = 'матчи с началом %s – %s МСК' % (w0.strftime('%d.%m %H:%M'), w1.strftime('%d.%m %H:%M'))
        if rd['src'] == 'channel':
            src = 'посты канала @jarvibet (%s; текст канала — окончательный, с вашими правками; прочитано постов: %d)' % (
                win, rd['chan']['total'])
        else:
            src = ('КАНАЛ НЕ ПРОЧИТАЛСЯ (%s) — запасной источник: записи бота, INBOX «опубликовано владельцем» + SENT.md (%s)'
                   % (compose.esc(rd['chan']['error'][:160]), win))
    else:
        src = ('опубликованные вами' if rd['src'] == 'inbox' else
               'ваш выбор в утреннем опросе (%s)' % rd['ask']['at'].strftime('%d.%m %H:%M') if rd['src'] == 'ask' else
               'ОПУБЛИКОВАННЫХ НЕТ — по отправленным вам (в канал не выходили; в самом посте об этом не сказано)')
    if recap:
        t = recap['tally']
        out.append(('' if solo else '2. ') + 'Итоги вчерашних ставок (%s): %s, зашло %d из %d%s%s.' % (
            pid_r, compose.plural(t['n'], 'прогноз', 'прогноза', 'прогнозов'), t['w'], t['d'],
            ', возвратов %d' % t['p'] if t['p'] else '', card_note))
        out.append('   Источник: %s — %s.' % (src, ids))
        edited = [r['pid'] for r in rd['rows'] if r.get('edited')]
        if edited:
            out.append('   С вашей правкой в боте: %s.' % ', '.join(edited))
        tg_ed = [r['pid'] for r in rd['rows'] if r.get('tg_edited')]
        if tg_ed:
            out.append('   Изменены в канале (взят текст после правки): %s.' % ', '.join(tg_ed))
    elif rd['src'] == 'ask':
        out.append('Из выбранного вами ещё ничего не доиграно — поста нет.')
    elif rd['src'] in ('channel', 'ledger'):
        out.append(('' if solo else '2. ') + 'Итоги вчерашних ставок: %s — поста нет.' % (
            'ни один прогноз не посчитан (см. ниже)' if rd['pending'] or rd['bad'] else
            'в канале нет прогнозов на эти матчи' if rd['src'] == 'channel' else 'и в записях бота прогнозов на эти матчи нет'))
        out.append('   Источник: %s.' % src)
    else:
        out.append('2. Итоги вчерашних ставок: прогнозов на вчерашние матчи нет — поста нет.')
    if rd['src'] == 'ask':
        a = rd['ask']
        for p in a['free']:
            out.append('   Свой: «%s» → %s — %s, %s%s.' % (compose.esc(p['note']), compose.esc(p['home']), compose.esc(p['away']),
                                                       compose.esc(p['bet']), ', кэф ' + compose.kef_s(p['kef']) if p['kef'] else ', кэф не указан'))
        for line, why in a['unparsed']:
            out.append('   не понял: «%s» — %s.' % (compose.esc(line), compose.esc(why)))
        if a['prev']:
            out.append('   Из вчерашнего опроса (доигрались позже): %s.' % ', '.join(
                compose.esc('%s — %s' % (r['home'], r['away'])) for r in a['prev']))
    for p, why in rd['pending']:
        if p in rd['carry']:
            continue
        out.append('   Не вошёл: %s — %s (%s) — %s.' % (compose.esc(p['home']), compose.esc(p['away']), src_label(p), why))
    for p in rd['carry']:
        out.append('   В завтрашние итоги: %s — %s (%s, начало %s) — ещё играют.' % (
            compose.esc(p['home']), compose.esc(p['away']), src_label(p), compose.hm(p['start'])))
    for r in rd['late']:
        if r not in rd['rows']:
            out.append('   В завтрашние итоги: %s — %s (%s) — закончился после %s.' % (
                compose.esc(r['home']), compose.esc(r['away']), src_label(r),
                'вашего ответа (%s)' % compose.hm(rd['ask']['at']) if rd['src'] == 'ask' else '%02d:%02d' % CUTOFF))
    for p, why in rd['bad']:
        out.append('   Не разобрал ставку %s «%s» (%s) — посчитайте вручную.' % (src_label(p), compose.esc(p['bet']), why))
    for n in rd['notes']:
        out.append('   ' + compose.esc(n))
    out += ['', '«Опубликовать» — пост выйдет сразу (в первой строке нет времени матча). «Редактировать» — поправить текст.']
    return '\n'.join(out)


def date_range(rows):
    """«15 октября» / «15–16 октября» / «31 октября – 1 ноября» по датам начала матчей (МСК)."""
    ds = sorted({r['g']['start'].date() for r in rows})
    a, b = ds[0], ds[-1]
    if a == b:
        return compose.dm(a)
    if a.month == b.month:
        return '%d–%s' % (a.day, compose.dm(b))
    return '%s – %s' % (compose.dm(a), compose.dm(b))


def log_scores(rd):
    """Строки DAILY_SCORES в лог Actions: по каждому матчу итогов — источник, итог, основное время, ОТ/Б, как
    определили, кто дома, на кого ставка, вердикт. Плюс не вошедшие и не разобранные."""
    def side_s(r):
        out = []
        for l_ in r['legs']:
            who = '' if 'side' not in l_ else ' на %s (%s)' % (r['home'] if l_['side'] == 'h' else r['away'],
                                                              'хозяева' if l_['side'] == 'h' else 'гости')
            out.append('%s%s, %s' % (l_['kind'], who, 'осн. время' if l_.get('scope', 'reg') == 'reg' else 'с ОТ/Б'))
        return '; '.join(out)
    for r in rd['rows']:
        g = r['g']
        reg = settle.scores(g, 'reg')
        print('DAILY_SCORES %s | %s | %s (дома) — %s (в гостях) | начало %s МСК | %s | итог %d:%d%s | осн. время %d:%d (%s) | '
              'ставка «%s» → %s | кэф %s | %s%s' % (
                  src_label(r), r['league'], r['home'], r['away'], g['start'].strftime('%d.%m %H:%M'), g.get('src', '?'),
                  g['hg'], g['ag'], ' ' + g['end'] if g.get('end') else '', reg[0], reg[1], g.get('how', '—'), r['bet'], side_s(r),
                  r.get('kef') or '—', settle.MARK[r['res']], ' | ВНИМАНИЕ: ' + g['warn'] if g.get('warn') else ''), flush=True)
    for p, why in rd['pending']:
        print('DAILY_SCORES %s | %s | %s — %s | %s — %s' % (src_label(p), p['league'], p['home'], p['away'], why,
                                                             'в завтрашние итоги' if p in rd['carry'] else 'в итоги не вошёл'))
    for p, why in rd['bad']:
        print('DAILY_SCORES %s | %s — %s | ставка «%s» не разобрана: %s' % (src_label(p), p['home'], p['away'], p['bet'], why))


def build(d, variant=0, card=True, out_dir=None, led=None, recap_only=False, sel=None, source='channel', greet_only=False,
          wait=False):
    """Всё утро: → (сообщения задания, сводка для лога, внутренности). Посты — с "emoji": true (team_job их не чистит).
    Итоги: sel — по выбору из опроса (--ask); иначе source='channel' — посты канала (запасной — INBOX + SENT.md),
    'ledger' — прежний режим (INBOX + SENT.md, граница CUTOFF). greet_only — только «Начало игрового дня»."""
    plan = engine().plan(d, variant)
    morning, merr = None, []
    if not recap_only:
        khl, nhl, leaders, merr = data.morning_games(d)
        morning = compose.morning_post(d, khl, nhl, leaders, plan)
    led = led or ledger.Ledger(cutoff(d))
    if greet_only:
        rd = None
    elif sel:
        rd = recap_ask_data(d, led, sel)
    elif source == 'channel':
        rd = recap_channel_data(d, led, wait)
    else:
        rd = recap_data(d, led)
    if rd:
        log_scores(rd)
    recap, card_note, images = None, '', []
    if rd and rd['rows']:
        recap = compose.recap_post(d, rd['rows'], rd['week'], plan)
        if card:
            t = recap['tally']
            try:
                import banner
                images = banner.render(rd['rows'], out_dir or os.path.join(ROOT, 'out', 'daily', d.isoformat()),
                                       '%s · зашло %s' % (date_range(rd['rows']), compose.score_line(t)))
                card_note = ', баннер' if len(images) == 1 else ', %d баннера альбомом' % len(images)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                card_note = ', без баннера (не нарисовался: %s)' % compose.esc(repr(e)[:80])
        if images and len(recap['text']) > compose.CAPTION_MAX:
            card_note += ' — подпись длиннее 1024: баннер отдельным постом %s-r2' % mmdd(d)
    msgs = [{'to': 'owner', 'type': 'text', 'html': True, 'text': intro(d, morning, recap, rd, merr, card_note, recap_only)}]
    problems = []
    post = dict(to='owner', html=True, buttons='post', emoji=True)
    if morning:
        problems += ['утро: ' + e for e in compose.validate(morning['text'])]
        msgs.append(dict(post, type='text', text=morning['text'], pid='%s-m1' % mmdd(d)))
    if recap:
        rel = [os.path.relpath(p, ROOT) for p in images]
        fits = len(recap['text']) <= compose.CAPTION_MAX
        problems += ['итоги: ' + e for e in compose.validate(recap['text'], photo=bool(rel) and fits)]
        if rel and fits:
            msgs.append(dict(post, type='photo' if len(rel) == 1 else 'album', files=rel, text=recap['text'], pid='%s-r1' % mmdd(d)))
        else:
            msgs.append(dict(post, type='text', text=recap['text'], pid='%s-r1' % mmdd(d)))
            if rel:
                msgs.append(dict(post, type='photo' if len(rel) == 1 else 'album', files=rel, text='', pid='%s-r2' % mmdd(d)))
    if not greet_only and not sel and source == 'channel':
        # футбол — отдельный пост со своим баннером (владелец 31.10): только опубликованное в канал, купоны не входят
        import foot_recap
        fm, fnote = foot_recap.build(d, engine().plan(d, variant + 7), os.path.join(out_dir or os.path.join(ROOT, 'out', 'daily', d.isoformat()), 'foot'), card)
        for m in fm:
            problems += ['футбол: ' + e for e in compose.validate(m['text'], photo=m['type'] != 'text')] if m['text'] else []
        msgs += fm
        msgs[0]['text'] += '\n\n' + fnote
    if problems:
        msgs[0]['text'] += '\n\nПроверка постов: ' + compose.esc('; '.join(problems))
    summary = dict(day=d.isoformat(), morning=morning and morning['layout'], recap=recap and recap['tone'],
                   picks=len(rd['rows']) if rd else 0, src=rd['src'] if rd else None, images=len(images), problems=problems)
    return msgs, summary, dict(plan=plan, morning=morning, recap=recap, rd=rd, images=images)


# ---------------------------------------------------------------- запуск

def wait_cutoff(d):
    now = data.now_msk()
    target = cutoff(d) + timedelta(minutes=5)
    if os.environ.get('GITHUB_ACTIONS') and now < target and (target - now) <= timedelta(hours=3):
        sec = min((target - now).total_seconds(), WAIT_MAX_MIN * 60)   # у itogi.yml предел 40 минут на задание
        print('DAILY жду %d мин (цель %02d:%02d МСК): матчи ночи должны закончиться' % (sec // 60, target.hour, target.minute), flush=True)
        time.sleep(sec)


def write_job(d, msgs, path=None):
    p = path or job_path(d)
    try:
        with open(p, encoding='utf-8') as f:
            job = json.load(f)
    except (OSError, ValueError):
        job = {'day': d.isoformat(), 'make': ['team/daily/morning.py %s' % d.isoformat()]}
    job['messages'] = msgs
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
        f.write('\n')
    return p


def make_template(d, name='morning', extra=''):
    p = os.path.join(ROOT, 'team', 'out', d.isoformat(), name + '.json')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    rel = os.path.relpath(p, ROOT)
    job = {'day': d.isoformat(), 'make': [('team/daily/morning.py %s --job-file %s %s' % (d.isoformat(), rel, extra)).strip()],
           'messages': []}
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(os.path.relpath(p, ROOT))


def history(d, days=7):
    eng = engine()
    for k in range(days, -1, -1):
        x = d - timedelta(days=k)
        if x < eng.epoch:
            continue
        p = eng.plan(x)
        print('%s %s  утро: %-7s итоги: %-7s обращения: %s' % (x.isoformat(), compose.WD[x.weekday()][:3], p.layout('m'),
                                                                 p.layout('r'), ' / '.join(p.many('addr'))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('day', nargs='?')
    ap.add_argument('--job')
    ap.add_argument('--history')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--variant', type=int, default=0)
    ap.add_argument('--no-card', action='store_true')     # баннер итогов в шаблоне «Матчи дня» — по умолчанию есть (16.10, вечер)
    ap.add_argument('--no-wait', action='store_true')
    ap.add_argument('--recap-only', action='store_true')
    ap.add_argument('--ask', action='store_true', help='итоги по выбору владельца из утреннего опроса бота (ask.py; опрос отменён 16.10)')
    ap.add_argument('--source', choices=('channel', 'ledger'), default='channel',
                    help='откуда итоги: channel — посты канала t.me/s/jarvibet (по умолчанию), ledger — INBOX + SENT.md')
    ap.add_argument('--greet-only', action='store_true', help='только «Начало игрового дня» (06:00, без итогов)')
    ap.add_argument('--job-file', help='куда писать сообщения (по умолчанию team/out/<D>/morning.json)')
    ap.add_argument('--name', default='morning', help='с --job: имя файла задания (morning2 → morning2.json)')
    a = ap.parse_args(argv)
    if a.job:
        extra = ' '.join(x for x, on in (('--no-wait', a.no_wait), ('--recap-only', a.recap_only), ('--no-card', a.no_card),
                                         ('--ask', a.ask), ('--greet-only', a.greet_only),
                                         ('--source ledger', a.source == 'ledger')) if on)
        return make_template(date.fromisoformat(a.job), a.name, extra)
    if a.history:
        return history(date.fromisoformat(a.history))
    d = date.fromisoformat(a.day) if a.day else data.now_msk().date()
    sel, led = None, None
    if a.ask:                                  # выбор владельца: переменные от бота (RECAP_*) или строка INBOX
        led = ledger.Ledger(cutoff(d))
        sel = ask.selection(d, led.inbox_text)
        if not sel or sel['none'] or not (sel['pids'] or sel['free']):
            why = 'вы выбрали «Сегодня без итогов»' if sel and sel['none'] else 'вашего выбора в опросе нет (ни в запуске, ни в INBOX)'
            msgs = [{'to': 'owner', 'type': 'text', 'html': True,
                     'text': '<b>Итоги на %s</b>: не собираю — %s.' % (compose.dm(d), why)}]
            print('DAILY ' + json.dumps(dict(day=d.isoformat(), ask='нет выбора'), ensure_ascii=False), flush=True)
            if not a.dry:
                jf = os.path.join(ROOT, a.job_file) if a.job_file and not os.path.isabs(a.job_file) else a.job_file
                write_job(d, msgs, jf)
            return
    elif not a.no_wait and not a.dry and a.source == 'ledger' and not a.greet_only:
        wait_cutoff(d)
    msgs, summary, _ = build(d, a.variant, card=not a.no_card, led=led, recap_only=a.recap_only or a.ask, sel=sel,
                             source=a.source, greet_only=a.greet_only,
                             wait=a.source == 'channel' and not a.no_wait and not a.dry)
    print('DAILY ' + json.dumps(summary, ensure_ascii=False), flush=True)
    if a.dry:
        for m in msgs:
            print('\n=== %s %s ===\n%s' % (m.get('pid', 'владельцу'), m['type'], m['text']))
        return
    jf = os.path.join(ROOT, a.job_file) if a.job_file and not os.path.isabs(a.job_file) else a.job_file
    print('DAILY задание: ' + os.path.relpath(write_job(d, msgs, jf), ROOT), flush=True)


if __name__ == '__main__':
    main()
