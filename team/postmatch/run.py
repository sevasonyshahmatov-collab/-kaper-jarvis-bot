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

WAIT_MIN = 14                     # сколько ждать финала, если бот запустил чуть раньше (лимит задания — 20 мин)
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
WEEK = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']


# ───────────────────────────── данные ─────────────────────────────

def load_pick(pm):
    st = datetime.strptime(str(pm['start'])[:16], '%Y-%m-%d %H:%M').replace(tzinfo=data.MSK)
    kef = str(pm.get('kef') or '').replace(',', '.').strip()
    lg = 'NHL' if str(pm.get('league', '')).upper() in ('NHL', 'НХЛ') else 'KHL'
    return dict(pid=str(pm['pid']), league=lg, home=settle.canon(pm['home']), away=settle.canon(pm['away']), start=st,
                pick=str(pm['pick']).strip(), kef=float(kef) if re.fullmatch(r'\d+(\.\d+)?', kef) else None,
                ch=pm.get('ch'))


def final_game(p):
    """Матч прогноза; ждёт финала до WAIT_MIN минут. → матч или None."""
    t_end = time.time() + WAIT_MIN * 60
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


# ───────────────────────────── текст ─────────────────────────────

def name(team, case='nom'):
    return settle.gen(team) if case == 'gen' else team


def minute(sec):
    return sec // 60 + 1


def plural(n, one, few, many):
    return settle.plural(n, one, few, many)


def story(p, g, goals, rnd):
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
        s.append('%s открыл%s счёт уже на %d-й минуте%s.' % (T, _end(T), m, who))
    else:
        s.append('Счёт открыл%s %s на %d-й минуте %s периода%s.' % (_end(T), T, m, _ord(f['per']), who))
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
        s.append('После трёх периодов %d:%d, и всё решилось %s — %s дожал%s.' % (
            after[2][0], after[2][1], 'в овертайме' if end == 'ОТ' else 'в серии буллитов', W, _end(W)))
    elif diffs[key] >= 2:
        sc = _scored(by_per[key], win, names, W)
        if key == 0:
            s.append('%s задал%s тон уже в первом периоде: %s.' % (W, _end(W), sc))
        elif (before[0] - before[1]) * sgn <= 0:
            if key == 2 and before[0] == before[1]:
                s.append('Два периода прошли на равных, и на последний перерыв ушли при %d:%d.' % before)
            else:
                s.append('После %s периода было %d:%d.' % ((_ord(key),) + before))
            s.append('А в %s периоде %s включил%s по-настоящему и %s.' % (_ord(key + 1, 'pr'), W, _end(W, 'ся'), sc))
        else:
            s.append('В %s периоде %s окончательно забрал%s игру: %s.' % (_ord(key + 1, 'pr'), W, _end(W), sc))
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
    return (pr if case == 'pr' else gen).get(n, str(n))


def _scored(per, win, names, W):
    w, l_ = (per[0], per[1]) if win == 'h' else (per[1], per[0])
    base = ('забил%s %s без ответа' % (_end(W), _num(w))) if not l_ else ('забросил%s %s' % (_end(W), plural(w, 'шайбу', 'шайбы', 'шайб')))
    if names:
        uniq = list(dict.fromkeys(names))
        base += ': ' + (', '.join(uniq[:-1]) + ' и ' + uniq[-1] if len(uniq) > 1 else uniq[0])
    return base


def _num(n):
    return {1: 'одну', 2: 'две', 3: 'три', 4: 'четыре', 5: 'пять', 6: 'шесть'}.get(n, str(n))


OUTRO = {
    settle.WIN: ['Понервничал, но команда дожала 💪 Едем дальше!', 'Как и ждал — забираем 💪 Работаем дальше!',
                 'Спокойно и по делу ✔️ Двигаемся дальше 💪', 'Плюс в копилку 🔥 Дальше — больше!'],
    settle.LOSS: ['Ждал совсем другого, но что есть, то есть. Работаем дальше 💪', 'Сегодня не наш день. Без эмоций — работаем дальше.',
                  'Обидно, но это хоккей. Делаем выводы и идём дальше 💪'],
    settle.PUSH: ['Ставка вернулась — ни плюса, ни минуса. Едем дальше.', 'Возврат: при своих. Работаем дальше 💪'],
}


def post_text(p, g, goals, res, why):
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
    st = story(p, g, goals, rnd)
    lines += ['', '<i>%s</i>%s' % (e(st), ' 🔥' if res == settle.WIN else ''), '', rnd.choice(OUTRO[res]), '',
              '#%s #итог #jarvibet' % ('кхл' if p['league'] == 'KHL' else 'нхл')]
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
            how = ' В ОСН. ВРЕМЯ' if l_.get('scope', 'reg') == 'reg' else ''
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
    return pm.render(p['home'], p['away'], g['hg'], g['ag'], path, mark=g.get('end') or '', league=p['league'], date=date,
                     pick=p['pick'], kef=p['kef'], hit=hit, style='verdict_anim',
                     checks=checks_for(p, g, legs, res_legs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pm', default=os.environ.get('POSTMATCH', ''))
    ap.add_argument('--job-file', required=True)
    ap.add_argument('--no-render', action='store_true')
    a = ap.parse_args()
    if not a.pm:
        print('POSTMATCHERR нет данных прогноза (POSTMATCH)')
        return 0
    p = load_pick(json.loads(a.pm))
    print('прогноз:', p['pid'], p['home'], '—', p['away'], p['start'], p['pick'], p['kef'], flush=True)
    g = final_game(p)
    if not g:
        print('POSTMATCHERR матч ещё не закончен — поста нет', flush=True)
        return 0
    res, legs, why = settle.settle(p['pick'], p['home'], p['away'], g)
    res_legs = [settle.settle_leg(l_, g) for l_ in legs]
    goals = goals_of(p, g)
    text = post_text(p, g, goals, res, why)
    print(text, flush=True)
    path = os.path.join('out', 'postmatch', '%s.mp4' % p['pid'])
    if not a.no_render:
        render(p, g, legs, res, res_legs, path)
    msg = {'to': 'owner', 'type': 'animation', 'files': [path], 'text': text, 'html': True, 'emoji': True,
           'buttons': 'post', 'pid': p['pid'] + 'r'}
    with open(a.job_file, encoding='utf-8') as f:
        job = json.load(f)
    job['messages'] = (job.get('messages') or []) + [msg]
    with open(a.job_file, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
