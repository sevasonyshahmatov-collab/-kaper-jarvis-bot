# -*- coding: utf-8 -*-
"""Лига НХЛ для набора JARVIS: реестр 32 клубов, эмблемы, разведение цветов, «скин» НХЛ.

Логика та же, что в КХЛ-части: команда ищется по названию в poster.TEAMS,
эмблема — файл в emblems/<slug>.png, фон баннера — poster.BANNER[team].
Поэтому достаточно один раз зарегистрировать клубы НХЛ внутри poster —
и ВСЕ существующие рендеры (и «Карточки», и «Бока», и сводные) начинают
работать с командами НХЛ без правок.

    import nhl
    nhl.register()                       # один раз в начале скрипта
    nhl.skin()                           # контекст: акцент ICE + шапка «JARVIS | NHL»

Система очков НХЛ совпадает с нынешней КХЛ: победа 2, поражение в ОТ/буллитах 1,
поражение в основное 0. Значит работает та же проверка:
    points == 2 * wins + 1 * OT_losses
Буквы формы те же: W / L / X (победа в ОТ) / O (поражение в ОТ).
"""
import json
import os
import re
from contextlib import contextmanager

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import poster

DIR = os.path.dirname(os.path.abspath(__file__))
EMB = poster.EMB
MARK = os.path.join(EMB, '_nhl_placeholders.json')

ICE = (122, 202, 255)          # акцент НХЛ вместо золота КХЛ
ICE_DARK = (8, 26, 40)

# ru-название: (slug, осн. цвет, второй цвет, аббревиатура, en-название, дивизион)
# Цвета — фирменные. slug: minnesota/dallas — уже присланные автором реальные логотипы.
TEAMS = {
    # Атлантический
    'Бостон':        ('nhl_bos', (255, 184, 28), (17, 17, 17),  'BOS', 'Boston Bruins',        'Атлантический'),
    'Баффало':       ('nhl_buf', (0, 48, 135),   (255, 184, 28), 'BUF', 'Buffalo Sabres',      'Атлантический'),
    'Детройт':       ('nhl_det', (206, 17, 38),  (235, 235, 235), 'DET', 'Detroit Red Wings',  'Атлантический'),
    'Флорида':       ('nhl_fla', (200, 16, 46),  (4, 30, 66),    'FLA', 'Florida Panthers',    'Атлантический'),
    'Монреаль':      ('nhl_mtl', (175, 30, 45),  (25, 33, 104),  'MTL', 'Montreal Canadiens',  'Атлантический'),
    'Оттава':        ('nhl_ott', (200, 16, 46),  (194, 145, 44), 'OTT', 'Ottawa Senators',     'Атлантический'),
    'Тампа-Бэй':     ('nhl_tbl', (18, 62, 140),  (235, 235, 235), 'TBL', 'Tampa Bay Lightning', 'Атлантический'),
    'Торонто':       ('nhl_tor', (16, 60, 140),  (235, 235, 235), 'TOR', 'Toronto Maple Leafs', 'Атлантический'),
    # Столичный
    'Каролина':      ('nhl_car', (204, 0, 0),    (25, 25, 25),   'CAR', 'Carolina Hurricanes', 'Столичный'),
    'Коламбус':      ('nhl_cbj', (20, 60, 130),  (206, 17, 38),  'CBJ', 'Columbus Blue Jackets', 'Столичный'),
    'Нью-Джерси':    ('nhl_njd', (206, 17, 38),  (25, 25, 25),   'NJD', 'New Jersey Devils',   'Столичный'),
    'Нью-Йорк Айлендерс': ('nhl_nyi', (0, 83, 155), (244, 125, 48), 'NYI', 'New York Islanders', 'Столичный'),
    'Нью-Йорк Рейнджерс': ('nhl_nyr', (0, 56, 168), (206, 17, 38), 'NYR', 'New York Rangers',  'Столичный'),
    'Филадельфия':   ('nhl_phi', (247, 73, 2),   (25, 25, 25),   'PHI', 'Philadelphia Flyers', 'Столичный'),
    'Питтсбург':     ('nhl_pit', (252, 181, 20), (25, 25, 25),   'PIT', 'Pittsburgh Penguins', 'Столичный'),
    'Вашингтон':     ('nhl_wsh', (200, 16, 46),  (4, 30, 66),    'WSH', 'Washington Capitals', 'Столичный'),
    # Центральный
    'Чикаго':        ('nhl_chi', (207, 10, 44),  (25, 25, 25),   'CHI', 'Chicago Blackhawks',  'Центральный'),
    'Колорадо':      ('nhl_col', (130, 45, 72),  (35, 97, 146),  'COL', 'Colorado Avalanche',  'Центральный'),
    'Даллас':        ('dallas',  (0, 132, 90),   (25, 25, 25),   'DAL', 'Dallas Stars',        'Центральный'),
    'Миннесота':     ('minnesota', (30, 100, 68), (166, 25, 46), 'MIN', 'Minnesota Wild',      'Центральный'),
    'Нэшвилл':       ('nhl_nsh', (255, 184, 28), (4, 30, 66),    'NSH', 'Nashville Predators', 'Центральный'),
    'Сент-Луис':     ('nhl_stl', (0, 47, 135),   (252, 181, 20), 'STL', 'St. Louis Blues',     'Центральный'),
    'Юта':           ('nhl_uta', (113, 175, 229), (20, 20, 22),  'UTA', 'Utah Mammoth',        'Центральный'),
    'Виннипег':      ('nhl_wpg', (22, 56, 110),  (140, 150, 165), 'WPG', 'Winnipeg Jets',      'Центральный'),
    # Тихоокеанский
    'Анахайм':       ('nhl_ana', (244, 122, 56), (185, 151, 91), 'ANA', 'Anaheim Ducks',       'Тихоокеанский'),
    'Калгари':       ('nhl_cgy', (210, 0, 28),   (250, 175, 25), 'CGY', 'Calgary Flames',      'Тихоокеанский'),
    'Эдмонтон':      ('nhl_edm', (255, 76, 0),   (4, 30, 66),    'EDM', 'Edmonton Oilers',     'Тихоокеанский'),
    'Лос-Анджелес':  ('nhl_lak', (130, 140, 145), (25, 25, 25),  'LAK', 'Los Angeles Kings',   'Тихоокеанский'),
    'Сан-Хосе':      ('nhl_sjs', (0, 109, 117),  (234, 114, 0),  'SJS', 'San Jose Sharks',     'Тихоокеанский'),
    'Сиэтл':         ('nhl_sea', (0, 96, 128),   (153, 217, 217), 'SEA', 'Seattle Kraken',     'Тихоокеанский'),
    'Ванкувер':      ('nhl_van', (0, 62, 130),   (0, 132, 61),   'VAN', 'Vancouver Canucks',   'Тихоокеанский'),
    'Вегас':         ('nhl_vgk', (180, 151, 90), (51, 63, 66),   'VGK', 'Vegas Golden Knights', 'Тихоокеанский'),
}

# короткая подпись на баннере (двух слов из ru-названия не выйдет — берём как есть)
SHORT = {
    'Нью-Йорк Айлендерс': 'Айлендерс',
    'Нью-Йорк Рейнджерс': 'Рейнджерс',
    'Лос-Анджелес': 'Лос-Анджелес',
}

# как автор может написать название: en, аббревиатура, прозвище, частые опечатки
ALIASES = {
    'бостон брюинз': 'Бостон', 'брюинз': 'Бостон', 'boston': 'Бостон', 'bruins': 'Бостон',
    'баффало сейбрз': 'Баффало', 'сейбрз': 'Баффало', 'buffalo': 'Баффало', 'бафало': 'Баффало',
    'детройт ред уингз': 'Детройт', 'ред уингз': 'Детройт', 'detroit': 'Детройт',
    'флорида пантерз': 'Флорида', 'пантерз': 'Флорида', 'florida': 'Флорида',
    'монреаль канадиенс': 'Монреаль', 'канадиенс': 'Монреаль', 'montreal': 'Монреаль',
    'оттава сенаторз': 'Оттава', 'сенаторз': 'Оттава', 'ottawa': 'Оттава',
    'тампа': 'Тампа-Бэй', 'тампа бэй': 'Тампа-Бэй', 'лайтнинг': 'Тампа-Бэй', 'tampa': 'Тампа-Бэй',
    'торонто мейпл лифс': 'Торонто', 'мейпл лифс': 'Торонто', 'toronto': 'Торонто',
    'каролина харрикейнз': 'Каролина', 'харрикейнз': 'Каролина', 'carolina': 'Каролина',
    'коламбус блю джекетс': 'Коламбус', 'блю джекетс': 'Коламбус', 'columbus': 'Коламбус',
    'нью джерси': 'Нью-Джерси', 'девилз': 'Нью-Джерси', 'new jersey': 'Нью-Джерси',
    'айлендерс': 'Нью-Йорк Айлендерс', 'нью-йорк айлендерз': 'Нью-Йорк Айлендерс',
    'islanders': 'Нью-Йорк Айлендерс', 'нью йорк айлендерс': 'Нью-Йорк Айлендерс',
    'рейнджерс': 'Нью-Йорк Рейнджерс', 'рейнджеры': 'Нью-Йорк Рейнджерс',
    'rangers': 'Нью-Йорк Рейнджерс', 'нью йорк рейнджерс': 'Нью-Йорк Рейнджерс',
    'филадельфия флайерз': 'Филадельфия', 'флайерз': 'Филадельфия', 'philadelphia': 'Филадельфия',
    'питтсбург пингвинз': 'Питтсбург', 'пингвинз': 'Питтсбург', 'питсбург': 'Питтсбург',
    'pittsburgh': 'Питтсбург',
    'вашингтон кэпиталз': 'Вашингтон', 'кэпиталз': 'Вашингтон', 'washington': 'Вашингтон',
    'чикаго блэкхокс': 'Чикаго', 'блэкхокс': 'Чикаго', 'chicago': 'Чикаго',
    'колорадо эвеланш': 'Колорадо', 'эвеланш': 'Колорадо', 'colorado': 'Колорадо',
    'даллас старс': 'Даллас', 'старс': 'Даллас', 'dallas': 'Даллас',
    'миннесота уайлд': 'Миннесота', 'уайлд': 'Миннесота', 'minnesota': 'Миннесота',
    'минессота': 'Миннесота', 'минесота': 'Миннесота', 'минессоты': 'Миннесота',
    'нэшвилл предаторз': 'Нэшвилл', 'предаторз': 'Нэшвилл', 'нашвилл': 'Нэшвилл',
    'nashville': 'Нэшвилл',
    'сент луис': 'Сент-Луис', 'блюз': 'Сент-Луис', 'st louis': 'Сент-Луис', 'st. louis': 'Сент-Луис',
    'юта маммот': 'Юта', 'маммот': 'Юта', 'utah': 'Юта', 'юта хоккей клаб': 'Юта',
    'виннипег джетс': 'Виннипег', 'джетс': 'Виннипег', 'winnipeg': 'Виннипег',
    'анахайм дакс': 'Анахайм', 'дакс': 'Анахайм', 'анахайм дакc': 'Анахайм', 'anaheim': 'Анахайм',
    'калгари флэймз': 'Калгари', 'флэймз': 'Калгари', 'calgary': 'Калгари',
    'эдмонтон ойлерз': 'Эдмонтон', 'ойлерз': 'Эдмонтон', 'edmonton': 'Эдмонтон',
    'лос анджелес': 'Лос-Анджелес', 'кингз': 'Лос-Анджелес', 'la kings': 'Лос-Анджелес',
    'los angeles': 'Лос-Анджелес',
    'сан хосе': 'Сан-Хосе', 'шаркс': 'Сан-Хосе', 'san jose': 'Сан-Хосе',
    'сиэтл кракен': 'Сиэтл', 'кракен': 'Сиэтл', 'seattle': 'Сиэтл',
    'ванкувер кэнакс': 'Ванкувер', 'кэнакс': 'Ванкувер', 'vancouver': 'Ванкувер',
    'вегас голден найтс': 'Вегас', 'голден найтс': 'Вегас', 'лас-вегас': 'Вегас',
    'лас вегас': 'Вегас', 'vegas': 'Вегас',
}
for _ru, _v in TEAMS.items():
    ALIASES[_v[3].lower()] = _ru          # BOS, DAL, MIN…
    ALIASES[_v[4].lower()] = _ru          # Boston Bruins…


def _norm(s):
    s = str(s).strip().lower().replace('ё', 'е')
    return re.sub(r'[\s\-–—.]+', ' ', s).strip()


def resolve(name):
    """Название в любом виде → ключ из TEAMS. Бросает KeyError со подсказкой."""
    if name in TEAMS:
        return name
    n = _norm(name)
    direct = {_norm(k): k for k in TEAMS}
    if n in direct:
        return direct[n]
    al = {_norm(k): v for k, v in ALIASES.items()}
    if n in al:
        return al[n]
    hits = [k for nk, k in direct.items() if n and (n in nk or nk in n)]
    hits += [v for nk, v in al.items() if n and (n in nk or nk in n)]
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise KeyError('«%s» — неоднозначно: %s' % (name, ', '.join(hits)))
    raise KeyError('«%s» нет в реестре НХЛ. Доступно: %s' % (name, ', '.join(sorted(TEAMS))))


# ── фон баннера: один яркий цвет на клуб (как poster.BANNER для КХЛ) ────────────
BANNER = {ru: v[1] for ru, v in TEAMS.items()}
SECOND = {ru: v[2] for ru, v in TEAMS.items()}


# ── эмблемы ────────────────────────────────────────────────────────────────────
def _placeholders():
    try:
        with open(MARK, encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_placeholders(s):
    with open(MARK, 'w', encoding='utf-8') as f:
        json.dump(sorted(s), f, ensure_ascii=False, indent=1)


def _make_placeholder(ru, size=512):
    """Оригинальная заглушка: круг в клубных цветах + аббревиатура. Не логотип клуба."""
    slug, c1, c2, abbr = TEAMS[ru][0], TEAMS[ru][1], TEAMS[ru][2], TEAMS[ru][3]
    S = 2
    W = size * S
    im = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = int(W * 0.04)
    d.ellipse((pad, pad, W - pad, W - pad), fill=c2 + (255,))
    ring = int(W * 0.055)
    d.ellipse((pad + ring, pad + ring, W - pad - ring, W - pad - ring), fill=c1 + (255,))
    d.ellipse((pad, pad, W - pad, W - pad), outline=(255, 255, 255, 235), width=int(W * 0.016))
    sz = int(W * 0.30)
    f = poster._font('display', sz)
    while f.getlength(abbr) > W * 0.60 and sz > 40:
        sz -= 6
        f = poster._font('display', sz)
    d.text((W / 2, W / 2 - W * 0.015), abbr, font=f, fill=(255, 255, 255, 255), anchor='mm',
           stroke_width=int(W * 0.012), stroke_fill=(0, 0, 0, 90))
    im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(EMB, slug + '.png'), optimize=True)
    return slug


def register(make_placeholders=True):
    """Вписывает клубы НХЛ в poster.TEAMS / SHORT / BANNER. Возвращает список
    команд, у которых пока нет настоящего логотипа (стоит заглушка)."""
    poster.TEAMS.update({ru: (v[0], v[1], v[2]) for ru, v in TEAMS.items()})
    poster.SHORT.update(SHORT)
    poster.BANNER.update(BANNER)
    ph = _placeholders()
    missing = []
    for ru, v in TEAMS.items():
        p = os.path.join(EMB, v[0] + '.png')
        if not os.path.exists(p):
            if make_placeholders:
                _make_placeholder(ru)
                ph.add(v[0])
            missing.append(ru)
        elif v[0] in ph:
            missing.append(ru)
    if make_placeholders:
        _save_placeholders(ph)
    return missing


def missing_logos():
    """Команды НХЛ, у которых на баннере пока заглушка, а не настоящий логотип."""
    ph = _placeholders()
    return [ru for ru, v in TEAMS.items()
            if v[0] in ph or not os.path.exists(os.path.join(EMB, v[0] + '.png'))]


def _strip_white(im, thresh=228):
    """Снимает белый фон снаружи логотипа, если файл пришёл без прозрачности.

    Заливка от углов перекрашивает связную светлую область в красный, и фоном
    считается ТОЛЬКО перекрашенное (R=255, G=0). Если брать просто «тёмное»,
    в фон попадут тёмные пиксели самого логотипа и он потеряет цвета —
    так однажды и случилось с Колорадо.
    Белое внутри логотипа (шайба, буквы, контуры) заливка не достаёт.
    """
    if im.getchannel('A').getextrema()[0] < 250:
        return im
    mask = im.convert('RGB').convert('L').point(lambda v: 255 if v >= thresh else 0)
    work = Image.merge('RGB', (mask, mask, mask))
    touched = False
    for xy in [(0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)]:
        if work.getpixel(xy) == (255, 255, 255):
            ImageDraw.floodfill(work, xy, (255, 0, 0), thresh=10)
            touched = True
    if not touched:
        return im
    r = work.getchannel('R').point(lambda v: 255 if v >= 128 else 0)
    g = work.getchannel('G').point(lambda v: 255 if v < 128 else 0)
    im = im.copy()
    im.putalpha(ImageChops.invert(ImageChops.multiply(r, g)))
    return im


def install_logo(name, src, trim=True):
    """Ставит присланный автором логотип на место заглушки.
    src — png/webp/jpg, с прозрачностью или на белом фоне.
    Белый фон снимается сам, пустые поля обрезаются."""
    ru = resolve(name)
    slug = TEAMS[ru][0]
    im = _strip_white(Image.open(src).convert('RGBA'))
    if trim:
        bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
        if bb:
            im = im.crop(bb)
    side = max(im.size)
    sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    if side > 700:
        sq = sq.resize((700, 700), Image.LANCZOS)
    sq.save(os.path.join(EMB, slug + '.png'), optimize=True)
    ph = _placeholders()
    ph.discard(slug)
    _save_placeholders(ph)
    return ru, os.path.join(EMB, slug + '.png')


# ── разведение похожих клубных цветов ──────────────────────────────────────────
def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def pair_colors(home, away, apply=True, threshold=110):
    """В НХЛ половина лиги красная и половина тёмно-синяя, поэтому пары сливаются
    чаще, чем в КХЛ. Функция сама уводит гостей во второй клубный цвет, если
    основные слишком близки. Возвращает (c1, c2) и, при apply, правит poster.BANNER."""
    h, a = resolve(home), resolve(away)
    c1, c2 = BANNER[h], BANNER[a]
    if _dist(c1, c2) < threshold:
        for cand in (SECOND[a], SECOND[h], (34, 62, 118)):
            if _dist(c1, cand) >= threshold:
                if cand is SECOND[h]:
                    c1 = cand
                else:
                    c2 = cand
                break
    if apply:
        poster.BANNER[h] = c1
        poster.BANNER[a] = c2
    return c1, c2


# ── «скин» НХЛ: ледяной акцент вместо золота и шапка «JARVIS | NHL» ────────────
@contextmanager
def skin(tag='NHL', accent=ICE):
    """Пока контекст открыт, любой рендер (в том числе сводные из recap)
    рисуется в оформлении НХЛ, а не КХЛ."""
    import recap
    saved = (poster.ACC, recap.ACC, recap._brand_kxl, poster.FONTS7)

    def brand(d, cx, y, S, size=26):
        fb = recap._fr('brand', size * S)
        sp, bar = 3 * S, 22 * S
        w1 = sum(fb.getlength(c) for c in 'JARVIS') + sp * 5
        w2 = sum(fb.getlength(c) for c in tag) + sp * max(0, len(tag) - 1)
        x0 = cx - (w1 + 2 * bar + w2) / 2
        poster._spaced(d, (x0, y), 'JARVIS', fb, (255, 255, 255, 255), sp)
        d.rounded_rectangle((x0 + w1 + bar - 1.5 * S, y - 14 * S, x0 + w1 + bar + 1.5 * S, y + 14 * S),
                            radius=S, fill=(255, 255, 255, 150))
        poster._spaced(d, (x0 + w1 + 2 * bar, y), tag, fb, accent + (255,), sp)

    poster.ACC = accent
    recap.ACC = accent
    recap._brand_kxl = brand
    try:
        yield accent
    finally:
        poster.ACC, recap.ACC, recap._brand_kxl, poster.FONTS7 = saved


team_info = poster.team_info
