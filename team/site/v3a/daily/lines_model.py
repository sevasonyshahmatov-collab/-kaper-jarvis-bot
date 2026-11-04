# -*- coding: utf-8 -*-
"""Линии (коэффициенты) и вероятности модели на матчи ближайших 2 дней (сегодня и завтра по Москве) → data/lines.json,
data/model.json, data/today.json (+ .js). Ключ матча: лига|дата МСК|хозяева slug|гости slug (daily/README.md).

Хоккей (КХЛ, НХЛ) — код команды (ветка команды, team/picks):
  линия: Фонбет (fonbet.py, открытая выгрузка линии; по нему ставит владелец) → приложение КХЛ, поле bets (только КХЛ) → Pinnacle (pin.py);
  модель: calc.match() + новый рейтинг khl_live / nhl_live (xG/броски, вратарь, два дня подряд) — то же, что в ежедневных прогнозах.
Футбол — football_day.py команды (Дикси-Коулс + смесь с линией Pinnacle; кэфы Фонбета и Pinnacle), матч сопоставляется с ESPN
  (football.json) по лиге, времени (±20 мин) и названиям; нет — линия ESPN и простая модель Пуассона football/build_data.py (ver poisson-v1).
Каждый источник в своём try: упал — шаг идёт дальше, причина в notes (→ daily_log.json)."""
import difflib, io, json, os, re, sys, unicodedata
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

notes = []


def note(s):
    print('NOTE', s, flush=True)
    notes.append(s)


def num(x):
    try:
        v = float(str(x).replace(',', '.'))
        return round(v, 3) if v > 1 else None
    except (TypeError, ValueError):
        return None


def best_total(pairs):
    """{линия: (больше, меньше)} → (линия, больше, меньше): та, где кэфы ближе всего друг к другу (основная линия)."""
    ok = {l: p for l, p in pairs.items() if p[0] and p[1]}
    if not ok:
        return None
    l = min(ok, key=lambda x: (abs(1 / ok[x][0] - 1 / ok[x][1]), x))
    return l, ok[l][0], ok[l][1]


def window():
    today = C.now_msk().date()
    return {today.isoformat(), (today + timedelta(days=1)).isoformat()}


# ───────────────────────────────── хоккей ─────────────────────────────────
def hockey(lines, model, today_rows):
    names = (C.jload(os.path.join(C.V3A, 'assets', 'data', 'teams.json'), {}) or {}).get('names') or {}
    slug_of = {v: k for k, v in names.items()}
    tc = os.path.join(C.TEAMCODE, 'team', 'picks')
    sys.path.insert(0, tc)
    cwd = os.getcwd()
    os.chdir(C.TEAMCODE)           # .lines/ и относительные пути кода команды
    try:
        import calc, fonbet, pin  # noqa: E401
        win = window()
        today = C.now_msk().date()
        for lg in ('khl', 'nhl'):
            try:
                if lg == 'khl':
                    import khl_data as DATA
                    import khl_live as LIVE
                    days = [today.isoformat(), (today + timedelta(days=1)).isoformat()]
                else:
                    import nhl_data as DATA
                    import nhl_live as LIVE
                    days = [(today + timedelta(days=d)).isoformat() for d in (-1, 0, 1)]     # игровой день НХЛ — по Нью-Йорку
            except Exception as e:  # noqa: BLE001
                note('%s: модули команды не загрузились: %r' % (lg.upper(), e))
                continue
            games_cache = None
            for day in days:
                try:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        games, nxt = DATA.fetch(day)
                except Exception as e:  # noqa: BLE001
                    note('%s %s: расписание/матчи сезона не получены: %r' % (lg.upper(), day, e))
                    continue
                games_cache = games_cache or games
                nxt = [x for x in nxt if x['d'][:10] in win]
                if not nxt:
                    continue
                pairs = [(x['h'], x['a']) for x in nxt]
                # — линии
                fon = {}
                try:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        fon = fonbet.hockey_day(lg, day, pairs)
                except Exception as e:  # noqa: BLE001
                    note('%s %s: Фонбет недоступен: %r' % (lg.upper(), day, e))
                pins = {}
                try:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        pins, _ = pin.fetch(lg, day, pairs)
                except Exception as e:  # noqa: BLE001
                    note('%s %s: Pinnacle недоступен: %r' % (lg.upper(), day, e))
                # — модель
                new, wn = {}, 0.8
                try:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        new = LIVE.prepare(day, nxt)
                    wn = LIVE.WN
                except Exception as e:  # noqa: BLE001
                    note('%s %s: новый рейтинг не посчитан, модель по-старому: %r' % (lg.upper(), day, e))
                calc.NHL_WN = wn
                T = M = None
                try:
                    g = calc.prep(games_cache)
                    T, M = calc.team_games(g), calc.model(g)
                except Exception as e:  # noqa: BLE001
                    note('%s: модель сезона не построена: %r' % (lg.upper(), e))
                for x in nxt:
                    H, A = x['h'], x['a']
                    hs, as_ = slug_of.get(H), slug_of.get(A)
                    if not hs or not as_:
                        note('%s: нет slug для %s — %s' % (lg.upper(), H, A))
                        continue
                    dt = datetime.strptime(x['d'], '%Y-%m-%d %H:%M')
                    key = C.match_key(lg, dt, hs, as_)
                    row = {'key': key, 'lg': lg, 't': x['d'], 'h': hs, 'a': as_, 'hn': H, 'an': A, 'arena': x.get('arena') or x.get('venue')}
                    # линия
                    cand = {}
                    f = (fon.get((H, A)) or {}).get('flat') or {}
                    if all(k in f for k in ('П1', 'Х', 'П2')):
                        tp = {}
                        for k, v in f.items():
                            if k.startswith('ТБ '):
                                u = f.get('ТМ ' + k[3:])
                                if u:
                                    tp[k[3:]] = (v, u)
                        bt = best_total(tp)
                        cand['fonbet'] = dict(p1=f['П1'], x=f['Х'], p2=f['П2'], **(dict(tot=float(bt[0]), over=bt[1], under=bt[2]) if bt else {}),
                                              **({'fin1': f['итог П1'], 'fin2': f['итог П2']} if 'итог П1' in f and 'итог П2' in f else {}))
                    b = x.get('bets') or {}
                    if lg == 'khl' and num(b.get('team_a_win')) and num(b.get('team_b_win')):
                        cand['khl-app'] = dict(p1=num(b.get('team_a_win')), x=num(b.get('draw')), p2=num(b.get('team_b_win')))
                    mks = pins.get((H, A))
                    if mks:
                        g3 = [calc.odds_for(('ml', 6, s), mks)[0] for s in ('home', 'draw', 'away')]
                        tp = {}
                        for m in mks:
                            if m['type'] == 'total' and m['period'] == 6:
                                ov = {p['points']: p['price'] for p in m['prices'] if p['designation'] == 'over'}
                                un = {p['points']: p['price'] for p in m['prices'] if p['designation'] == 'under'}
                                for l in ov:
                                    if l in un:
                                        tp[str(l)] = (ov[l], un[l])
                        bt = best_total(tp)
                        if all(g3):
                            cand['pinnacle'] = dict(p1=g3[0], x=g3[1], p2=g3[2], **(dict(tot=float(bt[0]), over=bt[1], under=bt[2]) if bt else {}))
                    if cand:
                        order = [s for s in ('fonbet', 'khl-app', 'pinnacle') if s in cand]
                        L = dict(cand[order[0]])
                        L['src'] = order[0]
                        if 'tot' not in L:
                            for s in order[1:]:
                                if 'tot' in cand[s]:
                                    L.update(tot=cand[s]['tot'], over=cand[s]['over'], under=cand[s]['under'], tot_src=s)
                                    break
                        else:
                            L['tot_src'] = order[0]
                        L['t'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
                        L['start'] = x['d']
                        if len(order) > 1:
                            L['alt'] = {s: {k: v for k, v in cand[s].items() if k in ('p1', 'x', 'p2')} for s in order[1:]}
                        lines[key] = L
                        row['line'] = L['src']
                    # модель
                    if T and M and H in T and A in T:
                        try:
                            r = calc.match(T, M, H, A, new.get((H, A)))
                            P = {}
                            for q in r['rows']:
                                P[q['t']] = q['p']
                            p1 = next(v for k, v in P.items() if k.startswith('П1 ') and 'в осн' in k)
                            p2 = next(v for k, v in P.items() if k.startswith('П2 ') and 'в осн' in k)
                            px = P['Х ничья в осн. время']
                            w1, w2 = P.get('итоговая победа %s (с ОТ и Б)' % H), P.get('итоговая победа %s (с ОТ и Б)' % A)
                            tots = {}
                            for l in ('4,5', '5,5', '6,5'):
                                if 'ТБ %s в осн. время' % l in P:
                                    tots[l.replace(',', '.')] = round(P['ТБ %s в осн. время' % l], 3)
                            L = lines.get(key) or {}
                            tl = '%.1f' % L['tot'] if L.get('tot') is not None and '%.1f' % L['tot'] in tots else '5.5'
                            mm = dict(p1=round(p1, 3), x=round(px, 3), p2=round(p2, 3), w1=round(w1, 3) if w1 else None, w2=round(w2, 3) if w2 else None,
                                      tot=float(tl), over=tots.get(tl), totals=tots, lam=[round(r['lam'][0], 2), round(r['lam'][1], 2)],
                                      src='model', ver='jarvis-hockey-v2' if new.get((H, A)) else 'jarvis-hockey-v1',
                                      t=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'))
                            model[key] = mm
                            row['model'] = mm['ver']
                        except Exception as e:  # noqa: BLE001
                            note('%s %s—%s: модель матча не посчитана: %r' % (lg.upper(), H, A, e))
                    today_rows.append(row)
    finally:
        os.chdir(cwd)


# ───────────────────────────────── футбол ─────────────────────────────────
TITLE = {'АПЛ': 'epl', 'Ла Лига': 'laliga', 'Серия А': 'seriea', 'Бундеслига': 'bundesliga', 'Лига 1': 'ligue1',
         'Лига чемпионов': 'ucl', 'Лига Европы': 'uel'}


def _n(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()


def sim(a, b):
    a, b = _n(a), _n(b)
    if not a or not b:
        return 0.0
    ta, tb = set(a.split()), set(b.split())
    j = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return max(difflib.SequenceMatcher(None, a, b).ratio(), j * .9)


def parse_kv(txt):
    out = {}
    for part in txt.split(' · '):
        m = re.match(r'^(.+?) (-?\d+(?:\.\d+)?)(%?)$', part.strip())
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


def parse_fd(text):
    """Вывод football_day.py → [{title, t, ph, pa, pin, fon, prob, lam}]"""
    res, cur = [], None
    for ln in text.split('\n'):
        if ln.startswith('FDMATCH '):
            m = re.match(r'FDMATCH (.+?) \| (\d\d:\d\d) \| .+? \| Pinnacle: (.+?) — (.+)$', ln)
            cur = dict(title=m.group(1), t=m.group(2), ph=m.group(3), pa=m.group(4)) if m else None
            if cur:
                res.append(cur)
        elif cur and ln.startswith('FDLINE '):
            cur['pin'] = parse_kv(ln[7:])
        elif cur and ln.startswith('FDFON '):
            cur['fon'] = parse_kv(ln[6:])
        elif cur and ln.startswith('FDPROB '):
            head, _, rest = ln[7:].partition('|')
            m = re.match(r'λ (\d+\.\d+) : (\d+\.\d+)', head.strip())
            cur['lam'] = [float(m.group(1)), float(m.group(2))] if m else None
            cur['prob'] = {k: v / 100 for k, v in parse_kv(rest).items()}
    return res


def l3(d, tp_pref=''):
    """{'П1':…, 'Х':…, 'П2':…, 'ТБ 2.5':…} → (p1, x, p2, (линия, больше, меньше)|None)"""
    if not d or not all(k in d for k in ('П1', 'Х', 'П2')):
        return None
    tp = {}
    for k, v in d.items():
        if k.startswith('ТБ ') and ('ТМ ' + k[3:]) in d:
            tp[k[3:]] = (v, d['ТМ ' + k[3:]])
    return d['П1'], d['Х'], d['П2'], best_total(tp)


def football(lines, model, today_rows):
    fb = C.jload(os.path.join(C.V3A, 'football', 'data', 'football.json'))
    if not fb:
        note('футбол: нет football.json'); return
    win = window()
    ups = [u for u in fb['up'] if u['t'][:10] in win]
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    by_key = {}
    for u in ups:
        key = C.match_key(u['lg'], u['t'][:10], u['h'], u['a'])
        by_key[key] = u
        mm = dict(p1=u['pr'][0], x=u['pr'][1], p2=u['pr'][2], tot=2.5, over=None, btts=u.get('bt'), lam=u.get('xg'),
                  src='model', ver='poisson-v1', t=now_iso)
        mm['over'] = u.get('ov')            # football/build_data.py: P(тотал больше 2,5)
        model[key] = mm
        if u.get('k') and all(u['k']):
            L = dict(src='espn', t=now_iso, start=u['t'], p1=u['k'][0], x=u['k'][1], p2=u['k'][2])
            if u.get('tt') and u['tt'][1] and u['tt'][2]:
                L.update(tot=u['tt'][0], over=u['tt'][1], under=u['tt'][2], tot_src='espn')
            lines[key] = L
        TN = fb['teams']
        today_rows.append(dict(key=key, lg=u['lg'], t=u['t'], h=u['h'], a=u['a'], hn=TN[u['h']]['n'], an=TN[u['a']]['n'],
                               line=lines.get(key, {}).get('src'), model='poisson-v1'))
    rows_by_key = {r['key']: r for r in today_rows}
    # — команда: football_day.py (Фонбет, Pinnacle, модель)
    fdn = 0
    for day in sorted(win):
        try:
            rc, outp = C.run([sys.executable, os.path.join(C.TEAMCODE, 'team', 'picks', 'football_day.py'), day, '--narrow'],
                             cwd=C.TEAMCODE, timeout=1500)
        except Exception as e:  # noqa: BLE001
            note('футбол %s: football_day.py не отработал: %r' % (day, e)); continue
        if rc != 0:
            note('футбол %s: football_day.py код %d: %s' % (day, rc, outp[-300:].replace('\n', ' ')))
        errs = [l for l in outp.split('\n') if l.startswith('FDERR')]
        if errs:
            note('футбол %s: %s' % (day, '; '.join(e[6:90] for e in errs[:4])))
        for fd in parse_fd(outp):
            lgk = TITLE.get(fd['title'])
            if not lgk:
                continue
            hh, mm_ = fd['t'].split(':')
            tm = int(hh) * 60 + int(mm_)
            cands = []
            for k, u in by_key.items():
                if u['lg'] != lgk or u['t'][:10] != day:
                    continue
                um = int(u['t'][11:13]) * 60 + int(u['t'][14:16])
                if abs(um - tm) <= 20:
                    cands.append((sim(fb['teams'][u['h']]['en'], fd['ph']) + sim(fb['teams'][u['a']]['en'], fd['pa']), k))
            if not cands:
                note('футбол: %s %s %s — %s не сопоставлен с ESPN (нет матча в это время)' % (fd['title'], fd['t'], fd['ph'], fd['pa'])); continue
            cands.sort(reverse=True)
            if len(cands) > 1 and cands[0][0] < 0.9 or cands[0][0] < 0.5:
                note('футбол: %s — %s сопоставлен слабо (%.2f)' % (fd['ph'], fd['pa'], cands[0][0]))
                if cands[0][0] < 0.5:
                    continue
            key = cands[0][1]
            fdn += 1
            srcs = {}
            a = l3(fd.get('fon')) if fd.get('fon') else None
            if a:
                srcs['fonbet'] = a
            a = l3(fd.get('pin'))
            if a:
                srcs['pinnacle'] = a
            if srcs:
                order = [s for s in ('fonbet', 'pinnacle') if s in srcs]
                p1, x, p2, bt = srcs[order[0]]
                L = dict(src=order[0], t=now_iso, start=by_key[key]['t'], p1=p1, x=x, p2=p2)
                if bt is None:                       # тотал берём из следующего источника (Фонбет часто без полного набора)
                    for s in order[1:]:
                        if srcs[s][3]:
                            bt = srcs[s][3]; L['tot_src'] = s; break
                else:
                    L['tot_src'] = order[0]
                if bt:
                    L.update(tot=float(bt[0]), over=bt[1], under=bt[2])
                old = lines.get(key)
                if len(order) > 1:
                    L['alt'] = {s: dict(zip(('p1', 'x', 'p2'), srcs[s][:3])) for s in order[1:]}
                if old and old.get('src') == 'espn':
                    L.setdefault('alt', {})['espn'] = {k: old[k] for k in ('p1', 'x', 'p2')}
                lines[key] = L
                rows_by_key[key]['line'] = L['src']
            pr = fd.get('prob') or {}
            if all(k in pr for k in ('П1', 'Х', 'П2')):
                tl = (lines.get(key) or {}).get('tot')
                tk = 'ТБ %.1f' % tl if tl is not None and 'ТБ %.1f' % tl in pr else 'ТБ 2.5'
                model[key] = dict(p1=round(pr['П1'], 3), x=round(pr['Х'], 3), p2=round(pr['П2'], 3), tot=float(tk[3:]), over=round(pr.get(tk, 0), 3) or None,
                                  btts=round(pr['ОЗ да'], 3) if 'ОЗ да' in pr else None, lam=fd.get('lam'), src='model',
                                  ver='jarvis-foot-fd (football_day.py)', t=now_iso)
                rows_by_key[key]['model'] = 'jarvis-foot-fd'
    note('футбол: матчей в окне %d, сопоставлено с football_day.py: %d' % (len(ups), fdn))


def main():
    lines, model, today_rows = {}, {}, []
    old_l, old_m = C.jload(os.path.join(C.DATA, 'lines.json'), {}) or {}, C.jload(os.path.join(C.DATA, 'model.json'), {}) or {}
    for name, fn in (('hockey', hockey), ('football', football)):
        try:
            fn(lines, model, today_rows)
        except Exception as e:  # noqa: BLE001
            import traceback
            note('%s: шаг упал: %r %s' % (name, e, traceback.format_exc()[-400:].replace('\n', ' | ')))
    today = C.now_msk().date().isoformat()
    # старые записи сегодняшних и будущих матчей, которых нет в новом снимке (матч уже идёт — в списках источников его нет)
    for src, dst in ((old_l, lines), (old_m, model)):
        for k, v in src.items():
            if k.split('|')[1] >= today and k not in dst:
                dst[k] = v
    for k in [k for k in lines if k.split('|')[1] < today]:
        del lines[k]
    for k in [k for k in model if k.split('|')[1] < today]:
        del model[k]
    today_rows.sort(key=lambda r: (r['t'], r['key']))
    C.jsave(os.path.join(C.DATA, 'lines.json'), lines, 'JV_LINES')
    C.jsave(os.path.join(C.DATA, 'model.json'), model, 'JV_MODEL')
    C.jsave(os.path.join(C.DATA, 'today.json'), {'built': C.now_msk().strftime('%Y-%m-%d %H:%M'), 'days': sorted(window()), 'matches': today_rows}, 'JV_TODAY')
    cnt = '%d линий, %d вероятностей модели, %d матчей в окне' % (len(lines), len(model), len(today_rows))
    print(cnt)
    return cnt, notes


if __name__ == '__main__':
    main()
