# -*- coding: utf-8 -*-
"""Заходимость всех прогнозов, отправленных владельцу в бот (team/picks/SENT.md, с 15.10), — владелец 29.10.
Счёт — из приложения КХЛ / API НХЛ (team/daily/data.py), расчёт — team/daily/settle.py.
Два среза: «как прислал бот» (все черновики, повторы одного матча с той же ставкой — один раз) и «как в канале»
(опубликованные владельцем, с его правками). В лог — строки HR_ROW / HR_SUM, итог владельцу — в задание.

  python3 team/out/2026-10-29/hitrate.py [--job team/out/2026-10-29/hitrate.json]
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))

import data  # noqa: E402
import ledger  # noqa: E402
import settle  # noqa: E402

NOW = datetime.now(data.MSK)


def promised(sent_text):
    """«Что заходит» из SENT.md: {pid: вероятность 0..1}."""
    out = {}
    for line in sent_text.splitlines():
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 6 and re.fullmatch(ledger.PID, c[0]):
            m = re.search(r'(\d+)[,.]?(\d*)\s*%', c[5])
            if m:
                out[c[0]] = float(m.group(1) + '.' + (m.group(2) or '0')) / 100
    return out


def kind(bet):
    b = bet.lower()
    if 'индивидуальный тотал' in b or re.search(r'\bит[бм1-2]', b):
        k = 'инд. тотал'
    elif 'тотал' in b:
        k = 'тотал ' + ('больше' if 'больше' in b else 'меньше')
    elif 'фора' in b:
        k = 'фора'
    elif 'не проиграет' in b or 'не проиграют' in b:
        k = 'двойной шанс'
    elif 'итоговая' in b or 'с учётом от' in b:
        k = 'победа с ОТ'
    else:
        k = 'победа в осн. время'
    return k


def stats(rows):
    w = sum(r['res'] == settle.WIN for r in rows)
    l_ = sum(r['res'] == settle.LOSS for r in rows)
    pu = sum(r['res'] == settle.PUSH for r in rows)
    profit = sum((r['kef'] - 1) if r['res'] == settle.WIN else (-1 if r['res'] == settle.LOSS else 0)
                 for r in rows if r.get('kef'))
    staked = sum(1 for r in rows if r.get('kef') and r['res'] != settle.PUSH)
    pr = [r['p'] for r in rows if r.get('p') and r['res'] != settle.PUSH]
    kefs = [r['kef'] for r in rows if r.get('kef')]
    return dict(n=len(rows), w=w, l=l_, push=pu, hit=(w / (w + l_) if w + l_ else 0),
                roi=(profit / staked if staked else 0), profit=profit,
                promised=(sum(pr) / len(pr) if pr else 0), kef=(sum(kefs) / len(kefs) if kefs else 0))


def fmt(s):
    return '%d из %d (%.0f %%), возвратов %d, обещали %.0f %%, ср. кэф %.2f, итог %+.1f ед. (ROI %+.0f %%)' % (
        s['w'], s['w'] + s['l'], 100 * s['hit'], s['push'], 100 * s['promised'], s['kef'], s['profit'], 100 * s['roi'])


def main():
    job = sys.argv[sys.argv.index('--job') + 1] if '--job' in sys.argv else None
    with open(os.path.join(ROOT, 'team', 'picks', 'SENT.md'), encoding='utf-8') as f:
        sent_text = f.read()
    led = ledger.Ledger(NOW)
    prom = promised(sent_text)

    # «как прислал бот»: все черновики, один раз на (матч, ставка)
    bot, seen = [], set()
    for pid, row in sorted(led.sent.items(), key=lambda x: (x[1]['start'], int(x[0].split('-')[1]))):
        key = (row['league'], row['home'], row['away'], row['start'].date(), row['bet'].lower())
        if key in seen:
            continue
        seen.add(key)
        bot.append(dict(row, p=prom.get(pid)))
    # «как в канале»: опубликованные, с правками владельца
    chan = []
    for pid, ts in led.pub.items():
        row = led.sent.get(pid)
        if row:
            bet, kef, ch = ledger.channel_version(row, ts, led.edits)
            chan.append(dict(row, bet=bet, kef=kef, edited=ch, p=prom.get(pid) if not ch else None))

    picks = [p for p in bot + chan if p['start'] < NOW - timedelta(hours=3)]
    found, errs = data.games_for(picks)
    for e in errs:
        print('HR_ERR', e, flush=True)

    out = {}
    for name, lst in (('bot', bot), ('chan', chan)):
        lst = [p for p in lst if p['start'] < NOW - timedelta(hours=3)]
        rows, pending, bad = settle_rows(lst, found)
        out[name] = rows
        for r in rows:
            print('HR_ROW', name, r['pid'], r['league'], r['start'].strftime('%d.%m'), '%s — %s' % (r['home'], r['away']),
                  '%s:%s%s' % (r['g']['hg'], r['g']['ag'], (' ' + r['g']['end']) if r['g'].get('end') else ''),
                  '|', r['bet'], '|', r.get('kef'), '|', r.get('p'), '|', r['res'], flush=True)
        for p, why in pending:
            print('HR_PEND', name, p['pid'], p['home'], p['away'], why, flush=True)
        for p, why in bad:
            print('HR_BAD', name, p['pid'], p['bet'], why, flush=True)

    lines = []
    for name, title in (('bot', 'Все прогнозы бота (черновики)'), ('chan', 'Опубликованные в канале (с вашими правками)')):
        rows = out[name]
        lines.append('<b>%s</b>' % title)
        lines.append('Всего: ' + fmt(stats(rows)))
        for lg, lgn in (('KHL', 'КХЛ'), ('NHL', 'НХЛ')):
            lines.append('%s: %s' % (lgn, fmt(stats([r for r in rows if r['league'] == lg]))))
        print('HR_SUM', name, fmt(stats(rows)), flush=True)
        if name == 'bot':
            cut = datetime(2026, 10, 22, 12, 0, tzinfo=data.MSK)     # поправка вероятностей (calib.json) с 22.10
            for lg in ('KHL', 'NHL'):
                for lab, f_ in (('до 22.10', lambda r: r['start'] < cut), ('с 22.10', lambda r: r['start'] >= cut)):
                    print('HR_PERIOD', lg, lab, fmt(stats([r for r in rows if r['league'] == lg and f_(r)])), flush=True)
            by = defaultdict(list)
            for r in rows:
                by[(r['league'], kind(r['bet']))].append(r)
            for k in sorted(by):
                print('HR_KIND', k[0], k[1], fmt(stats(by[k])), flush=True)
            buck = defaultdict(list)
            for r in rows:
                if r.get('p'):
                    buck[(r['league'], min(int(r['p'] * 20) * 5, 75))].append(r)
            for k in sorted(buck):
                print('HR_BUCKET', k[0], '%d–%d %%' % (k[1], k[1] + 5), fmt(stats(buck[k])), flush=True)
        lines.append('')

    text = 'Заходимость прогнозов с 15.10 по %s\n\n' % NOW.strftime('%d.%m') + '\n'.join(lines).strip()
    print(text, flush=True)
    if job:
        with open(os.path.join(ROOT, job), encoding='utf-8') as f:
            j = json.load(f)
        j['messages'] = [{'to': 'owner', 'type': 'text', 'html': True, 'text': text}]
        with open(os.path.join(ROOT, job), 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, indent=1)


def settle_rows(picks, found):
    rows, pending, bad = [], [], []
    for p in picks:
        g = data.match_game(found, p)
        if not g:
            pending.append((p, 'матч не найден'))
            continue
        if g['state'] != 'final':
            pending.append((p, g['state']))
            continue
        try:
            res, legs, why = settle.settle(p['bet'], p['home'], p['away'], g)
        except ValueError as e:
            bad.append((p, str(e)))
            continue
        rows.append(dict(p, g=g, res=res))
    return rows, pending, bad


if __name__ == '__main__':
    main()
