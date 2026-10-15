# -*- coding: utf-8 -*-
"""Наборы эмодзи канала в Telegram через бота (Bot API createNewStickerSet, sticker_type=custom_emoji).
Владелец наборов — владелец канала @jarvibet (создатель канала по getChatAdministrators), имя набора —
<set>_by_<имя бота>. Файлы и замены — team/emoji/build/manifest.json (собирает team/emoji/build.py).
Набор уже есть — дописываем только недостающие по порядку (повторный запуск безопасен).
В конце бот присылает владельцу ссылки t.me/addemoji/<имя>.
Запуск в Actions заданием команды: "make": ["team/emoji/publish.py"] (нужен TG_BOT_TOKEN)."""
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, 'team', 'emoji', 'build')
TOKEN = os.environ.get('TG_BOT_TOKEN')
CHANNEL = '@jarvibet'


def api(method, data=None, files=None):
    for k in range(4):
        r = requests.post('https://api.telegram.org/bot%s/%s' % (TOKEN, method), data=data or {}, files=files, timeout=120)
        j = r.json()
        if j.get('ok'):
            return j['result']
        ra = (j.get('parameters') or {}).get('retry_after')
        if ra and k < 3:
            time.sleep(ra + 1)
            continue
        raise RuntimeError('%s: %s' % (method, j.get('description')))


def sticker(item, key):
    return {'sticker': 'attach://' + key, 'format': item['format'], 'emoji_list': [item['emoji']]}


def open_file(item):
    return open(os.path.join(BUILD, item['file']), 'rb')


def main():
    if not TOKEN:
        print('TG_BOT_TOKEN не задан — наборы не создаю')
        return
    man = json.load(open(os.path.join(BUILD, 'manifest.json'), encoding='utf-8'))
    bot = api('getMe')['username']
    owner = next(m['user']['id'] for m in api('getChatAdministrators', {'chat_id': CHANNEL}) if m['status'] == 'creator')
    links, errors = [], []
    for s in man['sets']:
        name = '%s_by_%s' % (s['name'], bot)
        items = s['items']
        try:
            have = len(api('getStickerSet', {'name': name})['stickers'])
            print('набор %s уже есть: %d из %d' % (name, have, len(items)))
        except RuntimeError:
            first = items[:50]
            files = {'f%d' % i: open_file(it) for i, it in enumerate(first)}
            try:
                api('createNewStickerSet', {'user_id': owner, 'name': name, 'title': s['title'], 'sticker_type': 'custom_emoji',
                                            'stickers': json.dumps([sticker(it, 'f%d' % i) for i, it in enumerate(first)],
                                                                   ensure_ascii=False)}, files)
            finally:
                for f in files.values():
                    f.close()
            have = len(first)
            print('создан набор %s: %d' % (name, have))
        for it in items[have:]:
            with open_file(it) as f:
                try:
                    api('addStickerToSet', {'user_id': owner, 'name': name,
                                            'sticker': json.dumps(sticker(it, 'f0'), ensure_ascii=False)}, {'f0': f})
                except RuntimeError as e:
                    errors.append('%s %s: %s' % (name, it['file'], e))
                    print('ОШИБКА', errors[-1])
                    continue
            time.sleep(0.4)
        links.append('%s — https://t.me/addemoji/%s (%d шт.)' % (s['title'], name, len(items)))
        print('готово:', links[-1])
    text = 'Наборы эмодзи канала готовы (владелец — вы):\n' + '\n'.join(links)
    if errors:
        text += '\n\nНе добавились: %d — команда поправит.' % len(errors)
    api('sendMessage', {'chat_id': owner, 'text': text, 'disable_web_page_preview': 'true'})
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
