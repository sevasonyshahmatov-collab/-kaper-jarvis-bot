# -*- coding: utf-8 -*-
"""Итог экспресса (владелец 01.11): счёт каждой ноги (API лиги) → расчёт → баннер «ИТОГ ЭКСПРЕССА» с отметками.
    PYTHONPATH=render python3 team/picks/express_result.py <coupons.json> <номер купона с 1> <папка> [pid]
Печатает строки EXPRRES (для Actions-аннотаций): нога, счёт, итог; EXPRTOTAL win|loss|pending. Баннер — <папка>/e<k>_result.jpg,
только если все ноги сыграны. Без процентов (EXPRESS.md)."""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for sub in ('render', 'team/daily', 'team/picks'):
    sys.path.insert(0, os.path.join(ROOT, sub))
import data  # noqa: E402
import settle  # noqa: E402
import express_card as ec  # noqa: E402
import express_render as er  # noqa: E402


def compute(src, k, out):
    """→ (c, legs, res, status): status win|loss|push|pending; баннер рисуется, если все ноги сыграны."""
    c = json.load(open(os.path.join(ROOT, src), encoding='utf-8'))['coupons'][int(k) - 1]
    picks = []
    for x in c['legs']:
        st = datetime.strptime('%s %s' % (x['date'], x['time']), '%Y-%m-%d %H:%M').replace(tzinfo=data.MSK)
        picks.append(dict(league='NHL' if x['league'] in ('НХЛ', 'NHL') else 'KHL', home=settle.canon(x['home']),
                          away=settle.canon(x['away']), start=st, bet=x['bet']))
    found, errs = data.games_for(picks)
    for e in errs:
        print('EXPRERR', e, flush=True)
    legs, res = [], []
    for x, p in zip(c['legs'], picks):
        g = data.match_game(found, p)
        live_ok = os.environ.get('EXPRESS_FORCE_LIVE') == '1' and g and g.get('hg') is not None and g['state'] in ('live', 'final')
        if not g or (g['state'] != 'final' and not live_ok) or g.get('hg') is None:
            print('EXPRRES %s — %s: нет финала (%s)' % (x['home'], x['away'], g and g['state']), flush=True)
            res.append(None)
            continue
        r, _, _ = settle.settle(p['bet'], p['home'], p['away'], g)
        res.append(r)
        print('EXPRRES %s — %s %s:%s %s → %s (%s)' % (x['home'], x['away'], g['hg'], g['ag'], g.get('end') or '', r, x['bet']), flush=True)
        legs.append(dict(home=x['home'], away=x['away'], time=x['time'], bet=x['bet_short'], kef=x['kef'],
                         league=x['league'], mark={'win': 'win', 'loss': 'loss'}.get(r, 'push'),
                         score='%s:%s%s' % (g['hg'], g['ag'], {'ot': ' ОТ', 'so': ' Б'}.get(str(g.get('end') or '').lower(), ''))))
    if None in res:
        print('EXPRTOTAL pending', flush=True)
        return c, legs, res, 'pending'
    status = 'loss' if settle.LOSS in res else 'win' if all(r == settle.WIN for r in res) else 'push'
    print('EXPRTOTAL', status, flush=True)
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    for fmt in ('feed',):
        p = ec.render(legs, os.path.join(ROOT, out, 'e%s_result.jpg' % k), fmt=fmt, title='ИТОГ ЭКСПРЕССА',
                      date_title=er.date_title(c['legs']), total=c['kef'])
        print('EXPRFILE', p, flush=True)
    return c, legs, res, status


def main(src, k, out):
    compute(src, k, out)


def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def result_text(c, legs, status):
    """Подпись «Итог экспресса»: спокойный тон, без процентов и обещаний (EXPRESS.md)."""
    head = {'win': 'Итог экспресса ✅ Зашёл!', 'loss': 'Итог экспресса ❌ Не зашёл',
            'push': 'Итог экспресса ↩️ Часть ног вернулась'}[status]
    lines = [head, '', '%s · %s' % (c['legs'][0]['league'], er.date_title(c['legs'])), '']
    sign = {'win': '✅', 'loss': '❌', 'push': '↩️'}
    for i, l in enumerate(legs, 1):
        lines.append('%d. <b>%s — %s</b> %s · %s %s' % (i, esc(l['home']), esc(l['away']), l['score'], esc(l['bet']), sign[l['mark']]))
    lines.append('')
    if status == 'win':
        lines.append('Общий кэф: <b>%s</b>' % str(c['kef']).replace('.', ','))
    elif status == 'loss':
        lines += ['Одна нога не дошла — бывает. Идём дальше, следующие купоны — по тем же правилам.']
    else:
        lines += ['Возврат по ноге — кэф купона пересчитывается.']
    lines += ['', {'НХЛ': '#нхл', 'КХЛ': '#кхл'}.get(c['legs'][0]['league'], '#хоккей') + ' #экспресс #jarvibet']
    return '\n'.join(lines)


def auto(job_file):
    """Бот (expressTick_) запустил итог: EXPRESS_RES={"pid":"ДДММ-eN","ch":<номер поста купона в канале>}, день — из пути задания
    (team/out/<день>/…). Дописывает в задание сообщение владельцу «Итог экспресса» (кнопки «Опубликовать», номер ДДММ-eNr<ch>)."""
    import re
    ex = json.loads(os.environ.get('EXPRESS_RES') or '{}')
    m = re.fullmatch(r'(\d{4})-e(\d{1,2})', str(ex.get('pid') or ''))
    day = re.search(r'team/out/(\d{4}-\d\d-\d\d)/', job_file.replace(os.sep, '/'))
    if not m or not day:
        print('EXPRERR нет EXPRESS_RES или дня задания', flush=True)
        return 1
    src = 'team/out/%s/express_coupons.json' % day.group(1)
    out = 'out/express/%s' % day.group(1)
    c, legs, res, status = compute(src, m.group(2), out)
    if status == 'pending':
        print('EXPRERR не все ноги сыграны — итог не собран', flush=True)
        return 1
    ch = str(ex.get('ch') or '')
    ch = ch if ch.isdigit() else ''
    img = os.path.join(out, 'e%s_result.jpg' % m.group(2))
    msg = {'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': [img], 'text': result_text(c, legs, status),
           'buttons': 'post', 'pid': '%s-e%sr%s' % (m.group(1), m.group(2), ch)}
    jp = os.path.join(ROOT, job_file) if not os.path.isabs(job_file) else job_file
    job = json.load(open(jp, encoding='utf-8'))
    job['messages'] = (job.get('messages') or []) + [msg]
    json.dump(job, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('EXPRSENT', ex['pid'], status, flush=True)
    return 0


def manual(src, k, out, job_file, pid):
    """Разово по просьбе владельца: рассчитать купон src[k] и дописать «Итог экспресса» в задание job_file (pid — ДДММ-eN)."""
    os.environ['EXPRESS_FORCE_LIVE'] = '1'          # владелец подтвердил: идущий матч уже решил ногу («больше» не отыгрывается)
    c, legs, res, status = compute(src, k, out)
    if status == 'pending':
        print('EXPRERR не все ноги сыграны', flush=True)
        return 1
    day, n = pid.split('-e')
    img = os.path.join(out, 'e%s_result.jpg' % k)
    msg = {'to': 'owner', 'type': 'photo', 'html': True, 'emoji': True, 'files': [img], 'text': result_text(c, legs, status),
           'buttons': 'post', 'pid': '%s-e%sr' % (day, n)}
    jp = os.path.join(ROOT, job_file)
    job = json.load(open(jp, encoding='utf-8'))
    job['messages'] = (job.get('messages') or []) + [msg]
    json.dump(job, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('EXPRSENT', pid, status, flush=True)
    return 0


if __name__ == '__main__':
    if sys.argv[1] == '--manual':
        sys.exit(manual(*sys.argv[2:7]))
    if sys.argv[1] == '--auto':
        sys.exit(auto(sys.argv[2]))
    main(*sys.argv[1:4])
