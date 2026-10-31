# -*- coding: utf-8 -*-
"""Купоны «Экспресс» (рубрика владельца 31.10, правила — team/picks/EXPRESS.md): из сводок дня собирает купоны по 2–3
события из самых вероятных исходов модели.

    python3 team/picks/express.py --nhl out/picks/nhl-D/brief.md --khl out/picks/khl-D/brief.md \
        --foot out/picks/foot-D/fd.txt --sizes 3,3,2 --out out/picks/express-D.json

Источники (любые из трёх, хотя бы один):
  --nhl / --khl — brief.md из team/picks/notice_brief.py (строки «- Х—Г | p% (модель m%) СТАВКА | кэф k (…)»);
  --foot        — строки FD* из football_day.py (FDMATCH + FDWIDE; FDWIDE печатает только кэф от 1,5 — ног из футбола мало).
Правила отбора (EXPRESS.md): p модели от 65 %, кэф ноги 1,20–1,65; рынки — инд. тоталы, тоталы, победа (осн. время /
итоговая), форы — не больше одной на купон; 1Х/Х2 не берём; из матча одна нога; матчи между купонами не повторяются;
общий кэф — цель 1,80–2,00, нет такого сочетания — 1,75–2,05; в купоне — сочетание с наибольшим произведением p.
Печатает купоны и кандидатов; --out — JSON для текстов и баннеров (render/express_card.py)."""
import argparse
import itertools
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'render'))

P_MIN, K_MIN, K_MAX = 0.65, 1.20, 1.65
TARGET, WIDE = (1.80, 2.00), (1.75, 2.05)
TOP_PER_MATCH = 3            # в переборе — до 3 лучших ног матча (одна самая вероятная часто даёт слишком малый кэф)
MAX_FORA = 1
CAT_OK = ('it', 'total', 'win', 'fora')

GEN = {'Тампа-Бэй': 'Тампы', 'Лос-Анджелес': 'Лос-Анджелеса', 'Сент-Луис': 'Сент-Луиса', 'Сан-Хосе': 'Сан-Хосе',
       'Нью-Джерси': 'Нью-Джерси', 'Айлендерс': 'Айлендерс', 'Рейнджерс': 'Рейнджерс', 'Ак Барс': 'Ак Барса',
       'Салават Юлаев': 'Салавата Юлаева', 'Динамо Москва': 'Динамо Москва', 'Динамо Минск': 'Динамо Минск',
       'Торпедо': 'Торпедо', 'Колорадо': 'Колорадо', 'Баффало': 'Баффало', 'Чикаго': 'Чикаго', 'Сиэтл': 'Сиэтла',
       'Юта': 'Юты', 'Калгари': 'Калгари', 'Шанхайские Драконы': 'Шанхайских Драконов', 'Нефтехимик': 'Нефтехимика'}


def gen(t):
    """Родительный падеж названия клуба (фора Детройта, тотал Оттавы); неизвестное составное — как есть."""
    if t in GEN:
        return GEN[t]
    if ' ' in t or '-' in t or not re.search('[а-яё]$', t):
        return t
    if t.endswith('а'):
        return t[:-1] + ('и' if t[-2:-1] in 'кгхжшчщ' else 'ы')
    if t.endswith('я') or t.endswith('ь'):
        return t[:-1] + 'и'
    if t[-1] in 'оеиуыэю':
        return t
    return t + 'а'


def cat(bet):
    b = bet.strip()
    if b.startswith(('1Х', 'Х2', '12')):
        return 'dc'
    if b.startswith('Ф'):
        return 'fora'
    if b.startswith(('ИТБ', 'ИТМ', 'ИТ1', 'ИТ2')):
        return 'it'
    if b.startswith(('ТБ', 'ТМ')):
        return 'total'
    if b.startswith(('П1', 'П2', 'итоговая победа')):
        return 'win'
    return 'other'


def human(bet, home, away, league):
    """Ставка словами для поста и баннера: (полностью, коротко)."""
    b = bet.strip()
    ot = league == 'НХЛ' and 'осн. время' in b
    tail = ' в основное время' if ot else ''
    m = re.match(r'Ф([12])\(([+\-−][\d,]+)\) (.+)$', b)
    if m:
        s = 'фора %s %s' % (gen(m.group(3)), m.group(2).replace('-', '−'))
        return s, s
    m = re.match(r'ИТ([БМ]) ([\d,]+) (.+?)( в осн\. время)?$', b)
    if m:
        w = 'больше' if m.group(1) == 'Б' else 'меньше'
        s = 'индивидуальный тотал %s %s %s' % (gen(m.group(3)), w, m.group(2))
        return s + tail, 'инд. тотал %s %s %s' % (gen(m.group(3)), w, m.group(2))
    m = re.match(r'Т([БМ]) ([\d,.]+)', b)
    if m:
        w = 'больше' if m.group(1) == 'Б' else 'меньше'
        s = 'тотал матча %s %s' % (w, m.group(2).replace('.', ','))
        return s + tail, 'тотал %s %s' % (w, m.group(2).replace('.', ','))
    m = re.match(r'П([12])\s*(.*?)( в осн\. время)?$', b)
    if m:
        team = m.group(2) or (home if m.group(1) == '1' else away)
        s = 'победа %s' % gen(team)
        return s + (' в основное время' if league in ('НХЛ', 'КХЛ') else ''), s + (' в осн. время' if league != 'Футбол' else '')
    m = re.match(r'итоговая победа (.+?) \(с ОТ и Б\)', b)
    if m:
        s = 'итоговая победа %s' % gen(m.group(1))
        return s, s
    return b, b


def parse_brief(path, league):
    legs, cur = [], None
    for line in open(path, encoding='utf-8'):
        m = re.match(r'## \d+\. (.+?) — (.+?) · (\d{4}-\d\d-\d\d) (\d\d:\d\d) МСК', line)
        if m:
            cur = dict(home=m.group(1), away=m.group(2), date=m.group(3), time=m.group(4))
            continue
        m = re.match(r'- .+? \|\s+([\d.]+)% \(модель\s*([\d.]+)%\) (.+?)\s+\| кэф ([\d.]+) \((.+?)\)', line)
        if m and cur:
            bet = m.group(3).strip()
            legs.append(dict(cur, league=league, p=float(m.group(1)) / 100, p_model=float(m.group(2)) / 100, bet=bet,
                             kef=float(m.group(4)), src=m.group(5), cat=cat(bet)))
    return legs


def _ru(name):
    """Футбольный клуб по-русски (render/football.resolve), не вышло — как есть."""
    try:
        import football
        return football.resolve(name) or name
    except Exception:  # noqa: BLE001
        return name


def parse_foot(path):
    legs, cur = [], None
    for line in open(path, encoding='utf-8'):
        if line.startswith('FDMATCH'):
            parts = [x.strip() for x in line.split('|')]
            h, a = [x.strip() for x in parts[2].split(' — ', 1)] if len(parts) > 2 and ' — ' in parts[2] else ('?', '?')
            t = parts[1] if len(parts) > 1 else ''
            mt = re.search(r'(\d{4}-\d\d-\d\d)?\D*(\d\d:\d\d)', t)
            cur = dict(home=_ru(h), away=_ru(a), date=(mt.group(1) or '') if mt else '', time=mt.group(2) if mt else t,
                       title=parts[0].replace('FDMATCH', '').strip())
            continue
        m = re.match(r'FDWIDE\s+(.+?) \| p ([\d.]+)% · кэф ([\d.]+)', line)
        if m and cur:
            bet = m.group(1).strip()
            legs.append(dict(cur, league='Футбол', p=float(m.group(2)) / 100, p_model=float(m.group(2)) / 100, bet=bet,
                             kef=float(m.group(3)), src='Pinnacle', cat=cat(bet)))
    return legs


def candidates(legs):
    ok = [x for x in legs if x['p'] >= P_MIN and K_MIN <= x['kef'] <= K_MAX and x['cat'] in CAT_OK]
    by = {}
    for x in sorted(ok, key=lambda x: -x['p']):
        by.setdefault((x['home'], x['away']), []).append(x)
    return {k: v[:TOP_PER_MATCH] for k, v in by.items()}


def best_coupon(by, n, used, lo_hi):
    keys = [k for k in by if k not in used]
    best = None
    for ms in itertools.combinations(keys, n):
        for legs in itertools.product(*(by[k] for k in ms)):
            if sum(x['cat'] == 'fora' for x in legs) > MAX_FORA:
                continue
            k = round(math.prod(x['kef'] for x in legs), 2)
            if not lo_hi[0] <= k <= lo_hi[1]:
                continue
            p = math.prod(x['p'] for x in legs)
            if best is None or p > best[0]:
                best = (p, k, legs)
    return best


def build(legs, sizes):
    by = candidates(legs)
    used, out = set(), []
    for n in sizes:
        b = best_coupon(by, n, used, TARGET) or best_coupon(by, n, used, WIDE)
        if not b:
            out.append(dict(size=n, legs=[], note='нет сочетания %d ног в рамках %.2f–%.2f' % (n, WIDE[0], WIDE[1])))
            continue
        p, k, ls = b
        used |= {(x['home'], x['away']) for x in ls}
        L = []
        for x in sorted(ls, key=lambda x: (x['date'], x['time'])):
            full, short = human(x['bet'], x['home'], x['away'], x['league'])
            L.append(dict(x, bet_full=full, bet_short=short))
        out.append(dict(size=n, legs=L, kef=k, p=round(p, 4), p_line=round(1 / k, 4),
                        in_target=TARGET[0] <= k <= TARGET[1]))
    return out, by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nhl')
    ap.add_argument('--khl')
    ap.add_argument('--foot')
    ap.add_argument('--sizes', default='3,3,2')
    ap.add_argument('--out')
    a = ap.parse_args()
    legs = []
    if a.nhl:
        legs += parse_brief(a.nhl, 'НХЛ')
    if a.khl:
        legs += parse_brief(a.khl, 'КХЛ')
    if a.foot:
        legs += parse_foot(a.foot)
    coupons, by = build(legs, [int(s) for s in a.sizes.split(',')])
    print('Кандидаты (p ≥ %d %%, кэф %.2f–%.2f, без 1Х/Х2): %d матчей' % (100 * P_MIN, K_MIN, K_MAX, len(by)))
    for (h, aw), xs in sorted(by.items(), key=lambda kv: -kv[1][0]['p']):
        print('  %s — %s: %s' % (h, aw, ' | '.join('%s %.2f (%.1f%%)' % (x['bet'], x['kef'], 100 * x['p']) for x in xs)))
    for i, c in enumerate(coupons, 1):
        if not c['legs']:
            print('Купон %d: %s' % (i, c['note']))
            continue
        print('Купон %d (%d ноги): кэф %.2f%s, модель %.1f %% против %.1f %% в кэфе' % (
            i, c['size'], c['kef'], '' if c['in_target'] else ' (вне 1,80–2,00)', 100 * c['p'], 100 * c['p_line']))
        for x in c['legs']:
            print('   %s %s %s — %s: %s · %.2f (%.1f%%)' % (x['league'], x['time'], x['home'], x['away'], x['bet_full'],
                                                       x['kef'], 100 * x['p']))
    if a.out:
        json.dump(dict(coupons=coupons), open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
