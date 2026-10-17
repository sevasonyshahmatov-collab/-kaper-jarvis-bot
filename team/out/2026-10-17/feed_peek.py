# -*- coding: utf-8 -*-
"""Проверка ленты @jarvibet: последние посты с номерами, временем, первой строкой и ответом-на (вышли ли итоги 17.10)."""
import os, re, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
import channel
page = channel.fetch()
for p in channel.parse_page(page):
    first = p['text'][0][0] if p['text'] else ''
    print('FEED %d | %s | %s | %s' % (p['id'], p['posted'] and p['posted'].strftime('%d.%m %H:%M'), first[:70], p['media']), flush=True)
for block in page.split('tgme_widget_message_wrap')[1:]:
    n = re.search(r'data-post="jarvibet/(\d+)"', block)
    r = re.search(r'tgme_widget_message_reply[^>]*href="[^"]*/(\d+)"', block)
    if n and r:
        print('REPLY %s → %s' % (n.group(1), r.group(1)), flush=True)
