# -*- coding: utf-8 -*-
"""Сборка наборов эмодзи для публикации: PNG (make.py), анимированные WEBM (anim.py) и «живые» плашки клубов
(clubs_anim.py) → team/emoji/build/, список → build/manifest.json (его читает publish.py в Actions).
Наборы: «JARVIS · хоккей» (base + цифры + шкала) и «JARVIS · клубы» (КХЛ + НХЛ).

Плашки клубов уже опубликованы статичными, поэтому их WEBM идут с пометкой "replace": publish.py заменит
стикер на той же позиции (replaceStickerInSet) — ссылка t.me/addemoji/jarvibet_clubs_… не меняется.
Перед перезаписью сверяет порядок и эмодзи с прежним build/manifest.json (= опубликованным): расхождение — ошибка.

Запуск: python team/emoji/build.py [папка PNG] [папка WEBM] [папка WEBM клубов]"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make  # noqa: E402

SCR = '/tmp/claude-0/-home-user--kaper-jarvis-bot/750ccff3-fed4-56c4-8b4f-e7d578ed1f4d/scratchpad'
PNG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, 'emoji')
WEBM = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SCR, 'emoji_anim')
CLUBS = sys.argv[3] if len(sys.argv) > 3 else os.path.join(SCR, 'owner8_9', 'clubs_anim')
OUT = os.path.join(HERE, 'build')
SETS = [('jarvibet_emoji', 'JARVIS · хоккей', ('base', 'score', 'bar')),
        ('jarvibet_clubs', 'JARVIS · клубы КХЛ и НХЛ', ('khl', 'nhl'))]
REPLACE = {'jarvibet_clubs'}                 # опубликованы статичными → анимированные заменяют их на месте

old = {}
if os.path.exists(os.path.join(OUT, 'manifest.json')):
    with open(os.path.join(OUT, 'manifest.json'), encoding='utf-8') as f:
        old = {s['name']: s for s in json.load(f)['sets']}

man = {'sets': []}
files = {}
for name, title, groups in SETS:
    items = []
    for g in groups:
        for key in make.GROUPS[g]:
            emoji = make.EMOJI[key][1]
            webm = os.path.join(CLUBS if name in REPLACE else WEBM, key + '.webm')
            if os.path.exists(webm):
                files[key + '.webm'] = webm
                it = {'key': key, 'file': key + '.webm', 'format': 'video', 'emoji': emoji}
                if name in REPLACE:
                    it['replace'] = True
            else:
                files[key + '.png'] = os.path.join(PNG, key + '.png')
                it = {'key': key, 'file': key + '.png', 'format': 'static', 'emoji': emoji}
            items.append(it)
    prev = old.get(name)
    if prev:                                  # порядок и эмодзи должны совпасть с опубликованным набором
        a = [(i['key'], i['emoji']) for i in prev['items']]
        b = [(i['key'], i['emoji']) for i in items]
        if a != b[:len(a)]:
            diff = [(x, y) for x, y in zip(a, b) if x != y][:10]
            raise SystemExit('%s: порядок/эмодзи отличаются от опубликованного: %s' % (name, diff))
    man['sets'].append({'name': name, 'title': title, 'sticker_type': 'custom_emoji', 'items': items})
    print(name, len(items), 'шт., из них анимированных', sum(i['format'] == 'video' for i in items),
          '· к замене на месте', sum(bool(i.get('replace')) for i in items))

missing = [p for p in files.values() if not os.path.exists(p)]
if missing:
    raise SystemExit('нет файлов: %s' % missing[:5])
# статичные PNG, которые заменяются видео, больше не нужны в build/ — убираем
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
for dst, src in files.items():
    shutil.copy(src, os.path.join(OUT, dst))
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
