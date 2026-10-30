# -*- coding: utf-8 -*-
"""Модель учится сама раз в неделю (владелец 30.10, «таблица-агент», шаг 1).

Что делает (workflow .github/workflows/learn-weekly.yml, пн утром):
1) Прогон рейтинга КХЛ и НХЛ на истории — тот же расчёт, что в прогнозах (nhl_bt.py: прогноз на день только по матчам
   ДО этого дня; параметры рейтинга — боевые из nhl_live.BEST / khl_live.BEST), прошлый и этот сезон. Отдельно — старый
   расчёт calc.match (запасной, если новый рейтинг не посчитался; это то, что считал backtest.py).
2) Честная проверка поправки logit(p') = a + b·logit(p) по виду ставки: отложенные данные — матчи последних HOLD_DAYS
   дней. Новая поправка учится на всём, что раньше, и сравнивается с текущей из calib.json по Брайеру на отложенных.
   Принимаем, только если не хуже текущей; тогда коэффициенты пересчитываются на всех данных и пишутся в calib.json
   (NHL2 / KHL2 — новый рейтинг, NHL / KHL — запасной расчёт). Хуже — оставляем как было.
3) «Обещали / зашло» за неделю: модель (все матчи, ставки от 55 %) и наши ставки (team/PICKS.md + SENT.md; правки
   владельца в боте — отдельно, у них нет вероятности модели).
4) Отчёт: team/out/<день>/learn_weekly.md и задание владельцу в бот team/out/<день>/learn_weekly.json (itogi_job.py).

    python team/picks/learn_weekly.py              # всё: обе лиги, calib.json, отчёт
    python team/picks/learn_weekly.py --dry        # не писать calib.json
    python team/picks/learn_weekly.py --part nhl   # служебное: прогон одной лиги → out/learn/nhl.json
"""
import json
import math
import multiprocessing
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'out', 'learn')
CALIB = os.path.join(HERE, 'calib.json')
HOLD_DAYS = 28          # отложенные данные: последние 4 недели
MIN_HOLD = 300          # меньше записей на отложенных — решения не принимаем, оставляем как было
MIN_FIT = 200           # как backtest.py / nhl_bt.py: вид ставки с меньшим числом записей — без поправки
WEEK = 7
LIKELY = 0.55           # «ставки, которые модель считала вероятными» — для «обещали / зашло» по модели
SECTIONS = (('NHL', 'new', 'NHL2'), ('NHL', 'old', 'NHL'), ('KHL', 'new', 'KHL2'), ('KHL', 'old', 'KHL'))
GROUPS = (('инд. тотал', 'инд. тоталы'), ('тотал', 'тоталы'), ('фора', 'форы'), ('не проиграет', '«не проиграет»'),
          ('победа', 'победы'), ('ничья', 'ничьи'))
MSK = timezone(timedelta(hours=3))


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def group_of(kind):
    for pref, name in GROUPS:
        if kind.startswith(pref) or (pref == 'победа' and 'победа' in kind):
            return name
    return kind


# ---------------------------------------------------------------- прогон одной лиги (отдельным процессом)

def part(lg):
    """Записи [день, сезон, вид, p_new, p_old, y] по всем рынкам всех матчей прошлого и этого сезона."""
    sys.argv = [sys.argv[0]] + (['--league', 'khl'] if lg == 'khl' else [])
    import nhl_bt as NB          # флаг лиги nhl_bt читает из sys.argv при импорте
    if lg == 'khl':
        import khl_hist as H
        import khl_live as LV
        allg = H.load()
    else:
        import nhl_hist as H
        import nhl_live as LV
        cur = H.season_of(datetime.now(timezone(timedelta(hours=-5))).date().isoformat())
        allg = H.load(seasons=[cur - 2, cur - 1, cur], with_odds=False)
    for g in allg:
        NB.SEAS.setdefault(g['s'], []).append(g)
    for s in NB.SEAS:
        NB.SEAS[s].sort(key=lambda g: g['d'])
    cur = max(NB.SEAS)
    NB.EVAL = (cur - 1, cur)
    tasks = [(s, d) for s in NB.EVAL if s in NB.SEAS for d in sorted({g['d'][:10] for g in NB.SEAS[s]})]
    with multiprocessing.get_context('fork').Pool(os.cpu_count() or 2) as pool:
        for chunk in pool.map(NB.old_day, tasks):
            NB.OLD.update(dict(chunk))
    nv = NB.new_variant(LV.BEST)
    li = (1 if LV.USE_GOALIE else 0) + (2 if LV.USE_TIRED else 0)      # порядок вариантов в nhl_bt.new_variant
    info = {g['id']: (g['d'][:10], g['s']) for g in allg}
    recs = []
    for gid, o in NB.OLD.items():
        if gid not in nv:
            continue
        d, s = info[gid]
        pm = nv[gid][li]
        for n, kind in enumerate(NB.KEYS):
            p_new = LV.WN * float(pm[n]) + (1 - LV.WN) * o['pe'][n]
            recs.append([d, s, kind, round(p_new, 5), round(o['p'][n], 5), o['y'][n]])
    recs.sort(key=lambda r: r[0])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, lg + '.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(cur=cur, games=len(nv), recs=recs), f, ensure_ascii=False, separators=(',', ':'))
    out('LWPART', '%s: матчей %d, записей %d, сезоны %s' % (lg, len(nv), len(recs), NB.EVAL))


# ---------------------------------------------------------------- поправка: проверка и решение

def decide(recs, idx, cur_ab, today):
    """recs: [[день, сезон, вид, p_new, p_old, y]], idx 3 / 4 — какой расчёт. → (новые коэффициенты или None, отчёт)."""
    import backtest as BT
    hold_from = (today - timedelta(HOLD_DAYS)).isoformat()
    train, hold = defaultdict(list), defaultdict(list)
    for r in recs:
        (hold if r[0] >= hold_from else train)[r[2]].append((r[idx], r[5]))
    n_hold = sum(len(v) for v in hold.values())
    rep = dict(n_hold=n_hold, n_train=sum(len(v) for v in train.values()), kinds={})
    if n_hold < MIN_HOLD:
        rep['why'] = 'мало новых матчей на проверке (%d записей) — оставил как было' % n_hold
        return None, rep
    cand = {k: BT.fit(v) for k, v in train.items() if len(v) >= MIN_FIT}
    b = dict(raw=0.0, cur=0.0, cand=0.0)
    for k, xs in hold.items():
        fc = (lambda p, ab=cur_ab.get(k): BT.apply(ab, p) if ab else p)
        fn = (lambda p, ab=cand.get(k): BT.apply(ab, p) if ab else p)
        kb = dict(raw=BT.brier(xs), cur=BT.brier(xs, fc), cand=BT.brier(xs, fn))
        for t in b:
            b[t] += kb[t] * len(xs)
        rep['kinds'][k] = dict(n=len(xs), **{t: round(v, 4) for t, v in kb.items()})
    for t in b:
        b[t] = round(b[t] / n_hold, 5)
    rep['brier'] = b
    if b['cand'] > b['cur']:
        rep['why'] = 'новая поправка на проверке хуже текущей (Брайер %.4f против %.4f) — оставил как было' % (b['cand'], b['cur'])
        return None, rep
    allk = defaultdict(list)
    for r in recs:
        allk[r[2]].append((r[idx], r[5]))
    new = {k: list(BT.fit(v)) for k, v in sorted(allk.items()) if len(v) >= MIN_FIT}
    rep['why'] = 'новая поправка на проверке не хуже (Брайер %.4f, было %.4f) — поправил' % (b['cand'], b['cur'])
    return new, rep


def week_model(recs, idx, ab_map, today):
    """Модель за неделю: ставки от 55 % (с поправкой, что действовала) по группам видов → {группа: (n, обещано, зашло)}."""
    import backtest as BT
    frm = (today - timedelta(WEEK)).isoformat()
    by = defaultdict(list)
    for r in recs:
        if r[0] < frm:
            continue
        ab = ab_map.get(r[2])
        p = BT.apply(ab, r[idx]) if ab else r[idx]
        if p >= LIKELY:
            by[group_of(r[2])].append((p, r[5]))
    return {g: (len(v), 100 * sum(p for p, _ in v) / len(v), 100 * sum(y for _, y in v) / len(v)) for g, v in by.items()}


# ---------------------------------------------------------------- наши ставки: PICKS.md + SENT.md

def bet_group(text):
    t = text.lower()
    if re.search(r'\s\+\s', t) or ' и тотал' in t:          # «1X + тотал», «П1 и тотал»; «фора +1,5» — не сюда
        return 'комбинированные'
    if re.search(r'инд|ит[12]?[бм]|индивидуальн', t):
        return 'инд. тоталы'
    if 'тотал' in t:
        return 'тоталы'
    if 'фора' in t:
        return 'форы'
    if 'не проиграет' in t or 'не проиграют' in t or re.search(r'\b(1x|x2|2x|1х|х2|2х)\b', t):
        return '«не проиграет»'
    if 'побед' in t or re.search(r'\bп[12]\b', t):
        return 'победы'
    return 'другое'


def our_bets(today):
    """→ {'week': {...}, 'all': {...}}: по группам [ставок с итогом, зашло, обещано (сумма %), с %-ом, правок, правок зашло]."""
    sent = {}
    try:
        for line in open(os.path.join(ROOT, 'team', 'picks', 'SENT.md'), encoding='utf-8'):
            c = [x.strip() for x in line.split('|')]
            if len(c) > 7 and re.match(r'\d{4}-\d+$', c[1]):
                m = re.match(r'([\d,]+)\s*%', c[6])
                sent[c[1]] = (float(m.group(1).replace(',', '.')) if m else None, 'исправил' in c[4])
    except OSError:
        pass
    res = {'week': defaultdict(lambda: [0, 0, 0.0, 0, 0, 0]), 'all': defaultdict(lambda: [0, 0, 0.0, 0, 0, 0])}
    frm = (today - timedelta(WEEK)).isoformat()
    try:
        lines = open(os.path.join(ROOT, 'team', 'PICKS.md'), encoding='utf-8').read().splitlines()
    except OSError:
        lines = []
    for line in lines:
        m = re.match(r'- (\d{4}-\d\d-\d\d) \| ([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|(.*)$', line)
        if not m:
            continue
        d, bet, tail = m.group(1), m.group(4).strip(), m.group(6)
        hit = 0 if 'не зашёл' in tail else (1 if 'зашёл' in tail else None)
        if hit is None:
            continue
        pid = (re.search(r'\((\d{4}-[0-9a-z]+)\)', tail) or [None, None])[1]
        edited = 'правка владельца' in bet.lower() or (pid in sent and sent[pid][1])
        pct = sent.get(pid, (None,))[0] if pid and not edited else None
        for key in ('all',) + (('week',) if d >= frm else ()):
            a = res[key][bet_group(bet)]
            if edited:
                a[4] += 1
                a[5] += hit
            else:
                a[0] += 1
                a[1] += hit
                if pct is not None:
                    a[2] += pct
                    a[3] += 1
    return res


def bets_lines(stat):
    rows = []
    for g, (n, hit, ps, npct, ne, nh) in sorted(stat.items(), key=lambda x: -(x[1][0] + x[1][4])):
        s = '%s: ' % g
        if n:
            s += 'обещали %s, зашло %d из %d (%d %%)' % ('%.0f %%' % (ps / npct) if npct else '— (нет % в SENT.md)', hit, n, round(100 * hit / n))
        if ne:
            s += ('; ' if n else '') + 'ваши правки — зашло %d из %d' % (nh, ne)
        rows.append(s)
    return rows


# ---------------------------------------------------------------- всё вместе

def main():
    dry = '--dry' in sys.argv
    today = datetime.now(MSK).date()
    run = os.environ.get('GITHUB_RUN_NUMBER') or 'локально'
    for lg in ('nhl', 'khl'):
        try:
            os.remove(os.path.join(OUT, lg + '.json'))         # прогон упал — не брать старый файл
        except OSError:
            pass
        r = subprocess.run([sys.executable, os.path.abspath(__file__), '--part', lg], cwd=ROOT)
        if r.returncode:
            out('LWERR', '%s: прогон упал (код %d)' % (lg, r.returncode))
    with open(CALIB, encoding='utf-8') as f:
        calib = json.load(f)
    old_calib = json.loads(json.dumps(calib))
    data = {}
    for lg in ('nhl', 'khl'):
        try:
            with open(os.path.join(OUT, lg + '.json'), encoding='utf-8') as f:
                data[lg.upper()] = json.load(f)
        except (OSError, ValueError):
            data[lg.upper()] = None
    reps, changed, md = {}, [], ['# Самообучение модели — %s (run %s)' % (today.strftime('%d.%m.%Y'), run), '',
                                 'Отложенные данные — матчи последних %d дней; поправка принимается, только если на них '
                                 'Брайер не хуже текущей (`team/picks/learn_weekly.py`).' % HOLD_DAYS, '']
    for lg, which, sec in SECTIONS:
        d = data.get(lg)
        if not d:
            reps[sec] = dict(why='нет данных (прогон лиги упал) — оставил как было')
            continue
        new, rep = decide(d['recs'], 3 if which == 'new' else 4, calib.get(sec) or {}, today)
        reps[sec] = rep
        if new is not None and new != calib.get(sec):
            calib[sec] = new
            changed.append(sec)
        md += ['## %s (%s)' % (sec, 'новый рейтинг, в работе' if which == 'new' else 'запасной расчёт calc.match'),
               '- %s' % rep['why']]
        if rep.get('brier'):
            b = rep['brier']
            md.append('- Брайер на проверке (%d записей): без поправки %.4f · текущая %.4f · новая %.4f'
                      % (rep['n_hold'], b['raw'], b['cur'], b['cand']))
            md.append('')
            md.append('| вид ставки | записей | без поправки | текущая | новая |')
            md.append('|---|---|---|---|---|')
            for k, v in sorted(rep['kinds'].items()):
                md.append('| %s | %d | %.4f | %.4f | %.4f |' % (k, v['n'], v['raw'], v['cur'], v['cand']))
        md.append('')
        out('LWDECIDE', '%s | %s' % (sec, rep['why']))

    # «обещали / зашло» за неделю — модель (новый рейтинг, с поправкой, что действовала неделю)
    week = {}
    for lg in ('KHL', 'NHL'):
        if data.get(lg):
            week[lg] = week_model(data[lg]['recs'], 3, old_calib.get(lg + '2') or {}, today)
    bets = our_bets(today)
    md.append('## За неделю: модель, ставки от %d %% (все матчи)' % round(100 * LIKELY))
    for lg, st in week.items():
        for g, (n, p, y) in sorted(st.items(), key=lambda x: -x[1][0]):
            md.append('- %s, %s: %d ставок, обещали %.1f %%, зашло %.1f %%' % (lg, g, n, p, y))
    md += ['', '## Наши ставки (team/PICKS.md, итог известен)', '### За неделю'] + ['- ' + x for x in bets_lines(bets['week'])]
    md += ['### С начала (15.10)'] + ['- ' + x for x in bets_lines(bets['all'])]

    if changed and not dry:
        calib['learn'] = dict(date=today.isoformat(), run=run, changed=changed,
                              note='learn_weekly.py: отложенные %d дней, принято, если Брайер не хуже текущей' % HOLD_DAYS)
        with open(CALIB, 'w', encoding='utf-8') as f:
            json.dump(calib, f, ensure_ascii=False, indent=1)
            f.write('\n')
    out('LWCHANGED', ','.join(changed) if changed else '-')

    # короткий отчёт владельцу (служебный: цифры можно, в канал не идёт)
    msg = ['Модель — недельная проверка (%s, run %s)' % (today.strftime('%d.%m'), run), '']
    for lg in ('KHL', 'NHL'):
        st = week.get(lg) or {}
        top = sorted(st.items(), key=lambda x: -x[1][0])[:3]
        if top:
            msg.append('%s за неделю, модель (ставки от 55 %%): ' % lg + '; '.join(
                '%s — обещали %.0f %%, зашло %.0f %% (%d)' % (g, p, y, n) for g, (n, p, y) in top))
        r = reps.get(lg + '2') or {}
        msg.append('Поправка %s: %s.' % (lg, r.get('why', '—')))
        msg.append('')
    bl = bets_lines(bets['week'])
    msg.append('Наши ставки за неделю: ' + ('; '.join(bl) if bl else 'итогов нет'))
    old = [s for s in ('KHL', 'NHL') if s in changed]
    if old:
        msg.append('Запасной расчёт (если новый рейтинг не посчитается): поправил %s.' % ', '.join(old))
    msg.append('Подробно: team/out/%s/learn_weekly.md' % today.isoformat())
    text = '\n'.join(msg)
    md += ['', '## Сообщение владельцу', '', '```', text, '```']
    day_dir = os.path.join(ROOT, 'team', 'out', today.isoformat())
    os.makedirs(day_dir, exist_ok=True)
    with open(os.path.join(day_dir, 'learn_weekly.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    with open(os.path.join(day_dir, 'learn_weekly.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(day=today.isoformat(), make=[], messages=[dict(to='owner', type='text', text=text)]),
                  f, ensure_ascii=False, indent=1)
    print(text, flush=True)


if __name__ == '__main__':
    if '--part' in sys.argv:
        part(sys.argv[sys.argv.index('--part') + 1])
    else:
        main()
