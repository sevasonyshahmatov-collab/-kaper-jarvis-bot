# -*- coding: utf-8 -*-
"""Статистика прогнозов канала @jarvibet по месяцам — для лендинга (владелец 23.10: «только то, что я выложил и не удалил»).

Источник — публичная лента t.me/s/jarvibet (team/daily/channel.py): посты-прогнозы с шапкой «КХЛ · 15 октября · 18:00 МСК»,
последняя версия поста, один пост на матч; удалённых постов в ленте нет. Итог — по счёту матча, как утренние итоги
(morning.settle_rows). Облачная сессия до t.me не достаёт — запускать в GitHub Actions.

  python team/site/months.py 2026-09-01 [OUT]  → OUT/months.json (по месяцам: n, w, l, p, kef, units) и OUT/months.md
                                                 (список всех прогнозов и что не вошло — для сверки владельцем)
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in ('team/daily', 'team/picks', 'team/reels_daily', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))

import channel  # noqa: E402
import data  # noqa: E402
import morning  # noqa: E402
from data import MSK  # noqa: E402

MONTH = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def month_stats(rows):
    """Рассчитанные прогнозы → [{m: 'ГГГГ-ММ', name, n, w, l, p, kef (средний), units (плюс/минус при ставке 1 на каждый)}]."""
    by = {}
    for r in rows:
        k = r['start'].astimezone(MSK).strftime('%Y-%m')
        by.setdefault(k, []).append(r)
    out = []
    for k in sorted(by):
        rs = by[k]
        w = [r for r in rs if r['res'] == 'win']
        l = [r for r in rs if r['res'] == 'loss']
        kefs = [r['kef'] for r in rs if r.get('kef')]
        units = sum(r['kef'] - 1 for r in w if r.get('kef')) - len(l)
        out.append(dict(m=k, name=MONTH[int(k[5:])], n=len(rs), w=len(w), l=len(l), p=len(rs) - len(w) - len(l),
                        kef=round(sum(kefs) / len(kefs), 2) if kefs else None, units=round(units, 2)))
    return out


def main():
    t0 = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=MSK) if len(sys.argv) > 1 else datetime(2026, 9, 1, tzinfo=MSK)
    out = sys.argv[2] if len(sys.argv) > 2 else 'out/months'
    channel.MAX_PAGES = 80                           # ~20 постов на страницу: с запасом до начала сентября
    t1 = datetime.now(MSK)
    seen = {}
    feed = channel.feed
    channel.feed = lambda t: seen.setdefault('v', feed(t))  # лента одна: и для прогнозов, и для списка нераспознанных
    picks, chan = channel.posts(t0, t1)
    used = {p['msg_id'] for p in chan['picks']}
    odd = [x for x in seen['v'][0] if x['id'] not in used and x['posted'] and x['posted'] >= t0
           and any(w in ' '.join(t for t, _ in x['text']).lower() for w in ('прогноз', 'кэф', 'коэф'))]
    found, errs = data.games_for(picks) if picks else ({}, [])
    rows, pending, bad = morning.settle_rows(picks, found)
    stats = month_stats(rows)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'months.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    res = {'win': 'зашёл', 'loss': 'не зашёл', 'push': 'возврат'}
    lines = ['# Прогнозы канала @jarvibet с %s' % t0.strftime('%d.%m.%Y'),
             'Прочитано страниц ленты: %s, постов: %s.' % (chan.get('pages'), chan.get('total')), '']
    for s in stats:
        lines.append('**%s %s**: прогнозов %d, зашло %d, не зашло %d, возврат %d, средний кэф %s, итог при ставке 1: %+.2f' % (
            s['name'], s['m'][:4], s['n'], s['w'], s['l'], s['p'], s['kef'], s['units']))
    lines += ['', '## Все прогнозы', '']
    for r in sorted(rows, key=lambda r: r['start']):
        g = r['g']
        lines.append('- %s №%d %s %s — %s: %s, кэф %s → %s (%s:%s%s)' % (
            r['start'].astimezone(MSK).strftime('%d.%m %H:%M'), r['msg_id'], r['league'], r['home'], r['away'], r['bet'],
            r.get('kef'), res.get(r['res'], r['res']), g.get('hg'), g.get('ag'), (' ' + g['end']) if g.get('end') else ''))
    if pending or bad:
        lines += ['', '## Не вошли', '']
        for p, why in pending + bad:
            lines.append('- №%d %s — %s: %s (%s)' % (p['msg_id'], p['home'], p['away'], p['bet'], why))
    if odd:
        lines += ['', '## Посты со словами «прогноз»/«кэф», не узнанные как прогноз (проверить: может, старый формат)', '']
        for x in odd:
            lines.append('- №%d %s: %s' % (x['id'], x['posted'].strftime('%d.%m'), ' / '.join(t for t, _ in x['text'])[:160]))
    if chan.get('notes') or errs:
        lines += ['', '## Заметки', ''] + ['- %s' % n for n in chan.get('notes', [])] + ['- %s' % e for e in errs]
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(out, 'months.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)
    print('MONTHS %s' % json.dumps(stats, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
