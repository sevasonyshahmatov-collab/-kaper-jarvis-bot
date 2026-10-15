# -*- coding: utf-8 -*-
"""Проверка задания с постами-прогнозами перед отправкой владельцу: формат поста (team/POSTS.md, «Прогноз на матч»),
лимиты Telegram, разметка, номера, запретные слова. Ошибки — код выхода 1 (задание не запускать, пока не исправлено).
Запуск: python team/picks/check.py team/out/<день>/picks_khl.json"""
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


def main(path):
    job = json.load(open(path, encoding='utf-8'))
    errs, warns, pids = [], [], []
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
        if m.get('type') != 'photo' or not m.get('files'):
            errs.append('%s: пост — фото с подписью (Versus)' % where)
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
        if not re.search(r'#прогноз(КХЛ|НХЛ) #(КХЛ|НХЛ)\s*$', text):
            errs.append('%s: в конце хэштеги «#прогнозКХЛ #КХЛ» / «#прогнозНХЛ #НХЛ»' % where)
        low = html.unescape(re.sub(r'<[^>]+>', '', text)).lower()
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
    for w in warns:
        print('ВНИМАНИЕ:', w)
    for e in errs:
        print('ОШИБКА:', e)
    print('постов: %d, ошибок: %d' % (len(pids), len(errs)))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
