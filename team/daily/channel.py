# -*- coding: utf-8 -*-
"""Прогнозы, которые владелец на самом деле опубликовал в @jarvibet, — с публичной веб-ленты канала t.me/s/jarvibet
(решение владельца 16.10: без утреннего опроса, источник итогов — сам канал; в канале — окончательный текст, со всеми
правками владельца). Облачная сессия до t.me не достаёт, GitHub Actions — достаёт.

Лента: https://t.me/s/jarvibet — HTML последних ~20 постов (старые — ?before=<номер самого старого на странице>).
Каждый пост — блок tgme_widget_message_wrap: data-post="jarvibet/<номер>", текст или подпись к фото / видео / гифке /
альбому — в tgme_widget_message_text (жирный — <b>, переносы — <br/>, эмодзи — <i class="emoji"><b>🔥</b></i>),
время публикации — <time datetime="…+00:00">, правка — «edited» рядом со временем.

Пост-прогноз узнаём по шапке первой строкой «КХЛ · 15 октября · 18:00 МСК» / «НХЛ · 16 октября · 02:00 МСК»
(шапка — время начала матча по МСК), дальше: матч «Хозяева — Гости» (жирным), «Прогноз: …», «Кэф: …». Остальные
посты (утро, итоги, анонсы) не трогаем. Ставку проверяем словарём settle.py; не разобралась как есть — разбор свободной
строки «Прогноз: …» из ask.py (П2, ТМ 5,5, Ф2(+1.5)… → одна форма); не разобралась и так — оставляем текст канала, итоги
напишут владельцу «посчитайте вручную».

  posts(t0, t1)  → (прогнозы на матчи с началом в [t0, t1), сводка) или Unavailable, если ленту не прочитать.
Один матч в двух постах — берём последний пост (больший номер), в сводке — заметка. Проверки: set_pages({None: html,
<номер>: html}) или DAILY_MOCK с ключом "channel": {"": html, "<номер>": html}; DAILY_CHANNEL_HTML=<файл> — одна страница.
"""
import html as _html
import os
import re
import time
from datetime import datetime, timedelta

import ask
import data
import settle
from data import MSK
from ledger import _kef, _year_for

CHANNEL = 'jarvibet'
URL = 'https://t.me/s/' + CHANNEL
MAX_PAGES = 12                          # ~20 постов на странице; с запасом на дни, когда постов много
LOOKBACK = timedelta(days=3)            # прогноз публикуют до матча: листаем, пока посты не старше начала окна − 3 дня
MONTHS = {m: i + 1 for i, m in enumerate(['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                                           'сентября', 'октября', 'ноября', 'декабря'])}
HEAD_RE = re.compile(r'^\W*(КХЛ|НХЛ)\s*[·•|∙⋅-]\s*(\d{1,2})\s+([а-яё]+)\s*[·•|∙⋅-]\s*(\d{1,2})[:.](\d\d)\s*(?:МСК)?', re.I)
LEAGUE = {'КХЛ': 'KHL', 'НХЛ': 'NHL'}
DASH = re.compile(r'\s+[—–-]\s+')
SHORT_RE = re.compile(r'(?<![а-яa-z0-9.])(?:п[12]|т[бм]|ф[12]|ит[бм][12]?|1x|x2|12)(?![а-яa-z0-9.])')   # сокращения ставок

_PAGES = None


class Unavailable(Exception):
    """Ленту канала прочитать не удалось (сеть, ответ не 200, в HTML нет ни одного поста)."""


def set_pages(pages):
    """Для проверок: {None: html первой страницы, <номер before>: html}; None — снова сеть."""
    global _PAGES
    _PAGES = pages


def _mock_page(before):
    if _PAGES is not None:
        return _PAGES.get(before, '')
    m = data._mock()
    if m and 'channel' in m:
        return m['channel'].get('' if before is None else str(before), '')
    f = os.environ.get('DAILY_CHANNEL_HTML')
    if f:
        if before is not None:
            return ''
        with open(f, encoding='utf-8') as fh:
            return fh.read()
    return None


def fetch(before=None):
    """HTML страницы ленты (до поста before). → str; ошибка сети — Unavailable."""
    page = _mock_page(before)
    if page is not None:
        return page
    import requests
    url = URL + ('?before=%d' % before if before else '')
    last = None
    for k in range(3):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)', 'Accept-Language': 'ru,en;q=0.8'},
                             timeout=30)
            if r.status_code == 200:
                return r.text
            last = 'HTTP %d' % r.status_code
        except Exception as e:  # noqa: BLE001
            last = data.err(e)
        print('DAILY_SOURCE повтор %s: %s' % (url, last), flush=True)
        time.sleep(2 + 2 * k)
    raise Unavailable('%s: %s' % (url, last))


# ---------------------------------------------------------------- разбор HTML ленты

def _div_inner(s, start):
    """Содержимое <div …> с позиции start (позиция «<div»), с учётом вложенных div. → (внутри, конец)."""
    open_end = s.find('>', start) + 1
    depth = 1
    for m in re.finditer(r'<(/?)div\b[^>]*>', s[open_end:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return s[open_end:open_end + m.start()], open_end + m.end()
    return s[open_end:], len(s)


def _plain(h):
    """Кусок HTML → текст: теги прочь, сущности (&quot; &#33; &nbsp;) раскрыты."""
    return _html.unescape(re.sub(r'<[^>]+>', '', h)).replace('\xa0', ' ')


def text_lines(inner):
    """HTML текста поста → [(строка, жирное в строке)]. Эмодзи-картинки Telegram — обратно в символ."""
    h = re.sub(r'<i class="emoji"[^>]*>\s*<b>(.*?)</b>\s*</i>', r'\1', inner, flags=re.S)
    h = re.sub(r'</?tg-emoji[^>]*>', '', h)
    h = re.sub(r'<br\s*/?>|</?blockquote[^>]*>|</?p>|</div>|<div[^>]*>', '\n', h)
    out = []
    for raw in h.split('\n'):
        t = re.sub(r'\s+', ' ', _plain(raw)).strip()
        if t:
            bold = ' '.join(re.sub(r'\s+', ' ', _plain(b)).strip() for b in re.findall(r'<b>(.*?)</b>', raw, re.S))
            out.append((t, bold.strip()))
    return out


def _media(block):
    if 'tgme_widget_message_grouped' in block:
        return 'альбом'
    if 'tgme_widget_message_roundvideo' in block:
        return 'кружок'
    if 'tgme_widget_message_video_player' in block:
        return 'гифка' if re.search(r'message_video_player[^"]*\bjs-message_gif|\bgif\b|data-gif|tgme_widget_message_gif', block, re.I) else 'видео'
    if 'tgme_widget_message_photo_wrap' in block:
        return 'фото'
    if 'tgme_widget_message_document' in block:
        return 'файл'
    return 'текст'


def _media_url(block):
    """Ссылка на файл поста на CDN Telegram (видео/гифка — mp4, фото — jpg) или ''. Нужна зеркалу в Instagram."""
    m = re.search(r'<video[^>]*\bsrc="([^"]+)"', block) or \
        re.search(r'tgme_widget_message_photo_wrap[^>]*background-image:url\(\'([^\']+)\'\)', block)
    return _html.unescape(m.group(1)) if m else ''


def parse_page(page):
    """HTML ленты → [{id, text: [(строка, жирное)], media, media_url, edited, posted: datetime МСК | None}] по номеру."""
    out = []
    starts = [m.start() for m in re.finditer(r'<div class="tgme_widget_message_wrap\b', page)]
    for i, a in enumerate(starts):
        block = page[a:starts[i + 1] if i + 1 < len(starts) else len(page)]
        num = re.search(r'data-post="%s/(\d+)"' % CHANNEL, block, re.I)
        if not num:
            continue
        mt = re.search(r'<div class="tgme_widget_message_text(?:\s[^"]*)?"', block)
        inner, rest = '', block
        if mt:
            inner, end = _div_inner(block, mt.start())
            rest = block[:mt.start()] + block[end:]
        meta = rest[rest.find('tgme_widget_message_footer'):] if 'tgme_widget_message_footer' in rest else rest
        edited = bool(re.search(r'tgme_widget_message_edited|>\s*(?:edited|изменено|изменён)\b|\b(?:edited|изменено)\s*<', meta, re.I))
        ts = re.search(r'<time[^>]*\bdatetime="([^"]+)"', meta) or re.search(r'<time[^>]*\bdatetime="([^"]+)"', rest)
        posted = None
        if ts:
            try:
                posted = datetime.fromisoformat(ts.group(1).replace('Z', '+00:00')).astimezone(MSK)
            except ValueError:
                pass
        out.append(dict(id=int(num.group(1)), text=text_lines(inner), media=_media(rest), media_url=_media_url(rest),
                        edited=edited, posted=posted))
    return sorted(out, key=lambda p: p['id'])


# ---------------------------------------------------------------- пост → прогноз

def _team(name):
    """Название из поста → название команды как в settle (обе лиги); не узнали — как есть."""
    n = settle.canon(re.sub(r'[«»"*_]', '', name).strip(' .,:;!'))
    if n in settle.GEN:
        return n, True
    occ = ask.find_teams(ask._n(n))
    if len(occ) == 1 and len(occ[0][2]) == 1:
        return occ[0][2][0], True
    return n, False


def _start(head, ref):
    m = HEAD_RE.match(head)
    if not m or m.group(3).lower() not in MONTHS:
        return None, None
    day, mon, hh, mm = int(m.group(2)), MONTHS[m.group(3).lower()], int(m.group(4)), int(m.group(5))
    try:
        return LEAGUE[m.group(1).upper()], datetime(_year_for(day, mon, ref), mon, day, hh, mm, tzinfo=MSK)
    except ValueError:
        return None, None


def _bet(bet, home, away, league, start):
    """Ставка канала → (ставка для итогов, кэф из строки, заметка). Разбирается как есть — как есть."""
    bet = re.sub(r'\s+', ' ', bet).strip(' .;')
    try:
        legs = settle.parse(bet, home, away)
        if SHORT_RE.search(settle._norm(bet)):              # «ТМ 5,5», «П2», «Ф2(+1.5)» — в итогах одной формой
            return ask.phrase(legs, home, away), None, ''
        return bet, None, ''
    except ValueError as e:
        why = str(e)
    g = dict(league=league, home=home, away=away, start=start, state='final')
    p, why2 = ask.parse_line('Прогноз: %s — %s %s' % (home, away, bet), [g])
    if p:
        return p['bet'], p['kef'], 'ставка «%s» → «%s»' % (bet, p['bet'])
    return bet, None, 'ставка не разобрана (%s; %s)' % (why, why2)


def pick_of(post):
    """Пост ленты → (прогноз, None) / (None, почему не прогноз) / (None, None) — не пост-прогноз вовсе."""
    lines = post['text']
    if not lines:
        return None, None
    hi = next((i for i, (t, _) in enumerate(lines[:2]) if HEAD_RE.match(t)), None)
    if hi is None:
        return None, None
    head = lines[hi][0]
    league, start = _start(head, post['posted'] or data.now_msk())
    if not league:
        return None, 'шапка «%s» не разобрана' % head
    home = away = bet = kef = None
    for t, bold in lines[hi + 1:]:
        if home is None and not re.match(r'(?i)\s*(прогноз|к[эе]ф)\b', t):
            for cand in (bold, t):
                parts = DASH.split(cand) if cand else []
                if len(parts) == 2:
                    home, away = parts
                    break
            if home is not None:
                continue
        mb = re.match(r'(?i)\s*прогноз\s*:\s*(.+)$', t)
        if mb and bet is None:
            bet = mb.group(1)
            continue
        mk = re.match(r'(?i)\s*(?:к[эе]ф|коэф\w*)\.?\s*:?\s*(\d+[.,]\d+)', t)
        if mk and kef is None:
            kef = _kef(mk.group(1))
    if home is None:
        return None, 'нет строки матча «Хозяева — Гости»'
    if not bet:
        return None, 'нет строки «Прогноз: …»'
    (home, ok_h), (away, ok_a) = _team(home), _team(away)
    m = ask.KEF_RX.search(ask._n(bet))
    if kef is None and m:                                    # «Прогноз: победа СКА, кэф 1,85» одной строкой
        kef = round(float(m.group(1)), 2)
    bet = re.sub(r'(?i)[,;]?\s*(?:кэф|кеф|коэф\w*\.?|кф|@)\s*[:=]?\s*\d+[.,]\d+\s*$', '', bet)
    note = '' if ok_h and ok_a else 'команда не узнана: %s' % ', '.join(n for n, ok in ((home, ok_h), (away, ok_a)) if not ok)
    bet2, kef2, bnote = _bet(bet, home, away, league, start)
    return dict(pid='№%d' % post['id'], msg_id=post['id'], league=league, home=home, away=away, start=start, bet=bet2,
                kef=kef if kef is not None else kef2, src='channel', note='; '.join(x for x in (note, bnote) if x),
                head=head, exact_time=True, tg_edited=post['edited'], media=post['media'], posted=post['posted'],
                url='https://t.me/%s/%d' % (CHANNEL, post['id']), edited=False), None


# ---------------------------------------------------------------- лента → прогнозы окна

def feed(t0):
    """Посты ленты, пока не дошли до опубликованных раньше t0 − LOOKBACK. → (посты, страниц)."""
    seen, before, pages = {}, None, 0
    while pages < MAX_PAGES:
        page = fetch(before)
        pages += 1
        got = parse_page(page)
        if not got:
            if pages == 1:
                raise Unavailable('в ответе %s нет ни одного поста (%d знаков) — разметка ленты изменилась?' % (URL, len(page or '')))
            break
        new = [p for p in got if p['id'] not in seen]
        for p in got:
            seen[p['id']] = p
        oldest = min(got, key=lambda p: p['id'])
        if not new or oldest['id'] <= 1 or (oldest['posted'] and oldest['posted'] < t0 - LOOKBACK):
            break
        before = oldest['id']
    return sorted(seen.values(), key=lambda p: p['id']), pages


def posts(t0, t1):
    """Прогнозы из канала на матчи с началом в [t0, t1): один на матч — последний пост. → (прогнозы, сводка).
    Сводка: pages, total (постов прочитано), picks (все посты-прогнозы с пометкой), notes (владельцу), log (строки лога)."""
    all_posts, pages = feed(t0)
    found, notes, bad = [], [], []
    for post in all_posts:
        p, why = pick_of(post)
        if p:
            found.append(p)
        elif why:
            bad.append((post, why))
    by_match, status = {}, {}
    for p in found:                                       # по номеру поста: последний перекрывает прежний
        if not (t0 <= p['start'] < t1):
            status[p['msg_id']] = 'вне окна'
            continue
        key = (p['league'], p['home'], p['away'])
        if key in by_match:
            old = by_match[key]
            status[old['msg_id']] = 'дубль — взят №%d' % p['msg_id']
            notes.append('%s — %s в канале дважды (№%d и №%d): в итогах последний, №%d' % (
                p['home'], p['away'], old['msg_id'], p['msg_id'], p['msg_id']))
        by_match[key] = p
        status[p['msg_id']] = 'в итоги'
    for post, why in bad:
        posted = post['posted']
        if posted is None or posted >= t0 - timedelta(hours=12):
            notes.append('пост №%d похож на прогноз, но %s — в итоги не вошёл' % (post['id'], why))
    for p in by_match.values():
        if p['note']:
            notes.append('№%d %s — %s: %s' % (p['msg_id'], p['home'], p['away'], p['note']))
    log = ['DAILY_SOURCE канал @%s: страниц %d, постов %d (№%s–%s), постов-прогнозов %d, в окне %s – %s: %d' % (
        CHANNEL, pages, len(all_posts), all_posts[0]['id'] if all_posts else '—', all_posts[-1]['id'] if all_posts else '—',
        len(found), t0.strftime('%d.%m %H:%M'), t1.strftime('%d.%m %H:%M'), len(by_match))]
    for p in found:
        log.append('DAILY_SOURCE №%d | %s | %s — %s | %s | кэф %s | %s%s | опубликован %s | %s' % (
            p['msg_id'], p['head'], p['home'], p['away'], p['bet'], ('%.2f' % p['kef']).replace('.', ',') if p['kef'] else '—',
            p['media'], ', изменён' if p['tg_edited'] else '', p['posted'].strftime('%d.%m %H:%M') if p['posted'] else '?',
            status.get(p['msg_id'], '')))
    for post, why in bad:
        log.append('DAILY_SOURCE №%d | не прогноз: %s | %s' % (post['id'], why, post['text'][0][0][:80] if post['text'] else ''))
    picks = sorted(by_match.values(), key=lambda p: p['start'])
    return picks, dict(pages=pages, total=len(all_posts), picks=found, notes=notes, log=log)
