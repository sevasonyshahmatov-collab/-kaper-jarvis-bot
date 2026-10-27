# Ролики YouTube за 30 дней — для разбора спада просмотров (владелец 27.10). Вывод — пометками ::notice::.
import json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
import requests, report  # noqa: E402
rows, src = [], ''
try:
    rows = report.yt_videos(30); src = 'api'
except Exception as e:  # noqa: BLE001
    print('::notice title=YTERR::api %r' % str(e)[:300])
if not rows:   # без права чтения: открытая страница «Shorts» канала
    hdr = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'ru-RU,ru'}
    h = requests.get('https://www.youtube.com/@jarvibet/shorts', headers=hdr, cookies={'CONSENT': 'YES+1'}, timeout=30).text
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', h, re.S)
    data = json.loads(m.group(1)) if m else {}
    def walk(o):
        if isinstance(o, dict):
            if 'shortsLockupViewModel' in o:
                v = o['shortsLockupViewModel']
                yield dict(id=(v.get('entityId') or '').replace('shorts-shelf-item-', ''),
                           title=(v.get('overlayMetadata') or {}).get('primaryText', {}).get('content', ''),
                           views=(v.get('overlayMetadata') or {}).get('secondaryText', {}).get('content', ''))
            for x in o.values():
                yield from walk(x)
        elif isinstance(o, list):
            for x in o:
                yield from walk(x)
    rows = list(walk(data)); src = 'page'
    print('::notice title=YTPAGE::len %d, shorts %d, subs %s' % (len(h), len(rows),
          (re.search(r'"subscriberCountText":\{[^}]*?"content":"([^"]+)"', h) or re.search(r'(\d[\d\s,.]*\s*(?:тыс\.\s*)?подписчик\w*)', h) or [None, '?'])[1]))
lines = []
for v in rows:
    at = v.get('at').strftime('%m-%d %H') if v.get('at') else ''
    lines.append('%s|%s|%s|%s|%s' % (at, v.get('views'), v.get('likes', ''), v.get('tpl') or '', (v.get('title') or '')[:60]))
print('::notice title=YTSRC::%s %d' % (src, len(lines)))
for k in range(0, min(len(lines), 360), 40):
    print('::notice title=YT%d::%s' % (k // 40, '%0A'.join(lines[k:k + 40]).replace('%', '%25').replace('%250A', '%0A')))
if rows and src == 'api':
    vid = rows[0]['id']
    j = report._get(report.API + 'videos', part='snippet', id=vid)['items'][0]['snippet']
    print('::notice title=YTMETA::%s' % json.dumps(dict(t=j['title'], d=j.get('description', '')[:900], tags=j.get('tags')), ensure_ascii=False).replace('%', '%25').replace('\n', ' / '))
