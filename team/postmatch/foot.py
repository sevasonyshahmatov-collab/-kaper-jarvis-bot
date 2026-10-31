# -*- coding: utf-8 -*-
"""Футбол для «Итога матча» (владелец 31.10: итог — на каждую опубликованную в канал футбольную ставку).
Счёт, голы и статистика — ESPN (как у бота: footEspnGames_), названия клубов — render/football.py (resolve → по-русски).
  game(p)   → матч прогноза: {league: 'FOOT', id, start, home, away, state, hg, ag, end: '', reg, goals, stats} или None;
  facts(p, g) → хроника текстом для writer.py;
  story(p, g, legs, res, k) → рассказ по фактам без нейросети (запасной текст)."""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'render'))
import football  # noqa: E402

API = 'https://site.api.espn.com/apis/site/v2/sports/soccer/%s/'
HDR = {'User-Agent': 'Mozilla/5.0'}
MSK = timezone(timedelta(hours=3))
TOURS = {'АПЛ': 'eng.1', 'Ла Лига': 'esp.1', 'Серия А': 'ita.1', 'Бундеслига': 'ger.1', 'Лига 1': 'fra.1',
         'Лига чемпионов': 'uefa.champions', 'Лига Европы': 'uefa.europa', 'Лига конференций': 'uefa.europa.conf',
         'Португалия': 'por.1'}


def _get(lg, path, **params):
    r = requests.get(API % lg + path, params=params, headers=HDR, timeout=30)
    r.raise_for_status()
    return r.json()


def _minute(clock):
    """«36'» → 36, «90'+3'» → 93."""
    n = [int(x) for x in re.findall(r'\d+', str(clock or ''))]
    return sum(n[:2]) if n else 0


def _last(name):
    """Фамилия из ESPN (латиница). В текст поста идёт только кириллица (foot.ru), латиницу не печатаем."""
    return str(name or '').split()[-1] if name else ''


def ru(who):
    return who if re.search('[а-яё]', who or '', re.I) else ''


def _codes(p):
    c = p.get('espn') or TOURS.get(p.get('tour') or '')
    return [c] if c else list(dict.fromkeys(TOURS.values()))


def game(p):
    """Матч прогноза p (home/away по-русски, start — МСК)."""
    for lg in _codes(p):
        for dd in (0, -1, 1):
            day = (p['start'] + timedelta(days=dd)).strftime('%Y%m%d')
            try:
                evs = _get(lg, 'scoreboard', dates=day).get('events') or []
            except Exception as e:  # noqa: BLE001
                print('POSTMATCHERR ESPN %s %s: %r' % (lg, day, e), flush=True)
                continue
            for ev in evs:
                c = ev['competitions'][0]
                side = {x['homeAway']: x for x in c['competitors']}
                if 'home' not in side or 'away' not in side:
                    continue
                h = football.resolve(side['home']['team']['displayName'])
                a = football.resolve(side['away']['team']['displayName'])
                st = datetime.strptime(ev['date'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc).astimezone(MSK)
                same = (h == p['home']) + (a == p['away'])
                if same == 2 or (same == 1 and abs((st - p['start']).total_seconds()) <= 1800):
                    return _game(lg, ev, c, side, h, a, st)
    return None


def _game(lg, ev, c, side, h, a, st):
    typ = ev['status']['type']
    hg, ag = (int(side[k].get('score') or 0) for k in ('home', 'away'))
    reg = (hg, ag)
    ls = [[x.get('value') for x in side[k].get('linescores') or []] for k in ('home', 'away')]
    if len(ls[0]) > 2 and len(ls[1]) > 2:                      # было дополнительное время — ставка на 90 минут
        reg = (int(sum(ls[0][:2])), int(sum(ls[1][:2])))
    hid = side['home']['team']['id']
    goals = []
    for d in c.get('details') or []:
        if not d.get('scoringPlay'):
            continue
        who = (d.get('athletesInvolved') or [{}])[0].get('displayName', '')
        own = bool(d.get('ownGoal'))
        tid = (d.get('team') or {}).get('id')
        goals.append(dict(min=_minute((d.get('clock') or {}).get('displayValue')), side='h' if tid == hid else 'a',
                          who=_last(who), pen=bool(d.get('penaltyKick')), own=own))
    reds = [dict(min=_minute((d.get('clock') or {}).get('displayValue')),
                 side='h' if (d.get('team') or {}).get('id') == hid else 'a')
            for d in c.get('details') or [] if d.get('redCard')]
    g = dict(league='FOOT', id=ev['id'], lg=lg, start=st, home=h, away=a, end='', reg=reg, goals=goals, reds=reds,
             state='final' if typ.get('completed') else 'live', hg=hg, ag=ag, stats={})
    try:
        for t in _get(lg, 'summary', event=ev['id']).get('boxscore', {}).get('teams', []):
            s = {x['name']: x.get('displayValue') for x in t.get('statistics', [])}
            k = 'h' if t['team']['id'] == hid else 'a'
            g['stats'][k] = dict(pos=s.get('possessionPct'), shots=s.get('totalShots'), sot=s.get('shotsOnTarget'),
                                 corners=s.get('wonCorners'))
    except Exception as e:  # noqa: BLE001
        print('POSTMATCHERR ESPN статистика: %r' % e, flush=True)
    return g


def _n(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def facts(p, g):
    team = {'h': p['home'], 'a': p['away']}
    out = ['Матч: %s (дома) — %s, итог %d:%d.' % (p['home'], p['away'], g['hg'], g['ag'])]
    if tuple(g['reg']) != (g['hg'], g['ag']):
        out.append('За 90 минут: %d:%d (дальше дополнительное время).' % tuple(g['reg']))
    ht = (sum(1 for x in g['goals'] if x['min'] <= 45 and x['side'] == 'h'), sum(1 for x in g['goals'] if x['min'] <= 45 and x['side'] == 'a'))
    out.append('Первый тайм: %d:%d.' % ht)
    for x in g['goals']:
        out.append('%d-я минута — гол, %s%s%s.' % (x['min'], team[x['side']], (': ' + x['who']) if x['who'] else '',
                                                   ' (пенальти)' if x['pen'] else ' (автогол соперника)' if x['own'] else ''))
    for x in g['reds']:
        out.append('%d-я минута — красная карточка у команды %s.' % (x['min'], team[x['side']]))
    for k in ('h', 'a'):
        s = g['stats'].get(k)
        if s:
            out.append('%s: владение %s %%, удары %s, в створ %s, угловые %s.' % (team[k], s['pos'], s['shots'], s['sot'], s['corners']))
    return '\n'.join(out)


def _pick(pool, k):
    return pool[k % len(pool)]


def _goals(n):
    return '%d %s' % (n, 'гол' if n % 10 == 1 and n % 100 != 11 else 'гола' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'голов')


def story(p, g, legs, res, k):
    """Рассказ по фактам ESPN: кто и когда забивал, счёт после первого тайма, удары. Только то, что есть в данных."""
    team = {'h': p['home'], 'a': p['away']}
    hg, ag = g['reg']
    goals = [x for x in g['goals'] if x['min'] <= 90 + 15]
    s = []
    if not goals:
        s.append(_pick(['Девяносто минут без голов — 0:0.', 'Голов не было: 0:0.'], k))
    else:
        f = goals[0]
        who = (' (%s)' % ru(f['who'])) if ru(f['who']) else ''
        who += ' с пенальти' if f['pen'] else ''
        s.append(_pick(['Счёт на %d-й минуте открыл %s%s.', 'Первым забил %s на %d-й минуте%s.'], k) %
                 ((f['min'], team[f['side']], who) if k % 2 == 0 else (team[f['side']], f['min'], who)))
        ht = (sum(1 for x in goals if x['min'] <= 45 and x['side'] == 'h'), sum(1 for x in goals if x['min'] <= 45 and x['side'] == 'a'))
        s.append('К перерыву — %d:%d.' % ht)
        rest = goals[1:]
        if rest:
            parts = ['%d-я — %s%s' % (x['min'], team[x['side']], (' (%s)' % ru(x['who'])) if ru(x['who']) else '') for x in rest[:4]]
            s.append('Дальше: %s. Финал — %d:%d.' % ('; '.join(parts), hg, ag))
        else:
            s.append('Больше голов не было — %d:%d.' % (hg, ag))
    for x in g['reds'][:1]:
        s.append('На %d-й минуте %s остался в меньшинстве.' % (x['min'], team[x['side']]))
    sh, sa = g['stats'].get('h') or {}, g['stats'].get('a') or {}
    if _n(sh.get('shots')) is not None and _n(sa.get('shots')) is not None:
        s.append('Удары — %d:%d, в створ — %s:%s, владение %s на %s.' % (_n(sh['shots']), _n(sa['shots']), sh.get('sot'), sa.get('sot'),
                                                                    sh.get('pos'), sa.get('pos')))
    leg = legs[0] if legs and len(legs) == 1 else None
    if leg and leg['kind'] == 'tot':
        s.append('Всего за 90 минут — %s при линии %s.' % (_goals(hg + ag), ('%g' % leg['line']).replace('.', ',')))
    return ' '.join(s)


OUTRO = {
    'win': ['Ставка зашла — спокойно идём дальше 💪', 'Плюс в копилку 🔥 Дальше — больше!', 'Расчёт сработал 👌 Едем дальше.'],
    'loss': ['Ждал другого, но что есть, то есть. Работаем дальше 💪', 'Сегодня мимо. Разберём и вернёмся с новым прогнозом.',
             'Обидно, но это футбол. Делаем выводы и идём дальше.'],
    'push': ['Возврат: при своих. Едем дальше.'],
}
