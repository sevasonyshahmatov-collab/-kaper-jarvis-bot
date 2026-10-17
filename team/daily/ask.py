# -*- coding: utf-8 -*-
"""Итоги по выбору владельца: утренний опрос бота «На какие прогнозы вчера ставили?» (apps-script/project/Код.js,
recapAsk*). Владелец отмечает кнопками отправленные ему прогнозы (номера из team/picks/SENT.md) и присылает свои строками
«Прогноз: …». По «Готово» бот пишет строку в team/INBOX.md и запускает itogi.yml с payload
{"kind": "team", "job": "team/out/<D>/recap_ask.json", "pids": [...], "free": [...], "day": "<D>", "at": "<D> ЧЧ:ММ"};
render/team_job.py передаёт выбор скрипту переменными RECAP_PIDS / RECAP_FREE / RECAP_DAY / RECAP_AT.

Здесь:
  • selection(d, inbox) — выбор владельца на утро d: из переменных (запуск ботом) или из строки INBOX
    «итоги ставок ДД.ММ: выбрано 1510-1, 1510-6; свои: "Прогноз: …"; …» / «… : сегодня без итогов» (ручной перезапуск);
  • window_games(d) — вчерашние матчи для своих строк: начало с 08:00 вчера до 08:00 утра d (МСК), как у кнопок бота;
  • parse_free(lines, games) — «Прогноз: …» → прогноз {league, home, away, start, bet, kef} или «не понял: … — почему».
    Матч — по названиям команд (русские названия и падежи обеих лиг, сокращения: Тампа, Динамо Мн…); «Динамо» без уточнения,
    если вчера играли оба Динамо, — не угадываем, пишем владельцу. Ставка — тем же словарём, что settle.py (победа, П1/П2,
    «не проиграет», 1X/X2, фора/Ф1, тотал/ТБ/ТМ, ИТБ/ИТМ, «с учётом ОТ»/«в осн. время», экспресс «и»/«+»); в итогах — в
    одной форме («победа СКА в основное время»). Кэф: «кэф 1,85», «коэф. 1.85», «@1.85» или число в конце строки, если без
    него ставка разбирается («победа СКА 1,85» — кэф; «тотал больше 5,5» — линия, кэфа нет).
"""
import json
import os
import re
from datetime import datetime, timedelta

import data
import settle
from data import MSK

SEL_RE = re.compile(r'- \[[ x]\] (\d\d)\.(\d\d) (\d\d):(\d\d) · итоги ставок (\d\d)\.(\d\d): (.*)$')
PID_RE = re.compile(r'^\d{4}-[0-9a-z]+$')
PREP = r'(?:в матче|на матч|матч|в игре|игра|против|vs|над|с|со)'
AMBIG = {'динамо': ('Динамо Москва', 'Динамо Минск')}
ALIAS = {  # дополнительно к settle.EXTRA: как пишут в чате
    'Питтсбург': ('питсбург',), 'Лос-Анджелес': ('лос анджелес', 'ла кингз', 'кингз'), 'Шанхайские Драконы': ('драконы', 'шанхайские'),
    'Динамо Москва': ('динамо москва', 'динамо мск', 'динамо м'), 'Динамо Минск': ('динамо минск', 'динамо мн'),
    'Тампа-Бэй': ('тампа',), 'Ак Барс': ('ак барс',), 'Салават Юлаев': ('салават', 'юлаев'), 'Нью-Джерси': ('джерси',),
    'Вегас': ('вегас',), 'Айлендерс': ('айлендерс', 'айлс'), 'Рейнджерс': ('рейнджерс',), 'Коламбус': ('коламбус',),
}
KEF_RX = re.compile(r'[,;]?\s*(?:кэф|кеф|коэф\w*\.?|кф|@)\s*[:=]?\s*(\d+(?:\.\d+)?)')


# ---------------------------------------------------------------- выбор владельца

def _at(s):
    try:
        return datetime.strptime(str(s).strip()[:16], '%Y-%m-%d %H:%M').replace(tzinfo=MSK)
    except ValueError:
        return None


def parse_selections(text, ref):
    """team/INBOX.md → {date утра: {at, pids, free, none}} (за день — последняя строка)."""
    from ledger import _year_for
    out = {}
    for line in str(text or '').splitlines():
        m = SEL_RE.match(line.strip())
        if not m:
            continue
        sd, smo, hh, mm, dd, mo, body = m.groups()
        y = _year_for(int(dd), int(mo), ref)
        day = datetime(y, int(mo), int(dd)).date()
        at = datetime(_year_for(int(sd), int(smo), ref), int(smo), int(sd), int(hh), int(mm), tzinfo=MSK)
        if body.strip().startswith('сегодня без итогов'):
            out[day] = dict(at=at, pids=[], free=[], none=True)
            continue
        head, _, own = body.partition('; свои: ')
        pids = [x.strip() for x in head.replace('выбрано', '').split(',') if PID_RE.match(x.strip())]
        out[day] = dict(at=at, pids=pids, free=re.findall(r'"([^"]*)"', own), none=False)
    return out


def selection(d, inbox_text, env=None):
    """Выбор на утро d: переменные RECAP_* (запуск ботом; день должен совпасть) или строка INBOX. None — выбора нет."""
    env = os.environ if env is None else env
    if env.get('RECAP_DAY') == d.isoformat() and (env.get('RECAP_PIDS') or env.get('RECAP_FREE')):
        pids = [x.strip() for x in str(env.get('RECAP_PIDS') or '').split(',') if PID_RE.match(x.strip())]
        try:
            free = [str(x) for x in json.loads(env.get('RECAP_FREE') or '[]')]
        except ValueError:
            free = []
        at = _at(env.get('RECAP_AT') or '') or data.now_msk()
        return dict(at=at, pids=pids, free=free, none=False, src='payload')
    sel = parse_selections(inbox_text, datetime(d.year, d.month, d.day, 12, tzinfo=MSK)).get(d)
    if sel:
        sel['src'] = 'inbox'
    return sel


# ---------------------------------------------------------------- вчерашние матчи

def window(d):
    t1 = datetime(d.year, d.month, d.day, 8, 0, tzinfo=MSK)
    return t1 - timedelta(days=1), t1


def window_games(d):
    """Матчи КХЛ и НХЛ с началом в окне опроса утра d. → (матчи, ошибки)."""
    t0, t1 = window(d)
    games, errs = [], []
    try:
        games += data.khl_games(t0, t1)
    except Exception as e:  # noqa: BLE001
        errs.append('КХЛ: вчерашние матчи не загрузились (%s)' % data.err(e))
    try:
        games += [g for g in data.nhl_day((d - timedelta(days=1)).isoformat()) if t0 <= g['start'] < t1]
    except KeyError:
        pass
    except Exception as e:  # noqa: BLE001
        errs.append('НХЛ: вчерашние матчи не загрузились (%s)' % data.err(e))
    return [g for g in games if g['state'] != 'off'], errs


# ---------------------------------------------------------------- названия команд

def _n(s):
    """Как settle._norm, плюс дефис между буквами — пробел («Тампа-Бэй» = «тампа бэй»)."""
    return re.sub(r'(?<=[а-яa-z])-(?=[а-яa-z])', ' ', settle._norm(s))


def _decl(word):
    """Падежи последнего слова названия: «лада» → лады, ладе, ладу, ладой; «сиэтл» → сиэтла, сиэтлу, сиэтлом, сиэтле."""
    w = word
    if len(w) < 3 or w[-1] in 'оеиуэю':
        return []
    if w[-1] == 'а':
        y = 'и' if w[-2] in 'кгхжшчщ' else 'ы'
        return [w[:-1] + x for x in (y, 'е', 'у', 'ой')]
    if w[-1] == 'я':
        return [w[:-1] + x for x in ('и', 'е', 'ю', 'ей')]
    if w[-1] == 'ь':
        return [w[:-1] + 'и', w + 'ю']
    if w[-1] == 'й':
        return [w[:-1] + x for x in ('я', 'ю', 'ем', 'е')]
    if w[-1] == 'ы':
        return [w[:-1] + x for x in ('ов', 'ам', 'ами', 'ах')]
    return [w + x for x in ('а', 'у', 'ом', 'е')]


_FORMS = None


def forms():
    """{форма (нормализованная): (команды…)} — обе лиги; «динамо» — две команды."""
    global _FORMS
    if _FORMS is None:
        out = {}
        for team in settle.GEN:
            fs = {_n(team), _n(settle.gen(team))} | {_n(x) for x in settle.EXTRA.get(team, ())} | {_n(x) for x in ALIAS.get(team, ())}
            if team != team.upper():                                  # СКА, ЦСКА не склоняются
                base = _n(team).split(' ')
                fs |= {' '.join(base[:-1] + [x]) for x in _decl(base[-1])}
            for f in fs:
                out.setdefault(f, set()).add(team)
        for f, ts in AMBIG.items():
            out[f] = set(ts)
        _FORMS = {f: tuple(sorted(ts)) for f, ts in out.items()}
    return _FORMS


def find_teams(t):
    """Упоминания команд в нормализованном тексте: [(начало, конец, (команды…))], длинные формы — первыми, без наложений."""
    taken, out = [False] * len(t), []
    for f in sorted(forms(), key=len, reverse=True):
        for m in re.finditer(r'(?<![а-яa-z0-9])%s(?![а-яa-z0-9])' % re.escape(f), t):
            if any(taken[m.start():m.end()]):
                continue
            taken[m.start():m.end()] = [True] * (m.end() - m.start())
            out.append((m.start(), m.end(), forms()[f]))
    return sorted(out)


# ---------------------------------------------------------------- строка «Прогноз: …»

def _num_s(v, sign=False):
    s = ('%g' % abs(v)).replace('.', ',')
    return (('+' if v > 0 else '−' if v < 0 else '') + s) if sign else s


def phrase(legs, home, away):
    """Ставка одной формой для поста: «победа СКА в основное время», «итоговая победа Торпедо», «фора Сиэтла +1,5»…"""
    out = []
    for l_ in legs:
        k, fin = l_['kind'], l_.get('scope') == 'fin'
        team = home if l_.get('side', 'h') == 'h' else away
        G = settle.gen(team)
        ot = ' с учётом ОТ' if fin else ''
        if k == 'win':
            out.append('итоговая победа %s' % G if fin else 'победа %s в основное время' % G)
        elif k == 'dc':
            out.append('%s не проиграет %s' % (team, 'с учётом ОТ' if fin else 'в основное время'))
        elif k == 'draw':
            out.append('ничья в основное время')
        elif k == 'nodraw':
            out.append('12 (без ничьей в основное время)')
        elif k == 'hc':
            out.append('фора %s %s%s' % (G, _num_s(l_['line'], True), ot))
        elif k == 'tot':
            out.append('тотал матча %s %s%s' % ('больше' if l_['ou'] == 'over' else 'меньше', _num_s(l_['line']), ot))
        elif k == 'it':
            out.append('индивидуальный тотал %s %s %s%s' % (G, 'больше' if l_['ou'] == 'over' else 'меньше', _num_s(l_['line']), ot))
    return ' и '.join(out)


def _pick_game(occ, games):
    """Матч по упоминаниям команд → (матч, None) или (None, почему)."""
    played = {}
    for g in games:
        for t in (g['home'], g['away']):
            played.setdefault(t, []).append(g)
    named = sorted({t for _, _, ts in occ for t in ts})
    occ_f = [(a, b, tuple(t for t in ts if t in played)) for a, b, ts in occ]
    if not any(ts for _, _, ts in occ_f):
        return None, 'вчера не играли: %s' % ', '.join(named)
    score = {}
    for g in games:
        s = sum(1 for _, _, ts in occ_f if g['home'] in ts or g['away'] in ts)
        if s:
            score[id(g)] = (s, g)
    top = max(s for s, _ in score.values())
    best = [g for s, g in score.values() if s == top]
    if len(best) > 1:
        amb = [ts for _, _, ts in occ_f if len(ts) > 1]
        if amb:
            return None, 'непонятно, какая команда: %s' % ' или '.join(amb[0])
        return None, 'несколько матчей: %s' % '; '.join('%s — %s' % (g['home'], g['away']) for g in best)
    return best[0], None


def parse_line(line, games):
    """Одна строка «Прогноз: …» → (прогноз, None) или (None, почему не понял)."""
    body = re.sub(r'^\s*прогноз\s*:\s*', '', str(line), flags=re.I).strip()
    t = _n(body)
    kef = None
    m = KEF_RX.search(t)
    if m:
        kef = float(m.group(1))
        t = (t[:m.start()] + t[m.end():]).strip()
    occ = find_teams(t)
    if not occ:
        return None, 'не нашёл команду'
    g, why = _pick_game(occ, games)
    if not g:
        return None, why
    pair = {g['home'], g['away']}
    mine = [(a, b, [x for x in ts if x in pair][0]) for a, b, ts in occ if set(ts) & pair]
    drop, keep = [], []
    i = 0
    while i < len(mine):                                    # «Лада — СКА», «Вегас vs Калгари» — пара, не сторона ставки
        if i + 1 < len(mine) and mine[i][2] != mine[i + 1][2] and \
                re.fullmatch(r'[\s—–\-:,/]*(?:vs\.?|против|и)?[\s—–\-:,/]*', t[mine[i][1]:mine[i + 1][0]]):
            drop.append((mine[i][0], mine[i + 1][1]))
            i += 2
            continue
        keep.append(mine[i])
        i += 1
    first = keep[0][2] if keep else None
    out, pos = [], 0
    for a, b, team in sorted([(a, b, None) for a, b in drop] + keep):
        pre = t[pos:a]
        if team is None or (first and team != first):          # пара или «… над Тампой» — убрать вместе с предлогом
            pre = re.sub(r'\s*%s\s*$' % PREP, ' ', pre)
            out.append(pre)
        else:
            out.append(pre + settle._norm(settle.gen(team)))
        pos = b
    out.append(t[pos:])
    bet = re.sub(r'\s+', ' ', ''.join(out)).strip(' ,;:—-')
    bet = re.sub(r'^\s*%s\s+' % PREP, '', bet)
    if kef is None:                                         # число в конце — кэф, если без него ставка разбирается
        m = re.search(r'(?:^|[\s,;])(\d{1,2}\.\d{1,3})\s*$', bet)
        if m and 1.01 <= float(m.group(1)) <= 30:
            rest = bet[:m.start()].strip(' ,;')
            try:
                settle.parse(rest, g['home'], g['away'])
                kef, bet = float(m.group(1)), rest
            except ValueError:
                pass
    try:
        legs = settle.parse(bet, g['home'], g['away'])
        for l_ in legs:
            if l_['kind'] in ('tot', 'it', 'hc') and abs(l_['line'] * 2 - round(l_['line'] * 2)) > 1e-9:
                raise ValueError('азиатская линия — посчитайте вручную')
    except ValueError as e:
        return None, 'ставка: %s' % e
    if kef is not None and not 1.01 <= kef <= 30:
        kef = None
    return dict(pid='', league=g['league'], home=g['home'], away=g['away'], start=g['start'], bet=phrase(legs, g['home'], g['away']),
                kef=round(kef, 2) if kef else None, src='free', note=str(line).strip(), exact_time=True), None


def parse_free(lines, games):
    """→ (прогнозы, [(строка, почему)])."""
    ok, bad = [], []
    for line in lines or []:
        if not re.sub(r'^\s*прогноз\s*:\s*', '', str(line), flags=re.I).strip():
            continue
        p, why = parse_line(line, games)
        if p:
            ok.append(p)
        else:
            bad.append((str(line).strip(), why))
    return ok, bad
