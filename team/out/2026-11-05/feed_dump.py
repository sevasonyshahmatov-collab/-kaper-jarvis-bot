"""Посты канала про футбол, экспрессы и итоги (с 01.10) → пометки FD_n (gzip+base64 JSON) — разбор формата для сайта."""
import base64, gzip, json, os, re, sys
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
import channel
from data import MSK
channel.MAX_PAGES = 60
html = {}
fetch = channel.fetch
def f2(before=None):
    p = fetch(before)
    html[before] = p
    return p
channel.fetch = f2
posts, pages = channel.feed(datetime(2026, 10, 1, tzinfo=MSK))
KW = re.compile(r'(?i)экспресс|итог|футбол|лига чемпионов|лига европы|апл|ла лига|серия а|бундеслига|лига 1|рпл')
out = []
for p in posts:
    t = ' '.join(x for x, _ in p['text'])
    if KW.search(t):
        out.append(dict(id=p['id'], posted=p['posted'].isoformat() if p['posted'] else None, media=p['media'], text=[x for x, _ in p['text']]))
# ответы: номер поста, на который ответ
rep = {}
for pg in html.values():
    for m in re.finditer(r'data-post="jarvibet/(\d+)"(.*?)(?=data-post="jarvibet/|\Z)', pg or '', re.S):
        r = re.search(r'tgme_widget_message_reply[^>]*href="https://t\.me/jarvibet/(\d+)"', m.group(2))
        if r:
            rep[m.group(1)] = int(r.group(1))
for o in out:
    o['reply'] = rep.get(str(o['id']))
print('FEED posts %d pages %d kept %d replies %d' % (len(posts), pages, len(out), len(rep)))
b = base64.b64encode(gzip.compress(json.dumps(out, ensure_ascii=False).encode())).decode()
parts = [b[i:i + 3500] for i in range(0, len(b), 3500)]
for i, s in enumerate(parts):
    print('FDX_%d %s' % (i + 1, s), flush=True)
