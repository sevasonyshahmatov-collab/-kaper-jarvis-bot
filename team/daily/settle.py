# -*- coding: utf-8 -*-
"""Расчёт ставки по финальному счёту: «зашло» / «минус» / «возврат».

В team/picks/calc.py расчёта ставок по счёту нет: там вероятности, а рынки (calc.markets) — предикаты только для линий
,5 (без возврата, без целых линий и без «с ОТ» для фор и тоталов). Отсюда берём его соглашение об основном времени
(победа в ОТ/Б — ровно на одну шайбу, значит счёт основного времени — (меньшее, меньшее)), а сами calc.markets служат
эталоном в проверке team/daily/test_daily.py: по каждой их ставке наш разбор текста и расчёт дают тот же итог.

Ставка — текст как в посте («победа СКА в осн. время», «Айлендерс не проиграют в основное время», «фора Сиэтла +1,5»,
«тотал матча меньше 4,5», «индивидуальный тотал Юты больше 2,5 в основное время», «итоговая победа Торпедо»,
«победа Бостона с учётом ОТ», «тотал меньше 6», «П1 и тотал меньше 5,5», «1X + тотал больше 3,5», «ИТБ Барыса больше 2,5»).
Правила (как в таблицах и team/picks/README.md, шаг 3):
  • победа / П1 / П2 / двойной шанс / фора / тоталы — по основному времени, если не сказано «итоговая», «с учётом ОТ»,
    «с ОТ», «включая ОТ»; «победа X» без уточнения — в основное время (П1/П2 в русской линии);
  • целая линия (тотал 6, фора −1) — при равенстве возврат; линии ,25 / ,75 не разбираем (ошибка → владельцу).
"""
import re

KHL_GEN = {'Динамо Москва': 'Динамо Москва', 'Авангард': 'Авангарда', 'Амур': 'Амура', 'ЦСКА': 'ЦСКА', 'Спартак': 'Спартака',
           'Торпедо': 'Торпедо', 'Сибирь': 'Сибири', 'Локомотив': 'Локомотива', 'Трактор': 'Трактора', 'Металлург': 'Металлурга',
           'Салават Юлаев': 'Салавата Юлаева', 'Нефтехимик': 'Нефтехимика', 'Динамо Минск': 'Динамо Минск', 'Ак Барс': 'Ак Барса',
           'Северсталь': 'Северстали', 'СКА': 'СКА', 'Барыс': 'Барыса', 'Автомобилист': 'Автомобилиста', 'Адмирал': 'Адмирала',
           'Лада': 'Лады', 'Сочи': 'Сочи', 'Шанхайские Драконы': 'Шанхайских Драконов'}
NHL_GEN = {'Анахайм': 'Анахайма', 'Бостон': 'Бостона', 'Баффало': 'Баффало', 'Калгари': 'Калгари', 'Каролина': 'Каролины',
           'Чикаго': 'Чикаго', 'Колорадо': 'Колорадо', 'Коламбус': 'Коламбуса', 'Даллас': 'Далласа', 'Детройт': 'Детройта',
           'Эдмонтон': 'Эдмонтона', 'Флорида': 'Флориды', 'Лос-Анджелес': 'Лос-Анджелеса', 'Миннесота': 'Миннесоты',
           'Монреаль': 'Монреаля', 'Нэшвилл': 'Нэшвилла', 'Нью-Джерси': 'Нью-Джерси', 'Айлендерс': 'Айлендерс',
           'Рейнджерс': 'Рейнджерс', 'Оттава': 'Оттавы', 'Филадельфия': 'Филадельфии', 'Питтсбург': 'Питтсбурга',
           'Сан-Хосе': 'Сан-Хосе', 'Сиэтл': 'Сиэтла', 'Сент-Луис': 'Сент-Луиса', 'Тампа-Бэй': 'Тампы', 'Торонто': 'Торонто',
           'Юта': 'Юты', 'Ванкувер': 'Ванкувера', 'Вегас': 'Вегаса', 'Вашингтон': 'Вашингтона', 'Виннипег': 'Виннипега'}
GEN = dict(KHL_GEN, **NHL_GEN)
ALIAS = {'Динамо Мн': 'Динамо Минск', 'Динамо М': 'Динамо Москва', 'Динамо Мск': 'Динамо Москва', 'Шанхай': 'Шанхайские Драконы',
         'Салават': 'Салават Юлаев', 'Металлург Мг': 'Металлург', 'Тампа': 'Тампа-Бэй', 'Ак Барс Казань': 'Ак Барс'}
EXTRA = {'Тампа-Бэй': ('тампа', 'тампы'), 'Динамо Минск': ('динамо мн',), 'Динамо Москва': ('динамо м', 'динамо мск'),
         'Шанхайские Драконы': ('шанхай', 'шанхая'), 'Салават Юлаев': ('салават', 'салавата')}

WIN, LOSS, PUSH = 'win', 'loss', 'push'
MARK = {WIN: 'ЗАШЛО', LOSS: 'МИНУС', PUSH: 'ВОЗВРАТ'}


def canon(name):
    name = re.sub(r'\s+', ' ', str(name or '')).strip()
    return ALIAS.get(name, name)


def gen(name):
    """Родительный падеж: «победа Спартака», «фора Тампы»."""
    return GEN.get(canon(name), canon(name))


def _norm(s):
    s = str(s or '').lower().replace('ё', 'е').replace(' ', ' ')
    s = re.sub(r'[−–‐‑](?=\s?\d)', '-', s)          # минус «−1,5», «–1,5» → «-1,5»
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)
    s = re.sub(r'(?<![а-яa-z])([12]?)х([12]?)(?![а-яa-z])', r'\1x\2', s)   # кириллическая Х в «1Х», «Х2»
    s = re.sub(r'\bс от и б\b', 'с от/б', s)                         # «(с ОТ и Б)» — не делить на две ставки
    return re.sub(r'\s+', ' ', s).strip()


def _forms(team):
    t = canon(team)
    out = {_norm(t), _norm(gen(t))} | {_norm(x) for x in EXTRA.get(t, ())}
    return sorted(out, key=len, reverse=True)


def _find_side(text, home, away):
    """'h' / 'a' / None — какая команда названа в тексте ставки (самое длинное совпадение)."""
    best = (0, None)
    for side, team in (('h', home), ('a', away)):
        for f in _forms(team):
            if re.search(r'(?<![\w-])%s(?![\w])' % re.escape(f), text) and len(f) > best[0]:
                best = (len(f), side)
    return best[1]


def _num(text, signed=False):
    m = re.search(r'([+-]\s?)?(\d+(?:\.\d+)?)', text)
    if not m:
        return None
    v = float(m.group(2))
    return -v if signed and m.group(1) and m.group(1).strip() == '-' else v


def _scope(text, default='reg'):
    if re.search(r'итогов|с уч[е]?том (от|овертайм)|включая (от|овертайм)|\bс от\b|с овертайм', text):
        return 'fin'
    if re.search(r'осн(\.|овн)|по основному', text):
        return 'reg'
    return default


def _ou(text):
    if re.search(r'больше|\bтб\b|\bитб|\bит\s?[12]\s?б\b|over', text):
        return 'over'
    if re.search(r'меньше|\bтм\b|\bитм|\bит\s?[12]\s?м\b|under', text):
        return 'under'
    return None


def parse_leg(text, home, away):
    t = _norm(text)
    t = re.sub(r'\((?:[^)]*(?:владел|повтор|проб|исправ)[^)]*)\)', ' ', t).strip()
    side = _find_side(t, home, away)
    scope = _scope(t)
    # индивидуальный тотал
    # «ИТБ1», «ИТБ 2» и «ИТ1Б», «ИТ2М» (номер команды до «Б/М» — так пишет владелец, 27.10)
    m = re.search(r'индивидуальн\w* тотал|\bит[бм]\b|\bит[бм]\s?[12](?![\d.])|\bит\s?[12]\s?[бм]\b', t)
    if m:
        code = re.search(r'\bит[бм]\s?([12])(?![\d.])|\bит\s?([12])\s?[бм]\b', t)
        s = side or ({'1': 'h', '2': 'a'}.get(code.group(1) or code.group(2)) if code else None)
        ou, line = _ou(t), _num(re.sub(r'\bит[бм]\s?[12](?![\d.])|\bит\s?[12]\s?[бм]\b', ' ', t))
        if not s or not ou or line is None:
            raise ValueError('индивидуальный тотал: не понял команду/линию')
        return dict(kind='it', side=s, ou=ou, line=line, scope=scope)
    # тотал матча
    if re.search(r'\bтотал|\bт[бм]\b', t) or (re.search(r'больше|меньше', t) and not side and not re.search(r'\bф[12]\b|\bфор', t)
                                                 and _num(t) is not None):   # «5.5 меньше» без слова «тотал» (владелец 01.11)
        ou, line = _ou(t), _num(t)
        if not ou or line is None:
            raise ValueError('тотал: не понял больше/меньше или линию')
        return dict(kind='tot', ou=ou, line=line, scope=scope)
    # фора
    m = re.search(r'\bф([12])\b|\bф([12])\s?\(|\bфор[аоуы]\w*', t)
    if m:
        code = re.search(r'\bф([12])', t)
        s = {'1': 'h', '2': 'a'}.get(code.group(1)) if code else side
        rest = t[m.end():] if not code else t[code.end():]
        line = _num(rest, signed=True)
        if line is None:
            line = _num(t, signed=True)
        if not s or line is None:
            raise ValueError('фора: не понял команду/линию')
        return dict(kind='hc', side=s, line=line, scope=scope)
    # двойной шанс
    if re.search(r'не проигра', t):
        if not side:
            raise ValueError('«не проиграет»: не понял команду')
        return dict(kind='dc', side=side, scope=scope)
    m = re.search(r'(?<![\w.])(1x|x1|x2|2x|12)(?![\w.])', t)
    if m:
        code = m.group(1)
        if code == '12':
            return dict(kind='nodraw', scope=scope)
        return dict(kind='dc', side='h' if '1' in code else 'a', scope=scope)
    # ничья
    if re.search(r'\bничь|^x\b|^x ', t):
        return dict(kind='draw', scope='reg')
    # победа
    m = re.search(r'\bп([12])\b', t)
    if m or re.search(r'побед|выигр', t):
        s = {'1': 'h', '2': 'a'}.get(m.group(1)) if m else side
        if not s:
            raise ValueError('победа: не понял, чья')
        return dict(kind='win', side=s, scope=scope)
    raise ValueError('не понял ставку')


def parse(bet, home, away):
    """Текст ставки → список «ног» (экспресс внутри матча: «П1 и тотал меньше 5,5»)."""
    t = re.sub(r'\((?:[^)]*(?:владел|повтор|проб|исправ)[^)]*)\)', ' ', _norm(bet))
    parts = [p for p in re.split(r'\s(?:и|\+)\s|\s\+(?=\s?[а-яa-z])', t) if p.strip()]
    legs = [parse_leg(p, home, away) for p in parts]
    if not legs:
        raise ValueError('пустая ставка')
    return legs


def scores(g, scope):
    """g — {hg, ag, end: ''|'ОТ'|'Б'} → счёт для расчёта: 'reg' — основное время, 'fin' — итоговый."""
    hg, ag = int(g['hg']), int(g['ag'])
    if scope == 'reg' and g.get('reg'):
        return tuple(g['reg'])                      # по периодам из данных лиги (data.khl_regulation / nhl_regulation)
    if scope == 'reg' and g.get('end'):
        m = min(hg, ag)
        return m, m
    return hg, ag


def _cmp(x):
    return WIN if x > 1e-9 else LOSS if x < -1e-9 else PUSH


def settle_leg(leg, g):
    k = leg['kind']
    if k in ('tot', 'it', 'hc') and abs(leg['line'] * 2 - round(leg['line'] * 2)) > 1e-9:
        raise ValueError('азиатская линия %.2f — посчитать вручную' % leg['line'])
    h, a = scores(g, leg.get('scope', 'reg'))
    me, op = (h, a) if leg.get('side', 'h') == 'h' else (a, h)
    if k == 'win':
        return WIN if me > op else LOSS
    if k == 'dc':
        return WIN if me >= op else LOSS
    if k == 'draw':
        return WIN if h == a else LOSS
    if k == 'nodraw':
        return WIN if h != a else LOSS
    if k == 'hc':
        return _cmp(me - op + leg['line'])
    if k == 'tot':
        d = h + a - leg['line']
        return _cmp(d if leg['ou'] == 'over' else -d)
    if k == 'it':
        d = me - leg['line']
        return _cmp(d if leg['ou'] == 'over' else -d)
    raise ValueError(k)


def settle(bet, home, away, g):
    """→ (итог win/loss/push, ноги, пояснение к возврату или '')."""
    legs = parse(bet, home, away)
    res = [settle_leg(l_, g) for l_ in legs]
    if LOSS in res:
        out = LOSS
    elif WIN in res:
        out = WIN
    else:
        out = PUSH
    why = ''
    if out == PUSH:
        why = push_reason(legs[res.index(PUSH)], g)
    return out, legs, why


def push_reason(leg, g):
    h, a = scores(g, leg.get('scope', 'reg'))
    n = int(round(leg['line']))
    if leg['kind'] == 'tot':
        return 'ровно %s' % plural(n, 'шайба', 'шайбы', 'шайб') + (' в основное время' if g.get('end') and leg['scope'] == 'reg' else '')
    if leg['kind'] == 'it':
        return 'ровно %s у команды' % plural(n, 'шайба', 'шайбы', 'шайб')
    if leg['kind'] == 'hc':
        return 'разница ровно в %s' % plural(abs(n), 'шайбу', 'шайбы', 'шайб')
    return 'ставка вернулась'


def plural(n, one, few, many):
    n = int(n)
    k = n % 100
    w = many if 11 <= k <= 14 else one if k % 10 == 1 else few if 2 <= k % 10 <= 4 else many
    return '%d %s' % (n, w)


def short(legs, home, away):
    """Короткая запись для табло и картинки: «П2», «Х2», «ТМ 4,5», «Ф2 +1,5», «ИТБ Юты 2,5», «П1 с ОТ»."""
    out = []
    for l_ in legs:
        k, s = l_['kind'], l_.get('side')
        n = '1' if s == 'h' else '2'
        num = lambda v, sign=False: (('+' if v > 0 else '−' if v < 0 else '') if sign else '') + ('%g' % abs(v)).replace('.', ',')
        if k == 'win':
            out.append('П%s%s' % (n, ' с ОТ' if l_['scope'] == 'fin' else ''))
        elif k == 'dc':
            out.append('1Х' if s == 'h' else 'Х2')
        elif k == 'draw':
            out.append('Х')
        elif k == 'nodraw':
            out.append('12')
        elif k == 'hc':
            out.append('Ф%s %s' % (n, num(l_['line'], True)))
        elif k == 'tot':
            out.append('%s %s' % ('ТБ' if l_['ou'] == 'over' else 'ТМ', num(l_['line'])))
        elif k == 'it':
            out.append('%s %s %s' % ('ИТБ' if l_['ou'] == 'over' else 'ИТМ', gen(home if s == 'h' else away), num(l_['line'])))
    return ' + '.join(out)
