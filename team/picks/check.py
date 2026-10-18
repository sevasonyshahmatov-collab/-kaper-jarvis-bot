# -*- coding: utf-8 -*-
"""Проверка задания с постами-прогнозами перед отправкой владельцу: формат поста (team/POSTS.md, «Прогноз на матч»),
лимиты Telegram, разметка, номера, запретные слова, разнообразие постов одного запуска («Не под копирку»). Ошибки — код выхода 1 (задание не запускать, пока не исправлено).
Запуск: python team/picks/check.py team/out/<день>/picks_khl.json
Следующий свободный номер поста на день: python team/picks/check.py --next 1610 → 1610-4"""
import glob
import html
import json
import re
import sys

MONTHS = 'января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря'
HEAD = re.compile(r'^(КХЛ|НХЛ) · \d{1,2} (%s) · \d\d:\d\d МСК$' % MONTHS)
TAGS = {'b', 'i', 'u', 's', 'blockquote', 'code', 'pre', 'a', 'tg-spoiler'}
BANNED = ('джарвис', 'jarvis', 'гарант', 'на момент публикации', '18+', 'мнение, а не', 'промокод')
CAREFUL = ('таблиц', 'букмекер', 'фонбет', 'pinnacle', 'пинакл')     # можно, но проверить: не аналитическая таблица и не реклама
EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]')


def tags_ok(text):
    stack = []
    for close, name in re.findall(r'<(/?)([a-z\-]+)[^>]*>', text):
        if name not in TAGS:
            return 'тег <%s> Telegram не поймёт' % name
        if close:
            if not stack or stack.pop() != name:
                return 'теги не закрыты по порядку (</%s>)' % name
        else:
            stack.append(name)
    return 'не закрыт <%s>' % stack[-1] if stack else ''


def plain(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


def head(s, k=2):
    return ' '.join(re.findall(r'[\w\-]+', s.lower())[:k])


def variety(posts, errs, warns):
    """Посты одного запуска не должны быть под копирку (владелец 15.10 и 18.10, team/POSTS.md «Не под копирку»)."""
    n = len(posts)
    if n < 2:
        return
    lim = max(1, n // 4)
    # риск словами: «риск», «единственное, что смущает», «опасность», «проблема», «может помешать»… (владелец 18.10)
    rx = (r'риск|единственн|опасн|проблем|смущает|настораживает|слабое место|может помешать|может подвести'
          r'|не всё так гладко|подвох|ахиллес|страшно|пугает|беспоко|сомнени|оговорк|но если\b')
    risky = [p['pid'] for p in posts if re.search(rx, p['q'].lower())]
    if len(risky) > lim:
        errs.append('про риск / «единственная проблема» в %d постах из %d (%s) — только иногда: не больше %d, '
                    'остальные вообще без оговорок' % (len(risky), n, ', '.join(risky), lim))
    for p in posts:
        last = re.split(r'(?<=[.!?…])\s+', p['q'].strip())[-1].lower()
        if re.search(rx, last):
            errs.append('пост %s: цитата кончается риском / оговоркой — так не заканчиваем, последняя мысль — за ставку' % p['pid'])
        if len(p['q']) < 420:
            errs.append('пост %s: обоснование %d знаков — коротко; нужно 7–8 строк (от 420 знаков): '
                        'что я посмотрел и почему пришёл к этой ставке' % (p['pid'], len(p['q'])))
        if not re.search(r'(?<!\w)(я|мне|меня|мной|мой|моя|моё|мое|мои|по-моему|беру|ставлю)(?!\w)', p['q'].lower()):
            errs.append('пост %s: не от первого лица — пишем от лица владельца: «я посмотрел», «я решил», «беру»' % p['pid'])
    for key, what in (('q', 'цитаты начинаются'), ('c', 'концовки начинаются')):
        seen = {}
        for p in posts:
            h = head(p[key])
            if h:
                seen.setdefault(h, []).append(p['pid'])
        for h, ids in seen.items():
            if len(ids) > 1:
                errs.append('%s одинаково — «%s…» (%s): переписать' % (what, h, ', '.join(ids)))
    asks = [p['pid'] for p in posts if p['c'].rstrip().endswith('?')]
    if n >= 3 and len(asks) > lim:
        errs.append('концовка-вопрос в %d постах из %d (%s) — не больше %d' % (len(asks), n, ', '.join(asks), lim))
    many = [p['pid'] for p in posts if len(re.findall(r'\d+(?:[,.:]\d+)?', p['q'])) >= 5]
    if n >= 3 and len(many) == n:
        warns.append('в каждом посте много цифр — в части постов хватит одной-двух и мысли')


def main(path):
    job = json.load(open(path, encoding='utf-8'))
    errs, warns, pids, posts = [], [], [], []
    used = set()
    for f in glob.glob('team/out/**/*.json', recursive=True):
        if f.replace('\\', '/') == path.replace('\\', '/'):
            continue
        try:
            for m in json.load(open(f, encoding='utf-8')).get('messages') or []:
                if m.get('pid'):
                    used.add(str(m['pid']))
        except (ValueError, AttributeError):
            pass
    for i, m in enumerate(job.get('messages') or [], 1):
        text = str(m.get('text') or '')
        where = 'сообщение %d' % i
        if m.get('to') != 'owner':
            errs.append('%s: отправлять только владельцу ("to": "owner")' % where)
        bad = tags_ok(text)
        if bad:
            errs.append('%s: %s' % (where, bad))
        if m.get('type') == 'text' and len(text) > 4000:
            errs.append('%s: текст %d знаков, предел 4000' % (where, len(text)))
        if m.get('buttons') != 'post':
            continue
        pid = str(m.get('pid') or '')
        where = 'пост %s' % (pid or i)
        if not re.match(r'^\d{4}-\d+$', pid):
            errs.append('%s: номер должен быть ММДД-N' % where)
        if pid in pids or pid in used:
            errs.append('%s: номер уже занят' % where)
        pids.append(pid)
        if m.get('type') != 'animation' or not str((m.get('files') or [''])[0]).endswith('.mp4'):
            errs.append('%s: пост — анимированный баннер: "type": "animation", файл .mp4 (владелец 15.10)' % where)
        if not m.get('html'):
            errs.append('%s: нужен "html": true' % where)
        if len(text) > 1024:
            errs.append('%s: подпись %d знаков вместе с тегами, предел 1024 — сократить' % (where, len(text)))
        lines = text.split('\n')
        if not HEAD.match(lines[0]):
            errs.append('%s: первая строка «КХЛ · 16 октября · 19:00 МСК» (по ней бот ставит выход за 1,5 ч до матча), сейчас «%s»'
                        % (where, lines[0]))
        if len(lines) < 2 or not re.match(r'^<b>[^<]+ — [^<]+</b>$', lines[1]):
            errs.append('%s: вторая строка — матч жирным «<b>Хозяева — Гости</b>»' % where)
        if not re.search(r'^Прогноз: <b>[^<]+</b>$', text, re.M):
            errs.append('%s: нет строки «Прогноз: <b>…</b>»' % where)
        km = re.search(r'^Кэф: <b>(\d+),(\d\d)</b>$', text, re.M)
        if not km:
            errs.append('%s: нет строки «Кэф: <b>1,67</b>» (запятая, две цифры)' % where)
        elif float(km.group(1) + '.' + km.group(2)) < 1.6:
            warns.append('%s: кэф ниже 1,6 — правило владельца: от 1,6' % where)
        if '<blockquote>' not in text:
            errs.append('%s: нет цитаты <blockquote> с обоснованием' % where)
        if not re.search(r'^<i>.+</i>$', text, re.M):
            errs.append('%s: нет строки-завершения курсивом' % where)
        want = '#%s #прогноз #jarvibet' % ('кхл' if lines[0].startswith('КХЛ') else 'нхл')
        if not text.rstrip().endswith('\n' + want):
            errs.append('%s: последней строкой хэштеги «%s» — лига из шапки, без даты (владелец 15.10)' % (where, want))
        low = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'#\w+', '', text))).lower()   # хэштеги (#jarvibet) не проверяем
        for w in BANNED:
            if w in low:
                errs.append('%s: «%s» — в постах не пишем' % (where, w))
        for w in CAREFUL:
            if w in low:
                warns.append('%s: «%s» — проверить (аналитическую таблицу и букмекеров в постах не упоминаем)' % (where, w))
        if EMOJI.search(text):
            errs.append('%s: эмодзи в подписи — в канале без эмодзи' % where)
        if not m.get('vs'):
            warns.append('%s: нет поля "vs" — баннер не нарисуется banners.py' % where)
        q = re.search(r'<blockquote>(.*?)</blockquote>', text, re.S)
        c = re.search(r'^<i>(.+)</i>$', text, re.M)
        posts.append(dict(pid=pid or str(i), q=plain(q.group(1)) if q else '', c=plain(c.group(1)) if c else ''))
    variety(posts, errs, warns)
    for w in warns:
        print('ВНИМАНИЕ:', w)
    for e in errs:
        print('ОШИБКА:', e)
    print('постов: %d, ошибок: %d' % (len(pids), len(errs)))
    return 1 if errs else 0


def next_pid(mmdd):
    """Номера ММДД-N из всех заданий team/out и строк INBOX — следующий свободный."""
    n = 0
    for f in glob.glob('team/out/**/*.json', recursive=True) + ['team/INBOX.md']:
        try:
            for x in re.findall(r'\b%s-(\d+)\b' % re.escape(mmdd), open(f, encoding='utf-8').read()):
                n = max(n, int(x))
        except OSError:
            pass
    return '%s-%d' % (mmdd, n + 1)


if __name__ == '__main__':
    if sys.argv[1] == '--next':
        print(next_pid(sys.argv[2]))
        sys.exit(0)
    sys.exit(main(sys.argv[1]))
