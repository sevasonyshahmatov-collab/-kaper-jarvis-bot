# -*- coding: utf-8 -*-
"""Карусель Instagram — 1 в день на самый уверенный матч дня (владелец 22.10; docs/handoff/SMM_AGENT.md). Данные и
прогноз — как у конвейера шортсов (приложение КХЛ / API НХЛ, линия Pinnacle, правило владельца, team/reels_daily/pick.py);
нет прогноза в КХЛ — берём ночь НХЛ. Прогноз на 5-м слайде — в 1 день из 5, в остальные — «полный прогноз в Telegram».
Слайды — slides.py. Запускает .github/workflows/carousel-daily.yml.

    PYTHONPATH=render python team/carousel/make.py [ГГГГ-ММ-ДД] [--preview]   (--preview — только владельцу в Telegram)
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'team', 'reels_daily'),
          os.path.join(ROOT, 'team', 'mirror'), os.path.join(ROOT, 'team', 'daily'), HERE):
    sys.path.insert(0, p)

import slides  # noqa: E402

MSK = timezone(timedelta(hours=3))
API = 'https://graph.facebook.com/v21.0/'
MON = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
SKIP = ('+2,5', 'Ф1(+1,5)', 'Ф2(-1,5)', 'Ф1(-1,5)', 'ИТБ 3,5')     # для «что часто заходит» — слишком очевидно или редко


def reveal(day):
    return day.toordinal() % 5 == 0


def short(t):
    """Название события для слайда: «победа Сибири», «Сибирь не проиграет», «победа Сибири с ОТ», «ТМ 5,5», «Ф2 (+1,5) Сибирь»."""
    import re
    import settle
    t = t.replace(' в осн. время', '')
    m = re.match(r'итоговая победа (.+) \(с ОТ и Б\)$', t)
    if m:
        return 'победа %s с ОТ' % settle.gen(m.group(1))
    m = re.match(r'П[12] (.+)$', t)
    if m:
        return 'победа %s' % settle.gen(m.group(1))
    m = re.match(r'(?:1Х|Х2) (.+)$', t)
    if m:
        return m.group(1)
    return t.replace('(', ' (').replace('  ', ' ').strip()


def last5(games, team, before):
    out = []
    for g in sorted(games, key=lambda g: g['d'], reverse=True):
        if g['d'][:16] >= before or team not in (g['h'], g['a']) or g.get('hg') is None:
            continue
        home = g['h'] == team
        gf, ga = (g['hg'], g['ag']) if home else (g['ag'], g['hg'])
        out.append((g['a'] if home else g['h'], '%d:%d' % (gf, ga), 'В' if gf > ga else 'П', g.get('e') or ''))
        if len(out) == 5:
            break
    return out


def freq(games, H, A, before, n=10):
    """События, которые чаще всего заходили у обеих команд за последние n матчей (основное время, как в таблице)."""
    import calc
    G = calc.prep([g for g in games if g['d'][:16] < before])
    T = calc.team_games(G)
    th = sorted(T.get(H, []), key=lambda x: x['day'], reverse=True)[:n]
    ta = sorted(T.get(A, []), key=lambda x: x['day'], reverse=True)[:n]
    rows = []
    for mk in calc.markets(H, A):
        if any(s in mk['t'] for s in SKIP):
            continue
        xh = sum(1 for x in th if mk['f'](calc.view(x, True)))
        xa = sum(1 for x in ta if mk['f'](calc.view(x, False)))
        sh, sa = xh / max(1, len(th)), xa / max(1, len(ta))
        if max(sh, sa) > 0.95 or min(sh, sa) < 0.5:
            continue
        rows.append((min(sh, sa) + (sh + sa) / 2, (short(mk['t']), xh, len(th), xa, len(ta))))
    rows.sort(key=lambda r: -r[0])
    return [r[1] for r in rows[:5]]


def build(day):
    """→ (D, подпись) или (None, причина)."""
    import pick
    import pin
    import khl_data
    import nhl_data
    for league, mod, d in (('khl', khl_data, day), ('nhl', nhl_data, day)):
        try:
            games, nxt = mod.fetch(d.isoformat())
        except Exception as e:  # noqa: BLE001
            print('CAROUSELERR %s: %r' % (league, e), flush=True)
            continue
        fon = {(x['h'], x['a']): x.get('bets') for x in nxt} if league == 'khl' else {}
        try:
            pins, _ = pin.fetch(league, d.isoformat(), [(x['h'], x['a']) for x in nxt])
        except Exception as e:  # noqa: BLE001
            print('PINERR %r' % e, flush=True)
            pins = {}
        ms = [m for m in pick.day_picks(games, nxt, pins, fon, league) if m.get('x1x2')]
        if not ms:
            continue
        m = max(ms, key=lambda m: m['p'])
        md = date.fromisoformat(m['d'][:10])
        L = league.upper()
        D = dict(league=L, date='%d %s' % (md.day, MON[md.month - 1]), time=m['d'][11:16], home=m['h'], away=m['a'],
                 line=tuple(m['x1x2']), last=dict(home=last5(games, m['h'], m['d']), away=last5(games, m['a'], m['d'])),
                 freq=freq(games, m['h'], m['a'], m['d']), pick=m['pick'],
                 odds=('%.2f' % m['odds']).replace('.', ','), reveal=reveal(day))
        lg = 'КХЛ' if L == 'KHL' else 'НХЛ'
        tag = lambda s: '#' + s.replace(' ', '').replace('-', '')  # noqa: E731
        cap = '\n'.join([
            '%s — %s · %s, %s МСК' % (m['h'], m['a'], D['date'], D['time']),
            'Полный прогноз на матч — в Telegram @jarvibet (ссылка в шапке профиля)' if not D['reveal'] else
            'Прогноз JARVIS: %s · кэф %s. Прогноз — мнение, не совет.' % (m['pick'], D['odds']),
            '',
            'Линия, форма команд и что чаще всего заходит у них — листайте.',
            'Все прогнозы на КХЛ и НХЛ каждый день — в Telegram @jarvibet',
            '',
            ' '.join(['#хоккей', '#' + lg.lower(), '#прогнозы', tag(m['h']), tag(m['a'])])])
        return D, cap
    return None, 'нет матча с прогнозом по правилу'


def wait_publish(cid, tok, uid):
    import time
    for _ in range(60):
        st = requests.get(API + cid, params=dict(fields='status_code', access_token=tok), timeout=30).json()
        if st.get('status_code') in ('FINISHED', None):
            break
        if st.get('status_code') in ('ERROR', 'EXPIRED'):
            raise RuntimeError('обработка: %s' % st)
        time.sleep(5)
    for _ in range(6):
        p = requests.post(API + uid + '/media_publish', data=dict(creation_id=cid, access_token=tok), timeout=60).json()
        if 'id' in p or (p.get('error') or {}).get('code') != 9007:
            break
        time.sleep(15)
    if 'id' not in p:
        raise RuntimeError('публикация: %s' % (p.get('error') or p))
    return p['id']


def publish(paths, caption):
    import ig_mirror
    import instagram
    tok, uid = instagram._env()
    kids = []
    for p in paths:
        r = requests.post(API + uid + '/media', timeout=60, data=dict(image_url=ig_mirror.host(p), is_carousel_item='true',
                                                                       access_token=tok)).json()
        if 'id' not in r:
            raise RuntimeError('слайд: %s' % (r.get('error') or r))
        kids.append(r['id'])
    r = requests.post(API + uid + '/media', timeout=60, data=dict(media_type='CAROUSEL', children=','.join(kids),
                                                                   caption=caption, access_token=tok)).json()
    if 'id' not in r:
        raise RuntimeError('карусель: %s' % (r.get('error') or r))
    return wait_publish(r['id'], tok, uid)


def to_owner(paths, caption):
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('TG_BOT_TOKEN не задан', flush=True)
        return
    import json
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    media = [dict(type='photo', media='attach://f%d' % i, **({'caption': caption[:1024]} if i == 0 else {}))
             for i in range(len(paths))]
    files = {'f%d' % i: open(p, 'rb') for i, p in enumerate(paths)}
    try:
        tj._api(tok, 'sendMediaGroup', dict(chat_id=chat, media=json.dumps(media, ensure_ascii=False)), files, timeout=300)
    finally:
        for f in files.values():
            f.close()


def main():
    a = sys.argv[1:]
    day = date.fromisoformat(next((x for x in a if x[:2] == '20'), datetime.now(MSK).date().isoformat()))
    D, cap = build(day)
    if not D:
        print('CAROUSEL %s: %s' % (day, cap), flush=True)
        return
    paths = slides.render(D, os.path.join(ROOT, 'out', 'carousel', day.isoformat()))
    print('CAROUSEL %s | %s — %s | прогноз %s' % (day, D['home'], D['away'], 'раскрыт' if D['reveal'] else 'скрыт'),
          flush=True)
    if '--preview' in a:
        to_owner(paths, 'ПРОБА карусели (не выложено)\n\n' + cap)
        return
    import instagram
    if not instagram.enabled():
        print('CAROUSEL нет IG_TOKEN / IG_USER_ID — не выложено', flush=True)
        return
    print('CAROUSEL опубликована %s' % publish(paths, cap), flush=True)


if __name__ == '__main__':
    main()
