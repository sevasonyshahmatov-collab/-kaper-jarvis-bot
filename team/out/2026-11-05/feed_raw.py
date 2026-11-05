"""Сырой HTML постов-ответов (итоги экспрессов) — понять разметку подписи."""
import os, re, sys, urllib.request
for before in (1366, 1406):
    req = urllib.request.Request('https://t.me/s/jarvibet?before=%d' % before, headers={'User-Agent': 'Mozilla/5.0'})
    page = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
    for n in (1364, 1404, 1395):
        i = page.find('data-post="jarvibet/%d"' % n)
        if i < 0:
            continue
        blk = page[i:i + 6000]
        blk = re.sub(r'background-image:url\([^)]*\)', 'BG', blk)
        print('RAWPOST', n)
        for ln in re.findall(r'<[^>]*class="[^"]*(?:reply|message_text|message_photo|caption)[^"]*"[^>]*>[^<]{0,120}', blk):
            print('RAW', n, ln[:300])
