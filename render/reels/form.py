# -*- coding: utf-8 -*-
"""Форма клуба для роликов «команда 1 → команда 2 → прогноз на дроп» (tape, jarvis, card).

Вход — запись team_stats.json аналитика:
  {"league", "last3": [{"date", "opp", "home", "score", "res"}], "points", "games", "place", "gd"}
Пустые (null) поля просто не показываются.
"""
import re

import poster

from reels import core as C

WIN = (46, 204, 113)
LOSS = (231, 76, 60)


def _res(r, score):
    s = str(r or '').strip().upper()
    if s[:1] in ('В', 'W'):
        return 'В'
    if s[:1] in ('П', 'L'):
        return 'П'
    try:                                                     # нет res — по счёту (счёт со стороны клуба)
        a, b = str(score).split()[0].split(':')
        return 'В' if int(a) > int(b) else 'П'
    except Exception:
        return ''


def opp_key(name):
    if name in poster.TEAMS:
        return name
    for k, v in poster.SHORT.items():
        if v == name and k in poster.TEAMS:
            return k
    return None


def _date_key(d):
    d = str(d or '')
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', d)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r'(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?', d)
    if m:
        return (int(m.group(3) or 0), int(m.group(2)), int(m.group(1)))
    return (0, 0, 0)


def _date_txt(d):
    k = _date_key(d)
    return '%02d.%02d' % (k[2], k[1]) if k[1] else str(d or '')


def _num(v):
    """Число из 16 / "+15" / "−3" / "7 в лиге (…)"; иначе None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    m = re.match(r'\s*([+\-−]?\d+)', str(v))
    return int(m.group(1).replace('−', '-')) if m else None


def _place_scope(v):
    """«12 на Востоке (общее 26 в лиге)» → «на Востоке»; «7 в лиге (…)» → «в лиге»."""
    if not isinstance(v, str):
        return ''
    s = re.sub(r'\(.*?\)', '', v)
    s = re.sub(r'^\s*[+\-−]?\d+\s*', '', s).strip()
    return s


def norm(rec):
    """Запись аналитика → dict(games=[...], points, gp, place, place_scope, gd); всё неизвестное — None."""
    rec = rec or {}
    games = []
    for g in sorted(rec.get('last3') or [], key=lambda g: _date_key(g.get('date')), reverse=True)[:3]:
        if not g or not g.get('score'):
            continue
        sc = str(g['score']).replace('-', ':').strip()
        parts = sc.split()
        note = ' '.join(parts[1:]).upper()
        note = {'OT': 'ОТ', 'SO': 'Б', 'ПБ': 'Б', 'БУЛ': 'Б', 'OT/SO': 'ОТ/Б'}.get(note, note)
        opp = str(g.get('opp') or '')
        games.append(dict(res=_res(g.get('res'), sc), score=parts[0] if parts else sc, note=note,
                          opp=poster.SHORT.get(opp, opp), opp_key=opp_key(opp), home=g.get('home'), date=_date_txt(g.get('date'))))
    return dict(games=games, points=_num(rec.get('points')), gp=_num(rec.get('games')), place=_num(rec.get('place')),
                place_scope=_place_scope(rec.get('place')), gd=_num(rec.get('gd')))


def gd_txt(v):
    return ('+%d' % v) if v > 0 else ('−%d' % -v) if v < 0 else '0'


def stat_rows(s):
    """[(подпись, значение-строка), ...] — только известные цифры."""
    out = []
    if s['points'] is not None:
        out.append(('ОЧКИ', '%d' % s['points']))
    if s['gp'] is not None:
        out.append(('МАТЧИ', '%d' % s['gp']))
    if s['place'] is not None:
        out.append(('МЕСТО', '%d' % s['place']))
    if s['gd'] is not None:
        out.append(('ШАЙБЫ ±', gd_txt(s['gd'])))
    return out


def form_word(s):
    """«2 из 3» — побед в последних играх."""
    g = s['games']
    if not g:
        return ''
    return '%d из %d' % (sum(1 for x in g if x['res'] == 'В'), len(g))


def split_pick(pick):
    """«Победа Барыса в основное время» → ('ПОБЕДА БАРЫСА', 'В ОСНОВНОЕ ВРЕМЯ')."""
    p = pick.strip()
    low = p.lower()
    for tail in (' в основное время', ' в осн. время', ' с учётом от', ' с учетом от'):
        if low.endswith(tail):
            return p[:-len(tail)].upper(), tail.strip().upper()
    return p.upper(), ''


def head_main(pick1):
    """Прогноз → (верхняя строка, главная) для шаблонов с крупной главной строкой (владелец 19.10: длинное не мельчить).
    «ПОБЕДА САЛАВАТА ЮЛАЕВА» → ('ПОБЕДА', 'САЛАВАТА ЮЛАЕВА'); «ИНДИВИДУАЛЬНЫЙ ТОТАЛ КОЛАМБУСА МЕНЬШЕ 2,5» →
    ('ИНДИВИДУАЛЬНЫЙ ТОТАЛ КОЛАМБУСА', 'МЕНЬШЕ 2,5'); иначе ('', весь прогноз)."""
    p = pick1.strip()
    m = re.match(r'(ПОБЕДА|ФОРА)\s+(.+)$', p)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r'(.+?)\s+((?:БОЛЬШЕ|МЕНЬШЕ|НЕ ПРОИГРАЕТ)\b.*)$', p)
    if m:
        return m.group(1), m.group(2)
    return '', p


def pick_team(h, a, pick):
    """'h' | 'a' — если в прогнозе названа команда; None — прогноз на матч целиком (тотал и т. п.)."""
    p = pick.lower().replace('-', ' ')
    for side, t in (('a', a), ('h', h)):
        if t.short.lower().replace('-', ' ').split()[0][:4] in p:
            return side
    return None


def fav_side(h, a, pick):
    """Чей прогноз: 'h' | 'a' — по основе названия в тексте прогноза."""
    p = pick.lower()
    for side, t in (('a', a), ('h', h)):
        st = t.short.lower().replace('-', ' ').split()[0][:4]
        if st in p.replace('-', ' '):
            return side
    return 'h'


def lg_ru(league):
    return 'НХЛ' if str(league).upper() == 'NHL' else 'КХЛ'


def tag(league):
    return 'JARVIS | NHL' if str(league).upper() == 'NHL' else 'JARVIS | KXL'


def res_col(r):
    return WIN if r == 'В' else LOSS if r == 'П' else (150, 150, 160)


def chip(r, d=60, txt=(255, 255, 255)):
    im = C.rrect(d, d, d * 0.22, res_col(r))
    C.put(im, C.text(r or '?', 'unb', d * 0.55, txt, 800), d / 2, d / 2)
    return im
