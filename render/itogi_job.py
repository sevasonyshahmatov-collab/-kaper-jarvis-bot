"""Постеры «Итоги дня» и «Матчи дня» по данным таблицы → в Telegram (запускается GitHub Actions, .github/workflows/itogi.yml).

Таблица (Apps Script) после последнего матча дня шлёт в GitHub событие «itogi» с данными:
    {"league": "KHL" | "NHL", "day": "2026-09-30", "date_title": "среда, 30 сентября", "chat": "<id>",
     "items": [{"home": "Амур", "away": "Нефтехимик", "sh": 1, "sa": 0, "mark": "" | "ОТ" | "Б" | "ОТ/Б"}]}
Рисуем формат «Ячейки» (results_ice2, variant 10) и отправляем фото в чат chat ботом TG_BOT_TOKEN (секрет репозитория).
Больше 5 матчей — несколько постеров одним альбомом, как у «Матчей дня» (split_matchi).
"players" — постер «Игроки дня» сразу следом за итогами: {league, title?, items: [{name, team, g, a} | {name, team, sv, sa}],
caption?, chats?} (players_ice); то же отдельно — "kind": "players" (событие «players»).
"after_text" (HTML) — отдельный пост сразу следом (у НХЛ — «Игроки дня»); "after_chats" — куда его отправить
(по умолчанию — туда же, куда итоги).

«Матчи дня» — то же с "kind": "matchi" (событие «matchi»), в items вместо счёта время и линия в основное время:
    {"home": "Спартак", "away": "Трактор", "time": "19:30", "odds": [1.84, 4.37, 3.91] | null}
Рисуем формат «Колонки» (preview_ice, style='columns').
"extra" (необязательно, HTML) — дописывается к подписи: у НХЛ это «🇷🇺 Наши» (результативность россиян).
Не влезает в лимит подписи Telegram (1024 знака) — уходит отдельным сообщением сразу после фото.
«Итоги игрового дня» КХЛ + НХЛ одним постом — "kind": "itogi2" (событие «itogi2»):
    {"leagues": [{"league": "KHL", "date_title": "…", "items": [...]}, {"league": "NHL", ...}], "date_title": "…", "chats": [...]}
Два баннера «Ячейки» альбомом, в подписи — счёт всех матчей по лигам; "after_text" (HTML) — пост «Игроки дня» сразу следом.
"chats" — куда отправить (канал и группа у автоматики, ваш чат у кнопок); нет — "chat".
Картинка не нарисовалась — в те же чаты уходит подпись текстом (итоги не пропадут), задание помечается ошибкой.
«Баннеры матчей дня» в 4К — "kind": "sides" (событие «sides»): каждый матч отдельным баннером в шаблоне «Бока»
(nhl_kit.preview, как к прогнозам: эмблемы, день и время по МСК, линия П1/Х/П2), 3840×1920:
    {"league": "KHL" | "NHL", "day": "2026-10-11", "date_title": "воскресенье, 11 октября", "chat": "<ваш id>",
     "items": [{"home": "Адмирал", "away": "Лада", "day": "2026-10-11", "time": "10:00", "odds": [1.89, 3.72, 3.64] | null}]}
Уходят вам в личку файлами (альбомы до 10) — без сжатия Telegram; линии ещё нет — баннер без строки коэффициентов.
Без TG_BOT_TOKEN — только сохраняем картинку (для проверки: python render/itogi_job.py payload.json).
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MARKS = {'', 'ОТ', 'Б', 'ОТ/Б'}
# подписи — без эмодзи: анимированные (премиум) бот в канал поставить не может, а обычные решили не ставить
LEAGUE_TITLE = {'KHL': '<b>КХЛ · итоги дня</b>', 'NHL': '<b>НХЛ · итоги ночи</b>'}
MATCHI_TITLE = {'KHL': '<b>КХЛ · матчи дня</b>', 'NHL': '<b>НХЛ · матчи дня</b>'}
EMOJI = re.compile('(?:[\U0001F1E6-\U0001F1FF]|[\U0001F000-\U0001FAFF]|[\u2600-\u27BF]|[\u2B00-\u2BFF]|\uFE0F|\u200D)+ ?')


def no_emoji(text):
    return re.sub(r'(?m)^[ \t]+', '', EMOJI.sub('', text))


def load_payload():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as f:
            return json.load(f)
    raw = os.environ.get('PAYLOAD') or ''
    if not raw.strip() or raw.strip() == 'null':
        raw = os.environ.get('INPUT_PAYLOAD') or '{}'
    return json.loads(raw)


def clean(payload):
    league = str(payload.get('league', '')).upper()
    if league not in LEAGUE_TITLE:
        raise SystemExit('неизвестная лига: %r' % league)
    items = []
    for it in payload.get('items') or []:
        home, away = str(it.get('home', '')).strip(), str(it.get('away', '')).strip()
        try:
            sh, sa = int(it.get('sh')), int(it.get('sa'))
        except (TypeError, ValueError):
            continue
        mark = str(it.get('mark') or '').strip()
        if home and away:
            items.append(dict(home=home, away=away, sh=sh, sa=sa, mark=mark if mark in MARKS else ''))
    if not items:
        raise SystemExit('в данных нет ни одного сыгранного матча')
    return league, items, str(payload.get('date_title') or '').strip(), str(payload.get('chat') or '').strip()


def clean_matchi(payload):
    league = str(payload.get('league', '')).upper()
    if league not in MATCHI_TITLE:
        raise SystemExit('неизвестная лига: %r' % league)
    items = []
    for it in payload.get('items') or []:
        home, away = str(it.get('home', '')).strip(), str(it.get('away', '')).strip()
        if not home or not away:
            continue
        odds = it.get('odds')
        try:
            odds = tuple(float(x) for x in odds) if odds and len(odds) == 3 and all(float(x) > 1 for x in odds) else None
        except (TypeError, ValueError):
            odds = None
        items.append(dict(home=home, away=away, time=str(it.get('time') or '').strip()[:5], odds=odds))
    if not items:
        raise SystemExit('в данных нет ни одного матча')
    return league, items, str(payload.get('date_title') or '').strip(), str(payload.get('chat') or '').strip()


MATCHI_PER_POSTER = 5        # больше — делим на постеры
MATCHI_MAX = 7               # больше 7 на одном постере не помещается


def split_matchi(items):
    """Матчи дня и итоги дня по постерам. До 5 — один. Больше — поровну, первый крупнее (6 → 3+3, 7 → 4+3, 9 → 5+4,
    13 → 7+6); не влезает в два по 7 — три и больше (15 → 5+5+5, 16 → 6+5+5).
    Все постеры альбома одного размера, ячейки на одних местах (preview_ice rows=)."""
    n = len(items)
    if n <= MATCHI_PER_POSTER:
        return [items]
    g = max(2, -(-n // MATCHI_MAX))
    out, i = [], 0
    for k in range(g):
        size = n // g + (1 if k < n % g else 0)
        out.append(items[i:i + size])
        i += size
    return out


def caption_matchi(league, items, date_title):
    """«02:30 | Филадельфия — Питтсбург» по строке на матч и «Время московское.» (как в канале)."""
    lines = ['%s%s — %s' % (html.escape(i['time']) + ' | ' if i['time'] else '', html.escape(i['home']), html.escape(i['away']))
             for i in items]
    return '\n'.join(lines) + '\n\nВремя московское.'


def caption(league, items, date_title):
    lines = ['%s — %s <b>%d:%d</b>%s' % (html.escape(i['home']), html.escape(i['away']), i['sh'], i['sa'],
                                          ' ' + i['mark'] if i['mark'] else '') for i in items]
    head = LEAGUE_TITLE[league] + (' · ' + html.escape(date_title) if date_title else '')
    return head + '\n\n' + '\n'.join(lines)


CAPTION_MAX = 1024


def send_message(token, chat, text):
    import requests
    r = requests.post('https://api.telegram.org/bot%s/sendMessage' % token, timeout=60,
                      data={'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'})
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


TG_SIDES_MAX = 9900            # Telegram: у фото ширина + высота не больше 10 000
TG_BYTES_MAX = 9500000         # и файл не больше 10 МБ


def tg_ready(path):
    """Постеры рисуются в 4К (quality.S = 3); если фото не проходит по ограничениям Telegram (сумма сторон, 10 МБ) —
    отправляем уменьшенную копию *_tg.jpg, сам 4К-файл остаётся. Проходит — тот же путь."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
        if w + h <= TG_SIDES_MAX and os.path.getsize(path) <= TG_BYTES_MAX:
            return path
        k = min(1.0, TG_SIDES_MAX / float(w + h))
        small = im.convert('RGB').resize((int(w * k), int(h * k)), Image.LANCZOS) if k < 1 else im.convert('RGB')
    out = os.path.splitext(path)[0] + '_tg.jpg'
    q = 92
    while True:
        small.save(out, quality=q, subsampling=0)
        if os.path.getsize(out) <= TG_BYTES_MAX or small.size[0] < 800:
            break
        if q > 74:
            q -= 6                                   # сначала качество JPEG
        else:
            small = small.resize((int(small.size[0] * 0.85), int(small.size[1] * 0.85)), Image.LANCZOS)   # потом размер
    print('для Telegram уменьшено: %s → %dx%d, %d КБ' % (os.path.basename(path), small.size[0], small.size[1], os.path.getsize(out) // 1024))
    return out


def send_album(token, chat, paths, text):
    """Альбом из нескольких фото; подпись — под альбомом (у первого фото)."""
    import requests
    media, files = [], {}
    for i, path in enumerate(paths):
        m = {'type': 'photo', 'media': 'attach://p%d' % i}
        if i == 0 and text:
            m.update(caption=text, parse_mode='HTML')
        media.append(m)
        files['p%d' % i] = open(tg_ready(path), 'rb')
    try:
        r = requests.post('https://api.telegram.org/bot%s/sendMediaGroup' % token, timeout=90,
                          data={'chat_id': chat, 'media': json.dumps(media, ensure_ascii=False)}, files=files)
    finally:
        for f in files.values():
            f.close()
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


PLAYERS_TITLE = {'KHL': 'ИГРОКИ ДНЯ', 'NHL': 'НАШИ В НХЛ'}
PLAYERS_HEAD = {'KHL': 'КХЛ · игроки дня', 'NHL': 'НХЛ · наши'}


def clean_players(pl):
    """Блок «Игроки дня»: {league, items: [{name, team, g, a} | {name, team, sv, sa}], title?, caption?, chats?, date_title?}."""
    league = str(pl.get('league', '')).upper()
    if league not in PLAYERS_TITLE:
        raise SystemExit('неизвестная лига: %r' % league)
    items = []
    for it in pl.get('items') or []:
        name, team = str(it.get('name', '')).strip(), str(it.get('team', '')).strip()
        if not name or not team:
            continue
        try:
            if it.get('sa') not in (None, ''):
                items.append(dict(name=name, team=team, sv=int(it.get('sv') or 0), sa=int(it['sa'])))
            else:
                items.append(dict(name=name, team=team, g=int(it.get('g') or 0), a=int(it.get('a') or 0)))
        except (TypeError, ValueError):
            continue
    if not items:
        raise SystemExit('нет игроков')
    title = str(pl.get('title') or PLAYERS_TITLE[league]).strip()[:30]
    chats = [str(c).strip() for c in (pl.get('chats') or []) if str(c or '').strip()]
    return league, items, title, no_emoji(str(pl.get('caption') or '').strip())[:CAPTION_MAX], chats


def caption_players(league, items, date_title):
    """Подпись к постеру «Игроки дня», если таблица её не прислала: строка на игрока."""
    lines = []
    for i in items:
        if 'sa' in i:
            lines.append('%s (%s) — %d из %d%s' % (html.escape(i['name']), html.escape(i['team']), i['sv'], i['sa'],
                                                  ', сухой матч' if i['sv'] == i['sa'] else ''))
        else:
            lines.append('%s (%s) — %d+%d' % (html.escape(i['name']), html.escape(i['team']), i['g'], i['a']))
    head = '<b>%s</b>' % PLAYERS_HEAD[league] + (' · ' + html.escape(date_title) if date_title else '')
    return head + '\n\n' + '\n'.join(lines)


def players_post(token, pl, date_title, default_chats):
    """Постер «Игроки дня» (больше 5 игроков — альбом, как «Матчи дня») с подписью-текстом; не нарисовался — текст.
    Без token только рисует. Возвращает список ошибок."""
    try:
        league, items, title, text, chats = clean_players(pl)
    except SystemExit as e:
        print('«Игроки дня» пропущены:', e)
        return []
    chats = chats or default_chats
    date_title = str(pl.get('date_title') or date_title or '').strip()
    text = text or caption_players(league, items, date_title)
    groups = split_matchi(items)
    rows = max(len(g) for g in groups)
    paths = [os.path.join(os.getcwd(), 'players_%s%s.jpg' % (league.lower(), '_%d' % (k + 1) if len(groups) > 1 else ''))
             for k in range(len(groups))]
    drawn = True
    try:
        if league == 'NHL':
            import nhl
            nhl.register()
        import players_ice as pli
        for k, (grp, path) in enumerate(zip(groups, paths)):
            pli.render(grp, path, league, title=title, date_title=date_title or None, cont=k > 0, rows=rows)
        print('«Игроки дня» нарисованы:', ', '.join(paths), '— игроков', '+'.join(str(len(g)) for g in groups))
        print('подпись «Игроки дня»:\n' + text)
    except Exception as e:                       # noqa: BLE001 — не нарисовалось: публикуем текстом
        drawn = False
        print('«Игроки дня» не нарисовались:', repr(e))
    if not token:
        return []
    errors = []
    for c in chats:
        try:
            if not drawn:
                send_message(token, c, text)
            elif len(paths) > 1:
                send_album(token, c, paths, text)
            else:
                send_photo(token, c, paths[0], text)
            print('«Игроки дня» отправлены в', c)
        except SystemExit as e:
            errors.append('%s: %s' % (c, e))
    if not drawn:
        errors.append('постер «Игроки дня» не нарисовался — опубликован текст')
    return errors


def caption_both(blocks, date_title):
    """Подпись общего поста: «Итоги игрового дня · дата», затем по лиге: название и счёт матчей."""
    parts = ['<b>Итоги игрового дня</b>' + (' · ' + html.escape(date_title) if date_title else '')]
    for league, items in blocks:
        lines = ['%s — %s <b>%d:%d</b>%s' % (html.escape(i['home']), html.escape(i['away']), i['sh'], i['sa'],
                                              ' ' + i['mark'] if i['mark'] else '') for i in items]
        parts.append('<b>%s</b>\n%s' % ('КХЛ' if league == 'KHL' else 'НХЛ', '\n'.join(lines)))
    return '\n\n'.join(parts)


def main_both(payload):
    """Общий пост: баннер на каждую лигу (КХЛ первым), альбомом, подпись — счёт всех матчей."""
    blocks = []
    for lg in payload.get('leagues') or []:
        try:
            league, items, title, _ = clean(dict(lg, chat=''))
        except SystemExit as e:
            print('пропускаю лигу:', e)
            continue
        blocks.append((league, items, title))
    if not blocks:
        raise SystemExit('в данных нет ни одного сыгранного матча')
    blocks.sort(key=lambda b: 0 if b[0] == 'KHL' else 1)
    date_title = str(payload.get('date_title') or blocks[0][2] or '').strip()
    text = no_emoji(caption_both([(b[0], b[1]) for b in blocks], date_title))
    after = ''
    if len(text) > CAPTION_MAX:                  # большой день: альбом без подписи, счёт — следом сообщением
        text, after = '', text
    chats = [str(c).strip() for c in (payload.get('chats') or [payload.get('chat')]) if str(c or '').strip()]
    # «Игроки дня» — отдельным сообщением сразу следом за итогами (порядок в канале гарантирован)
    players = no_emoji(str(payload.get('after_text') or '').strip())[:4000]
    print('подпись:\n' + (text or after) + ('\n--- следом:\n' + players if players else ''))
    paths, drawn = [], True
    try:
        import results_ice2 as ri
        for league, items, title in blocks:
            if league == 'NHL':
                import nhl
                nhl.register()
            groups = split_matchi(items)
            for k, grp in enumerate(groups):
                out = os.path.join(os.getcwd(), 'itogi2_%s%s.jpg' % (league.lower(), '_%d' % (k + 1) if len(groups) > 1 else ''))
                ri.render(grp, out, variant=10, league=league, date_title=title or date_title or None, cont=k > 0,
                          rows=max(len(g) for g in groups))
                paths.append(out)
        print('нарисовано:', ', '.join(paths))
    except Exception as e:                       # noqa: BLE001 — не нарисовалось: публикуем текстом
        drawn = False
        print('картинки не нарисовались:', repr(e))
    token = os.environ.get('TG_BOT_TOKEN')
    if not token:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        return
    if not chats:
        raise SystemExit('не указан чат (chat / chats) для отправки')
    errors = []
    for c in chats:
        try:
            if drawn:
                if len(paths) == 1:
                    send_photo(token, c, paths[0], text)
                else:
                    send_album(token, c, paths, text)
                if after:
                    send_message(token, c, after)
            else:
                send_message(token, c, text or after)
            if players:
                send_message(token, c, players)
            print('отправлено в', c)
        except SystemExit as e:
            errors.append('%s: %s' % (c, e))
    if errors or not drawn:
        raise SystemExit('; '.join(errors) or 'картинки не нарисовались — опубликован текст')


def send_photo(token, chat, path, text):
    import requests
    with open(tg_ready(path), 'rb') as f:
        r = requests.post('https://api.telegram.org/bot%s/sendPhoto' % token, timeout=60,
                          data={'chat_id': chat, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': f})
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


SIDES_LEAGUE = {'KHL': 'КХЛ', 'NHL': 'НХЛ'}
WEEKDAYS = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
SIDES_PER_GROUP = 10                                # Telegram: в альбоме до 10 файлов


def clean_sides(payload):
    """«Баннеры матчей дня»: лига, день, матчи [{home, away, day, time, odds}] — как у «Матчей дня», плюс дата матча."""
    league = str(payload.get('league', '')).upper()
    if league not in SIDES_LEAGUE:
        raise SystemExit('неизвестная лига: %r' % league)
    day = str(payload.get('day') or '').strip()[:10]
    _, items, date_title, chat = clean_matchi(payload)
    for it, raw in zip(items, [r for r in payload.get('items') or []
                               if str(r.get('home', '')).strip() and str(r.get('away', '')).strip()]):
        d = str(raw.get('day') or '').strip()[:10]
        it['day'] = d if re.match(r'^\d{4}-\d{2}-\d{2}$', d) else day
    return league, day, items, date_title, chat


def side_when(day, time):
    """«СБ 10.10 · 10:00 МСК» — подпись под эмблемами, как на баннерах к прогнозам."""
    import datetime
    try:
        d = datetime.date.fromisoformat(day)
        s = '%s %02d.%02d' % (WEEKDAYS[d.weekday()], d.day, d.month)
    except (TypeError, ValueError):
        s = ''
    t = '%s МСК' % time if time else ''
    return ' · '.join(x for x in (s, t) if x) or None


def side_slug(league, team):
    """Латиница для имени файла: «Ак Барс» → akbars (по эмблемам набора); не нашли — None."""
    try:
        import poster
        if league == 'NHL':
            import nhl
            team = nhl.resolve(team)
        return re.sub(r'[^a-z0-9]+', '', str(poster.TEAMS[team][0]).lower()) or None
    except Exception:                           # noqa: BLE001 — имя файла не главное
        return None


def side_caption(it):
    odds = ' · П1 %.2f · Х %.2f · П2 %.2f' % it['odds'] if it['odds'] else ''
    return '<b>%s — %s</b>\n%s%s' % (html.escape(it['home']), html.escape(it['away']), html.escape(side_when(it['day'], it['time']) or ''), odds)


def send_documents(token, chat, docs):
    """Файлами (без сжатия Telegram): [(путь, подпись)] — альбомами по 10, один файл — sendDocument."""
    import requests
    for k in range(0, len(docs), SIDES_PER_GROUP):
        part = docs[k:k + SIDES_PER_GROUP]
        files = {'d%d' % i: (os.path.basename(path), open(path, 'rb'), 'image/jpeg') for i, (path, _) in enumerate(part)}
        try:
            if len(part) == 1:
                r = requests.post('https://api.telegram.org/bot%s/sendDocument' % token, timeout=120,
                                  data={'chat_id': chat, 'caption': part[0][1], 'parse_mode': 'HTML'},
                                  files={'document': files['d0']})
            else:
                media = [{'type': 'document', 'media': 'attach://d%d' % i, 'caption': text, 'parse_mode': 'HTML'}
                         for i, (_, text) in enumerate(part)]
                r = requests.post('https://api.telegram.org/bot%s/sendMediaGroup' % token, timeout=180,
                                  data={'chat_id': chat, 'media': json.dumps(media, ensure_ascii=False)}, files=files)
        finally:
            for f in files.values():
                f[1].close()
        j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
        if not j.get('ok'):
            raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


def main_sides(payload):
    """Каждый матч дня — баннер «Бока» в 4К (scale=3, 3840×1920) → вам файлами. Не нарисовался один — остальные всё равно уходят."""
    league, day, items, date_title, chat = clean_sides(payload)
    import nhl_kit
    kw = dict(scale=3)
    if league == 'NHL':
        import nhl
        nhl.register()
    else:
        import poster
        kw.update(tag='KXL', accent=poster.ACC)
    out_dir = os.path.join(os.getcwd(), 'sides_%s_%s' % (league.lower(), day.replace('-', '') or 'day'))
    os.makedirs(out_dir, exist_ok=True)
    docs, failed = [], []
    for k, it in enumerate(items):
        pair = [side_slug(league, it['home']), side_slug(league, it['away'])]
        name = '%s_%s_%02d%s.jpg' % (league.lower(), (it['day'] or day).replace('-', ''), k + 1,
                                     '_' + '_'.join(pair) if all(pair) else '')
        path = os.path.join(out_dir, name)
        try:
            path = nhl_kit.preview(it['home'], it['away'], dict(when=side_when(it['day'] or day, it['time']), odds=it['odds']), path, **kw)
            docs.append((path, side_caption(it)))
            print('нарисовано:', path)
        except Exception as e:                  # noqa: BLE001
            failed.append('%s — %s' % (it['home'], it['away']))
            print('не нарисовался %s — %s: %r' % (it['home'], it['away'], e))
    head = '<b>%s · баннеры матчей дня</b>%s\n%d %s в 4К (3840×1920) — файлами, без сжатия.' % (
        SIDES_LEAGUE[league], ' · ' + html.escape(date_title) if date_title else '', len(docs),
        'баннер' if len(docs) % 10 == 1 and len(docs) % 100 != 11 else
        'баннера' if 2 <= len(docs) % 10 <= 4 and not 12 <= len(docs) % 100 <= 14 else 'баннеров')
    if failed:
        head += '\nНе нарисовались: ' + html.escape(', '.join(failed)) + '.'
    print(head)
    token = os.environ.get('TG_BOT_TOKEN')
    if not token:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        return
    if not chat:
        raise SystemExit('не указан чат (chat) для отправки')
    send_message(token, chat, head)
    if docs:
        send_documents(token, chat, docs)
    print('отправлено в', chat, '— баннеров', len(docs))
    if failed or not docs:
        raise SystemExit('не нарисовались: ' + ', '.join(failed or ['все']))


def main():
    payload = load_payload()
    kind = str(payload.get('kind') or os.environ.get('EVENT_KIND') or 'itogi').lower()
    if kind == 'team':                          # команда JARVIS: задание team/out/<день>/job.json (render/team_job.py)
        import team_job
        return team_job.main(payload)
    if kind == 'itogi2':
        return main_both(payload)
    if kind == 'sides':                         # баннеры «Бока» каждого матча дня в 4К → вам файлами
        return main_sides(payload)
    if kind == 'players':                       # «Игроки дня» отдельно (запасной вариант — после утреннего обновления)
        chats = [str(c).strip() for c in (payload.get('chats') or [payload.get('chat')]) if str(c or '').strip()]
        token = os.environ.get('TG_BOT_TOKEN')
        if token and not chats:
            raise SystemExit('не указан чат (chat / chats) для отправки')
        errors = players_post(token, payload, payload.get('date_title'), chats)
        if not token:
            print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        if errors:
            raise SystemExit('; '.join(errors))
        return
    league, items, date_title, chat = (clean_matchi if kind == 'matchi' else clean)(payload)
    # куда: список chats (канал и группа — автоматика, или ваш чат — кнопки меню); старые события — один chat
    chats = [str(c).strip() for c in (payload.get('chats') or [chat]) if str(c or '').strip()]
    # подпись — до рисования: если картинка не получится, её же опубликуем текстом
    if kind == 'matchi':
        text = str(payload.get('caption') or '').strip()[:1000] or caption_matchi(league, items, date_title)
    else:
        text = caption(league, items, date_title)
    extra = str(payload.get('extra') or '').strip()[:3500] if kind != 'matchi' else ''
    after = ''
    if extra:
        if len(text) + 2 + len(extra) <= CAPTION_MAX:
            text += '\n\n' + extra
        else:
            after = extra
    text, after = no_emoji(text), no_emoji(after)
    # «Игроки дня» — отдельным сообщением сразу следом за итогами НХЛ
    players = no_emoji(str(payload.get('after_text') or '').strip())[:4000] if kind != 'matchi' else ''
    # куда «Игроки дня»: "after_chats" (в нём и каналы КХЛ — там лучшие игроки КХЛ), нет — туда же, куда итоги
    pchats = [str(c).strip() for c in (payload.get('after_chats') or chats) if str(c or '').strip()] if players else []
    print('подпись:\n' + text + ('\n--- отдельным сообщением:\n' + after if after else '')
          + ('\n--- следом:\n' + players if players else ''))

    # «Матчи дня» и «Итоги дня»: больше 5 матчей — несколько постеров одним постом-альбомом
    # (все одного размера, ячейки на одном уровне, на продолжении крупно «JARVIS | KHL/NHL»)
    groups = split_matchi(items)
    rows = max(len(g) for g in groups)
    outs = [os.path.join(os.getcwd(), '%s_%s%s.jpg' % (kind, league.lower(), '_%d' % (k + 1) if len(groups) > 1 else ''))
            for k in range(len(groups))]
    out = outs[0]
    drawn = True
    try:
        if league == 'NHL':
            import nhl
            nhl.register()
        for grp, path in zip(groups, outs):
            if kind == 'matchi':
                import preview_ice as pv
                pv.render(grp, path, style='columns', league=league, date_title=date_title or None, cont=path != outs[0], rows=rows)
            else:
                import results_ice2 as ri
                ri.render(grp, path, variant=10, league=league, date_title=date_title or None, cont=path != outs[0], rows=rows)
        print('нарисовано:', ', '.join(outs), '— матчей', '+'.join(str(len(g)) for g in groups))
    except Exception as e:                      # noqa: BLE001 — любая ошибка рисования: публикуем текст
        drawn = False
        print('картинка не нарисовалась:', repr(e))

    token = os.environ.get('TG_BOT_TOKEN')
    pl = payload.get('players') if kind != 'matchi' else None      # постер «Игроки дня» — следом за итогами
    if not token:
        if pl:
            players_post(None, pl, date_title, chats)
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        return
    if not chats:
        raise SystemExit('не указан чат (chat / chats) для отправки')
    errors = []
    for c in chats:
        try:
            if drawn:
                if len(outs) > 1:
                    send_album(token, c, outs, text)
                else:
                    send_photo(token, c, out, text)
                if after:
                    send_message(token, c, after)
            else:
                send_message(token, c, text + ('\n\n' + after if after else ''))
            if c in pchats:
                send_message(token, c, players)
            print('отправлено в', c)
        except SystemExit as e:
            errors.append('%s: %s' % (c, e))
    for c in pchats:                            # «Игроки дня» в чаты, куда итоги этой лиги не идут (канал и группа КХЛ)
        if c in chats:
            continue
        try:
            send_message(token, c, players)
            print('«Игроки дня» отправлены в', c)
        except SystemExit as e:
            errors.append('%s: %s' % (c, e))
    if pl:
        errors += players_post(token, pl, date_title, chats)
    if errors or not drawn:
        raise SystemExit('; '.join(errors) or 'картинка не нарисовалась — опубликован текст')


if __name__ == '__main__':
    main()
