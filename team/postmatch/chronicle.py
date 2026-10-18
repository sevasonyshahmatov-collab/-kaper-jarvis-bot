# -*- coding: utf-8 -*-
"""Хроника матча для послематчевого разбора (владелец 18.10: «найдём текстовую трансляцию… составлять рисунок матча»).

КХЛ — карточка матча приложения КХЛ (event_v2): текстовая трансляция text_events (голы, удаления, видеопросмотры,
замены вратаря, статистика каждого периода), голы с авторами и ассистентами, броски и большинство команд, история пары.
НХЛ — api-web.nhle.com: landing (голы с авторами и ассистентами, удаления, три звезды) и play-by-play (броски по
периодам, силовые, снятие вратаря).
facts(p, g) → текст хроники по-русски (строки «П2 27:14 — …»); ошибка источника — пустая строка, пост соберётся по-старому.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'daily'))
import data  # noqa: E402

KEEP_KHL = ('goal', 'violation', 'video_review', 'replace', 'info', 'state')


def _mmss(sec):
    return '%d:%02d' % (sec // 60, sec % 60)


def khl(p, g):
    j = data.khl_get('event_v2.json?id=%s' % g['id'])
    e = j.get('event') or j
    ta, tb = e.get('team_a') or {}, e.get('team_b') or {}
    out = ['Матч: %s (дома) — %s, итог %s:%s%s.' % (p['home'], p['away'], g['hg'], g['ag'],
                                                    {'ОТ': ' в овертайме', 'Б': ' по буллитам'}.get(g.get('end') or '', ''))]
    sc = e.get('scores') or {}
    per = [sc.get(k) for k in ('first_period', 'second_period', 'third_period', 'overtime', 'bullitt') if sc.get(k)]
    if per:
        out.append('По периодам: ' + ', '.join(per) + '.')
    for t, nm in ((ta, p['home']), (tb, p['away'])):
        out.append('%s: бросков в створ %s, голов в большинстве %s из %s попыток, штрафных минут %s.' % (
            nm, t.get('shots', '?'), t.get('ppg', '?'), t.get('ppc', '?'), t.get('pim', '?')))
    ps = e.get('this_pair_stat') or {}
    if ps.get('events_count'):
        out.append('История пары: %s матчей, побед %s — %s, %s — %s.' % (
            ps['events_count'], p['home'], (ps.get('team_a') or {}).get('wins_count'),
            p['away'], (ps.get('team_b') or {}).get('wins_count')))
    gps = {}
    for x in e.get('goals') or []:
        au = x.get('author') or {}
        if au.get('name') and au.get('gps'):
            gps[au['name']] = au['gps']
    out.append('')
    out.append('Текстовая трансляция:')
    for x in sorted(e.get('text_events') or [], key=lambda x: x.get('seconds') or 0):
        if x.get('type') not in KEEP_KHL or not x.get('text'):
            continue
        txt = re.sub(r'\s+', ' ', x['text']).strip()
        for name, n in gps.items():
            if name in txt and x['type'] == 'goal':
                txt += ' (%s-й гол в сезоне)' % n
        when = ('П%s %s' % (x['period'], x.get('time_s'))) if x.get('period') else ''
        out.append(('%s — %s' % (when, txt)) if when else txt)
    return '\n'.join(out)


def _n(v):
    return v.get('default') if isinstance(v, dict) else (v or '')


def nhl(p, g):
    land = data.nhl_get('gamecenter/%s/landing' % g['id'])
    pbp = data.nhl_get('gamecenter/%s/play-by-play' % g['id'])
    hid = (pbp.get('homeTeam') or {}).get('id')
    hab = (land.get('homeTeam') or {}).get('abbrev')
    team = {hab: p['home']}
    team[(land.get('awayTeam') or {}).get('abbrev')] = p['away']
    out = ['Матч НХЛ: %s (дома) — %s, итог %s:%s%s. Имена игроков ниже — латиницей.' % (
        p['home'], p['away'], g['hg'], g['ag'], {'ОТ': ' в овертайме', 'Б': ' по буллитам'}.get(g.get('end') or '', ''))]
    shots, hits, blocks, pulled = {}, {}, {}, []
    last_sit = None
    for x in pbp.get('plays') or []:
        per = (x.get('periodDescriptor') or {}).get('number') or 0
        d = x.get('details') or {}
        side = 'h' if d.get('eventOwnerTeamId') == hid else 'a'
        t = x.get('typeDescKey')
        if t in ('shot-on-goal', 'goal'):
            shots.setdefault(per, {'h': 0, 'a': 0})[side] += 1
        elif t == 'hit':
            hits[side] = hits.get(side, 0) + 1
        elif t == 'blocked-shot':
            blocks[side] = blocks.get(side, 0) + 1
        sit = str(x.get('situationCode') or '')
        if len(sit) == 4 and sit != last_sit:
            if sit[0] == '0' and (not last_sit or last_sit[0] != '0'):
                pulled.append('П%s %s — %s снимает вратаря' % (per, x.get('timeInPeriod'), p['away']))
            if sit[3] == '0' and (not last_sit or last_sit[3] != '0'):
                pulled.append('П%s %s — %s снимает вратаря' % (per, x.get('timeInPeriod'), p['home']))
            last_sit = sit
    if shots:
        out.append('Броски в створ по периодам (%s — %s): %s; всего %d — %d.' % (
            p['home'], p['away'], ', '.join('%d:%d' % (v['h'], v['a']) for _, v in sorted(shots.items())),
            sum(v['h'] for v in shots.values()), sum(v['a'] for v in shots.values())))
    if hits or blocks:
        out.append('Силовые приёмы %d — %d, блокированные броски %d — %d.' % (
            hits.get('h', 0), hits.get('a', 0), blocks.get('h', 0), blocks.get('a', 0)))
    sm = land.get('summary') or {}
    out += ['', 'Голы:']
    for pd in sm.get('scoring') or []:
        n = (pd.get('periodDescriptor') or {}).get('number')
        for x in pd.get('goals') or []:
            ast = ', '.join(_n(a.get('name')) for a in x.get('assists') or [])
            st = {'pp': 'в большинстве', 'sh': 'в меньшинстве', 'ev': 'в равенстве'}.get(x.get('strength'), '')
            mod = ' в пустые ворота' if x.get('goalModifier') == 'empty-net' else ''
            out.append('П%s %s — %s: %s %s (%s-й гол в сезоне)%s%s, счёт %s:%s%s' % (
                n, x.get('timeInPeriod'), team.get(_n(x.get('teamAbbrev')), _n(x.get('teamAbbrev'))),
                _n(x.get('firstName')), _n(x.get('lastName')), x.get('goalsToDate'), ', ' + st if st else '', mod,
                x.get('homeScore'), x.get('awayScore'), ', передачи: ' + ast if ast else ''))
    pen = []
    for pd in sm.get('penalties') or []:
        n = (pd.get('periodDescriptor') or {}).get('number')
        for x in pd.get('penalties') or []:
            who = x.get('committedByPlayer') or {}
            who = ('%s %s' % (_n(who.get('firstName')), _n(who.get('lastName')))).strip() if isinstance(who, dict) else str(who)
            pen.append('П%s %s — удаление %s (%s), %s мин, %s' % (
                n, x.get('timeInPeriod'), who or 'командный штраф', team.get(_n(x.get('teamAbbrev')), ''),
                x.get('duration'), x.get('descKey')))
    if pen:
        out += ['', 'Удаления:'] + pen
    if pulled:
        out += ['', 'Вратари:'] + pulled
    stars = []
    for s in sm.get('threeStars') or []:
        extra = ('%s%% отражённых' % round(100 * s['savePctg'], 1)) if s.get('savePctg') is not None else \
            '%s+%s' % (s.get('goals', 0), s.get('assists', 0))
        stars.append('%s. %s (%s, %s), %s' % (s.get('star'), _n(s.get('name')), team.get(s.get('teamAbbrev'), ''),
                                              s.get('position'), extra))
    if stars:
        out += ['', 'Три звезды матча:'] + stars
    return '\n'.join(out)


def facts(p, g):
    try:
        return khl(p, g) if p['league'] == 'KHL' else nhl(p, g)
    except Exception as e:  # noqa: BLE001 — без хроники пост соберётся по-старому
        print('POSTMATCHERR хроника: %r' % e, flush=True)
        return ''
