# -*- coding: utf-8 -*-
"""Сборка наборов эмодзи для публикации: PNG (make.py) и анимированные WEBM (anim.py) → team/emoji/build/,
список с заменами → build/manifest.json (его читает publish.py в Actions).
Наборы: «JARVIS · хоккей» (base + цифры + шкала) и «JARVIS · клубы» (КХЛ + НХЛ).
Запуск: python team/emoji/build.py [папка PNG] [папка WEBM]"""
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
OUT = os.path.join(HERE, 'build')
SETS = [('jarvibet_emoji', 'JARVIS · хоккей', ('base', 'score', 'bar')),
        ('jarvibet_clubs', 'JARVIS · клубы КХЛ и НХЛ', ('khl', 'nhl'))]

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
man = {'sets': []}
for name, title, groups in SETS:
    items = []
    for g in groups:
        for key in make.GROUPS[g]:
            emoji = make.EMOJI[key][1]
            webm = os.path.join(WEBM, key + '.webm')
            if os.path.exists(webm):
                shutil.copy(webm, os.path.join(OUT, key + '.webm'))
                items.append({'key': key, 'file': key + '.webm', 'format': 'video', 'emoji': emoji})
            else:
                shutil.copy(os.path.join(PNG, key + '.png'), os.path.join(OUT, key + '.png'))
                items.append({'key': key, 'file': key + '.png', 'format': 'static', 'emoji': emoji})
    man['sets'].append({'name': name, 'title': title, 'items': items})
    print(name, len(items), 'шт., из них анимированных', sum(i['format'] == 'video' for i in items))
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
