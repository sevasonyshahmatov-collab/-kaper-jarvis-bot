# -*- coding: utf-8 -*-
"""Последние посты @jarvibet с публичной веб-страницы канала (t.me/s/jarvibet): номер поста и начало текста.
Нужно, чтобы найти номер поста 1510-2 (Северсталь — Локомотив) в канале и увидеть, что в нём сейчас. Только чтение.
Облачная сессия до t.me не достаёт, Actions — достаёт: печатает «TGPOST <номер> | <текст>» в лог."""
import html
import re

import requests

r = requests.get('https://t.me/s/jarvibet', headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
print('TGPEEK статус', r.status_code, len(r.text), flush=True)
for block in r.text.split('tgme_widget_message_wrap')[1:]:
    num = re.search(r'data-post="jarvibet/(\d+)"', block)
    txt = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
    edited = 'edited' in block
    t = html.unescape(re.sub(r'<br\s*/?>', ' / ', txt.group(1))) if txt else ''
    t = re.sub(r'<[^>]+>', '', t)
    print('TGPOST %s%s | %s' % (num.group(1) if num else '?', ' (изменён)' if edited else '', t[:400]), flush=True)
