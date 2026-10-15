"""Видео YouTube по просьбе владельца (15.10): название, описание, главы и субтитры — в лог Actions (из облачной сессии YouTube не открывается).
Запуск: python team/out/2026-10-15/yt_fetch.py <id>"""
import json
import re
import subprocess
import sys

VID = sys.argv[1] if len(sys.argv) > 1 else 'XNW5xUFIpBg'
URL = 'https://www.youtube.com/watch?v=' + VID
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'yt-dlp', 'youtube-transcript-api'], check=False)
try:
    info = json.loads(subprocess.run(['yt-dlp', '-J', '--skip-download', URL], capture_output=True, text=True, timeout=180).stdout or '{}')
    print('YTMETA ' + json.dumps({k: info.get(k) for k in ('title', 'channel', 'upload_date', 'duration', 'view_count', 'description', 'chapters', 'tags')},
                                  ensure_ascii=False))
except Exception as e:  # noqa: BLE001
    print('YTERR meta', repr(e))
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    tr = api.fetch(VID, languages=['ru', 'en', 'uk'])
    text = ' '.join(s.text for s in tr)
    for i in range(0, len(text), 3000):
        print('YTTEXT ' + text[i:i + 3000])
except Exception as e:  # noqa: BLE001
    print('YTERR transcript', repr(e)[:500])
    r = subprocess.run(['yt-dlp', '--skip-download', '--write-auto-subs', '--write-subs', '--sub-langs', 'ru,en', '--sub-format', 'vtt',
                        '-o', 'yt.%(ext)s', URL], capture_output=True, text=True, timeout=180)
    print('YTDLP', r.stderr[-800:])
    import glob
    for f in glob.glob('yt*.vtt'):
        raw = open(f, encoding='utf-8').read()
        lines, prev = [], ''
        for ln in raw.splitlines():
            ln = re.sub(r'<[^>]+>', '', ln).strip()
            if not ln or '-->' in ln or ln.startswith(('WEBVTT', 'Kind:', 'Language:')) or ln == prev:
                continue
            lines.append(ln); prev = ln
        text = ' '.join(lines)
        for i in range(0, len(text), 3000):
            print('YTTEXT %s %s' % (f, text[i:i + 3000]))
