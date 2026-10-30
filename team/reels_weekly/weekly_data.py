# -*- coding: utf-8 -*-
"""Данные недельных роликов (team/reels_weekly/BRIEF.md): «Топ недели» и антирейтинги сезона.

Источник — то же, что у итогов дня (team/daily/data.py): приложение КХЛ (khl.api.webcaster.pro, карточки матчей с
периодами) и API НХЛ (api-web.nhle.com). Облачная сессия до них не достаёт — считается в Actions (itogi.yml).
Итог наших прогнозов за неделю — опубликованные владельцем (team/INBOX.md + SENT.md, с его правками в боте) и строки
team/PICKS.md, расчёт по счёту — team/daily/settle.py, как в утренних итогах.

  python team/reels_weekly/weekly_data.py week khl 2026-10-19     топ-5 результативных команд недели пн–вс + наши прогнозы
  python team/reels_weekly/weekly_data.py under khl 2026-10-30    худшие для тотала больше 5,5 за сезон (по основному времени)
  python team/reels_weekly/weekly_data.py over nhl 2026-10-30     чаще всех тотал больше 5,5;  defense — меньше всех пропускают
"""
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
import data as D  # noqa: E402  (team/daily/data.py)

MSK = D.MSK
LG_RU = {'KHL': 'КХЛ', 'NHL': 'НХЛ'}
MIN_GAMES = {'KHL': 15, 'NHL': 20}          # меньше матчей в сезоне — команду в антирейтинг не берём (шум малой выборки)


def week_bounds(monday):
    d = date.fromisoformat(monday)
    d -= timedelta(days=d.weekday())
    t0 = datetime(d.year, d.month, d.day, tzinfo=MSK)
    return t0, t0 + timedelta(days=7)


def season_start(day):
    d = date.fromisoformat(day)
    y = d.year if d.month >= 8 else d.year - 1
    return datetime(y, 8, 1, tzinfo=MSK)


def games(league, t0, t1):
    """Сыгранные матчи [t0, t1) со счётом основного времени (g['reg']) и концовкой (g['end']: '' | 'ОТ' | 'Б')."""
    if league == 'KHL':
        out = D.khl_games(t0, t1, detail_if=lambda h, a: True)
    else:
        out, d = [], t0.date() - timedelta(days=1)
        while d <= t1.date():
            for g in D.nhl_day(d.isoformat()):
                if t0 <= g['start'] - timedelta(hours=12) < t1:      # ночные матчи НХЛ — к игровому дню накануне
                    out.append(g)
            d += timedelta(days=1)
    out = [g for g in out if g['state'] == 'final' and g['hg'] is not None]
    for g in out:
        if not g.get('reg'):                                # периодов нет — победа в ОТ/Б на одну шайбу
            m = min(g['hg'], g['ag'])
            g['reg'] = (m, m) if g['end'] else (g['hg'], g['ag'])
        if g.get('warn'):
            print('WEEKWARN %s — %s: %s' % (g['home'], g['away'], g['warn']), flush=True)
    return out


def goals(g, side):
    """Шайбы команды в матче без победного буллита (буллиты — не шайбы в статистике команды)."""
    if g['end'] == 'Б':
        return g['reg'][0 if side == 'h' else 1]
    return g['hg'] if side == 'h' else g['ag']


def top_scoring(gs, n=5):
    """Самые результативные команды: больше шайб, при равенстве — меньше матчей, потом меньше пропущено."""
    t = defaultdict(lambda: dict(gp=0, gf=0, ga=0))
    for g in gs:
        for side, me, op in (('h', g['home'], 'a'), ('a', g['away'], 'h')):
            t[me]['gp'] += 1
            t[me]['gf'] += goals(g, side)
            t[me]['ga'] += goals(g, op)
    rows = [dict(team=k, **v) for k, v in t.items()]
    rows.sort(key=lambda r: (-r['gf'], r['gp'], r['ga'], r['team']))
    return rows[:n], len(rows)


def worst_over(gs, line=5.5, league='KHL', n=5, over=False):
    """Доля матчей сезона с тоталом основного времени меньше line (over=True — больше): больше доля — выше; при равенстве —
    ниже (over — выше) средний тотал. Поле under — число таких матчей в обоих случаях."""
    t = defaultdict(lambda: dict(gp=0, under=0, tot=0))
    for g in gs:
        tot = g['reg'][0] + g['reg'][1]
        for me in (g['home'], g['away']):
            t[me]['gp'] += 1
            t[me]['under'] += (tot > line) if over else (tot < line)
            t[me]['tot'] += tot
    rows = []
    for k, v in t.items():
        if v['gp'] >= MIN_GAMES[league]:
            rows.append(dict(team=k, gp=v['gp'], under=v['under'], avg=round(v['tot'] / v['gp'], 2),
                             share=round(v['under'] / v['gp'], 4)))
    rows.sort(key=lambda r: (-r['share'], -r['avg'] if over else r['avg'], -r['gp'], r['team']))
    return rows[:n], len(rows), len(t)


def best_defense(gs, league='KHL', n=5):
    """Меньше всех пропускают за игру (без победных буллитов); команды от MIN_GAMES матчей."""
    t = defaultdict(lambda: dict(gp=0, gf=0, ga=0))
    for g in gs:
        for side, me, op in (('h', g['home'], 'a'), ('a', g['away'], 'h')):
            t[me]['gp'] += 1
            t[me]['gf'] += goals(g, side)
            t[me]['ga'] += goals(g, op)
    rows = [dict(team=k, avg=round(v['ga'] / v['gp'], 2), **v) for k, v in t.items() if v['gp'] >= MIN_GAMES[league]]
    rows.sort(key=lambda r: (r['ga'] / r['gp'], -r['gp'], r['team']))
    return rows[:n], len(rows), len(t)


def our_week(league, t0, t1):
    """Наши прогнозы на матчи недели: (зашло, не зашло, возврат, не рассчитано) — по опубликованным ставкам владельца."""
    import ledger                                          # team/daily — подтягиваем только здесь (тяжёлые тексты не нужны)
    import morning
    led = ledger.Ledger(t1)
    picks, notes = led.published(t0, t1)
    picks = [p for p in picks if p['league'] == league and t0 <= p['start'] < t1]   # ledger берёт с запасом ±14 ч
    for s in notes:
        print('WEEKNOTE ' + s, flush=True)
    found, errs = D.games_for(picks)
    for s in errs:
        print('WEEKERR ' + s, flush=True)
    rows, pending, bad = morning.settle_rows(picks, found)
    res = [r['res'] for r in rows]
    out = dict(win=res.count('win'), loss=res.count('loss'), push=res.count('push'), open=len(pending) + len(bad))
    for r in rows:
        print('WEEKPICK %s %s — %s | %s | %s:%s %s | %s' % (r['start'].date(), r['home'], r['away'], r['bet'], r['g']['hg'],
                                                           r['g']['ag'], r['g']['end'], r['res']), flush=True)
    for p, why in pending + bad:
        print('WEEKPICK %s %s — %s | %s | не рассчитан: %s' % (p['start'].date(), p['home'], p['away'], p['bet'], why), flush=True)
    return out


def week(league, monday):
    t0, t1 = week_bounds(monday)
    gs = games(league, t0, t1)
    top, nteams = top_scoring(gs)
    try:
        ours = our_week(league, t0, t1)
    except Exception as e:  # noqa: BLE001 — без итога прогнозов ролик всё равно собираем (блок не показываем)
        print('WEEKERR наши прогнозы: %r' % e, flush=True)
        ours = None
    return dict(kind='week', topic='scoring', league=league, t0=t0.date().isoformat(), t1=(t1 - timedelta(days=1)).date().isoformat(),
                games=len(gs), teams=nteams, top=top, ours=ours,
                src='приложение КХЛ' if league == 'KHL' else 'api-web.nhle.com')


def season_games(league, day):
    return games(league, season_start(day), datetime.fromisoformat(day).replace(tzinfo=MSK) + timedelta(days=1))


def under(league, day, line=5.5, over=False):
    gs = season_games(league, day)
    top, nteams, nall = worst_over(gs, line, league, over=over)
    return dict(kind='over' if over else 'under', league=league, line=line, upto=day, games=len(gs), teams=nteams, teams_all=nall, top=top,
                last=max(g['start'] for g in gs).date().isoformat() if gs else None,
                src='приложение КХЛ' if league == 'KHL' else 'api-web.nhle.com')


def defense(league, day):
    gs = season_games(league, day)
    top, nteams, nall = best_defense(gs, league)
    return dict(kind='defense', league=league, upto=day, games=len(gs), teams=nteams, teams_all=nall, top=top,
                last=max(g['start'] for g in gs).date().isoformat() if gs else None,
                src='приложение КХЛ' if league == 'KHL' else 'api-web.nhle.com')


def build(kind, league, day):
    if kind == 'week':
        return week(league, day)
    if kind == 'defense':
        return defense(league, day)
    return under(league, day, over=kind == 'over')


if __name__ == '__main__':
    kind, lg, day = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    r = build(kind, lg, day)
    print('WEEKDATA ' + json.dumps(r, ensure_ascii=False, separators=(',', ':')), flush=True)
