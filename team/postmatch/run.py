# -*- coding: utf-8 -*-
"""Послематчевый пост по одному опубликованному прогнозу (решение владельца 16.10, team/postmatch/README.md).

Бот таблицы КХЛ, когда матч опубликованного прогноза закончился, запускает itogi.yml с payload
{kind: 'team', job: 'team/out/<D>/postmatch_auto.json', day: D, pm: {pid, league, home, away, start, pick, kef, ch}}
(render/team_job.py кладёт pm в переменную POSTMATCH). Скрипт:
  1. берёт финальный счёт, периоды и голы (приложение КХЛ / API НХЛ — team/daily/data.py); не финал — ждёт до WAIT_MIN;
  2. считает ставку (team/daily/settle.py): зашла / не зашла / возврат;
  3. пишет текст от лица владельца по фактам матча (вариант 1 владельца: ✅ и жирный счёт, 🎯 ставка, 📈 кэф,
     рассказ курсивом, вывод, хэштеги) — HTML, эмодзи разрешены;
  4. рисует анимированный «Итог матча» (postmatch_styles, style='verdict_anim', прежний шёлковый фон);
  5. дописывает сообщение в задание (тип animation, кнопки «Опубликовать», номер <pid>r). Бот публикует его ответом
     на пост прогноза в канале (номер поста ch бот запомнил при публикации прогноза).
Вручную: python team/postmatch/run.py --pm '{"pid":"1610-1","league":"KHL","home":"Адмирал","away":"Спартак",
         "start":"2026-10-16 12:30","pick":"победа Спартака в основное время","kef":"1,95"}' --job-file out/pm.json [--no-render]
"""
import argparse
import hashlib
import html
import json
import os
import random
import re
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
sys.path.insert(0, os.path.join(ROOT, 'render'))

import data  # noqa: E402
import settle  # noqa: E402

RENDER_MAX = 6 * 60                # на баннер не больше 6 мин, иначе — текстом
WAIT_MIN = 14                     # сколько ждать финала, если бот запустил чуть раньше (лимит задания — 20 мин)
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
WEEK = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']


# ───────────────────────────── данные ─────────────────────────────

def load_pick(pm):
    st = datetime.strptime(str(pm['start'])[:16], '%Y-%m-%d %H:%M').replace(tzinfo=data.MSK)
    kef = str(pm.get('kef') or '').replace(',', '.').strip()
    lgr = str(pm.get('league', '')).upper()
    lg = 'NHL' if lgr in ('NHL', 'НХЛ') else 'FOOT' if lgr in ('FOOT', 'ФУТБОЛ') else 'KHL'
    nm = (lambda x: str(x).replace('«', '').replace('»', '').strip()) if lg == 'FOOT' else settle.canon
    return dict(pid=str(pm['pid']), league=lg, home=nm(pm['home']), away=nm(pm['away']), start=st,
                pick=str(pm['pick']).strip(), kef=float(kef) if re.fullmatch(r'\d+(\.\d+)?', kef) else None,
                ch=pm.get('ch'), tour=str(pm.get('tour') or ''), espn=str(pm.get('espn') or ''))


# Один итог на прогноз (31.10: владельцу дважды пришёл итог 3110-1 — бот и ручная досылка). Журнал переходит
# из задания в задание через кэш Actions (.pm_recent, itogi.yml); повтор — только с "force": 1 в pm.
DONE = os.path.join(ROOT, '.pm_recent', 'done.json')


DONE_REPO = os.path.join(HERE, 'sent_pm.json')      # отправленные вручную чатами команды — вписывать сюда же


def done_pids():
    d = {}
    for path in (DONE_REPO, DONE):
        try:
            with open(path, encoding='utf-8') as f:
                d.update(json.load(f))
        except (OSError, ValueError):
            pass
    return d


def mark_done(pid, how):
    try:
        with open(DONE, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d[pid] = '%s · %s' % (datetime.now(data.MSK).strftime('%d.%m %H:%M'), how)
    if len(d) > 300:
        d = dict(list(d.items())[-300:])
    os.makedirs(os.path.dirname(DONE), exist_ok=True)
    with open(DONE, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def final_game(p):
    """Матч прогноза; ждёт финала до WAIT_MIN минут. → матч или None."""
    t_end = time.time() + WAIT_MIN * 60
    while p['league'] == 'FOOT':
        import foot
        g = foot.game(p)
        if g and g['state'] == 'final':
            return g
        print('ещё не финал:', g and g['state'], flush=True)
        if time.time() > t_end:
            return None
        time.sleep(60)
    while True:
        found, errs = data.games_for([p])
        for e in errs:
            print('POSTMATCHERR', e, flush=True)
        g = data.match_game(found, p)
        if g and g['state'] == 'final' and g.get('hg') is not None:
            return g
        print('ещё не финал:', g and g['state'], flush=True)
        if time.time() > t_end:
            return None
        time.sleep(60)


def goals_of(p, g):
    """Голы матча по порядку: [{per: 1..5, sec, side: 'h'|'a', who: фамилия или '', status: 'бол'|'мен'|'рав'|''}]."""
    out = []
    if p['league'] == 'FOOT':
        return out                                    # футбол: голы — в g['goals'] (foot.py)
    try:
        if p['league'] == 'KHL':
            j = data.khl_get('event_v2.json?id=%s' % g['id'])
            d = j.get('event') or j
            ida = (d.get('team_a') or {}).get('id')
            for x in d.get('goals') or []:
                au = x.get('author') or {}
                side = 'h' if au.get('team_id') == ida else 'a'
                sec = int(x.get('time') or 0)
                out.append(dict(per=int(x.get('period') or 1), sec=sec, side=side,
                                who=str(au.get('name') or '').split()[0] if au.get('name') else '',
                                status=str(x.get('status_abbr') or '')))
            g['shots'] = ((d.get('team_a') or {}).get('shots'), (d.get('team_b') or {}).get('shots'))
        else:
            day = data.nhl_game_day(g['start'])
            raw = next((x for x in data.nhl_get('score/' + day).get('games') or [] if x.get('id') == g['id']), {})
            hab = (raw.get('homeTeam') or {}).get('abbrev')
            for x in raw.get('goals') or []:
                pd = x.get('periodDescriptor') or {}
                n = pd.get('number') or x.get('period') or 1
                mm, ss = (str(x.get('timeInPeriod') or '0:0') + ':0').split(':')[:2]
                ab = x.get('teamAbbrev')
                ab = ab.get('default') if isinstance(ab, dict) else ab
                out.append(dict(per=int(n), sec=(int(n) - 1) * 1200 + int(mm) * 60 + int(ss), side='h' if ab == hab else 'a',
                                who='', status={'pp': 'бол', 'sh': 'мен'}.get(x.get('strength'), '')))
            g['shots'] = ((raw.get('homeTeam') or {}).get('sog'), (raw.get('awayTeam') or {}).get('sog'))
    except Exception as e:  # noqa: BLE001 — без голов текст всё равно будет, по периодам/счёту
        print('POSTMATCHERR голы: %r' % e, flush=True)
    out.sort(key=lambda x: (x['per'], x['sec']))
    return out


def channel_post(p):
    """Лента канала (t.me/s/jarvibet, team/daily/channel.py) → (номер поста прогноза или None, обоснование из него,
    тексты последних послематчевых постов — чтобы новый их не повторял)."""
    msg_id, why, recent = None, '', []
    try:
        import channel
        from datetime import timedelta
        posts, _ = channel.feed(p['start'] - timedelta(days=2))
        for post in posts:
            lines = [t for t, _ in post['text']]
            if any('#итог' in t for t in lines):
                recent.append('\n'.join(t for t in lines if not t.startswith('#')))
                continue
            q, _ = channel.pick_of(post)
            if q and q['league'] == p['league'] and q['home'] == p['home'] and q['away'] == p['away'] \
                    and abs((q['start'] - p['start']).total_seconds()) <= 60:
                msg_id = q['msg_id']
                k = next((i for i, t in enumerate(lines) if re.match(r'(?i)\s*к[эе]ф', t)), 2)
                why = '\n'.join(t for t in lines[k + 1:] if not t.startswith('#'))
        if msg_id:
            print('пост прогноза в канале: №%d' % msg_id, flush=True)
    except Exception as e:  # noqa: BLE001
        print('POSTMATCHERR лента канала: %r' % e, flush=True)
    return msg_id, why, recent[::-1][:4]


# ───────────────────────────── текст ─────────────────────────────

def name(team, case='nom'):
    return settle.gen(team) if case == 'gen' else team


def minute(sec):
    return sec // 60 + 1


def plural(n, one, few, many):
    return settle.plural(n, one, few, many)


def _pick(pool, k):
    """Вариант из пула по номеру прогноза: у соседних прогнозов одного дня — разные фразы."""
    return pool[k % len(pool)]


def _num_of(p):
    m = re.search(r'-(\d+)', p['pid'])
    return int(m.group(1)) if m else 0


def _line(x):
    return ('%g' % x).replace('.', ',')


def _goals_word(n):
    return plural(n, 'шайба', 'шайбы', 'шайб')          # settle.plural уже ставит число: «4 шайбы»


def _periods(goals):
    reg = [x for x in goals if x['per'] <= 3]
    return [(sum(1 for x in reg if x['per'] == k and x['side'] == 'h'), sum(1 for x in reg if x['per'] == k and x['side'] == 'a'))
            for k in (1, 2, 3)]


def _details(p, g, goals, ou):
    """Факты о ходе матча (без оценки победителя) — для постов про тоталы."""
    team = {'h': p['home'], 'a': p['away']}
    out = []
    if goals:
        f = goals[0]
        T, m = team[f['side']], minute(f['sec'] - (f['per'] - 1) * 1200)
        who = (' (%s)' % f['who']) if f['who'] else ''
        out.append('Первую шайбу забросил%s %s на %d-й минуте %s периода%s.' % (_end(T), T, m, _ord(f['per']), who))
        per = _periods(goals)
        tot = [a + b for a, b in per]
        k = max(range(3), key=lambda i: tot[i])
        if tot[k] >= 2:
            out.append('Больше всего голов было %s периоде — %d:%d.' % ((_v(k + 1),) + per[k]))
        zero = [i for i in range(3) if tot[i] == 0]
        if zero:
            out.append('%s период и вовсе прошёл без голов.' % _ord(zero[0] + 1, 'nom').capitalize())
    shots = g.get('shots') or ()
    if len(shots) == 2 and all(isinstance(x, int) for x in shots):
        out.append(('Бросков в створ — %d:%d, но вратари своё отработали.' if ou == 'under'
                    else 'Бросков в створ — %d:%d, вратарям досталось.') % shots)
    return out


def _ot_note(p, g, k):
    """Фраза про овертайм/буллиты для ставок на основное время: исход дополнительного времени на ставку не влиял."""
    end = g.get('end') or ''
    if not end:
        return ''
    team = {'h': p['home'], 'a': p['away']}
    W = team['h' if g['hg'] > g['ag'] else 'a']
    where = 'в овертайме' if end == 'ОТ' else 'в серии буллитов'
    extra = 'Дальше был овертайм' if end == 'ОТ' else 'Дальше были буллиты'
    return _pick(['%s дожал%s соперника %s, но для ставки важны были только 60 минут.' % (W, _end(W), where),
                  '%s — на ставку это уже не влияло.' % extra,
                  'Победителя определили %s (%s), а ставка к тому моменту уже сыграла.' % (where, W)], k)


def story_total(p, g, goals, leg, res, k):
    """Пост про тотал: главное — сколько забили за время ставки, а не кто победил."""
    h, a = settle.scores(g, leg.get('scope', 'reg'))
    n, L, ou = h + a, _line(leg['line']), leg['ou']
    reg = leg.get('scope', 'reg') == 'reg'
    span = 'За 60 минут' if reg else 'За матч'
    hit = res == settle.WIN
    if ou == 'under' and hit:
        pool = ['%s — %s на двоих: до %s так и не дотянули.' % (span, _goals_word(n), L),
                ('Основное время — %d:%d, всего %s при линии %s.' if reg else 'Итог — %d:%d, всего %s при линии %s.') % (
                    h, a, _goals_word(n), L),
                'Матч получился %s: %d:%d, %s — меньше %s.' % ('закрытым' if n <= 3 else 'без перестрелки', h, a, _goals_word(n), L),
                ('Шайб было немного — %s, линия %s осталась с запасом.' if leg['line'] - n >= 1.5 else
                 'Уложились впритык: %s при линии %s.') % (_goals_word(n), L)]
    elif ou == 'under':
        pool = ['%s забросили %s — больше %s.' % (span, _goals_word(n), L),
                'Спокойной игры не вышло: %d:%d, %s при линии %s.' % (h, a, _goals_word(n), L),
                'Линию %s пробили — %s.' % (L, _goals_word(n))]
    elif hit:
        pool = ['%s — %s на двоих, больше %s.' % (span, _goals_word(n), L),
                'Голов хватило: %d:%d, %s при линии %s.' % (h, a, _goals_word(n), L),
                'Открытый хоккей — %s, линия %s пройдена.' % (_goals_word(n), L)]
    else:
        pool = ['%s — только %s, до %s не хватило.' % (span, _goals_word(n), L),
                'Вратари оказались сильнее: %d:%d, %s при линии %s.' % (h, a, _goals_word(n), L),
                'Голов не хватило — %s.' % _goals_word(n)]
    s = [_pick(pool, k)]
    det = _details(p, g, goals, ou)
    if det:
        s.append(_pick(det, k + 1))
    ot = _ot_note(p, g, k) if reg else ''
    if ot:
        s.append(ot)
    return ' '.join(s)


def story_it(p, g, goals, leg, res, k):
    """Пост про индивидуальный тотал: сколько забила команда за время ставки."""
    h, a = settle.scores(g, leg.get('scope', 'reg'))
    T = p['home'] if leg['side'] == 'h' else p['away']
    me = h if leg['side'] == 'h' else a
    L = _line(leg['line'])
    if me > leg['line']:
        pool = ['%s забросил%s %s — больше %s.' % (T, _end(T), _goals_word(me), L),
                'У %s %s за время ставки, линия %s пройдена.' % (name(T, 'gen'), _goals_word(me), L)]
    else:
        pool = ['У %s только %s — меньше %s.' % (name(T, 'gen'), _goals_word(me), L),
                'Итог %s — %s, линия %s не пройдена.' % (name(T, 'gen'), _goals_word(me), L)]
    s = [_pick(pool, k)]
    det = _details(p, g, goals, leg['ou'])
    if det:
        s.append(_pick(det, k + 1))
    if leg.get('scope', 'reg') == 'reg':
        ot = _ot_note(p, g, k)
        if ot:
            s.append(ot)
    return ' '.join(s)


def story(p, g, goals, rnd, legs=None, res=None):
    """Рассказ о матче по фактам — от вида ставки: тотал — сколько забили, исход — как к нему пришли."""
    k = _num_of(p)
    leg = legs[0] if legs and len(legs) == 1 else None
    if leg and leg['kind'] == 'tot':
        return story_total(p, g, goals, leg, res, k)
    if leg and leg['kind'] == 'it':
        return story_it(p, g, goals, leg, res, k)
    return story_side(p, g, goals, k)


def story_side(p, g, goals, k):
    """Рассказ о матче по фактам: кто открыл счёт, ход по периодам, решающий отрезок, броски. Только то, что есть в данных."""
    H, A = p['home'], p['away']
    hg, ag = g['hg'], g['ag']
    end = g.get('end') or ''
    team = {'h': H, 'a': A}
    win = 'h' if hg > ag else 'a'
    lose = 'a' if win == 'h' else 'h'
    W = team[win]
    s = []
    if not goals:
        if end:
            s.append('Основное время закончилось вничью %d:%d, всё решилось %s.' % (
                min(hg, ag), min(hg, ag), 'в овертайме' if end == 'ОТ' else 'в серии буллитов'))
        return ' '.join(s) or 'Итог — %d:%d.' % (hg, ag)
    f = goals[0]
    T, m = team[f['side']], minute(f['sec'] - (f['per'] - 1) * 1200)
    who = (' — отличился %s' % f['who']) if f['who'] else ''
    if f['per'] == 1 and m <= 5:
        s.append(_pick(['%s открыл%s счёт уже на %d-й минуте%s.' % (T, _end(T), m, who),
                        'Быстрый старт — уже на %d-й минуте забил%s %s%s.' % (m, _end(T), T, who)], k))
    else:
        s.append(_pick(['Счёт открыл%s %s на %d-й минуте %s периода%s.' % (_end(T), T, m, _ord(f['per']), who),
                        'Первой отличилась команда «%s» — %d-я минута %s периода%s.' % (T, m, _ord(f['per']), who),
                        'Первый гол в матче — за командой «%s»: %s период, %d-я минута%s.' % (T, _ord(f['per'], 'nom'), m, who)], k))
    reg = [x for x in goals if x['per'] <= 3]
    by_per = [(sum(1 for x in reg if x['per'] == k and x['side'] == 'h'), sum(1 for x in reg if x['per'] == k and x['side'] == 'a'))
              for k in (1, 2, 3)]
    after, h, a = [], 0, 0
    for bh, ba in by_per:
        h, a = h + bh, a + ba
        after.append((h, a))
    sgn = 1 if win == 'h' else -1
    diffs = [(bh - ba) * sgn for bh, ba in by_per]
    key = max(range(3), key=lambda k: (diffs[k], k))
    names = [x['who'] for x in reg if x['per'] == key + 1 and x['side'] == win and x['who']]
    before = after[key - 1] if key else (0, 0)
    if end:
        where = 'в овертайме' if end == 'ОТ' else 'в серии буллитов'
        s.append(_pick(['После трёх периодов %d:%d, и всё решилось %s — %s дожал%s.' % (after[2][0], after[2][1], where, W, _end(W)),
                        'Основное время закончилось %d:%d, победителя определили %s — им стал%s %s.' % (
                            after[2][0], after[2][1], where, _end(W), W),
                        'За 60 минут — %d:%d, а %s сильнее был%s %s.' % (after[2][0], after[2][1], where, _end(W), W)], k))
    elif diffs[key] >= 2:
        sc = _scored(by_per[key], win, names, W)
        if key == 0:
            s.append('%s задал%s тон уже в первом периоде: %s.' % (W, _end(W), sc))
        elif (before[0] - before[1]) * sgn <= 0:
            if key == 2 and before[0] == before[1]:
                s.append('Два периода прошли на равных, и на последний перерыв ушли при %d:%d.' % before)
            else:
                s.append('После %s периода было %d:%d.' % ((_ord(key),) + before))
            s.append('А %s периоде %s прибавил%s по-настоящему и %s.' % (_v(key + 1), W, _end(W), sc))
        else:
            s.append('%s периоде %s окончательно забрал%s игру: %s.' % (_v(key + 1).capitalize(), W, _end(W), sc))
    else:
        s.append('После двух периодов было %d:%d, финал — %d:%d.' % (after[1] + (hg, ag)))
    shots = g.get('shots') or ()
    if len(shots) == 2 and all(isinstance(x, int) for x in shots):
        ws, ls = (shots[0], shots[1]) if win == 'h' else (shots[1], shots[0])
        if ws - ls >= 10:
            s.append('По броскам в створ — %d:%d в пользу %s.' % (ws, ls, name(W, 'gen')))
        elif ls - ws >= 8:
            L = team[lose]
            s.append('Причём %s бросал%s больше — %d против %d, но реализация решила.' % (L, _end(L), ls, ws))
    return ' '.join(s)


def _end(team, base=''):
    """Окончание глагола прошедшего времени для клуба: «Спартак забил», «Каролина забила», «Рейнджерс забили»."""
    plural_ = team in ('Рейнджерс', 'Айлендерс', 'Шанхайские Драконы')
    fem = team in ('Лада', 'Сибирь', 'Северсталь', 'Каролина', 'Флорида', 'Филадельфия', 'Миннесота', 'Оттава', 'Юта',
                   'Тампа-Бэй')
    neu = team in ('Динамо Москва', 'Динамо Минск', 'Торпедо', 'Сочи', 'Нью-Джерси', 'Чикаго', 'Колорадо', 'Калгари',
                   'Торонто', 'Сан-Хосе', 'Баффало')
    e = 'и' if plural_ else 'а' if fem else 'о' if neu else ''
    return e + base


def _ord(n, case='gen'):
    gen = {1: 'первого', 2: 'второго', 3: 'третьего'}
    pr = {1: 'первом', 2: 'втором', 3: 'третьем'}
    nom = {1: 'первый', 2: 'второй', 3: 'третий'}
    return {'pr': pr, 'nom': nom}.get(case, gen).get(n, str(n))


def _v(n):
    """«в первом», «во втором», «в третьем» периоде."""
    return ('во ' if n == 2 else 'в ') + _ord(n, 'pr')


def _scored(per, win, names, W):
    w, l_ = (per[0], per[1]) if win == 'h' else (per[1], per[0])
    base = ('забил%s %s без ответа' % (_end(W), _num(w))) if not l_ else ('забросил%s %s' % (_end(W), plural(w, 'шайбу', 'шайбы', 'шайб')))
    if names:
        uniq = list(dict.fromkeys(names))
        base += ': ' + (', '.join(uniq[:-1]) + ' и ' + uniq[-1] if len(uniq) > 1 else uniq[0])
    return base


def _num(n):
    return {1: 'одну', 2: 'две', 3: 'три', 4: 'четыре', 5: 'пять', 6: 'шесть'}.get(n, str(n))


# концовки без «команда дожала»: ставка может быть на тотал, а не на клуб (замечание владельца 17.10)
OUTRO = {
    settle.WIN: ['Как и ждал — забираем 💪 Работаем дальше!', 'Спокойно и по делу ✔️ Двигаемся дальше 💪',
                 'Плюс в копилку 🔥 Дальше — больше!', 'Расчёт сработал 👌 Идём дальше!', 'Записываем в плюс ✅ Следующий матч уже скоро.',
                 'Есть! 🔥 Едем дальше.', 'Прочитали матч верно 💪 Работаем дальше!'],
    settle.LOSS: ['Ждал совсем другого, но что есть, то есть. Работаем дальше 💪', 'Сегодня не наш день. Без эмоций — работаем дальше.',
                  'Обидно, но это хоккей. Делаем выводы и идём дальше 💪', 'Мимо. Разберём и вернёмся с новым прогнозом 💪'],
    settle.PUSH: ['Ставка вернулась — ни плюса, ни минуса. Едем дальше.', 'Возврат: при своих. Работаем дальше 💪'],
}


def post_text(p, g, goals, res, why, legs=None, body=None):
    rnd = random.Random(int(hashlib.md5(p['pid'].encode()).hexdigest()[:8], 16))
    mark = {'ОТ': ' ОТ', 'Б': ' Б'}.get(g.get('end') or '', '')
    sign = {settle.WIN: '✅', settle.LOSS: '❌', settle.PUSH: '↩️'}[res]
    word = {settle.WIN: 'зашла', settle.LOSS: 'не зашла', settle.PUSH: 'возврат'}[res]
    e = html.escape
    lines = ['%s <b>%s — %s %d:%d%s</b>' % (sign, e(p['home']), e(p['away']), g['hg'], g['ag'], mark), '',
             '🎯 Ставка: <b>%s</b>' % e(p['pick'])]
    kef = ('%.2f' % p['kef']).replace('.', ',') if p['kef'] else ''
    tail = ' ✔️' if res == settle.WIN else ''
    lines.append(('📈 Кэф: <b>%s</b> — <b>%s</b>%s' % (kef, word, tail)) if kef else ('📈 Итог: <b>%s</b>%s' % (word, tail)))
    if res == settle.PUSH and why:
        lines[-1] += ' (%s)' % e(why)
    if body:
        st, outro = body
    elif p['league'] == 'FOOT':
        import foot
        st, outro = foot.story(p, g, legs, res, _num_of(p)), _pick(foot.OUTRO[res], _num_of(p))
    else:
        st, outro = story(p, g, goals, rnd, legs, res), _pick(OUTRO[res], _num_of(p))
    lines += ['', '<i>%s</i>%s' % (e(st), ' 🔥' if res == settle.WIN else ''), '', e(outro) if body else outro, '',
              '#%s #итог #jarvibet' % {'KHL': 'кхл', 'NHL': 'нхл', 'FOOT': 'футбол'}[p['league']]]
    return '\n'.join(lines)


# ───────────────────────────── баннер ─────────────────────────────

def checks_for(p, g, legs, res_legs):
    sc = '%d:%d%s' % (g['hg'], g['ag'], {'ОТ': ' ОТ', 'Б': ' Б'}.get(g.get('end') or '', ''))
    out = []
    for l_, r in zip(legs, res_legs):
        ok = True if r == settle.WIN else False if r == settle.LOSS else None
        h, a = settle.scores(g, l_.get('scope', 'reg'))
        if l_['kind'] == 'tot':
            t = '%s — %s' % (sc, plural(h + a, 'ГОЛ', 'ГОЛА', 'ГОЛОВ') + (' В ОСН. ВРЕМЯ' if g.get('end') and l_['scope'] == 'reg' else ''))
        elif l_['kind'] == 'it':
            tm = p['home'] if l_['side'] == 'h' else p['away']
            t = '%s — %s: %s' % (sc, tm.upper(), plural(h if l_['side'] == 'h' else a, 'ШАЙБА', 'ШАЙБЫ', 'ШАЙБ'))
        elif l_['kind'] in ('win', 'dc', 'draw', 'nodraw'):
            how = ' В ОСН. ВРЕМЯ' if l_.get('scope', 'reg') == 'reg' and p['league'] != 'FOOT' else ''
            if h == a:
                t = '%s — НИЧЬЯ%s' % (sc, how)
            else:
                t = '%s — ПОБЕДА %s%s' % (sc, settle.gen(p['home'] if h > a else p['away']).upper(), how)
        else:
            t = '%s — %s' % (sc, settle.short([l_], p['home'], p['away']).upper())
        out.append((t, ok))
    return out


def render(p, g, legs, res, res_legs, path):
    import postmatch_styles as pm
    sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
    import banners
    banners.ensure_ffmpeg()
    d = g['start']
    date = '%s, %d %s' % (WEEK[d.weekday()], d.day, MONTHS[d.month - 1])
    hit = True if res == settle.WIN else False if res == settle.LOSS else None
    league = p['league']
    if league == 'FOOT':                                   # футбол: эмблемы ESPN (render/football.py), подпись — турнир
        import football
        football.register()
        league = p.get('tour') if football.is_foot(p.get('tour') or '') else 'FOOT'
    return pm.render(p['home'], p['away'], g['hg'], g['ag'], path, mark=g.get('end') or '', league=league, date=date,
                     pick=p['pick'], kef=p['kef'], hit=hit, style='verdict_anim',
                     checks=checks_for(p, g, legs, res_legs))


# Тексты, уже отправленные владельцу (владелец 21.10: «текст по сути дублируется»): в канале видны только опубликованные,
# а посты одной ночи пишутся раньше, чем выходят. Файл переходит из задания в задание через кэш Actions (itogi.yml).
SENT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.pm_recent', 'sent.json')


def sent_texts():
    try:
        with open(SENT, encoding='utf-8') as f:
            return [x['text'] for x in json.load(f)][-6:]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def remember(p, body):
    try:
        with open(SENT, encoding='utf-8') as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = []
    old = [x for x in old if x.get('pid') != p['pid']] + [dict(pid=p['pid'], text=' '.join(body))]
    os.makedirs(os.path.dirname(SENT), exist_ok=True)
    with open(SENT, 'w', encoding='utf-8') as f:
        json.dump(old[-12:], f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pm', default=os.environ.get('POSTMATCH', ''))
    ap.add_argument('--job-file', required=True)
    ap.add_argument('--no-render', action='store_true')
    a = ap.parse_args()
    if not a.pm:
        print('POSTMATCHERR нет данных прогноза (POSTMATCH)')
        return 0
    raw = json.loads(a.pm)
    p = load_pick(raw)
    print('прогноз:', p['pid'], p['home'], '—', p['away'], p['start'], p['pick'], p['kef'], flush=True)
    sent = done_pids().get(p['pid'])
    if sent and not raw.get('force') and not raw.get('facts_only'):
        print('POSTMATCH итог %s уже отправлен (%s) — повтор не шлю; нужен заново — "force": 1' % (p['pid'], sent), flush=True)
        return 0
    g = final_game(p)
    if not g:
        print('POSTMATCHERR матч ещё не закончен — поста нет', flush=True)
        return 0
    res, legs, why = settle.settle(p['pick'], p['home'], p['away'], g)
    res_legs = [settle.settle_leg(l_, g) for l_ in legs]
    goals = goals_of(p, g)
    ch_num, pick_why, recent = channel_post(p)
    ch = p['ch'] if str(p.get('ch') or '').isdigit() else ch_num
    import chronicle
    import writer
    word = {settle.WIN: 'зашла', settle.LOSS: 'не зашла', settle.PUSH: 'возврат'}[res]
    mine = [t for t in sent_texts() if t not in recent]
    print('POSTMATCH сверка с недавними: в канале %d, отправлено владельцу %d' % (len(recent), len(mine)), flush=True)
    if p['league'] == 'FOOT':
        import foot
        facts = foot.facts(p, g)
    else:
        facts = chronicle.facts(p, g)
    # нейросети не отвечают (лимит Gemini, нет денег на Claude API) — текст пишет чат команды: сначала хроника
    # («facts_only»: только печать в лог, владельцу ничего), затем готовые «story» и «outro» в pm
    if raw.get('facts_only'):
        print('POSTMATCH обоснование прогноза:\n%s\nPOSTMATCH хроника:\n%s' % (pick_why, facts), flush=True)
        return 0
    if raw.get('story') and raw.get('outro'):
        body = (str(raw['story']).strip(), str(raw['outro']).strip())
    else:
        body = writer.write(p, g, word, facts, pick_why, (mine[::-1] + list(recent))[:6])
    if not body:
        # владелец 31.10: нейросеть не ответила — пост по шаблону из фактов (счёт, ставка, ✅/❌, ход матча), а не «не готов»
        print('POSTMATCHERR текста от нейросети нет — пост по шаблону из фактов', flush=True)
    else:
        remember(p, body)
    text = post_text(p, g, goals, res, why, legs, body)
    print(text, flush=True)
    path = os.path.join('out', 'postmatch', '%s.mp4' % p['pid'])
    msg = {'to': 'owner', 'type': 'animation', 'files': [path], 'text': text, 'html': True, 'emoji': True,
           'buttons': 'post', 'pid': '%sr%s' % (p['pid'], ch or '')}
    if not a.no_render:
        import signal

        def _too_long(*_):
            raise TimeoutError('баннер дольше %d с' % RENDER_MAX)
        signal.signal(signal.SIGALRM, _too_long)
        signal.alarm(RENDER_MAX)          # 31.10: баннер 3110-8 рисовался 38 мин — задание сняли, итог не ушёл
        try:
            render(p, g, legs, res, res_legs, path)
        except Exception as e:  # noqa: BLE001 — без баннера итог всё равно уходит текстом
            print('POSTMATCHERR баннер: %r — отправляю текстом' % e, flush=True)
            msg.update(type='text', files=[])
            msg.pop('files')
        finally:
            signal.alarm(0)
    # номер итога: <прогноз>r<номер поста прогноза в канале> — бот публикует итог ответом на этот пост
    with open(a.job_file, encoding='utf-8') as f:
        job = json.load(f)
    job['messages'] = (job.get('messages') or []) + [msg]
    with open(a.job_file, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    mark_done(p['pid'], 'нейросеть' if body else 'шаблон')
    return 0


if __name__ == '__main__':
    sys.exit(main())
