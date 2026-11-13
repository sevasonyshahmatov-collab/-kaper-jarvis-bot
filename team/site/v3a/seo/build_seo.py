#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO-сборка сайта v3a (без сети, только файлы сайта). Запуск: python3 seo/build_seo.py  (из любой папки).

Что делает (каждый запуск идемпотентен):
  1. Генерирует страницы: glossary.html (словарь терминов + FAQPage), forecast.html (все лиги), hockey/forecast-<лига>.html,
     football/forecast-<лига>.html («Прогноз на сегодня»; данные data/today.json, data/model.json, assets/data/teams.json,
     football/data/football.json; кэфов букмекеров на этих страницах нет).
  2. Во все страницы вписывает title, description, canonical, og:*, twitter:*, JSON-LD (блок между <!--seo:begin--> и <!--seo:end-->).
  3. Пишет sitemap.xml и robots.txt. Адрес — SITE_ORIGIN из seo/seo_config.py; пока INDEXING_OPEN=False: noindex на страницах,
     robots.txt закрывает сайт.
Ежедневно вызывается шагом `seo` из daily/run.py (после обновления данных)."""
import html as H
import json
import os
import re
import sys
import posixpath
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # team/site/v3a
sys.path.insert(0, HERE)
import seo_config as CFG  # noqa: E402
from glossary_terms import TERMS  # noqa: E402

ORIGIN = CFG.SITE_ORIGIN
OPEN = CFG.INDEXING_OPEN

WD = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
MON_G = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']


def jload(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return json.load(f)


def esc(s):
    return H.escape(str(s), quote=True)


def rd(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def wr(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    old = None
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            old = f.read()
    if old != text:
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        return True
    return False


# ───────────────────────── данные ─────────────────────────
TODAY = jload('data', 'today.json')
MODEL = jload('data', 'model.json')
TEAMS = jload('assets', 'data', 'teams.json')
FOOT = jload('football', 'data', 'football.json')
BUILT = TODAY.get('built') or datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')  # «ГГГГ-ММ-ДД ЧЧ:ММ» МСК
BUILT_DAY = BUILT[:10]


def gday(t):
    """Игровой день (владелец 09.11, одно правило на весь сайт): с 06:00 МСК до 06:00 следующего дня —
    ночные матчи НХЛ (02:00–05:00 МСК) относятся к вечеру накануне, как в прогнозах канала. t — 'ГГГГ-ММ-ДД ЧЧ:ММ' МСК."""
    return (datetime.datetime.strptime(t[:16], '%Y-%m-%d %H:%M') - datetime.timedelta(hours=6)).strftime('%Y-%m-%d')


BUILT_GD = gday(BUILT)

HL = {'khl': 'КХЛ', 'nhl': 'НХЛ'}
FL = {k: v['name'] for k, v in FOOT['leagues'].items()}
LG_ALL = list(HL) + list(FL)
SPORT_OF = {**{k: 'hockey' for k in HL}, **{k: 'football' for k in FL}}
LG_NAME = {**HL, **FL}
SPORT_RU = {'hockey': 'Хоккей', 'football': 'Футбол'}


def url(rel):
    return ORIGIN + '/' + rel.lstrip('/')


def ru_date(d):
    y, m, dd = map(int, d.split('-'))
    return '%d %s' % (dd, MON_G[m - 1]), WD[datetime.date(y, m, dd).weekday()]


def depth(from_dir):
    return 0 if from_dir == '' else from_dir.count('/') + 1


def club_href(sport, slug, from_dir):
    """Ссылка на страницу клуба; from_dir — папка страницы ('' корень, 'hockey', 'football', 'khl/2026-…').
    Если у клуба есть понятный адрес (seo/build_match.py: /khl/ska/), ведёт на него, иначе на старый ?id=."""
    pre = '../' * depth(from_dir)
    import build_match as BM
    cd = BM.club_dir(sport, slug)
    if cd:
        return pre + cd + '/index.html'
    if sport == 'hockey':
        return pre + 'team/index.html?id=' + slug
    return (pre + 'football/team.html?id=' + slug) if from_dir == '' else 'team.html?id=' + slug


def emblem(sport, slug, from_dir):
    pre = '../' * depth(from_dir)
    rel = ('assets/em/%s.webp' if sport == 'hockey' else 'assets/fc/%s.webp') % slug
    return pre + rel if os.path.exists(os.path.join(ROOT, rel)) else None


# ───────────────────────── матчи по лигам ─────────────────────────
def matches_for(lg):
    """Все будущие матчи лиги из данных сайта: [{t, h, hn, a, an, key, md(модель), arena?}]. Кэфов здесь нет намеренно."""
    out = []
    arenas = {m['key']: m.get('arena') for m in TODAY.get('matches', [])}
    if lg in HL:
        names = TEAMS['names']
        for k, v in TEAMS['teams'].items():
            if v.get('lg') != lg:
                continue
            for g in v.get('games', []):
                if 'gf' in g or g.get('h') != 1:
                    continue
                key = '%s|%s|%s|%s' % (lg, g['d'][:10], k, g['o'])
                md = MODEL.get(key)
                if not md and g.get('pm'):
                    p = g['pm']
                    md = {'p1': p[0], 'x': p[1], 'p2': p[2]}
                ar = arenas.get(key)
                out.append({'t': g['d'], 'h': k, 'a': g['o'], 'hn': names.get(k, k), 'an': names.get(g['o'], g['o']), 'key': key,
                            'md': md, 'arena': ar if isinstance(ar, dict) else None, 'arena_s': ar if isinstance(ar, str) else None})
    else:
        teams = FOOT['teams']
        for u in FOOT['up']:
            if u['lg'] != lg:
                continue
            key = '%s|%s|%s|%s' % (lg, u['t'][:10], u['h'], u['a'])
            md = MODEL.get(key)
            if not md and u.get('pr'):
                md = {'p1': u['pr'][0], 'x': u['pr'][1], 'p2': u['pr'][2], 'tot': 2.5, 'over': u.get('ov'), 'lam': u.get('xg')}
            out.append({'t': u['t'], 'h': u['h'], 'a': u['a'], 'hn': teams.get(u['h'], {}).get('n', u['h']),
                        'an': teams.get(u['a'], {}).get('n', u['a']), 'key': key, 'md': md, 'arena': None, 'arena_s': None})
    out.sort(key=lambda m: (m['t'], m['key']))
    return out


def pick_day(ms):
    """Ближайший игровой день: не раньше дня сборки; матчи, начавшиеся больше 3 часов назад, не считаем."""
    b = datetime.datetime.strptime(BUILT, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=3)
    cut = b.strftime('%Y-%m-%d %H:%M')
    left = [m for m in ms if m['t'] >= cut]
    if not left:
        return None, []
    d = gday(left[0]['t'])
    return d, [m for m in left if gday(m['t']) == d]


def mdl_block(m, sport):
    md = m.get('md')
    if not md:
        return '<p class="fc-none">Расчёта модели на этот матч пока нет.</p>'
    p1, x, p2 = [round(v * 100) for v in (md['p1'], md['x'], md['p2'])]
    tot = md.get('tot')
    over = md.get('over')
    lam = md.get('lam')
    f1 = lambda v: ('%.1f' % v).replace('.', ',')  # noqa: E731
    xl = 'ничья в основное время' if sport == 'hockey' else 'ничья'
    bar = ('<div class="fc-bar" aria-hidden="true"><i class="b1" style="width:%d%%"></i><i class="bx" style="width:%d%%"></i>'
           '<i class="b2" style="width:%d%%"></i></div>' % (p1, x, max(0, 100 - p1 - x)))
    nums = ('<ul class="fc-nums"><li><small>П1 · победа хозяев</small><b>%d %%</b></li><li><small>Х · %s</small><b>%d %%</b></li>'
            '<li><small>П2 · победа гостей</small><b>%d %%</b></li></ul>' % (p1, xl, x, p2))
    extra = []
    if tot is not None and over is not None:
        extra.append('Тотал %s: больше <b>%d %%</b>' % (f1(tot), round(over * 100)))
    if lam:
        extra.append('Ожидаемые голы <b>%s : %s</b>' % (f1(lam[0]), f1(lam[1])))
    return '<div class="fc-pm" role="group" aria-label="Вероятность модели">%s%s%s</div>' % (
        bar, nums, ('<p class="fc-ext">' + ' · '.join(extra) + '</p>') if extra else '')


def lv_attrs(m):
    """Атрибуты для assets/live.js (живой счёт): лига, начало (МСК), id и названия команд. Кэфов нет."""
    lg = m['key'].split('|')[0]
    return (' data-lv data-lv-lg="%s" data-lv-t="%s" data-lv-h="%s" data-lv-a="%s" data-lv-hn="%s" data-lv-an="%s"'
            % (esc(lg), esc(m['t'].replace(' ', 'T') + ':00+03:00'), esc(m['h']), esc(m['a']), esc(m['hn']), esc(m['an'])))


def match_li(m, sport, d_out):
    def team(slug, name):
        em = emblem(sport, slug, d_out)
        img = '<img src="%s" alt="" width="28" height="28" loading="lazy">' % esc(em) if em else '<span class="fc-noem"></span>'
        return '<a class="fc-tm" href="%s">%s<span>%s</span></a>' % (esc(club_href(sport, slug, d_out)), img, esc(name))
    ar = ''
    if m.get('arena') and m['arena'].get('name'):
        ar = '<small class="fc-arena">%s%s</small>' % (esc(m['arena']['name']), (', ' + esc(m['arena']['city'])) if m['arena'].get('city') else '')
    elif m.get('arena_s'):
        ar = '<small class="fc-arena">%s</small>' % esc(m['arena_s'])
    mid = 'm-' + re.sub(r'[^a-z0-9]+', '-', m['key'].lower()).strip('-')
    import build_match as BM
    mp = BM.match_rel(m['key'])
    ml = ('<a class="fc-mlink" href="%s">Страница матча ›</a>' % esc('../' * depth(d_out) + mp)) if mp else ''
    return ('<li class="fc-m" id="%s"%s><div class="fc-time"><b>%s</b><small>%sМСК</small></div>'
            '<div class="fc-teams">%s<span class="fc-vs" aria-hidden="true">—</span>%s%s%s</div>%s</li>'
            % (mid, lv_attrs(m), esc(m['t'][11:16]), ('ночь на %s.%s, ' % (m['t'][8:10], m['t'][5:7])) if m['t'][11:13] < '06' else '', team(m['h'], m['hn']), team(m['a'], m['an']), ar, ml, mdl_block(m, sport)))


# ───────────────────────── JSON-LD ─────────────────────────
def ld_script(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    s = s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return '<script type="application/ld+json">%s</script>' % s


def event_ld(m, sport, page_rel):
    """SportsEvent только из реальных полей: клубы, начало (МСК), арена, если она есть в данных."""
    d_out = posixpath.dirname(page_rel)
    mid = 'm-' + re.sub(r'[^a-z0-9]+', '-', m['key'].lower()).strip('-')

    def tm(slug, name):
        return {'@type': 'SportsTeam', 'name': name, 'url': url(posixpath.normpath(posixpath.join(d_out, club_href(sport, slug, d_out))).replace('/index.html', '/'))}
    ev = {'@type': 'SportsEvent', 'name': '%s — %s' % (m['hn'], m['an']),
          'startDate': m['t'].replace(' ', 'T') + ':00+03:00',
          'eventStatus': 'https://schema.org/EventScheduled',
          'sport': 'Ice hockey' if sport == 'hockey' else 'Association football',
          'homeTeam': tm(m['h'], m['hn']), 'awayTeam': tm(m['a'], m['an']),
          'url': url(page_rel) + '#' + mid}
    ar = m.get('arena')
    if ar and ar.get('name'):
        pl = {'@type': 'Place', 'name': ar['name']}
        if ar.get('address'):
            pl['address'] = ar['address']
        ev['location'] = pl
    return ev


def crumbs_ld(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': url(p)} for i, (n, p) in enumerate(items)]}


# ───────────────────────── таблица страниц ─────────────────────────
HOME = ('Главная', 'index.html')
HK = ('Хоккей', 'hockey/index.html')
FB = ('Футбол', 'football/index.html')

PAGES = {
    'index.html': dict(
        title='JARVIS: прогнозы на хоккей и футбол по собственной модели',
        desc='Прогнозы на КХЛ, НХЛ и топ-лиги Европы по собственной модели: вероятности исходов, ожидаемые голы, таблицы и клубы. Обновляется дважды в день.',
        og='assets/og/og-home.png', kind='home'),
    'hockey/index.html': dict(
        title='Хоккей: матчи КХЛ и НХЛ и прогнозы модели | JARVIS',
        desc='Матчи КХЛ и НХЛ на ближайшие дни: вероятность победы и тотала по расчёту модели, ожидаемые голы, таблицы и страницы клубов.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK], events='hockey'),
    'football/index.html': dict(
        title='Футбол: матчи АПЛ, Ла Лиги и еврокубков, прогнозы модели | JARVIS',
        desc='Ближайшие матчи АПЛ, Ла Лиги, Серии А, Бундеслиги, Лиги 1, РПЛ и еврокубков: вероятности исходов по модели, ожидаемые голы, таблицы.',
        og='assets/og/og-football.png', crumbs=[HOME, FB], events='football'),
    'football/ucl.html': dict(
        title='Лига чемпионов: таблица, матчи и расчёт модели | JARVIS',
        desc='Общий этап Лиги чемпионов: таблица, ближайшие матчи, вероятности исходов и тотала по расчёту модели, страницы клубов.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Лига чемпионов', 'football/ucl.html')]),
    'matches.html': dict(
        title='Колода матчей дня: КХЛ, НХЛ и футбол | JARVIS',
        desc='Матчи ближайших дней карточками: время, клубы, вероятности исходов по модели. Листайте колоду по лигам.',
        og='assets/og/og-matches.png', crumbs=[HOME, ('Матчи дня', 'matches.html')], events='all'),
    'model.html': dict(
        title='Как считает модель JARVIS: простыми словами',
        desc='Откуда модель берёт данные, как считает ожидаемые голы и вероятности исходов, чем отличается от линии букмекеров и в чём её ограничения.',
        og='assets/og/og-home.png', crumbs=[HOME, ('Как считает модель', 'model.html')]),
    'hockey/compare.html': dict(
        title='Сравнение клубов и игроков КХЛ и НХЛ | JARVIS',
        desc='Два клуба или два хоккеиста КХЛ и НХЛ рядом: очки, голы, броски, форма и личные встречи в одной таблице.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Сравнение', 'hockey/compare.html')]),
    'football/compare.html': dict(
        title='Сравнение футбольных клубов | JARVIS',
        desc='Два футбольных клуба топ-лиг рядом: место в таблице, голы, удары, форма и расчёт модели в одной таблице.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Сравнение', 'football/compare.html')]),
    'hockey/table.html': dict(
        title='Аналитическая таблица КХЛ и НХЛ | JARVIS',
        desc='Что внутри аналитической таблицы JARVIS по КХЛ и НХЛ: рейтинг Эло, прогнозы на все матчи, что заходит у команд, расписание и история ставок.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Аналитическая таблица', 'hockey/table.html')]),
    'hockey/trends.html': dict(
        title='Тренды дня в хоккее: КХЛ и НХЛ | JARVIS',
        desc='Что повторяется у клубов КХЛ и НХЛ перед ближайшими матчами: серии, тотал, овертаймы, игра дома и в гостях. Каждый факт в виде «n из N».',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Тренды дня', 'hockey/trends.html')]),
    'football/trends.html': dict(
        title='Тренды дня в футболе: серии, тотал, обе забьют | JARVIS',
        desc='Что повторяется у футбольных клубов перед ближайшими матчами: серии, тотал 2,5, обе забьют, сухие матчи, угловые. Факты в виде «n из N».',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Тренды дня', 'football/trends.html')]),
    'hockey/players.html': dict(
        title='Игроки НХЛ: очки, голы, передачи и броски | JARVIS',
        desc='Статистика игроков НХЛ: очки, голы, передачи, броски, время на льду, форма за 10 матчей, игра дома и в гостях.',
        og='assets/og/og-nhl.png', crumbs=[HOME, HK, ('Игроки НХЛ', 'hockey/players.html')]),
    'hockey/players_khl.html': dict(
        title='Игроки КХЛ: очки, голы и передачи | JARVIS',
        desc='Статистика игроков КХЛ: очки, голы, передачи, время на льду, форма за 10 матчей, игра дома и в гостях.',
        og='assets/og/og-khl.png', crumbs=[HOME, HK, ('Игроки КХЛ', 'hockey/players_khl.html')]),
    'football/players.html': dict(
        title='Футболисты: голы, удары и карточки | JARVIS',
        desc='Статистика игроков топ-лиг: голы, удары в створ, передачи, карточки и форма в последних матчах.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Игроки', 'football/players.html')]),
    'football/photo-credits.html': dict(
        title='Авторы фотографий футболистов | JARVIS',
        desc='Откуда взяты фотографии футболистов на сайте: файлы Wikimedia Commons и ссылки на страницы авторов.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Авторы фото', 'football/photo-credits.html')]),
    # страницы с параметром в адресе: заголовок и canonical по адресу ставит скрипт на самой странице
    'hockey/league.html': dict(
        title='КХЛ и НХЛ: таблица, матчи и бомбардиры | JARVIS',
        desc='Таблица лиги по конференциям, ближайшие матчи, последние результаты и лучшие бомбардиры КХЛ и НХЛ.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Лиги', 'hockey/league.html')], dyn=['lg']),
    'football/league.html': dict(
        title='Футбольные лиги: таблица, матчи и бомбардиры | JARVIS',
        desc='Таблица лиги, матчи ближайшего тура, последние результаты и бомбардиры: АПЛ, Ла Лига, Серия А, Бундеслига, Лига 1 и РПЛ.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Лиги', 'football/league.html')], dyn=['lg']),
    'team/index.html': dict(
        title='Клуб КХЛ или НХЛ: матчи, таблица, сила команды | JARVIS',
        desc='Страница клуба КХЛ или НХЛ: матчи сезона, место в таблице, шестиугольник силы, статистика игроков и расчёт модели на ближайшие игры.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Клубы', 'team/index.html')], dyn=['id']),
    'football/team.html': dict(
        title='Футбольный клуб: матчи, таблица, сила команды | JARVIS',
        desc='Страница футбольного клуба: матчи сезона, место в таблице, сила команды, тренды и расчёт модели на ближайшие игры.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Клубы', 'football/team.html')], dyn=['id']),
    'football/player.html': dict(
        title='Профиль футболиста: сезон, форма и матчи | JARVIS',
        desc='Профиль футболиста топ-лиги: голы, передачи, удары и карточки за сезон, форма в последних матчах.',
        og='assets/og/og-football.png', crumbs=[HOME, FB, ('Игроки', 'football/players.html')], dyn=['id']),
    'me/index.html': dict(
        title='Мой JARVIS — избранные клубы и матчи',
        desc='Личная страница: избранные клубы КХЛ, НХЛ и футбола, их ближайшие матчи и результаты с вашего прошлого визита. Список хранится в вашем браузере.',
        og='assets/og/og-home.png', crumbs=[HOME, ('Мой JARVIS', 'me/index.html')]),
    'hockey/player.html': dict(
        title='Профиль хоккеиста: сезон, форма и матчи | JARVIS',
        desc='Профиль хоккеиста КХЛ или НХЛ: статистика сезона, «n из N» по очку, голу, передаче и броскам, форма и все матчи.',
        og='assets/og/og-hockey.png', crumbs=[HOME, HK, ('Игроки', 'hockey/players.html')], dyn=['id', 'lg']),
    'glossary.html': dict(
        title='Словарь терминов: тотал, фора, xG, 1Х2 и другие | JARVIS',
        desc='Простыми словами: тотал, фора, овертайм, буллиты, 1Х2, двойной шанс, ожидаемые голы xG, вероятность модели, линия и маржа.',
        og='assets/og/og-home.png', crumbs=[HOME, ('Словарь терминов', 'glossary.html')], kind='glossary'),
    'results.html': dict(
        title='Итоги прогнозов: все ставки канала со счётом и ссылкой на пост | JARVIS',
        desc='Все прогнозы канала @jarvibet на хоккей и футбол: что зашло и что нет, со счётом матча и ссылкой на пост. Отдельно — ставки по модели, выбор автора и экспрессы.',
        og='assets/og/og-home.png', crumbs=[HOME, ('Итоги прогнозов', 'results.html')]),
    'forecast.html': dict(
        title='Прогноз на сегодня: КХЛ, НХЛ, АПЛ и другие лиги | JARVIS',
        desc='Матчи ближайшего игрового дня по лигам: КХЛ, НХЛ, АПЛ, Ла Лига, Серия А, Бундеслига, Лига 1, РПЛ и еврокубки. Вероятности исходов по модели.',
        og='assets/og/og-matches.png', crumbs=[HOME, ('Прогноз на сегодня', 'forecast.html')]),
}


def _wire_canon():
    import build_match as BM
    PAGES['team/index.html']['canon_map'] = BM.canon_map('hockey')
    PAGES['football/team.html']['canon_map'] = BM.canon_map('football')


def fc_rel(lg):
    return '%s/forecast-%s.html' % (SPORT_OF[lg], lg)


for _lg in LG_ALL:
    _sp = SPORT_OF[_lg]
    _n = LG_NAME[_lg]
    PAGES[fc_rel(_lg)] = dict(
        title='Прогноз на сегодня: %s, вероятности модели | JARVIS' % _n,
        desc='Матчи %s ближайшего игрового дня: вероятность победы, ничьей и тотала по расчёту модели JARVIS, ожидаемые голы, ссылки на клубы.' % _n,
        og='assets/og/og-%s.png' % ('khl' if _lg == 'khl' else 'nhl' if _lg == 'nhl' else _sp),
        crumbs=[HOME, (SPORT_RU[_sp], '%s/index.html' % _sp), ('Прогноз на сегодня: ' + _n, fc_rel(_lg))], kind='forecast', lg=_lg)


# ───────────────────────── голова страницы ─────────────────────────

BEGIN, END = '<!--seo:begin-->', '<!--seo:end-->'


def head_block(rel, P, extra_ld):
    page_url = url(rel)
    og_img = CFG.PUBLIC_ORIGIN + '/' + P['og'].lstrip('/')  # картинка превью — по живому адресу (seo_config.PUBLIC_ORIGIN)
    t, d = esc(P['title']), esc(P['desc'])
    lines = [BEGIN,
             '<meta name="description" content="%s">' % d]
    if P.get('canon_map'):
        # старые адреса клубов (?id=): canonical на понятный адрес /khl/ska/, если клуб известен; иначе прежняя логика
        lines.append('<script>(function(){try{var id=(new URLSearchParams(location.search).get("id")||"").toLowerCase(),M=%s,u=M[id]?%s+M[id]:%s,h=document.head,l=document.createElement("link");'
                     'l.rel="canonical";l.href=u;h.appendChild(l);var m=document.createElement("meta");m.setAttribute("property","og:url");m.content=u;h.appendChild(m)}catch(e){}})()</script>'
                     % (json.dumps(P['canon_map'], ensure_ascii=False, separators=(',', ':')), json.dumps(ORIGIN + '/'), json.dumps(page_url)))
    elif P.get('dyn'):
        # адрес страницы зависит от параметров (?id=, ?lg=): canonical и og:url ставит скрипт, остальные параметры отбрасываются
        keys = json.dumps(P['dyn'])
        lines.append('<script>(function(){try{var q=new URLSearchParams(location.search),s=[];%s.forEach(function(k){var v=q.get(k);'
                     'if(v&&/^[A-Za-z0-9_]{1,40}$/.test(v))s.push(k+"="+v)});var u=%s+(s.length?"?"+s.join("&"):""),h=document.head,l=document.createElement("link");'
                     'l.rel="canonical";l.href=u;h.appendChild(l);var m=document.createElement("meta");m.setAttribute("property","og:url");m.content=u;h.appendChild(m)}catch(e){}})()</script>'
                     % (keys, json.dumps(page_url)))
    else:
        lines.append('<link rel="canonical" href="%s">' % esc(page_url))
        lines.append('<meta property="og:url" content="%s">' % esc(page_url))
    lines += ['<meta property="og:type" content="website"><meta property="og:site_name" content="%s"><meta property="og:locale" content="ru_RU">' % CFG.SITE_NAME,
              '<meta property="og:title" content="%s"><meta property="og:description" content="%s">' % (t, d),
              '<meta property="og:image" content="%s"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' % esc(og_img),
              '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="%s"><meta name="twitter:description" content="%s">'
              '<meta name="twitter:image" content="%s">' % (t, d, esc(og_img))]
    graph = []
    if P.get('kind') == 'home':
        graph.append({'@type': 'Organization', '@id': ORIGIN + '/#org', 'name': CFG.SITE_NAME, 'url': url('index.html'),
                      'logo': url('icon-512.png'), 'sameAs': [CFG.TELEGRAM]})
        graph.append({'@type': 'WebSite', '@id': ORIGIN + '/#site', 'name': CFG.SITE_NAME, 'url': url('index.html'), 'inLanguage': 'ru',
                      'publisher': {'@id': ORIGIN + '/#org'},
                      'potentialAction': {'@type': 'SearchAction', 'target': {'@type': 'EntryPoint', 'urlTemplate': url('index.html') + '?q={search_term_string}'},
                                          'query-input': 'required name=search_term_string'}})
    else:
        graph.append({'@type': 'WebPage', 'name': P['title'], 'description': P['desc'], 'inLanguage': 'ru',
                      'isPartOf': {'@id': ORIGIN + '/#site'}, **({} if P.get('dyn') or P.get('canon_map') else {'url': page_url})})
        if P.get('crumbs'):
            graph.append(crumbs_ld(P['crumbs']))
    graph += extra_ld
    lines.append(ld_script({'@context': 'https://schema.org', '@graph': graph}))
    lines.append(END)
    return '\n'.join(lines)


def events_for(kind):
    """События окна данных (сегодня и завтра), как их показывают страницы матчей. Кэфов нет."""
    out = []
    for m in TODAY.get('matches', []):
        sp = SPORT_OF.get(m['lg'])
        if not sp or (kind in ('hockey', 'football') and sp != kind):
            continue
        ar = m.get('arena')
        out.append(({'t': m['t'], 'h': m['h'], 'a': m['a'], 'hn': m['hn'], 'an': m['an'], 'key': m['key'],
                     'arena': ar if isinstance(ar, dict) else None}, sp))
    return out[:40]


def patch_page(rel, extra_ld=None):
    return patch_text(rd(rel), rel, PAGES[rel], extra_ld)


def patch_text(src, rel, P, extra_ld=None):
    # title
    src = re.sub(r'<title>.*?</title>', '<title>%s</title>' % esc(P['title']), src, count=1, flags=re.S)
    # убрать всё, что теперь ведёт блок: description, og:*, twitter:*, canonical, TODO-комментарии, прежний блок
    src = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '', src, flags=re.S)
    src = re.sub(r'<meta\s+name="description"[^>]*>\s*', '', src)
    src = re.sub(r'<meta\s+(?:property="og:[^"]*"|name="twitter:[^"]*")[^>]*>\s*', '', src)
    src = re.sub(r'<link\s+rel="canonical"[^>]*>\s*', '', src)
    src = re.sub(r'<!--\s*TODO\(домен\).*?-->\s*', '', src, flags=re.S)
    # robots
    if OPEN:
        src = re.sub(r'<meta name="robots" content="noindex">\s*', '', src)
    elif 'name="robots"' not in src:
        src = src.replace('<meta name="theme-color"', '<meta name="robots" content="noindex">\n<meta name="theme-color"', 1)
    # блок перед </head>
    ld = list(extra_ld or [])
    ev = P.get('events')
    if ev and rel in PAGES:
        evs = events_for(ev)
        if evs:
            ld.append({'@type': 'ItemList', 'name': 'Ближайшие матчи', 'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1, 'item': event_ld(m, sp, rel)} for i, (m, sp) in enumerate(evs)]})
    blk = head_block(rel, P, ld)
    pre_ = '../' * rel.count('/')
    ldr = '<script src="%sassets/efir/efir-loader.js"></script>' % pre_  # тема «Эфир» (?theme=efir), ставится ПЕРЕД palettes.js
    pal = '<script src="%sassets/palettes.js"></script>' % pre_
    if 'assets/palettes.js' not in blk and 'assets/palettes.js' not in src:
        blk += '\n' + ldr + '\n' + pal
    elif 'efir-loader' not in src and 'efir-loader' not in blk:
        if pal in src:
            src = src.replace(pal, ldr + '\n' + pal, 1)
        else:
            blk = blk.replace(pal, ldr + '\n' + pal, 1)
    src = src.replace('</head>', blk + '\n</head>', 1)
    return src


# ───────────────────────── новые страницы ─────────────────────────
FONTS = ''  # Literata и Inter — локально (assets/v3a.css, 09.11)
TGSVG = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 '
         '.6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>')


def shell(rel, sport, body, extra_scripts='', extra_css='', head_js=''):
    d = posixpath.dirname(rel)
    pre = '../' * depth(d)
    if sport:
        hk = ('index.html' if sport == 'hockey' else '../hockey/index.html') if depth(d) < 2 else pre + 'hockey/index.html'
        fb = ('index.html' if sport == 'football' else '../football/index.html') if depth(d) < 2 else pre + 'football/index.html'
        header = ('<header class="hd" id="hd">\n  <div class="wrap">\n    <a class="logo" href="%sindex.html" aria-label="JARVIS, на главную">JAR<i>V</i>IS</a>\n'
                  '    <nav class="seg" aria-label="Вид спорта">\n      <a href="%s"%s>Хоккей</a>\n      <a href="%s"%s>Футбол</a>\n    </nav>\n'
                  '    <nav class="nav" aria-label="Разделы"></nav>\n'
                  '    <a class="btn btn-tg" href="%s" target="_blank" rel="noopener">%s<span>Прогнозы — бесплатно</span></a>\n  </div>\n</header>'
                  % (pre, hk, ' aria-current="page"' if sport == 'hockey' else '', fb, ' aria-current="page"' if sport == 'football' else '',
                     CFG.TELEGRAM, TGSVG))
    else:
        header = '<header class="hd" id="hd"><div class="wrap"><a class="logo" href="%sindex.html" aria-label="JARVIS, на главную">JARVIS</a></div></header>' % pre
    sattr = ' data-sport="%s"' % sport if sport else ''
    return ('<!doctype html>\n<html lang="ru"%s data-theme="arena">\n<head>\n<meta charset="utf-8">\n<meta name="referrer" content="strict-origin-when-cross-origin">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title></title>\n<meta name="robots" content="noindex">\n'
            '<meta name="theme-color" content="#071225">\n%s\n<link rel="stylesheet" href="%sassets/v3a.css">\n<link rel="stylesheet" href="%sassets/nav.css">\n'
            '<link rel="stylesheet" href="%sassets/forecast.css">\n%s%s<link rel="icon" href="%sfavicon.svg" type="image/svg+xml">\n'
            '<link rel="icon" href="%sfavicon-32.png" sizes="32x32" type="image/png">\n<link rel="apple-touch-icon" href="%sapple-touch-icon.png">\n'
            '<link rel="manifest" href="%ssite.webmanifest">\n<script src="%sassets/efir/efir-loader.js"></script>\n<script src="%sassets/palettes.js"></script>\n</head>\n<body class="fc"%s>\n<a class="skip" href="#main">К содержанию</a>\n%s\n\n<main id="main">\n%s\n</main>\n\n'
            '<footer><div class="wrap"><p id="foot">© JARVIS, @jarvibet</p></div></footer>\n\n'
            '<script src="%sassets/nav.js"></script>\n<script src="%sassets/footer.js"></script>\n%s</body>\n</html>\n'
            % (sattr, FONTS, pre, pre, pre, ('<link rel="stylesheet" href="%sassets/%s">\n' % (pre, extra_css)) if extra_css else '', head_js, pre, pre, pre, pre, pre, pre, ' data-field="%s"' % sport if sport else '', header, body, pre, pre, extra_scripts))


def crumbs_html(items, rel):
    d = posixpath.dirname(rel)
    parts = []
    for i, (n, p) in enumerate(items):
        href = posixpath.relpath(p, d or '.')
        parts.append('<a href="%s">%s</a>' % (esc(href), esc(n)) if i < len(items) - 1 else '<span aria-current="page">%s</span>' % esc(n))
    return '<nav class="fc-crumbs" aria-label="Хлебные крошки">%s</nav>' % ' <i aria-hidden="true">›</i> '.join(parts)


def upd_text():
    return 'Данные обновлены %s.%s в %s МСК.' % (BUILT[8:10], BUILT[5:7], BUILT[11:16])


def forecast_page(lg):
    rel = fc_rel(lg)
    sport = SPORT_OF[lg]
    d_out = sport
    P = PAGES[rel]
    name = LG_NAME[lg]
    day, ms = pick_day(matches_for(lg))
    if day:
        dm, wd = ru_date(day)
        if day == BUILT_GD:
            h2 = 'Матчи на сегодня, %s' % dm
            note = ''
        else:
            h2 = 'Ближайший игровой день: %s, %s' % (dm, wd)
            note = '<p class="fc-note">Сегодня матчей %s в данных нет. Показан ближайший игровой день.</p>' % esc(name)
        lis = ''.join(match_li(m, sport, d_out) for m in ms)
        listing = '%s<ul class="fc-list">%s</ul>' % (note, lis)
        n_txt = '%d %s' % (len(ms), 'матч' if len(ms) % 10 == 1 and len(ms) != 11 else 'матча' if 2 <= len(ms) % 10 <= 4 and not 12 <= len(ms) % 100 <= 14 else 'матчей')
    else:
        h2 = 'Ближайших матчей нет'
        listing = '<p class="fc-note">В последнем обновлении данных предстоящих матчей %s нет. Расписание появится после следующего обновления.</p>' % esc(name)
        n_txt = ''
    sw = ''.join('<li><a href="%s"%s>%s</a></li>' % (esc(posixpath.relpath(fc_rel(x), d_out)), ' aria-current="page"' if x == lg else '', esc(LG_NAME[x]))
                 for x in LG_ALL if SPORT_OF[x] == sport)
    lg_link = ('league.html?lg=%s' % lg) if sport == 'hockey' else ('ucl.html' if lg == 'ucl' else 'league.html?lg=%s' % lg)
    if sport == 'football' and lg == 'uel':
        lg_link = 'league.html?lg=uel'
    body = ('<section class="fc-top"><div class="wrap">\n%s\n<h1>Прогноз на сегодня:<br><span>%s</span></h1>\n'
            '<p class="lead">Цифры считает модель, а не эксперт, и они не гарантируют результат.</p>\n<p class="fc-upd"><time datetime="%s">%s</time></p>\n'
            '<ul class="fc-sw" aria-label="Лиги">%s</ul>\n</div></section>\n\n'
            '<section class="fc-sec" aria-labelledby="fc-day"><div class="wrap">\n<h2 id="fc-day">%s</h2>\n%s\n'
            '<p class="fc-links"><a href="%s">Таблица и результаты: %s</a> · <a href="%s">Все матчи дня колодой</a> · <a href="%s">Тренды дня</a></p>\n</div></section>\n\n'
            '<section class="fc-sec fc-how" aria-labelledby="fc-how"><div class="wrap">\n<h2 id="fc-how">Как читать цифры</h2>\n'
            '<p><b>П1, Х, П2</b> — победа хозяев, ничья и победа гостей за основное время, вместе 100 %%. <b>Тотал</b> — сколько голов забьют обе команды, '
            '«больше» значит выше заданной планки. <b>Ожидаемые голы</b> — средний прогноз модели на матч. Если термин незнаком, загляните в '
            '<a href="../glossary.html">словарь терминов</a>, а как устроен расчёт, расскажет страница <a href="../model.html?s=%s">«Как считает модель»</a>.</p>\n'
            '<p class="fc-legal">Материалы носят информационный характер. Реклама букмекеров на сайте не размещается. Сайт только для совершеннолетних (18+).</p>\n'
            '</div></section>'
            % (crumbs_html(P['crumbs'], rel), esc(name), esc(BUILT.replace(' ', 'T') + ':00+03:00'), esc(upd_text()), sw, esc(h2), listing,
               esc(lg_link), esc(name), esc('../matches.html?s=' + ('h' if sport == 'hockey' else 'f')), esc('trends.html'), 'h' if sport == 'hockey' else 'f'))
    ld = [{'@type': 'ItemList', 'name': 'Матчи %s: %s' % (name, ru_date(day)[0] if day else ''), 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'item': event_ld(m, sport, rel)} for i, m in enumerate(ms)]}] if day else []
    live_js = '<script src="%sassets/live.js" defer></script>\n' % ('../' * depth(d_out)) if day else ''
    return rel, shell(rel, sport, body, extra_scripts=live_js), ld


def hub_page():
    rel = 'forecast.html'
    P = PAGES[rel]
    # матчи сегодняшнего игрового дня — сразу с вероятностями, лиги — быстрыми ссылками-фильтром сверху (владелец 10.11);
    # лиги без матчей сегодня — короткой строкой «ближайший день» со ссылкой на свою страницу
    plural = lambda n: 'матч' if n % 10 == 1 and n != 11 else 'матча' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'матчей'  # noqa: E731
    chips, today, later, ld_ev = [], [], [], []
    for sport in ('hockey', 'football'):
        for lg in LG_ALL:
            if SPORT_OF[lg] != sport:
                continue
            day, ms = pick_day(matches_for(lg))
            if day and day == BUILT_GD:
                chips.append('<li><a href="#fc-%s">%s <small>%d</small></a></li>' % (esc(lg), esc(LG_NAME[lg]), len(ms)))
                today.append('<section class="fc-lg" id="fc-%s" aria-labelledby="fc-h-%s"><h2 id="fc-h-%s"><a href="%s">%s</a> <small>%d %s</small></h2>'
                             '<ul class="fc-list">%s</ul></section>'
                             % (esc(lg), esc(lg), esc(lg), esc(fc_rel(lg)), esc(LG_NAME[lg]), len(ms), plural(len(ms)), ''.join(match_li(m, sport, '') for m in ms)))
                ld_ev += [event_ld(m, sport, rel) for m in ms]
            else:
                if day:
                    dm, _ = ru_date(day)
                    cnt = '<small>%s, %d %s</small>' % (esc(dm), len(ms), plural(len(ms)))
                else:
                    cnt = '<small>матчей в данных нет</small>'
                later.append('<li><a href="%s"><b>%s</b>%s</a></li>' % (esc(fc_rel(lg)), esc(LG_NAME[lg]), cnt))
    if today:
        main = ('<section class="fc-sec"><div class="wrap">%s%s</div></section>\n'
                % (('<ul class="fc-sw fc-jump" aria-label="Лиги сегодня">%s</ul>' % ''.join(chips)) if len(chips) > 1 else '', ''.join(today)))
    else:
        main = '<section class="fc-sec"><div class="wrap"><p class="fc-note">Сегодня матчей в данных нет. Ниже — ближайшие игровые дни по лигам.</p></div></section>\n'
    rest = ('<section class="fc-sec" aria-labelledby="fc-later"><div class="wrap"><h2 id="fc-later">%s</h2><ul class="fc-hub">%s</ul></div></section>\n'
            % ('Ближайшие дни в других лигах' if today else 'Ближайшие игровые дни', ''.join(later))) if later else ''
    body = ('<section class="fc-top"><div class="wrap">\n%s\n<h1>Прогноз<br><span>на сегодня</span></h1>\n'
            '<p class="lead">Вероятности считает модель, а не эксперт, и они не гарантируют результат.</p>\n'
            '<p class="fc-upd"><time datetime="%s">%s</time></p>\n</div></section>\n\n%s%s'
            '<section class="fc-sec fc-how"><div class="wrap"><p class="fc-links"><a href="matches.html">Все матчи дня колодой</a> · <a href="model.html">Как считает модель</a> · '
            '<a href="glossary.html">Словарь терминов</a></p>\n'
            '<p class="fc-legal">Материалы носят информационный характер. Реклама букмекеров на сайте не размещается. Сайт только для совершеннолетних (18+).</p></div></section>'
            % (crumbs_html(P['crumbs'], rel), esc(BUILT.replace(' ', 'T') + ':00+03:00'), esc(upd_text()), main, rest))
    ld = [{'@type': 'ItemList', 'name': 'Матчи сегодня', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'item': e} for i, e in enumerate(ld_ev)]}] if ld_ev else []
    live_js = '<script src="assets/live.js" defer></script>\n' if today else ''
    return rel, shell(rel, '', body, extra_scripts=live_js), ld


def glossary_page():
    rel = 'glossary.html'
    P = PAGES[rel]
    toc = ''.join('<li><a href="#%s">%s</a></li>' % (esc(a), esc(t)) for a, t, _, _ in TERMS)
    dl = ''.join('<article class="gl-t" id="%s"><h3><a href="#%s" aria-label="Ссылка на термин">#</a> %s</h3><p>%s</p><p class="gl-ex"><b>Пример.</b> %s</p></article>'
                 % (esc(a), esc(a), esc(t), esc(d), esc(e)) for a, t, d, e in TERMS)
    body = ('<section class="fc-top"><div class="wrap">\n%s\n<h1>Словарь<br><span>терминов</span></h1>\n'
            '<p class="lead">Короткие объяснения слов, которые встречаются на сайте и в канале. Примеры условные: числа в них придуманы для понимания и не относятся к реальным матчам.</p>\n'
            '</div></section>\n\n<section class="fc-sec"><div class="wrap">\n<h2 class="gl-h">Все термины</h2>\n<ul class="gl-toc">%s</ul>\n</div></section>\n\n'
            '<section class="fc-sec"><div class="wrap gl-list">%s</div></section>\n\n'
            '<section class="fc-sec fc-how"><div class="wrap"><p>Не нашли нужное слово? Расчёт модели описан на странице <a href="model.html">«Как считает модель»</a>, '
            'а свежие вероятности по матчам лежат в разделе <a href="forecast.html">«Прогноз на сегодня»</a>.</p>\n'
            '<p class="fc-legal">Материалы носят информационный характер и не гарантируют результат. Реклама букмекеров на сайте не размещается. 18+.</p></div></section>'
            % (crumbs_html(P['crumbs'], rel), toc, dl))
    ld = [{'@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': 'Что значит «%s»?' % t, 'acceptedAnswer': {'@type': 'Answer', 'text': d}}
        for _, t, d, _ in TERMS]}]
    return rel, shell(rel, '', body), ld


def build_pages():
    made = {}
    for fn in [hub_page, glossary_page] + [lambda lg=lg: forecast_page(lg) for lg in LG_ALL]:
        rel, text, ld = fn()
        made[rel] = ld
        wr(rel, text)
    return made


# ───────────────────────── sitemap / robots ─────────────────────────
def lastmod():
    return BUILT_DAY


def build_sitemap(extra_ld_pages):
    urls = []
    skip = {'hockey/player.html', 'football/player.html', 'me/index.html', 'football/photo-credits.html', 'football/league.html', 'hockey/league.html', 'team/index.html', 'football/team.html'}
    for rel in PAGES:
        if rel in skip:
            continue
        urls.append(rel)
    for lg in HL:
        urls.append('hockey/league.html?lg=' + lg)
    for lg, v in FOOT['leagues'].items():
        if not v.get('cup') or lg != 'ucl':   # у ЛЧ своя страница football/ucl.html, Лига Европы — на общей странице лиги
            urls.append('football/league.html?lg=' + lg)
    # профили игроков (список 13.11, п. 8): адрес = canonical страницы (параметры в порядке dyn: id, затем lg)
    ppf = os.path.join(ROOT, 'football', 'data', 'pp')
    if os.path.isdir(ppf):
        urls += ['football/player.html?id=' + f[:-5] for f in sorted(os.listdir(ppf)) if f.endswith('.json') and f[:-5].isdigit()]
    for lg in HL:
        pph = os.path.join(ROOT, 'hockey', 'data', 'pp', lg)
        if os.path.isdir(pph):
            urls += ['hockey/player.html?id=%s&lg=%s' % (f[:-5], lg) for f in sorted(os.listdir(pph)) if f.endswith('.json') and f[:-5].isdigit()]
    import build_match as BM
    urls += BM.sitemap_paths()  # понятные адреса клубов и страницы матчей (старые ?id= остаются рабочими, но в sitemap их нет: у них canonical на новые)
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    lm = lastmod()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in out:
        xml.append('  <url><loc>%s</loc><lastmod>%s</lastmod></url>' % (esc(url(u)), lm))
    xml.append('</urlset>')
    wr('sitemap.xml', '\n'.join(xml) + '\n')
    return len(out)


def build_robots():
    closed = 'User-agent: *\nDisallow: /\n'
    opened = 'User-agent: *\nAllow: /\n\nSitemap: %s\n' % url('sitemap.xml')
    if OPEN:
        txt = ('# Сайт открыт для поиска (SITE_INDEXING_OPEN=1, решение владельца). Закрыть: вернуть INDEXING_OPEN=False в seo/seo_config.py.\n' + opened
               + '\n# --- закрытая версия (для отката) ---\n' + ''.join('# ' + l + '\n' if l else '#\n' for l in closed.strip().split('\n')))
    else:
        txt = ('# Сайт пока закрыт от поиска: домена нет, макет. Страницы тоже с meta robots noindex.\n' + closed
               + '\n# --- Готовая версия для открытия (раскомментировать вместе со снятием noindex; делает seo/build_seo.py при INDEXING_OPEN=True) ---\n'
               + ''.join('# ' + l + '\n' if l else '#\n' for l in opened.strip().split('\n')))
    wr('robots.txt', txt)


# ───────────────────────── версия кэша sw.js (список 13.11, п. 3) ─────────────────────────
def stamp_sw():
    """VER в sw.js = отпечаток файлов CORE (главные страницы, стили, скрипты, данные дня). Поменялись — новый sw.js,
    браузер ставит его и удаляет старые копии страниц. Не поменялись — sw.js тот же, лишних установок нет."""
    import hashlib
    rel = 'sw.js'
    text = rd(rel)
    core = re.search(r"const CORE=\[(.*?)\];", text, re.S)
    if not core:
        return
    h = hashlib.sha1()
    for f in re.findall(r"'([^']+)'", core.group(1)):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            with open(p, 'rb') as fh:
                h.update(fh.read())
    wr(rel, re.sub(r"const VER='[^']*'", "const VER='jv-%s'" % h.hexdigest()[:10], text, count=1))


# ───────────────────────── запуск ─────────────────────────
def main():
    import build_match as BM
    BM.init(sys.modules[__name__])
    _wire_canon()
    made = build_pages()
    changed = 0
    for rel in PAGES:
        if not os.path.exists(os.path.join(ROOT, rel)):
            print('нет файла', rel)
            continue
        new = patch_page(rel, made.get(rel))
        if wr(rel, new):
            changed += 1
    mstat = BM.run()
    n = build_sitemap(made)
    build_robots()
    stamp_sw()
    # 404: закрыт от поиска всегда, без canonical
    print('SEO: страниц %d (изменено %d), в sitemap %d адресов, origin %s, индексация %s; %s' % (len(PAGES), changed, n, ORIGIN, 'открыта' if OPEN else 'закрыта', mstat))


if __name__ == '__main__':
    main()
