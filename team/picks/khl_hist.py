# -*- coding: utf-8 -*-
"""История КХЛ для нового рейтинга (владелец 29.10: «да, начинай КХЛ») — в том же виде, что team/picks/nhl_hist.py,
чтобы рейтинг (nhl_model.py) и проверка (nhl_bt.py --league khl) работали одинаково для обеих лиг.

Источник — приложение КХЛ (khl.api.webcaster.pro, event_v2 — как у таблицы КХЛ, khlAppGameRow_): счёт, периоды,
«Статистика матча» (броски в створ), вратари обеих команд с игровым временем. xG в КХЛ нет — вместо него «ожидаемые
голы» = броски в створ × средняя реализация бросков в лиге этого сезона; качество вратаря — пропущено против того,
что пропустил бы средний вратарь на тех же бросках (аналог GSAx по броскам).
Матч: {id, s, d, h, a, hg, ag, e, p, r: [голы осн. время], x: [ожид. голы х, г], sog: [броски х, г], g: [вратарь х, г],
       gs: {вратарь: [ожидалось пропустить, пропустил]}}. Кэш — .lines/khl_hist/ (переносится itogi.yml).
Отдельно: python team/picks/khl_hist.py"""
import gzip
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import khl_data as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.lines', 'khl_hist')
MSK = K.MSK


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def season_of(day):
    y, m = int(day[:4]), int(day[5:7])
    return y if m >= 8 else y - 1


def stages():
    boot = K.get('data.json')
    return boot, boot.get('stages_v2') or []


def stage_for(year, boot, sts):
    """Регулярка сезона year/year+1 (текущий — current_stage_id)."""
    cur = next((x for x in sts if x.get('id') == boot.get('current_stage_id')), {})
    if str(cur.get('season') or '').startswith(str(year)):
        return cur
    cand = [x for x in sts if str(x.get('season') or '').startswith(str(year))
            and 'егуляр' in (str(x.get('title') or x.get('name') or '') + str(x.get('type') or '')).lower()]
    cand = cand or [x for x in sts if str(x.get('season') or '').startswith(str(year))]
    return cand[0] if cand else {}


def _num(v):
    """'30' → 30, '12:34' (время) → секунды."""
    if ':' in v:
        a, b = v.split(':')[:2]
        return int(a) * 60 + int(b)
    return int(v)


def info(ev):
    """«Статистика матча: Броски в створ: 30 - 25; …» → {'Броски в створ': [30, 25], …} (как khlAppInfo_ таблицы)."""
    line = next((x.get('text') for x in ev.get('text_events') or []
                 if x.get('type') == 'info' and str(x.get('text') or '').startswith('Статистика матча')), '') or ''
    res = {}
    for part in re.sub(r'^Статистика матча:\s*', '', line).split(';'):
        m = re.match(r'^\s*([^:]+):\s*([\d:]+)\s*-\s*([\d:]+)', part)
        if m:
            res[m.group(1).strip()] = [_num(m.group(2)), _num(m.group(3))]
    return res


def goalie(t):
    """Вратарь команды с наибольшим игровым временем (как khlAppGameRow_)."""
    best = None
    for p in t.get('players') or []:
        if p.get('role_key') != 'goaltender':
            continue
        toi = 0
        for x in p.get('match_stats') or []:
            if x.get('id') == 'toi':
                try:
                    toi = float(x.get('val') or 0)
                except (TypeError, ValueError):
                    toi = 0
        if toi > 0 and (not best or toi > best[1]):
            best = (str(p.get('name') or p.get('id')), toi)
    return best[0] if best else None


def build(year, boot, sts, upto, known=None):
    """known — {id: матч} из кэша: протоколы уже сыгранных матчей не качаем заново."""
    known = known or {}
    st = stage_for(year, boot, sts)
    if not st:
        out('KHLHISTERR', 'этап сезона %d не найден' % year)
        return []
    frm = int(datetime(year, 8, 1, tzinfo=timezone.utc).timestamp())
    to = int(min(datetime(year + 1, 5, 1, tzinfo=timezone.utc), datetime.fromisoformat(upto).replace(tzinfo=MSK)).timestamp())
    events = []
    for page in range(1, 150):
        q = ('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
             '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, st['id']))
        arr = K.get(q)
        if not isinstance(arr, list) or not arr:
            break
        events += [w.get('event') or w for w in arr if (w.get('event') or w).get('type_id') in (18, 24)]
        if len(arr) < 16:
            break
    done = [e for e in events if e.get('game_state_key') == 'finished']
    games = [known[e.get('id')] for e in done if e.get('id') in known]
    done = [e for e in done if e.get('id') not in known]
    with ThreadPoolExecutor(8) as ex:
        det = list(ex.map(K.detail, done))
    shown = False
    for e, d in zip(done, det):
        src = d or e
        sc = str(src.get('score') or e.get('score') or '').replace(' ', '').split(':')
        if len(sc) != 2 or not (sc[0].isdigit() and sc[1].isdigit()):   # технический результат («+ : −») — не матч
            continue
        s = src.get('scores') or {}
        end = 'Б' if s.get('bullitt') else 'ОТ' if s.get('overtime') else ''
        per = [s.get(k) or '' for k in ('first_period', 'second_period', 'third_period', 'overtime')]
        r = [0, 0]
        for p in per[:3]:
            a, _, b = str(p).replace(' ', '').partition(':')
            if a.isdigit() and b.isdigit():
                r[0] += int(a)
                r[1] += int(b)
        hg, ag = int(sc[0]), int(sc[1])
        if not any(per[:3]):                      # периодов нет — осн. время из итогового счёта
            m = min(hg, ag)
            r = [m, m] if end else [hg, ag]
        inf = info(src)
        sog = inf.get('Броски в створ')
        ta, tb = src.get('team_a') or e.get('team_a') or {}, src.get('team_b') or e.get('team_b') or {}
        g = {'id': e.get('id'), 's': year, 'd': K.msk(src.get('start_at') or e.get('start_at')), 'h': K.team(ta), 'a': K.team(tb),
             'hg': hg, 'ag': ag, 'e': end, 'p': per, 'r': r}
        if sog:
            g['sog'] = sog
        gh, ga = goalie(ta), goalie(tb)
        if gh and ga:
            g['g'] = [gh, ga]
        if not shown and d:
            out('KHLHISTSAMPLE', 'сезон %d: статистика %s | вратари %s / %s' % (year, json.dumps(inf, ensure_ascii=False)[:300], gh, ga))
            shown = True
        games.append(g)
    games.sort(key=lambda x: x['d'])
    # «ожидаемые голы» по броскам: средняя реализация бросков в створ в этом сезоне (без пустых ворот не отделить)
    S = sum(sum(g['sog']) for g in games if g.get('sog'))
    Gs = sum(g['hg'] + g['ag'] - (1 if g['e'] == 'Б' else 0) for g in games if g.get('sog'))
    Gr = sum(sum(g['r']) for g in games if g.get('sog'))
    conv, conv_r = (Gs / S, Gr / S) if S else (0.09, 0.085)
    for g in games:
        if g.get('sog'):
            g['x'] = [round(g['sog'][0] * conv_r, 3), round(g['sog'][1] * conv_r, 3)]   # в масштабе голов осн. времени
            if g.get('g'):
                gah = g['ag'] - (1 if g['e'] == 'Б' and g['ag'] > g['hg'] else 0)     # пропустил вратарь хозяев
                gaa = g['hg'] - (1 if g['e'] == 'Б' and g['hg'] > g['ag'] else 0)
                g['gs'] = {g['g'][0]: [round(g['sog'][1] * conv, 3), gah], g['g'][1]: [round(g['sog'][0] * conv, 3), gaa]}
    out('KHLHIST', 'сезон %d/%02d (этап %s): матчей %d, с бросками %d, с вратарями %d, реализация бросков %.3f'
        % (year, (year + 1) % 100, st.get('id'), len(games), sum(1 for g in games if g.get('sog')),
           sum(1 for g in games if g.get('g')), conv))
    return games


def load(seasons=None, today=None, refresh_current=True):
    today = today or datetime.now(MSK).date().isoformat()
    cur = season_of(today)
    seasons = sorted(seasons or [cur - 2, cur - 1, cur])
    os.makedirs(CACHE, exist_ok=True)
    boot, sts = stages()
    res = []
    for s in seasons:
        p = os.path.join(CACHE, 'season_%d.json.gz' % s)
        games = None
        if os.path.exists(p) and not (s == cur and refresh_current):
            try:
                with gzip.open(p, 'rt', encoding='utf-8') as f:
                    games = json.load(f)
                out('KHLHIST', 'сезон %d/%02d: из кэша, матчей %d' % (s, (s + 1) % 100, len(games)))
            except (OSError, ValueError):
                games = None
        if games is None:
            known = {}
            if os.path.exists(p):                 # текущий сезон: из кэша берём уже сыгранные, качаем только новые
                try:
                    with gzip.open(p, 'rt', encoding='utf-8') as f:
                        known = {g['id']: g for g in json.load(f)}
                except (OSError, ValueError):
                    known = {}
            games = build(s, boot, sts, today, known)
            if games:
                with gzip.open(p, 'wt', encoding='utf-8') as f:
                    json.dump(games, f, ensure_ascii=False, separators=(',', ':'))
        res += games
    res.sort(key=lambda g: g['d'])
    return res


if __name__ == '__main__':
    out('KHLHIST', 'всего матчей %d' % len(load()))
