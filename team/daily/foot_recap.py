# -*- coding: utf-8 -*-
"""Утренние «Итоги прогнозов» по футболу — отдельным постом от хоккея (владелец 31.10).

Источник — сам канал, как у хоккея: футбольные посты-прогнозы ленты t.me/s/jarvibet (шапка «АПЛ · 31 октября · 18:00 МСК»)
на матчи с началом в окне утра (08:00 вчера – 08:00 сегодня, ask.window). Только опубликованное в канал; купоны
«экспресс» (шапка без времени) не попадают. Счёт за 90 минут — ESPN (team/postmatch/foot.py), расчёт — settle.py.
Текст — тот же шаблон владельца (compose.recap_post), баннер — banner.render (футбольные эмблемы), номер поста ММДД-f1.
Нет футбольных ставок за окно — поста нет.
  python3 team/daily/foot_recap.py 2026-11-01 --dry"""
import os
import re
import sys
import traceback
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [HERE, os.path.join(ROOT, 'team', 'postmatch'), os.path.join(ROOT, 'render')]

import ask  # noqa: E402
import channel  # noqa: E402
import compose  # noqa: E402
import settle  # noqa: E402
from data import MSK  # noqa: E402

TOURS = ['АПЛ', 'Ла Лига', 'Серия А', 'Бундеслига', 'Лига 1', 'Лига чемпионов', 'Лига Европы', 'Лига конференций', 'Португалия']
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
HEAD = re.compile(r'^\W*(%s)\s*[·•|∙⋅-]\s*(\d{1,2})\s+([а-яё]+)\s*[·•|∙⋅-]\s*(\d{1,2})[:.](\d\d)' % '|'.join(TOURS), re.I)


def pick_of(post, year):
    """Футбольный пост-прогноз ленты → dict или None."""
    lines = [t for t, _ in post['text']]
    hi = next((i for i, t in enumerate(lines[:2]) if HEAD.match(t)), None)
    if hi is None:
        return None
    m = HEAD.match(lines[hi])
    tour = next(x for x in TOURS if x.lower() == m.group(1).lower())
    try:
        mon = MONTHS.index(m.group(3).lower()) + 1
    except ValueError:
        return None
    start = datetime(year, mon, int(m.group(2)), int(m.group(4)), int(m.group(5)), tzinfo=MSK)
    p = dict(msg_id=post['id'], pid='№%d' % post['id'], league='FOOT', tour=tour, start=start, home=None, away=None, bet=None, kef=None)
    for t in lines[hi + 1:]:
        tm = re.match(r'^(.+?)\s+[—–]\s+(.+)$', t.strip())
        if tm and not p['home'] and ':' not in t:
            p['home'], p['away'] = (x.replace('«', '').replace('»', '').strip() for x in tm.groups())
        bm = re.match(r'(?i)^\s*прогноз:\s*(.+)$', t)
        if bm and not p['bet']:
            p['bet'] = bm.group(1).strip()
        km = re.match(r'(?i)^\s*к[эе]ф:\s*([\d.,]+)', t)
        if km and p['kef'] is None:
            try:
                p['kef'] = float(km.group(1).replace(',', '.'))
            except ValueError:
                pass
    return p if p['home'] and p['bet'] else None


def rows_for(d):
    """→ (рассчитанные строки, не рассчитано [(прогноз, почему)])."""
    import foot
    t0, t1 = ask.window(d)
    posts, _ = channel.feed(t0)
    by_match = {}
    for post in sorted(posts, key=lambda x: x['id']):
        p = pick_of(post, t1.year)
        if p and t0 <= p['start'] < t1:
            by_match[(p['home'], p['away'], p['start'])] = p          # один матч в двух постах — последний пост
    rows, skipped = [], []
    for p in sorted(by_match.values(), key=lambda x: x['start']):
        print('FOOT_RECAP | %s | %s | %s — %s | %s | %s | кэф %s' % (p['pid'], p['tour'], p['home'], p['away'],
              p['start'].strftime('%d.%m %H:%M'), p['bet'], p['kef']), flush=True)
        try:
            g = foot.game(p)
        except Exception as e:  # noqa: BLE001
            skipped.append((p, 'ESPN: %r' % e))
            continue
        if not g or g['state'] != 'final':
            skipped.append((p, 'матч не найден в ESPN' if not g else 'не доигран'))
            continue
        g = dict(g, hg=g['reg'][0], ag=g['reg'][1])                      # ставки — на 90 минут
        try:
            res, legs, why = settle.settle(p['bet'], p['home'], p['away'], g)
        except ValueError as e:
            skipped.append((p, str(e)))
            continue
        leg_res = [settle.settle_leg(x, g) for x in legs]
        rows.append(dict(p, g=g, res=res, legs=legs, why=why, short=settle.short(legs, p['home'], p['away']),
                         leg_push=len(legs) > 1 and settle.PUSH in leg_res))
    return rows, skipped


def build(d, plan, out_dir, card=True):
    """→ (сообщения: пост итогов и, если надо, баннер отдельно; строка для вступления владельцу)."""
    try:
        rows, skipped = rows_for(d)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return [], 'футбол: итоги не собрались (%s)' % compose.esc(repr(e)[:100])
    note = ''
    if skipped:
        note = 'футбол без расчёта: ' + compose.esc('; '.join('%s — %s (%s)' % (p['home'], p['away'], why) for p, why in skipped))
    if not rows:
        return [], note or 'футбол: ставок в канале за окно нет — поста нет'
    recap = compose.recap_post(d, rows, None, plan)
    text = '⚽ <b>Футбол</b>\n\n' + recap['text'].replace('🏒', '⚽')
    images = []
    if card:
        try:
            import banner
            import football
            football.register()
            days = sorted({r['start'].strftime('%d.%m') for r in rows}, key=lambda x: (x[3:], x[:2]))
            images = banner.render(rows, out_dir, '%s · зашло %s' % ('–'.join(days[::max(1, len(days) - 1)]), compose.score_line(recap['tally'])))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            note += ('; ' if note else '') + 'футбольный баннер не нарисовался: %s' % compose.esc(repr(e)[:80])
    pid = '%s-f1' % d.strftime('%d%m')
    post = dict(to='owner', html=True, buttons='post', emoji=True)
    rel = [os.path.relpath(x, ROOT) for x in images]
    if rel and len(text) <= compose.CAPTION_MAX:
        msgs = [dict(post, type='photo' if len(rel) == 1 else 'album', files=rel, text=text, pid=pid)]
    else:
        msgs = [dict(post, type='text', text=text, pid=pid)]
        if rel:
            msgs.append(dict(post, type='photo' if len(rel) == 1 else 'album', files=rel, text='', pid='%s-f2' % d.strftime('%d%m')))
    return msgs, 'футбол: %d (зашло %s)%s' % (len(rows), compose.score_line(recap['tally']), ('; ' + note) if note else '')


if __name__ == '__main__':
    import morning
    d = date.fromisoformat(sys.argv[1])
    msgs, note = build(d, morning.engine().plan(d, 7), os.path.join(ROOT, 'out', 'daily', d.isoformat(), 'foot'), card='--no-card' not in sys.argv)
    print(note)
    for m in msgs:
        print(m['type'], m['pid'], m.get('files'), '\n' + m['text'])
