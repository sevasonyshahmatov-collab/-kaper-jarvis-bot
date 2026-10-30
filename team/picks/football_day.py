# -*- coding: utf-8 -*-
"""Футбол: данные на матчи дня для прогнозов (ТЗ docs/handoff/FOOTBALL_BRIEF.md, этап 2; «да» владельца на пробу 30.10).

Турниры пробы: АПЛ, Ла Лига, Серия А, Бундеслига, Лига 1, Лига чемпионов, Лига Европы (Португалия и Лига конференций —
не проходят проверку на истории, team/out/2026-10-30/football_bt.md). День — по Москве.
По каждому матчу печатает:
  FDMATCH  турнир | время МСК | хозяева — гости (имена football-data) | Pinnacle: имена
  FDLINE   кэфы Pinnacle 90 минут (П1 Х П2, тоталы, «не проиграет» = фора +0,5)
  FDPROB   вероятности: смесь модели с линией (как в проверке), λ модели
  FDPICK   «ВЫБОР <ставка> @кэф p» — самая вероятная из FOOT.markets с кэфом ≥ 1,6 и p ≥ FOOT_P; нет — «нет ставки»
  FDFORM   последние 5 матчей команды (дата, соперник, счёт, xG) и место/очки в лиге
  FDH2H    последние очные встречи (лиги, 3 сезона)
  FDERR    ошибки (нет линии, нет команды в истории)
Боевых прогнозов не шлёт. Запуск: python team/picks/football_day.py 2026-10-31"""
import bisect
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import football_bt as BT  # noqa: E402
import football_hist as FH  # noqa: E402
import football_live as FL  # noqa: E402
import football_model as FM  # noqa: E402

TOURN = [('E0', 'АПЛ'), ('SP1', 'Ла Лига'), ('I1', 'Серия А'), ('D1', 'Бундеслига'), ('F1', 'Лига 1'),
         ('UCL', 'Лига чемпионов'), ('UEL', 'Лига Европы')]


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def prep_x(games, C, lg):
    coef = (C.get('xg_coef') or {}).get(lg, (0.3, 0.03))
    for g in games:
        g.pop('x', None)
        if C.get('xg') == 'us' and g.get('xg'):
            g['x'] = g['xg']
        elif 'st' in g and lg in FH.OURS:
            g['x'] = [coef[0] * g['st'][i] + coef[1] * max(0, g['sh'][i] - g['st'][i]) for i in (0, 1)]


def find_team(name, data, s, only=None):
    """Имя Pinnacle → (лига, имя football-data): сначала среди only (лига турнира), потом во всех лигах сезона."""
    nn = FH.norm(name)
    if any(w in nn for w in FH.FOREIGN):
        return None, None
    best = (0, None, None)
    for code, gs in data['dom'].items():
        if only and code != only:
            continue
        names = {g['h'] for g in gs if g['s'] in (s, s - 1)} | {g['a'] for g in gs if g['s'] in (s, s - 1)}
        for c in names:
            sc = FH.score_name(nn, c)
            if sc > best[0]:
                best = (sc, code, c)
    return (best[1], best[2]) if best[0] >= 0.8 else (None, None)


def form(games, team, day, n=5):
    rows = [g for g in games if g['d'] < day and team in (g['h'], g['a'])][-n:]
    res = []
    for g in rows:
        home = g['h'] == team
        gf, ga = (g['hg'], g['ag']) if home else (g['ag'], g['hg'])
        x = g.get('xg')
        xs = ' xG %.1f:%.1f' % ((x[0], x[1]) if home else (x[1], x[0])) if x else ''
        res.append('%s %s %s %d:%d%s' % (g['d'][5:], 'д' if home else 'г', g['a'] if home else g['h'], gf, ga, xs))
    return res


def table(games, s, day):
    pts, gd, n = defaultdict(int), defaultdict(int), defaultdict(int)
    for g in games:
        if g['s'] != s or g['d'] >= day:
            continue
        for t, f, a in ((g['h'], g['hg'], g['ag']), (g['a'], g['ag'], g['hg'])):
            pts[t] += 3 if f > a else (1 if f == a else 0)
            gd[t] += f - a
            n[t] += 1
    order = sorted(pts, key=lambda t: (-pts[t], -gd[t]))
    return {t: (i + 1, pts[t], n[t], gd[t]) for i, t in enumerate(order)}


def main(day):
    P, C = FL.conf()
    floor = C.get('FOOT_P', 0.6)
    kinds = C.get('markets') or []
    st = C.get('stack') or {}
    cal = C.get('calib') or {}
    data = FH.load()
    s = FH.season_of(day)
    dom = {lg: sorted(gs, key=lambda g: g['d']) for lg, gs in data['dom'].items()}
    for lg in dom:
        prep_x(dom[lg], C, lg)
    fits = {}

    def rating(lg):
        if lg not in fits:
            known = {g['h'] for g in dom[lg] if g['s'] == s - 1}
            fits[lg] = FM.fit(dom[lg], day, P, known)
        return fits[lg]

    cupctx = None
    total = picks = 0
    for code, title in TOURN:
        try:
            line = FL.pin_day(code, day)
        except Exception as e:
            out('FDERR', '%s: линия Pinnacle недоступна %r' % (title, e))
            continue
        if not line:
            continue
        for (ph, pa, t), od in sorted(line.items(), key=lambda kv: kv[0][2]):
            if code in FH.OURS:
                (lh_, h), (la_, a) = find_team(ph, data, s, code), find_team(pa, data, s, code)
            else:
                (lh_, h), (la_, a) = find_team(ph, data, s), find_team(pa, data, s)
            total += 1
            out('FDMATCH', '%s | %s | %s — %s | Pinnacle: %s — %s' % (title, t, h or '?', a or '?', ph, pa))
            out('FDLINE', ' · '.join('%s %.2f' % (k, od[k]) for k in sorted(od)))
            if code in FH.OURS:
                if not h or not a:
                    out('FDERR', 'нет в истории лиги: %s — %s' % (ph, pa))
                    continue
                R, mh, ma = rating(code)
                lh, la = FM.lambdas(R, mh, ma, h, a, P)
            else:
                if cupctx is None:
                    cupctx = cup_context(data, dom, P, day)
                lh, la = cup_lams(cupctx, (lh_, h), (la_, a), rating, P)
            m = FM.markets(lh, la, P['rho'])
            mk = FL.line_probs(od, P['rho'])
            pr = {}
            for k, p in m.items():
                if mk and k in mk and k in st:
                    a_, b_, c_ = st[k]
                    p = 1 / (1 + math.exp(-(a_ + b_ * BT.logit(p) + c_ * BT.logit(mk[k]))))
                elif k in cal:
                    p = BT.cal(cal, k, p)
                pr[k] = p
            out('FDPROB', 'λ %.2f : %.2f | %s' % (lh, la, ' · '.join('%s %.1f%%' % (k, 100 * pr[k]) for k in sorted(pr))))
            ok = [(pr[k], k, od[k]) for k in od if k in pr and k in kinds and od[k] >= 1.6 and pr[k] >= floor]
            if ok:
                p, k, o = max(ok)
                picks += 1
                out('FDPICK', 'ВЫБОР %s @%.2f | p %.1f%%' % (k, o, 100 * p))
            else:
                best = max(((pr[k], k, od[k]) for k in od if k in pr and k in kinds and od[k] >= 1.6), default=None)
                out('FDPICK', 'нет ставки от %d%% (лучшая с кэфом от 1,6: %s)' % (
                    100 * floor, '%s @%.2f p %.1f%%' % (best[1], best[2], 100 * best[0]) if best else '—'))
            for side, (lg_, tm) in (('х', (lh_, h)), ('г', (la_, a))):
                if not tm or lg_ not in dom:
                    continue
                tb = table(dom[lg_], s, day).get(tm)
                pos = ' | %s: %d место, %d очк. за %d игр, разница %+d' % (lg_, tb[0], tb[1], tb[2], tb[3]) if tb else ''
                out('FDFORM', '%s %s%s | %s' % (side, tm, pos, '; '.join(form(dom[lg_], tm, day))))
            if h and a and lh_ == la_ and lh_ in dom:
                hh = [g for g in dom[lh_] if {g['h'], g['a']} == {h, a} and g['d'] < day][-3:]
                if hh:
                    out('FDH2H', '; '.join('%s %s %d:%d %s' % (g['d'], g['h'], g['hg'], g['ag'], g['a']) for g in hh))
    out('FDDONE', 'матчей %d, ВЫБОР %d, порог %d%%' % (total, picks, 100 * floor))


def cup_context(data, dom, P, day):
    """Сила лиг по еврокубкам до дня (как в проверке): снимки рейтингов лиг на дни кубковых матчей → fit_league_factors."""
    snaps_all = {}
    for lg in dom:
        snaps = BT.snapshots(dom[lg], P, FH.season_of(day) - 3)
        snaps_all[lg] = dict(days=sorted(snaps), snap=snaps)
    cups = sorted(data['cup'], key=lambda g: g['d'])
    lgs = set(snaps_all)
    rat = {'lgs': lgs}
    for g in cups:
        r = []
        for side in ('h', 'a'):
            t, lg = g[side], g[side + 'l']
            v = BT.team_rating(snaps_all, lg, t, g['d']) if lg in lgs and not t.startswith('espn:') else None
            r.append(v or (1.0, 1.0))
        rat[id(g)] = tuple(r)
    F, mu, hm = BT.fit_league_factors(cups, day, rat, dict(hl=365.0, k=3.0))
    out('FDCUPLG', 'сила лиг: ' + ' · '.join('%s %.2f/%.2f' % (k, v[0], v[1]) for k, v in sorted(F.items())))
    return dict(F=F, mu=mu, hm=hm, lgs=lgs)


def cup_lams(ctx, home, away, rating, P):
    F, mu, hm = ctx['F'], ctx['mu'], ctx['hm']
    rr = []
    for lg, tm in (home, away):
        r = (1.0, 1.0)
        if lg and tm:
            R = rating(lg)[0]
            r = R.get(tm, (1.0, 1.0))
        f = F.get(lg if lg in ctx['lgs'] else '?', (1.0, 1.0))
        rr.append((r, f))
    (rh, fh), (ra, fa) = rr
    return mu * rh[0] * fh[0] * ra[1] * fa[1] * hm, mu * ra[0] * fa[0] * rh[1] * fh[1] / hm


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else datetime.now(FL.MSK).strftime('%Y-%m-%d'))
