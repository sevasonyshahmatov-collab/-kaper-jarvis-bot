# -*- coding: utf-8 -*-
"""Новый рейтинг КХЛ в ежедневных прогнозах (владелец 29.10: «да, начинай КХЛ») — как nhl_live.py для НХЛ.

  • сила команд — nhl_model.py по матчам этого сезона (вместо xG — броски в створ × реализация лиги, team/picks/khl_hist.py)
    и сжатой силе прошлого сезона; параметры — лучшие по проверке на истории (nhl_bt.py --league khl, BEST ниже);
  • вратарь: подтверждённых стартеров у КХЛ заранее нет — «по ротации»: кто стоял в прошлой игре; если команда играла
    вчера — второй вратарь по числу игр; качество — пропущено против среднего вратаря на тех же бросках;
  • два дня подряд — по расписанию.
В лог: NHLRATE (тот же формат, что у НХЛ: brief.md его подхватывает), NHLGK, NHLLIVEERR.
Отдельно: python team/picks/khl_live.py 2026-10-30"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import khl_hist as KH  # noqa: E402
import nhl_model as MO  # noqa: E402

BEST = dict(MO.P0)
USE_GOALIE, USE_TIRED, WN = True, True, 0.8


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def prepare(day, nxt):
    """nxt — матчи дня из khl_data.fetch. → {(хозяева, гости): dict(lh, la, s, info)}; пусто — считать по-старому."""
    cur = KH.season_of(day)
    G = KH.load(seasons=[cur - 2, cur - 1, cur], today=day)
    S = {}
    for g in G:
        S.setdefault(g['s'], []).append(g)
    if not S.get(cur):
        out('NHLLIVEERR', 'КХЛ: нет матчей текущего сезона — новый рейтинг не считаю')
        return {}
    P = BEST
    final = {}
    for s in sorted(S):
        prior = MO.shrink_prior(final[s - 1], P) if s - 1 in final else None
        final[s] = MO.ratings(S[s], P, prior, final[s - 1]['mu'] if s - 1 in final else None)
    R = final[cur]
    r100 = MO.rating100(R)
    GT = MO.goalie_table(S[cur], S.get(cur - 1), P)
    res = {}
    for x in nxt:
        H, A = x['h'], x['a']
        info, gks = {}, {}
        for side, team in (('h', H), ('a', A)):
            tired = MO.tired(S[cur], team, x['d'])
            own = [g for g in S[cur] if team in (g['h'], g['a']) and g.get('g')]
            starts = Counter(g['g'][0 if g['h'] == team else 1] for g in own)
            last = own[-1]['g'][0 if own[-1]['h'] == team else 1] if own else None
            gid, how = last, 'по ротации'
            if tired and len(starts) > 1:
                gid = next(k for k, _ in starts.most_common() if k != last)
                how = 'по ротации (вчера играл другой)'
            f = MO.goalie_factor(GT, gid, P)
            gks[side] = f
            gx = MO.gsax(GT, gid)
            info[side] = dict(rate=r100.get(team), att=round(R['A'].get(team, 1), 2), de=round(R['D'].get(team, 1), 2),
                              tired=tired, goalie=gid or '—', how=how, gsax=None if gx is None else round(gx, 1), gk=round(f, 3))
            for k, n in starts.most_common():
                v = MO.gsax(GT, k)
                out('NHLGK', '%s | %s: игр %d в этом сезоне, пропущено против среднего вратаря на тех же бросках '
                    '(этот сезон + ½ прошлого) %s' % (team, k, n, '—' if v is None else '%+.1f' % v))
        lh, la = MO.lam(R, H, A, P, gks['h'] if USE_GOALIE else 1.0, gks['a'] if USE_GOALIE else 1.0,
                        info['h']['tired'] and USE_TIRED, info['a']['tired'] and USE_TIRED)
        s = MO.ot_share(lh, la)
        res[(H, A)] = dict(lh=lh, la=la, s=s, info=info)
        out('NHLRATE', '%s — %s | сила 1–100: %s %s, %s %s | λ %.2f : %.2f | вратари (не подтверждены): %s (%s, %s), %s (%s, %s) | '
            'два дня подряд: %s' % (H, A, H, info['h']['rate'], A, info['a']['rate'], lh, la,
                                    info['h']['goalie'], info['h']['how'], info['h']['gsax'], info['a']['goalie'],
                                    info['a']['how'], info['a']['gsax'],
                                    ', '.join(t for t, k in ((H, 'h'), (A, 'a')) if info[k]['tired']) or 'нет'))
    out('NHLRATEALL', 'КХЛ: ' + ' · '.join('%s %d' % (t, r100[t]) for t in sorted(r100, key=lambda t: -r100[t])))
    return res


if __name__ == '__main__':
    import khl_data
    d = sys.argv[1]
    _, nxt = khl_data.fetch(d)
    prepare(d, nxt)
