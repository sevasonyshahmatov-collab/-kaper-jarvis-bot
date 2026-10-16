# -*- coding: utf-8 -*-
"""Утренние посты владельцу (team/daily/README.md): «Начало игрового дня» и «Итоги вчерашних ставок», каждый — с кнопками
«Опубликовать» / «Редактировать» / «Не надо», перед ними — служебная строка владельцу.

  python3 team/daily/morning.py --job 2026-10-16        заготовка задания team/out/2026-10-16/morning.json
  python3 team/daily/morning.py 2026-10-16              (make задания, в Actions) данные → посты → сообщения в то же задание
  python3 team/daily/morning.py 2026-10-16 --dry        то же без записи в задание: тексты в консоль
  python3 team/daily/morning.py --history 2026-10-16    какие подачи и фразы выпали за 7 дней до даты (без сети)
  ключи: --variant N — другой вариант текстов этого дня; --card — итоги с картинкой (по умолчанию без — владелец 16.10); --no-wait — не ждать CUTOFF+5 мин

Номера постов — ММДД-m1 (утро) и ММДД-r1 (итоги; картинка отдельно, если подпись не влезла, — ММДД-r2): бот принимает
любой номер без «|» (tm|pub|<номер>), а буква не попадает под ММДД-N, по которому check.py --next считает номера
прогнозов, и под ММДД-N, по которому итоги ищут опубликованные прогнозы в INBOX.

Итоги за утро D — прогнозы, матчи которых закончились (по оценке: начало + 2:30, ОТ +0:15, буллиты +0:25) между
CUTOFF дня D−1 и CUTOFF дня D (06:00 МСК; другое — переменная DAILY_CUTOFF=ЧЧ:ММ). Матч НХЛ, что доигрывается после
CUTOFF (обычно начало в 04:00 и позже), уходит в итоги следующего утра — так каждый прогноз попадает в итоги ровно один
раз, а повторный запуск дня даёт то же самое. Запущено раньше CUTOFF+5 мин — в Actions ждёт (не дольше 35 мин).
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


# ---------------------------------------------------------------- сообщения

def intro(d, morning, recap, rd, merr, card_note):
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
    else:
        out.append('1. Начало игрового дня: матчей сегодня нет — поста нет.')
    for e in merr:
        out.append('   ' + compose.esc(e))
    if recap:
        t = recap['tally']
        src = ('опубликованные вами' if rd['src'] == 'inbox' else
               'ОПУБЛИКОВАННЫХ НЕТ — по отправленным вам (в канал не выходили; в самом посте об этом не сказано)')
        ids = ', '.join(r.get('pid') or 'PICKS.md' for r in rd['rows'])
        out.append('2. Итоги вчерашних ставок (%s): %s, зашло %d из %d%s. Подача «%s»%s.' % (
            pid_r, compose.plural(t['n'], 'прогноз', 'прогноза', 'прогнозов'), t['w'], t['d'],
            ', возвратов %d' % t['p'] if t['p'] else '', texts.LAYOUT_RU[recap['layout']], card_note))
        out.append('   Источник: %s — %s.' % (src, ids))
        edited = [r['pid'] for r in rd['rows'] if r.get('edited')]
        if edited:
            out.append('   С вашей правкой в боте: %s.' % ', '.join(edited))
    else:
        out.append('2. Итоги вчерашних ставок: прогнозов на вчерашние матчи нет — поста нет.')
    for p, why in rd['pending']:
        if p in rd['carry']:
            continue
        out.append('   Не вошёл: %s — %s (%s) — %s.' % (compose.esc(p['home']), compose.esc(p['away']), p.get('pid') or 'PICKS.md', why))
    for p in rd['carry']:
        out.append('   В завтрашние итоги: %s — %s (%s, начало %s) — ещё играют.' % (
            compose.esc(p['home']), compose.esc(p['away']), p.get('pid') or 'PICKS.md', compose.hm(p['start'])))
    for r in rd['late']:
        if r not in rd['rows']:
            out.append('   В завтрашние итоги: %s — %s (%s) — закончился после %02d:%02d.' % (
                compose.esc(r['home']), compose.esc(r['away']), r.get('pid') or 'PICKS.md', *CUTOFF))
    for p, why in rd['bad']:
        out.append('   Не разобрал ставку %s «%s» (%s) — посчитайте вручную.' % (p.get('pid') or 'PICKS.md', compose.esc(p['bet']), why))
    for n in rd['notes']:
        out.append('   ' + compose.esc(n))
    out += ['', '«Опубликовать» — пост выйдет сразу (в первой строке нет времени матча). «Редактировать» — поправить текст.']
    return '\n'.join(out)


def build(d, variant=0, card=True, out_dir=None, led=None):
    """Всё утро: → (сообщения задания, сводка для лога)."""
    plan = engine().plan(d, variant)
    khl, nhl, leaders, merr = data.morning_games(d)
    morning = compose.morning_post(d, khl, nhl, leaders, plan)
    led = led or ledger.Ledger(cutoff(d))
    rd = recap_data(d, led)
    recap, card_note, card_path = None, '', None
    msgs = []
    if rd['rows']:
        if card:
            t = compose.tally(rd['rows'])
            try:
                import card as card_mod
                card_path = card_mod.render(rd['rows'], os.path.join(out_dir or os.path.join(ROOT, 'out', 'daily', d.isoformat()), 'recap.jpg'),
                                            title_date=compose.dm(d - timedelta(days=1)),
                                            score='%d из %d' % (t['w'], t['d']) + (', возврат %d' % t['p'] if t['p'] else ''))
                if not card_path:
                    card_note = ', без картинки (больше %d матчей)' % card_mod.MAX_ROWS
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                card_note = ', без картинки (не нарисовалась: %s)' % compose.esc(repr(e)[:80])
        recap = compose.recap_post(d, rd['rows'], rd['week'], plan, photo=bool(card_path))
        if card_path and len(recap['text']) > compose.CAPTION_MAX:
            recap = compose.recap_post(d, rd['rows'], rd['week'], plan, photo=True, compact=True)
        split_card = card_path and len(recap['text']) > compose.CAPTION_MAX
        if card_path:
            card_note = ', картинка отдельным постом %s-r2 (подпись длиннее 1024)' % mmdd(d) if split_card else ', с картинкой'
        recap['photo'] = card_path if card_path and not split_card else None
        recap['card'] = card_path if split_card else None
    msgs.append({'to': 'owner', 'type': 'text', 'html': True, 'text': intro(d, morning, recap, rd, merr, card_note)})
    problems = []
    if morning:
        problems += ['утро: ' + e for e in compose.validate(morning['text'])]
        msgs.append({'to': 'owner', 'type': 'text', 'html': True, 'text': morning['text'], 'buttons': 'post', 'pid': '%s-m1' % mmdd(d)})
    if recap:
        problems += ['итоги: ' + e for e in compose.validate(recap['text'], photo=bool(recap['photo']))]
        rel = lambda p: os.path.relpath(p, ROOT)                     # noqa: E731
        if recap['photo']:
            msgs.append({'to': 'owner', 'type': 'photo', 'html': True, 'files': [rel(recap['photo'])], 'text': recap['text'],
                         'buttons': 'post', 'pid': '%s-r1' % mmdd(d)})
        else:
            msgs.append({'to': 'owner', 'type': 'text', 'html': True, 'text': recap['text'], 'buttons': 'post', 'pid': '%s-r1' % mmdd(d)})
            if recap['card']:
                cap = '<b>Итоги прогнозов · %s</b>\n\n%s' % (compose.dm(d - timedelta(days=1)), recap['tags'])
                msgs.append({'to': 'owner', 'type': 'photo', 'html': True, 'files': [rel(recap['card'])], 'text': cap,
                             'buttons': 'post', 'pid': '%s-r2' % mmdd(d)})
    if problems:
        msgs[0]['text'] += '\n\nПроверка постов: ' + compose.esc('; '.join(problems))
    summary = dict(day=d.isoformat(), morning=morning and morning['layout'], recap=recap and recap['layout'],
                   picks=len(rd['rows']), src=rd['src'], problems=problems)
    return msgs, summary, dict(plan=plan, morning=morning, recap=recap, rd=rd)


# ---------------------------------------------------------------- запуск

def wait_cutoff(d):
    now = data.now_msk()
    target = cutoff(d) + timedelta(minutes=5)
    if os.environ.get('GITHUB_ACTIONS') and now < target and (target - now) <= timedelta(hours=3):
        sec = min((target - now).total_seconds(), WAIT_MAX_MIN * 60)   # у itogi.yml предел 40 минут на задание
        print('DAILY жду %d мин (цель %02d:%02d МСК): матчи ночи должны закончиться' % (sec // 60, target.hour, target.minute), flush=True)
        time.sleep(sec)


def write_job(d, msgs):
    p = job_path(d)
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


def make_template(d):
    p = job_path(d)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    job = {'day': d.isoformat(), 'make': ['team/daily/morning.py %s' % d.isoformat()], 'messages': []}
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
    ap.add_argument('--card', action='store_true')        # картинка к итогам — владелец 16.10: пока без неё
    ap.add_argument('--no-wait', action='store_true')
    a = ap.parse_args(argv)
    if a.job:
        return make_template(date.fromisoformat(a.job))
    if a.history:
        return history(date.fromisoformat(a.history))
    d = date.fromisoformat(a.day) if a.day else data.now_msk().date()
    if not a.no_wait and not a.dry:
        wait_cutoff(d)
    msgs, summary, _ = build(d, a.variant, card=a.card)
    print('DAILY ' + json.dumps(summary, ensure_ascii=False), flush=True)
    if a.dry:
        for m in msgs:
            print('\n=== %s %s ===\n%s' % (m.get('pid', 'владельцу'), m['type'], m['text']))
        return
    print('DAILY задание: ' + os.path.relpath(write_job(d, msgs), ROOT), flush=True)


if __name__ == '__main__':
    main()
