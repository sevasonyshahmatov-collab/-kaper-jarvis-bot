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

import ask  # noqa: E402
import channel  # noqa: E402
import data  # noqa: E402
import morning  # noqa: E402
from data import MSK  # noqa: E402

import difflib  # noqa: E402
import re  # noqa: E402

import settle  # noqa: E402

# ---------------------------------------------------------------- старый формат (сентябрь — 15 октября)
# «🏒КХЛ. 🐺НЕФТЕХИМИК - ХК СОЧИ🐆» / «⚔️ Сочи — ЦСКА | 19:30» первой строкой, дальше разбор и строка
# «✅ Прогноз: Победа Нефтехимика в основное время за 1.72» (кэф — «за 1.72» в той же строке). Даты матча в посте нет:
# начало ≈ время поста, матч ищется в данных лиги в пределах ±30 ч (data.match_game).
OLD_TYPO = {'ФЛА': 'Филадельфия', 'АВТОМОБОИЛИСТ': 'Автомобилист', 'ДЕТЙРОЙ': 'Детройт', 'ДИНАМО': 'Динамо Москва',
            'ДИНАМО МСК': 'Динамо Москва', 'ЛОС-АНДЖЕЛЕС КИНГЗ': 'Лос-Анджелес', 'ФИЛА': 'Филадельфия'}
NICK = {'шаркс': 'Сан-Хосе', 'кингз': 'Лос-Анджелес', 'кингс': 'Лос-Анджелес', 'джетс': 'Виннипег', 'девилз': 'Нью-Джерси',
        'девилс': 'Нью-Джерси', 'пингвинз': 'Питтсбург', 'пингвинс': 'Питтсбург', 'пантерз': 'Флорида', 'пантерс': 'Флорида',
        'кенакс': 'Ванкувер', 'кэнакс': 'Ванкувер', 'эвеланш': 'Колорадо', 'лавины': 'Колорадо', 'ойлерз': 'Эдмонтон',
        'ойлерс': 'Эдмонтон', 'брюинз': 'Бостон', 'брюинс': 'Бостон', 'лифс': 'Торонто', 'кэпиталз': 'Вашингтон',
        'кэпиталс': 'Вашингтон', 'флайерз': 'Филадельфия', 'флайерс': 'Филадельфия', 'старз': 'Даллас', 'старс': 'Даллас',
        'блюз': 'Сент-Луис', 'уайлд': 'Миннесота', 'флэймз': 'Калгари', 'флеймз': 'Калгари', 'кракен': 'Сиэтл',
        'найтс': 'Вегас', 'голден найтс': 'Вегас', 'предаторз': 'Нэшвилл', 'предаторс': 'Нэшвилл', 'канадиенс': 'Монреаль',
        'хабс': 'Монреаль', 'сейбрз': 'Баффало', 'сейбрс': 'Баффало', 'сенаторз': 'Оттава', 'сенаторс': 'Оттава',
        'лайтнинг': 'Тампа-Бэй', 'харрикейнз': 'Каролина', 'харрикейнс': 'Каролина', 'блэкхокс': 'Чикаго',
        'блэкхоукс': 'Чикаго', 'дакс': 'Анахайм', 'ред уингз': 'Детройт', 'ред уингс': 'Детройт', 'блю джекетс': 'Коламбус',
        'мамонт': 'Юта'}
OLD_BET = re.compile(r'(?i)^\W*(?:прогноз|ставка)\s*[:\-–—]?\s*(.+)$')
OLD_KEF = re.compile(r'(?i)\s*(?:(?:за|на|кэф|кеф|кф|коэф\w*|@)\s*:?\s*(\d+(?:[.,]\d+)?)|\s(\d[.,]\d\d))\W*$')


def _old_team(name):
    name = re.sub(r'[^\w\s.-]', '', name).strip(' .-')
    name = OLD_TYPO.get(name.upper(), NICK.get(name.lower(), name))
    n, ok = channel._team(name)
    if not ok:
        close = difflib.get_close_matches(n.capitalize(), list(settle.GEN), n=1, cutoff=.8)
        if close:
            return close[0], True
    return n, ok


OLD_FIX = [           (r'ренйджерс', 'рейнджерс'), (r'питсбург', 'питтсбург'), (r'оснвоное', 'основное'), (r'\bменше\b', 'меньше'),
           (r'\bбольще\b', 'больше'), (r'\bтотаю\b', 'тотал'), (r'индивитуадльный итота', 'индивидуальный тотал'),
           (r'\bит([12])б\b', r'итб\1'), (r'\bит([12])м\b', r'итм\1'), (r'\bтотал м\s*\(', 'тм('), (r'\bтотал б\s*\(', 'тб('),
           (r'\bи меньше (\d)', r'и тм \1'), (r'\bи больше (\d)', r'и тб \1')]


def _old_bet(bet, home, away):
    """Свободная строка ставки старого поста → ближе к форме, которую понимает settle: опечатки, «с учётом ОТ и буллитов»,
    прозвища клубов НХЛ («победа лайтнинг» → «победа Тампа-Бэй»)."""
    b = bet
    if re.search(r'с уч[её]том', b):
        m = re.match(r'(?:итоговая )?победа (.+?) с уч[её]том', b)
        if m:
            b = 'итоговая победа ' + m.group(1)
    for rx, to in OLD_FIX:
        b = re.sub(rx, to, b)
    for nick, team in NICK.items():
        if team in (home, away):
            b = re.sub(r'\b%s\b' % nick, team, b)
    for team in (home, away):                    # «тотал Авангарда 2.5 больше», «Барыс тотал 2.5 больше» — тотал команды
        st = re.escape(team.lower()[:4] if len(team) > 4 else team.lower()[:-1])     # «Юта» → «ют»: «тотал Юты»
        m = re.search(r'(?i)(?:тотал\s+%s[\w-]*|%s[\w-]*\s+тотал)\s+(\d+(?:[.,]\d)?)\s+(больше|меньше)' % (st, st), b)
        if m:
            b = 'индивидуальный тотал %s %s %s' % (settle.GEN.get(team, team), m.group(2), m.group(1))
    return b


def old_pick(post):
    """Пост старого формата → (прогноз, None) / (None, почему) / (None, None) — не прогноз."""
    lines = [t for t, _ in post['text']]
    if not lines or not post['posted']:
        return None, None
    head = re.sub(r'\|\s*\d{1,2}[:.]\d\d.*$', '', lines[0])
    league = 'NHL' if re.search(r'НХЛ', head, re.I) else 'KHL' if re.search(r'КХЛ', head, re.I) else None
    head = re.sub(r'(?i)^\W*(?:кхл|нхл)\W*', '', head)
    parts = re.split(r'\s+[-—–]\s+|\s*[—–]\s*', head)
    if len(parts) != 2:
        return None, None
    (home, ok_h), (away, ok_a) = _old_team(parts[0]), _old_team(parts[1])
    if not (ok_h and ok_a):
        bet_line = any(OLD_BET.match(t) for t in lines[1:])
        return None, ('команда не узнана: %s' % head) if bet_line else None
    if league is None:
        league = 'NHL' if home in settle.NHL_GEN else 'KHL'
    bet = None
    for t in lines[1:]:
        m = OLD_BET.match(t)
        if m and not re.match(r'(?i)\W*почему', t):
            bet = m.group(1)
            break
    if not bet:
        stake = any(re.search(r'(?i)ставк|прогноз|\bкэф|\bкф\b', t) for t in lines[1:])
        return None, ('нет строки «Прогноз: …»' if stake else None)
    if re.search(r'(?i)брос', bet):
        return None, 'ставка на броски — по счёту не проверить, посчитать вручную'
    kef = None
    mk = OLD_KEF.search(bet)
    if mk:
        kef = round(float((mk.group(1) or mk.group(2)).replace(',', '.')), 2)
        bet = bet[:mk.start()]
    bet = re.sub(r'[^\w\s().,+\-–—]', ' ', bet)
    bet = re.sub(r'\s+', ' ', bet).strip(' .,-').lower()
    bet = _old_bet(bet, home, away)
    start = post['posted']
    bet2, kef2, bnote = channel._bet(bet, home, away, league, start)
    return dict(pid='№%d' % post['id'], msg_id=post['id'], league=league, home=home, away=away, start=start, bet=bet2,
                kef=kef if kef is not None else kef2, src='channel-old', note=bnote, head=lines[0], exact_time=False,
                tg_edited=post['edited'], media=post['media'], posted=post['posted'],
                url='https://t.me/%s/%d' % (channel.CHANNEL, post['id']), edited=False), None


MONTH = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def _row(r):
    """Прогноз для списка на сайте: дата матча, лига, матч, ставка обычными словами, кэф, счёт, итог, номер поста."""
    g = r['g']
    try:
        bet = ask.phrase(r['legs'], r['home'], r['away'])
    except Exception:  # noqa: BLE001
        bet = r['bet']
    return dict(d=r['start'].astimezone(MSK).strftime('%d.%m'), lg='КХЛ' if r['league'] == 'KHL' else 'НХЛ', h=r['home'],
                a=r['away'], bet=bet[:1].upper() + bet[1:], kef=r.get('kef'), sc='%s:%s' % (g.get('hg'), g.get('ag')),
                end=g.get('end') or '', r={'win': 'w', 'loss': 'l'}.get(r['res'], 'p'), id=r['msg_id'])


def published(picks, rows):
    """Все посты-прогнозы канала (владелец 25.10: на сайте и в приложении — только то, что выложено в канал) → список
    {lg, h, a, d (МСК), bet, kef, id[, r, sc]}: ставка и кэф — из поста; у сыгранных — итог и счёт (как в months.json)."""
    done = {r['msg_id']: r for r in rows}
    out = []
    for p in picks:
        r = done.get(p['msg_id'])
        try:
            bet = ask.phrase(p['legs'], p['home'], p['away'])
        except Exception:  # noqa: BLE001
            bet = p.get('bet') or ''
        x = dict(lg='khl' if p['league'] == 'KHL' else 'nhl', h=p['home'], a=p['away'], d=p['start'].astimezone(MSK).strftime('%Y-%m-%d %H:%M'),
                 bet=bet[:1].upper() + bet[1:], kef=p.get('kef'), id=p['msg_id'])
        if r:
            g = r['g']
            x.update(r=r['res'], sc='%s:%s%s' % (g.get('hg'), g.get('ag'), (' ' + g['end']) if g.get('end') else ''))
        out.append(x)
    return out


def month_stats(rows, now=None):
    """Рассчитанные прогнозы → [{m: 'ГГГГ-ММ', name, n, w, l, p, kef (средний), units (плюс/минус при ставке 1 на каждый),
    live (месяц идёт), upto (по какое число), rows (список для сайта)}]."""
    now = now or datetime.now(MSK)
    gen = {v: k for k, v in channel.MONTHS.items()}
    by = {}
    for r in rows:
        k = r['start'].astimezone(MSK).strftime('%Y-%m')
        by.setdefault(k, []).append(r)
    out = []
    for k in sorted(by):
        rs = sorted(by[k], key=lambda r: (r['start'], r['msg_id']))
        w = [r for r in rs if r['res'] == 'win']
        l = [r for r in rs if r['res'] == 'loss']
        kefs = [r['kef'] for r in rs if r.get('kef')]
        units = sum(r['kef'] - 1 for r in w if r.get('kef')) - len(l)
        last = rs[-1]['start'].astimezone(MSK)
        out.append(dict(m=k, name=MONTH[int(k[5:])], n=len(rs), w=len(w), l=len(l), p=len(rs) - len(w) - len(l),
                        kef=round(sum(kefs) / len(kefs), 2) if kefs else None, units=round(units, 2),
                        live=int(k == now.strftime('%Y-%m')), upto='%d %s' % (last.day, gen[last.month]),
                        rows=[_row(r) for r in rs]))
    return out


def main():
    t0 = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=MSK) if len(sys.argv) > 1 else datetime(2026, 9, 1, tzinfo=MSK)
    out = sys.argv[2] if len(sys.argv) > 2 else 'out/months'
    channel.MAX_PAGES = 80                           # ~20 постов на страницу: с запасом до начала сентября
    t1 = datetime.now(MSK)
    pages = {}
    fetch = channel.fetch
    channel.fetch = lambda before=None: pages.setdefault(before, fetch(before))
    seen = {}
    feed = channel.feed
    channel.feed = lambda t: seen.setdefault('v', feed(t))  # лента одна: и для прогнозов, и для списка нераспознанных
    picks, chan = channel.posts(t0, t1)
    used = {p['msg_id'] for p in chan['picks']}
    old, old_bad, last = {}, [], max((p['posted'] for p in chan['picks'] if p.get('posted')), default=t1)
    first_new = min((p['posted'] for p in chan['picks'] if p.get('posted')), default=t1)
    for x in seen['v'][0]:                        # старый формат — только до первого поста нового формата
        if x['id'] in used or not x['posted'] or not (t0 <= x['posted'] < first_new):
            continue
        p, why = old_pick(x)
        if p:
            old[(p['league'], p['home'], p['away'], p['start'].date())] = p     # повтор поста — берём последний
            used.add(x['id'])
        elif why:
            old_bad.append((x, why))
    picks = picks + sorted(old.values(), key=lambda p: p['msg_id'])
    odd = [x for x in seen['v'][0] if x['id'] not in used and x['posted'] and x['posted'] >= t0
           and any(w in ' '.join(t for t, _ in x['text']).lower() for w in ('прогноз', 'кэф', 'коэф'))]
    found, errs = data.games_for(picks) if picks else ({}, [])
    rows, pending, bad = morning.settle_rows(picks, found)
    if os.environ.get('MONTHS_DUMP'):                # копия ленты и счетов — разбирать формат постов без сети
        import pickle
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, 'dump.pkl'), 'wb') as f:
            pickle.dump(dict(pages=pages, found=found), f)
    stats = month_stats(rows)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'published.json'), 'w', encoding='utf-8') as f:     # сайт и приложение — только эти матчи
        json.dump(published(picks, rows), f, ensure_ascii=False)
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
        lines.append('- %s №%d %s %s — %s: %s [%s], кэф %s → %s (%s:%s%s)' % (
            r['start'].astimezone(MSK).strftime('%d.%m %H:%M'), r['msg_id'], r['league'], r['home'], r['away'], r['bet'], r['short'],
            r.get('kef'), res.get(r['res'], r['res']), g.get('hg'), g.get('ag'), (' ' + g['end']) if g.get('end') else ''))
    if pending or bad:
        lines += ['', '## Не вошли', '']
        for p, why in pending + bad:
            lines.append('- №%d %s — %s: %s (%s)' % (p['msg_id'], p['home'], p['away'], p['bet'], why))
    if old_bad:
        lines += ['', '## Старый формат: похоже на прогноз, но не разобрано', '']
        for x, why in old_bad:
            lines.append('- №%d %s: %s — %s' % (x['id'], x['posted'].strftime('%d.%m'), why, x['text'][0][0][:80]))
    if odd:
        lines += ['', '## Посты со словами «прогноз»/«кэф», не узнанные как прогноз (проверить: может, старый формат)', '']
        for x in odd:
            lines.append('- №%d %s: %s' % (x['id'], x['posted'].strftime('%d.%m'), ' / '.join(t for t, _ in x['text'])[:160]))
    if chan.get('notes') or errs:
        lines += ['', '## Заметки', ''] + ['- %s' % n for n in chan.get('notes', [])] + ['- %s' % e for e in errs]
    with open(os.path.join(out, 'odd.json'), 'w', encoding='utf-8') as f:   # полный текст нераспознанных — для разбора формата
        json.dump([dict(id=x['id'], posted=x['posted'].isoformat(), media=x['media'], edited=x['edited'], text=x['text']) for x in odd],
                  f, ensure_ascii=False, indent=0)
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(out, 'months.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)
    print('MONTHS %s' % json.dumps([{k: v for k, v in s.items() if k != 'rows'} for s in stats], ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
