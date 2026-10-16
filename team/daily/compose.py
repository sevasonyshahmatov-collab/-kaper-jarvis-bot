# -*- coding: utf-8 -*-
"""Тексты двух утренних постов из данных и выбора движка (variety.Plan):
  morning_post(day, khl, nhl, leaders, plan) → {text, layout, tags, info}   «Начало игрового дня»
  recap_post(day, rows, week, plan, photo)    → {text, layout, tags, info}   «Итоги вчерашних ставок»
rows — рассчитанные прогнозы: {league, home, away, start, bet, kef, res: win/loss/push, legs, why, g: матч}.
Шесть подач (макетов) у каждого поста — list, tablo, short, story, qa, number; какой — решает движок.
"""
import html
import os
import re
import sys
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'picks'))

import check  # noqa: E402  tags_ok, EMOJI, BANNED — те же проверки, что у постов-прогнозов
import settle  # noqa: E402

MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
WD = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
WD_ACC = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
WD_KEY = ['mon', 'mid', 'mid', 'mid', 'fri', 'sat', 'sun']
CAPTION_MAX, TEXT_MAX = 1024, 4000
MORE_BANNED = ('таблиц', 'букмекер', 'фонбет', 'pinnacle', 'пинакл', 'гарантир', 'беспроигрыш', '100%')

DERBY = {  # пара → как назвать (только общеизвестные противостояния)
    ('ЦСКА', 'Спартак'): 'московское дерби', ('ЦСКА', 'Динамо Москва'): 'московское дерби',
    ('Динамо Москва', 'Спартак'): 'московское дерби', ('СКА', 'ЦСКА'): 'армейское дерби',
    ('Ак Барс', 'Салават Юлаев'): 'зелёное дерби', ('Ак Барс', 'Нефтехимик'): 'татарстанское дерби',
    ('Металлург', 'Трактор'): 'уральское дерби', ('Автомобилист', 'Трактор'): 'уральское дерби',
    ('Автомобилист', 'Металлург'): 'уральское дерби', ('Авангард', 'Сибирь'): 'сибирское дерби',
    ('Динамо Минск', 'Динамо Москва'): 'динамовское дерби', ('Локомотив', 'Северсталь'): 'дерби соседей',
    ('Лада', 'Торпедо'): 'волжское дерби',
    ('Айлендерс', 'Рейнджерс'): 'нью-йоркское дерби', ('Нью-Джерси', 'Рейнджерс'): 'дерби через Гудзон',
    ('Калгари', 'Эдмонтон'): 'битва Альберты', ('Монреаль', 'Торонто'): 'канадская классика',
    ('Бостон', 'Монреаль'): 'одно из старейших противостояний НХЛ', ('Питтсбург', 'Филадельфия'): 'пенсильванское дерби',
    ('Анахайм', 'Лос-Анджелес'): 'калифорнийское дерби', ('Лос-Анджелес', 'Сан-Хосе'): 'калифорнийское дерби',
    ('Анахайм', 'Сан-Хосе'): 'калифорнийское дерби', ('Тампа-Бэй', 'Флорида'): 'флоридское дерби',
    ('Детройт', 'Чикаго'): 'классика «оригинальной шестёрки»', ('Оттава', 'Торонто'): 'битва Онтарио',
}
DERBY = {tuple(sorted(k)): v for k, v in DERBY.items()}


# ---------------------------------------------------------------- мелочи языка

def plural(n, one, few, many):
    return settle.plural(n, one, few, many)


def cap(s):
    return s[:1].upper() + s[1:] if s else s


def dm(d):
    return '%d %s' % (d.day, MONTHS[d.month - 1])


def hm(dt):
    return dt.strftime('%H:%M')


def esc(s):
    return html.escape(str(s), quote=False)


def kef_s(k):
    return ('%.2f' % k).replace('.', ',') if k else ''


def units_s(u):
    return '%s%s ед.' % ('+' if u > 0.004 else '−' if u < -0.004 else '', ('%.2f' % abs(u)).replace('.', ','))


def join_and(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' и ' + items[-1]


def fill(tpl, ctx):
    out = tpl.format(**ctx).replace('ед..', 'ед.')
    return re.sub(r'\s+([.,:;!?])', r'\1', out)


def bot_start(first_line):
    """Как бот (apps-script teamEditStart_) читает время матча из первой строки: дата словом + «ЧЧ:ММ» → пост встанет
    на выход «за 1,5 часа до матча». У утренних постов в первой строке этого быть не должно — пусть выходят сразу."""
    head = re.sub(r'<[^>]+>', '', first_line)
    d = re.search(r'(\d{1,2})\s+(январ|феврал|марта|апрел|мая|июн|июл|август|сентябр|октябр|ноябр|декабр)', head, re.I)
    t = re.search(r'(\d{1,2})[:.](\d{2})', head)
    return bool(d and t)


def validate(text, photo=False):
    """→ список ошибок (пусто — можно отправлять)."""
    errs = []
    bad = check.tags_ok(text)
    if bad:
        errs.append(bad)
    if check.EMOJI.search(text):
        errs.append('эмодзи')
    low = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'#\w+', '', text))).lower()
    for w in tuple(check.BANNED) + MORE_BANNED:
        if w in low:
            errs.append('запретное «%s»' % w)
    if bot_start(text.split('\n')[0]):
        errs.append('в первой строке дата и время — бот поставит пост на выход к матчу')
    if len(text) > (CAPTION_MAX if photo else TEXT_MAX):
        errs.append('длина %d > %d' % (len(text), CAPTION_MAX if photo else TEXT_MAX))
    return errs


def tags_for(leagues):
    return ' '.join(t for lg, t in (('KHL', '#кхл'), ('NHL', '#нхл')) if lg in leagues)


def compose(parts):
    """Склеить блоки: None/'' выбрасываем, подряд идущие пустые строки — одна."""
    out = []
    for p in parts:
        if p is None:
            continue
        p = re.sub(r'[ \t]+', ' ', p).strip(' ')
        if p == '' and (not out or out[-1] == ''):
            continue
        out.append(p)
    while out and out[-1] == '':
        out.pop()
    return '\n'.join(out)


def sent(*xs):
    """Предложения через пробел, пустые — мимо."""
    return ' '.join(x for x in xs if x)


# ---------------------------------------------------------------- «Начало игрового дня»

def _derby(khl, nhl, leaders):
    for g in khl + nhl:
        name = DERBY.get(tuple(sorted((g['home'], g['away']))))
        if name:
            return g, name
    for g in nhl:
        if g.get('ab_h') in leaders and g.get('ab_a') in leaders:
            return g, 'встреча лидеров НХЛ'
    return None, None


def morning_ctx(day, khl, nhl, leaders, plan):
    n_k, n_n = len(khl), len(nhl)
    addr = plan.one('addr', 0)
    c = dict(addr=addr, Addr=cap(addr), wd=WD[day.weekday()], Wd=cap(WD[day.weekday()]), wd_acc=WD_ACC[day.weekday()],
             date=dm(day), n_khl=n_k, n_nhl=n_n, n_total=n_k + n_n,
             n_khl_m=plural(n_k, 'матч', 'матча', 'матчей'), n_nhl_m=plural(n_n, 'матч', 'матча', 'матчей'),
             n_total_m=plural(n_k + n_n, 'матч', 'матча', 'матчей'),
             leagues_text=' и '.join(x for x, n in (('КХЛ', n_k), ('НХЛ', n_n)) if n),
             n_leagues='две лиги' if n_k and n_n else 'одна лига',
             night='ночь на %s' % dm(day + timedelta(days=1)))
    for key, games in (('khl', khl), ('nhl', nhl)):
        if games:
            first, last = hm(games[0]['start']), hm(games[-1]['start'])
            c[key + '_first'], c[key + '_last'] = first, last
            c[key + '_when'] = 'в %s' % first if first == last else 'с %s до %s' % (first, last)
            c[key + '_range'] = first if first == last else '%s–%s' % (first, last)
            c[key + '_lastline'] = '' if first == last else ', последний матч — в %s' % last
    g, name = _derby(khl, nhl, leaders)
    if g:
        c.update(derby='%s — %s' % (g['home'], g['away']), derby_name=name, Derby_name=cap(name), derby_time=hm(g['start']))
    c['few_list'] = join_and('%s — %s (%s)' % (x['home'], x['away'], hm(x['start'])) for x in khl + nhl)
    total = n_k + n_n
    c['situation'] = ('few' if total <= 3 else 'both_big' if n_k and n_n and total >= 12 else 'both' if n_k and n_n
                      else 'khl_only' if n_k else 'nhl_only')
    return c


def morning_post(day, khl, nhl, leaders, plan):
    if not khl and not nhl:
        return None
    c = morning_ctx(day, khl, nhl, leaders, plan)
    P = lambda bank: fill(plan.one(bank), c)                      # noqa: E731
    lay = plan.layout('m')
    day_s = P('m.day.' + c['situation'])
    derby = P('m.derby') if c.get('derby') else None
    nhlbig = P('m.nhlbig') if len(nhl) >= 10 and c['situation'] != 'nhl_only' else None
    khl_t = P('m.khl_times') if khl else None
    nhl_t = P('m.nhl_times') if nhl else None
    wd = fill(plan.one('m.wd.' + WD_KEY[day.weekday()]), c)
    tags = tags_for([lg for lg, gs in (('KHL', khl), ('NHL', nhl)) if gs])
    hello = P('m.hello')

    def listing():
        out = []
        if khl:
            out += ['<b>КХЛ</b>'] + ['%s %s — %s' % (hm(g['start']), esc(g['home']), esc(g['away'])) for g in khl]
        if nhl:
            out += ([''] if khl else []) + ['<b>НХЛ</b> · %s' % c['night']] + \
                   ['%s %s — %s' % (hm(g['start']), esc(g['home']), esc(g['away'])) for g in nhl]
        return out

    if lay == 'list':
        text = compose([P('m.head'), '', sent(hello, day_s, derby), ''] + listing() + ['', sent(P('m.cta'), P('m.picks')), '', tags])
    elif lay == 'tablo':
        board = []
        if khl:
            board.append('<b>КХЛ</b> · %s · %s' % (c['n_khl_m'], c['khl_range']))
        if nhl:
            board.append('<b>НХЛ</b> · %s · %s · %s' % (c['n_nhl_m'], c['nhl_range'], c['night']))
        if c.get('derby'):
            board.append('Главное: %s, %s · %s' % (c['derby'], c['derby_time'], c['derby_name']))
        text = compose([hello, day_s, '', '<blockquote>' + '\n'.join(board) + '</blockquote>', '',
                        sent(wd, P('m.cta')), P('m.close'), '', tags])
    elif lay == 'short':
        text = compose([sent(hello, day_s), P('m.cta'), '', tags])
    elif lay == 'story':
        text = compose([hello, '', sent(day_s, nhlbig, khl_t, derby, nhl_t, wd), '', sent(P('m.cta'), P('m.picks'), P('m.close')),
                        '', tags])
    elif lay == 'qa':
        Q = lambda k: '<b>%s</b>' % plan.one('m.q.' + k)            # noqa: E731
        text = compose([hello, '', Q('what'), sent(day_s, nhlbig), '', Q('when'), sent(khl_t, nhl_t), '',
                        Q('main') if derby else None, derby, '' if derby else None, Q('next'), sent(P('m.cta'), P('m.picks')),
                        '', tags])
    else:  # number
        text = compose([P('m.num'), '', sent(hello, wd), sent(khl_t, nhl_t, nhlbig), derby, '', sent(P('m.cta'), P('m.close')),
                        '', tags])
    return dict(text=text, layout=lay, tags=tags, info=dict(situation=c['situation'], khl=len(khl), nhl=len(nhl),
                                                             khl_when=c.get('khl_when'), nhl_when=c.get('nhl_when'),
                                                             derby=c.get('derby')))


# ---------------------------------------------------------------- «Итоги вчерашних ставок»

def score_s(g):
    return '%d:%d%s' % (g['hg'], g['ag'], ' ' + g['end'] if g.get('end') else '')


def section(r):
    """Подзаголовок группы: «КХЛ · 15 октября» / «НХЛ · ночь на 16 октября»."""
    st = r['g']['start']
    if r['league'] == 'KHL':
        return 'КХЛ · %s' % dm(st)
    night = st.date() if st.hour < 12 else st.date() + timedelta(days=1)
    return 'НХЛ · ночь на %s' % dm(night)


def tally(rows):
    w = sum(r['res'] == settle.WIN for r in rows)
    l_ = sum(r['res'] == settle.LOSS for r in rows)
    p = sum(r['res'] == settle.PUSH for r in rows)
    known = [r for r in rows if r.get('kef') and not (r['res'] == settle.WIN and len(r['legs']) > 1 and r.get('leg_push'))]
    u = sum((r['kef'] - 1) if r['res'] == settle.WIN else -1 if r['res'] == settle.LOSS else 0 for r in known)
    return dict(w=w, l=l_, p=p, n=len(rows), d=w + l_, units=u if known else None, known=len(known))


def tone(t):
    if t['d'] == 0:
        return 'allpush', 'even'
    if t['w'] == t['d']:
        return 'perfect', 'up'
    if t['w'] == 0:
        return 'zero', 'down'
    r = t['w'] / t['d']
    return ('up', 'up') if r > 0.5 else ('even', 'even') if r == 0.5 else ('down', 'down')


def recap_ctx(day, rows, week, plan):
    t = tally(rows)
    addr = plan.one('addr', 1)
    c = dict(addr=addr, Addr=cap(addr), ydate=dm(day - timedelta(days=1)), n_sob=plural(t['n'], 'событие', 'события', 'событий'),
             n_prog=plural(t['n'], 'прогноз', 'прогноза', 'прогнозов'), n_count=t['n'], w=t['w'], d=t['d'],
             score='%d из %d' % (t['w'], t['d']),
             ret_note='' if not t['p'] else ' и один возврат' if t['p'] == 1 else ' и %s' % plural(t['p'], 'возврат', 'возврата', 'возвратов'))
    if t['units'] is not None:
        c['units'] = units_s(t['units']) + ('' if t['known'] == t['n'] else ' (по %s с известным кэфом)'
                                            % plural(t['known'], 'прогнозу', 'прогнозам', 'прогнозам'))
    if week:
        wt = tally(week)
        c['wscore'] = '%d из %d' % (wt['w'], wt['d']) + ('' if not wt['p'] else ', %s' % plural(wt['p'], 'возврат', 'возврата', 'возвратов'))
        c['wunits'] = ', %s' % units_s(wt['units']) if wt['units'] is not None and wt['known'] == wt['n'] else ''
    return c, t


def recap_post(day, rows, week, plan, photo=False, compact=False):
    """week — прогнозы недели (вместе с вчерашними) или None."""
    if not rows:
        return None
    c, t = recap_ctx(day, rows, week, plan)
    P = lambda bank: fill(plan.one(bank), c)                      # noqa: E731
    lay = plan.layout('r')
    res_kind, close_kind = tone(t)
    res = P('r.res.' + res_kind)
    units = P('r.units') if 'units' in c and t['d'] else None
    weekline = None
    if week and len(week) > len(rows):
        weekline = P('r.week_done' if day.weekday() == 0 else 'r.week')
    close = P('r.close.' + close_kind)
    hello, count = P('r.hello'), P('r.count')
    pushes = [r for r in rows if r['res'] == settle.PUSH]
    ret = fill(plan.one('r.ret'), dict(match='%s — %s' % (pushes[0]['home'], pushes[0]['away']), reason=pushes[0]['why'])) \
        if pushes and lay not in ('list', 'tablo') else None
    leagues = sorted({r['league'] for r in rows}, key=lambda x: x != 'KHL')
    tags = tags_for(leagues)
    sections = []
    for r in rows:
        s = section(r)
        if not sections or sections[-1][0] != s:
            sections.append((s, []))
        sections[-1][1].append(r)
    multi = len(sections) > 1
    mark = lambda r: '<b>%s</b>' % settle.MARK[r['res']]          # noqa: E731
    match = lambda r: '%s — %s' % (esc(r['home']), esc(r['away']))  # noqa: E731

    def full(r):
        k = kef_s(r.get('kef'))
        return ['<b>%s %s</b>' % (match(r), score_s(r['g'])), '%s%s → %s' % (esc(r['bet']), ' · ' + k if k else '', mark(r))]

    def comp(r):
        return ['%s %s · %s · %s' % (match(r), score_s(r['g']), esc(r['short']), mark(r))]

    def listing(fmt, label=True):
        out = []
        for s, rs in sections:
            if multi and label:
                out += ([''] if out and fmt is full else []) + ['<i>%s</i>' % s]
            for r in rs:
                out += fmt(r)
        return out

    def items(kind):
        rs = [r for r in rows if r['res'] == kind]
        return '; '.join('%s %s (%s)' % (match(r), score_s(r['g']), esc(r['bet'])) for r in rs)

    if lay == 'list':
        body = listing(comp if compact else full)
        text = compose([P('r.head'), '', sent(hello, count), '', P('r.trans')] + body +
                       ['', sent(res, units), weekline, close, '', tags])
    elif lay == 'tablo':
        board = []
        for s, rs in sections:
            if multi:
                board.append('<i>%s</i>' % s)
            board += ['%s · %s · %s · %s' % (match(r), score_s(r['g']), esc(r['short']), mark(r)) for r in rs]
        text = compose([hello, count, '', '<blockquote>' + '\n'.join(board) + '</blockquote>', '', sent(res, units), weekline,
                        close, '', tags])
    elif lay == 'short':
        groups = []
        for kind in (settle.WIN, settle.LOSS, settle.PUSH):
            rs = [r for r in rows if r['res'] == kind]
            if rs:
                groups.append('<b>%s</b> · %s' % (settle.MARK[kind], ', '.join('%s %s' % (match(r), score_s(r['g'])) for r in rs)))
        text = compose([sent(hello, res)] + groups + [sent(units, weekline), close, '', tags])
    elif lay == 'story':
        parts = []
        for kind, key in ((settle.WIN, 'won'), (settle.LOSS, 'lost')):
            if any(r['res'] == kind for r in rows):
                parts.append(fill(plan.one('r.story.' + key), dict(items=items(kind))))
        if pushes:
            parts.append(fill(plan.one('r.story.push'), dict(items=items(settle.PUSH))))
        text = compose([hello, '', sent(count, *parts), ret, '', sent(res, units, weekline), close, '', tags])
    elif lay == 'qa':
        Q = lambda k: '<b>%s</b>' % plan.one('r.q.' + k)            # noqa: E731
        won, lost = items(settle.WIN), items(settle.LOSS)
        text = compose([hello, '', Q('count'), count, '', Q('won'), (won + '.') if won else 'Ничего.', '', Q('lost'),
                        (lost + '.') if lost else 'Ничего.', ret, '', Q('total'), sent(res, units), weekline, '', close, '', tags])
    else:  # number
        text = compose([P('r.num'), '', sent(hello, count)] + listing(comp) + [ret, '', sent(units, weekline), close, '', tags])
    return dict(text=text, layout=lay, tags=tags, tally=t, tone=res_kind)
