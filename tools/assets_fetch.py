# -*- coding: utf-8 -*-
"""Новые материалы для роликов (владелец 20.10: «Mixkit и LottieFiles — берём»). Запускает .github/workflows/assets-fetch.yml.

1) Mixkit — бесплатная музыка (Mixkit Stock Music Free License: коммерция, YouTube и Instagram, без указания автора; нельзя
   выдавать трек за свой и регистрировать в Content ID). Со страниц жанров берём треки, режем на кандидатов по настроению
   (MOODS), считаем темп и дроп (render/track_sync.analyze), лучшие шифруем TRACKS_KEY в tracks/mx_<id>.mp3.enc ветки
   треков (как tools/tracks_inbox/intake.sh) и пишем tracks/mixkit.json (название, ссылка, темп, дроп). Владельцу — по
   20 с вокруг дропа каждого, на слух. Открытыми треки никуда не кладём.
2) LottieFiles — бесплатные анимации (Lottie Simple License: коммерция без указания автора). Со страниц
   lottiefiles.com/free-animations/<слово> — первые подходящие json/.lottie (rlottie открывает, ≤ 600 КБ) →
   render/reels/lottie/<слово>_<n>.json + лист превью render/reels/lottie/_sheet.png; коммит в рабочую ветку.

    python tools/assets_fetch.py [mixkit|lottie|all|video]
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'render'))
HDR = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 '
                     'Safari/605.1.15', 'Accept-Language': 'en'}
TB = 'claude/team-dev-tracks-v2'
MOODS = {   # настроение → страницы Mixkit; для какого шаблона
    'simulate': (['tag/suspense', 'tag/cinematic', 'tag/epic', 'electronica'], '«10 000 симуляций»'),
    'numday': (['hip-hop', 'tag/trap', 'tag/drums', 'tag/energetic'], '«Цифра дня»'),
}
PER_MOOD = 3
LOTTIE_WORDS = ['success', 'checkmark', 'hockey', 'fire', 'trophy', 'confetti', 'chart', 'stopwatch', 'target', 'loading']
LOTTIE_PER = 2


def get(url, **kw):
    r = requests.get(url, headers=HDR, timeout=40, **kw)
    r.raise_for_status()
    return r


def mixkit_list(page):
    """Страница Mixkit → [(id, название, mp3)]."""
    html = get('https://mixkit.co/free-stock-music/%s/' % page).text
    urls = re.findall(r'https://assets\.mixkit\.co/[^"\'\s<>]+?\.mp3', html)
    print('MIXKIT %s: %d ссылок mp3, пример %s' % (page, len(urls), urls[:2]), flush=True)
    if not urls:
        print('MIXKITRAW', re.sub(r'\s+', ' ', html[html.find('<main'):][:1500]), flush=True)
    out, seen = [], set()
    for u in urls:
        m = re.search(r'(\d{2,6})(?:\.mp3|/)', u)
        tid = m.group(1) if m else str(abs(hash(u)) % 10 ** 6)
        if tid in seen:
            continue
        seen.add(tid)
        i = html.find(u)
        near = html[max(0, i - 3000):i]
        t = re.findall(r'(?:data-[a-z-]*title|aria-label|title)="([^"]{3,60})"', near) or \
            re.findall(r'>([A-Z][A-Za-z0-9 \'&-]{2,40})</(?:h\d|a|div|p)>', near)
        name = t[-1].strip() if t else re.sub(r'^mixkit-|-\d+$', '', os.path.basename(u)[:-4]).replace('-', ' ')
        out.append((tid, name, u))
    return out


def mixkit():
    import numpy as np
    import track_sync
    key = ''.join(os.environ.get('TRACKS_KEY', '').split())
    if not key:
        sys.exit('нет секрета TRACKS_KEY')
    tmp = tempfile.mkdtemp()
    subprocess.run(['git', 'fetch', '-q', 'origin', '%s:refs/remotes/origin/%s' % (TB, TB)], cwd=ROOT, check=True)
    have = subprocess.run(['git', 'ls-tree', '--name-only', 'origin/%s' % TB, 'tracks/'], cwd=ROOT, capture_output=True,
                          text=True).stdout.split()
    picked, used = [], set()
    for mood, (pages, tpl) in MOODS.items():
        cands = []
        for p in pages:
            try:
                cands += [c for c in mixkit_list(p) if c[0] not in used]
            except Exception as e:  # noqa: BLE001
                print('MIXKITERR %s: %r' % (p, e), flush=True)
        scored = []
        for tid, name, url in cands[:14]:
            if 'tracks/mx_%s.mp3.enc' % tid in have or tid in used:
                continue
            used.add(tid)
            mp3 = os.path.join(tmp, 'mx_%s.mp3' % tid)
            try:
                with open(mp3, 'wb') as f:
                    f.write(get(url).content)
                dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3],
                                           capture_output=True, text=True).stdout or 0)
                if dur < 50:
                    print('MX %s %s: короткий (%.0f с)' % (tid, name, dur), flush=True)
                    continue
                a = track_sync.analyze(mp3)
                drops = [d for d in a['drops'] if 6 <= d <= 75]
                if not drops:
                    print('MX %s %s: дропа нет' % (tid, name), flush=True)
                    continue
                x, sr = track_sync.load(mp3)
                d = drops[0]
                pre = np.sqrt((x[int((d - 4) * sr):int(d * sr)] ** 2).mean()) + 1e-6
                post = np.sqrt((x[int(d * sr):int((d + 6) * sr)] ** 2).mean())
                loud = np.sqrt((x ** 2).mean())
                score = float(post / pre) + float(loud) * 4
                print('MX %s %s: %.0f с, темп %s, дроп %.2f, удар %.2f' % (tid, name, dur, a['bpm'], d, post / pre), flush=True)
                scored.append((score, dict(id=tid, key='mx_%s' % tid, title=name, url=url, mood=mood, dur=round(dur, 1),
                                           bpm=a['bpm'], unit=a['unit'], drop=d, drops=a['drops'], start=a['start'])))
            except Exception as e:  # noqa: BLE001
                print('MXERR %s: %r' % (url, e), flush=True)
        scored.sort(key=lambda s: -s[0])
        picked += [s[1] for s in scored[:PER_MOOD]]
    if not picked:
        sys.exit('ни одного трека не подобрал')
    W = tempfile.mkdtemp()
    subprocess.run(['git', 'worktree', 'add', '-q', W, 'origin/%s' % TB], cwd=ROOT, check=True)
    os.makedirs(os.path.join(W, 'tracks'), exist_ok=True)
    env = dict(os.environ, TRACKS_KEY=key)
    for t in picked:
        subprocess.run(['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-pass', 'env:TRACKS_KEY', '-in',
                        os.path.join(tmp, t['key'] + '.mp3'), '-out', os.path.join(W, 'tracks', t['key'] + '.mp3.enc')],
                       check=True, env=env)
    meta = os.path.join(W, 'tracks', 'mixkit.json')
    old = json.load(open(meta)) if os.path.exists(meta) else []
    json.dump(old + picked, open(meta, 'w'), ensure_ascii=False, indent=1)
    subprocess.run(['git', 'add', 'tracks'], cwd=W, check=True)
    subprocess.run(['git', 'commit', '-qm', 'Mixkit tracks (free license), encrypted: ' + ' '.join(t['key'] for t in picked)],
                   cwd=W, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:' + TB], cwd=W, check=True)
    for t in picked:
        print('MIXKIT_PICK', json.dumps(t, ensure_ascii=False), flush=True)
    tok = os.environ.get('TG_BOT_TOKEN')
    if tok:
        import team_job as tj
        chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text='Новые треки с Mixkit (бесплатная лицензия, автора указывать не нужно) '
                                                           '— по 20 с вокруг дропа. Скажите, какие не нравятся.'))
        for k, t in enumerate(picked, 1):
            cut = os.path.join(tmp, t['key'] + '_cut.mp3')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(max(0, t['drop'] - 8)), '-t', '20', '-i',
                            os.path.join(tmp, t['key'] + '.mp3'), '-b:a', '128k', cut], check=True)
            with open(cut, 'rb') as f:
                requests.post('https://api.telegram.org/bot%s/sendAudio' % tok, timeout=60,
                              data=dict(chat_id=chat, title='%d. %s' % (k, t['title']), performer='Mixkit',
                                        caption='%d. %s — для %s, темп %s' % (k, t['title'], MOODS[t['mood']][1], t['bpm'])),
                              files=dict(audio=('%s.mp3' % t['key'], f, 'audio/mpeg')))


def lottie_json(raw):
    """json или .lottie (zip с animations/*.json) → dict."""
    if raw[:2] == b'PK':
        z = zipfile.ZipFile(io.BytesIO(raw))
        name = next(n for n in z.namelist() if n.startswith('animations/') and n.endswith('.json'))
        return json.loads(z.read(name))
    return json.loads(raw)


def lottie():
    from PIL import Image
    from rlottie_python import LottieAnimation
    D = os.path.join(ROOT, 'render', 'reels', 'lottie')
    os.makedirs(D, exist_ok=True)
    got, tiles = [], []
    for w in LOTTIE_WORDS:
        try:
            html = get('https://lottiefiles.com/free-animations/%s' % w).text
        except Exception as e:  # noqa: BLE001
            print('LOTTIEERR %s: %r' % (w, e), flush=True)
            continue
        urls = list(dict.fromkeys(re.findall(r'https://[a-z0-9.-]*(?:lottiefiles\.com|lottie\.host)/[^"\'\s<>\\]+?\.(?:json|lottie)',
                                             html)))
        print('LOTTIE %s: %d ссылок, пример %s' % (w, len(urls), urls[:2]), flush=True)
        n = 0
        for u in urls:
            if n >= LOTTIE_PER:
                break
            try:
                raw = get(u).content
                if len(raw) > 600_000:
                    continue
                j = lottie_json(raw)
                name = '%s_%d' % (w, n + 1)
                p = os.path.join(D, name + '.json')
                with open(p, 'w') as f:
                    json.dump(j, f, separators=(',', ':'))
                a = LottieAnimation.from_file(p)
                tot = a.lottie_animation_get_totalframe()
                strip = Image.new('RGBA', (4 * 200, 200), (40, 44, 60, 255))
                for k in range(4):
                    fr = a.render_pillow_frame(frame_num=int(tot * (k + 1) / 5), width=200, height=200)
                    strip.alpha_composite(fr.convert('RGBA'), (k * 200, 0))
                tiles.append((name, strip))
                got.append(dict(name=name, src=u, frames=tot, fps=a.lottie_animation_get_framerate(), kb=len(raw) // 1024))
                n += 1
            except Exception as e:  # noqa: BLE001
                print('LOTTIEERR %s: %r' % (u, e), flush=True)
                if os.path.exists(os.path.join(D, '%s_%d.json' % (w, n + 1))):
                    os.unlink(os.path.join(D, '%s_%d.json' % (w, n + 1)))
    if not got:
        sys.exit('ни одной анимации не скачал')
    from PIL import ImageDraw
    sheet = Image.new('RGBA', (900, 220 * len(tiles)), (20, 22, 30, 255))
    for i, (name, s) in enumerate(tiles):
        sheet.alpha_composite(s, (100, i * 220 + 10))
        ImageDraw.Draw(sheet).text((6, i * 220 + 100), name, fill=(255, 255, 255))
    sheet.convert('RGB').save(os.path.join(D, '_sheet.png'))
    with open(os.path.join(D, 'SOURCES.json'), 'w') as f:
        json.dump(dict(license='LottieFiles free animations — Lottie Simple License (коммерческое использование без указания автора)',
                       items=got), f, ensure_ascii=False, indent=1)
    for g in got:
        print('LOTTIE_GOT', json.dumps(g), flush=True)
    br = os.environ.get('GITHUB_REF_NAME')
    if br:
        subprocess.run(['git', 'add', D], cwd=ROOT, check=True)
        subprocess.run(['git', 'commit', '-qm', 'LottieFiles animations (free license) for reels: ' + ' '.join(g['name'] for g in got)],
                       cwd=ROOT, check=True)
        for _ in range(3):
            subprocess.run(['git', 'pull', '-q', '--rebase', 'origin', br], cwd=ROOT)
            if subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:' + br], cwd=ROOT).returncode == 0:
                break


VIDEO_PAGES = ['hockey', 'ice-skating', 'skating', 'ice', 'ice-rink', 'stadium', 'winter-sport']
VIDEO_WORDS = ('hockey', 'ice', 'skat', 'rink', 'puck', 'stadium', 'arena')


def video():
    """3) Видео для первого экрана сайта (владелец 23.10: «бесплатное стоковое видео хоккея»): Mixkit Stock Video Free License
    (коммерция без указания автора). Со страниц VIDEO_PAGES — ролики про лёд и хоккей → кадр из середины каждого → лист превью
    с номерами docs/site_video/sheet.jpg и список docs/site_video/candidates.json (номер, название, ссылка); коммит в рабочую
    ветку. Сами ролики в репозиторий не кладём — выбранный скачает задание сайта."""
    from PIL import Image, ImageDraw
    D = os.path.join(ROOT, 'docs', 'site_video')
    os.makedirs(D, exist_ok=True)
    found, seen = [], set()
    for page in VIDEO_PAGES:
        try:
            html = get('https://mixkit.co/free-stock-video/%s/' % page).text
        except Exception as e:  # noqa: BLE001 — такой страницы может не быть
            print('VIDEOERR %s: %r' % (page, e), flush=True)
            continue
        urls = re.findall(r'https://assets\.mixkit\.co/videos/[^"\'\s<>]+?\.mp4', html)
        slugs = dict((i, sl) for sl, i in re.findall(r'/free-stock-video/([a-z0-9-]+?)-(\d{3,6})/', html))
        print('VIDEO %s: %d mp4, %d карточек' % (page, len(urls), len(slugs)), flush=True)
        for u in urls:
            m = re.search(r'(\d{3,6})', u)
            vid = m.group(1) if m else u
            if vid in seen:
                continue
            title = slugs.get(vid, os.path.basename(u)[:-4]).replace('-', ' ')
            if not any(w in title.lower() for w in VIDEO_WORDS):
                continue
            seen.add(vid)
            found.append(dict(id=vid, title=title, src=u, page='https://mixkit.co/free-stock-video/%s-%s/' % (slugs.get(vid, ''), vid)))
    found = found[:16]
    tiles = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, v in enumerate(found, 1):
            mp4, jpg = os.path.join(tmp, '%d.mp4' % n), os.path.join(tmp, '%d.jpg' % n)
            try:
                with open(mp4, 'wb') as f:
                    f.write(get(v['src']).content)
                dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4],
                                           capture_output=True, text=True).stdout.strip() or 0)
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(dur * .4), '-i', mp4, '-frames:v', '1', '-vf', 'scale=480:-2', jpg], check=True)
                v.update(n=n, sec=round(dur, 1), mb=round(os.path.getsize(mp4) / 1e6, 1))
                tiles.append((n, v, Image.open(jpg).convert('RGB')))
            except Exception as e:  # noqa: BLE001
                print('VIDEOERR %s: %r' % (v['src'], e), flush=True)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols or 1
    sheet = Image.new('RGB', (cols * 480, rows * 300), (7, 18, 37))
    dr = ImageDraw.Draw(sheet)
    for k, (n, v, im) in enumerate(tiles):
        x, y = (k % cols) * 480, (k // cols) * 300
        im.thumbnail((480, 270))
        sheet.paste(im, (x, y))
        dr.rectangle((x, y, x + 44, y + 34), fill=(255, 201, 60))
        dr.text((x + 12, y + 8), str(n), fill=(7, 18, 37))
        dr.text((x + 6, y + 274), ('%s  ·  %s с' % (v['title'], v['sec']))[:70], fill=(234, 243, 255))
    sheet.save(os.path.join(D, 'sheet.jpg'), quality=88)
    with open(os.path.join(D, 'candidates.json'), 'w') as f:
        json.dump(dict(license='Mixkit Stock Video Free License — коммерческое использование без указания автора',
                       items=[v for _, v, _ in tiles]), f, ensure_ascii=False, indent=1)
    print('VIDEO_GOT %d' % len(tiles), flush=True)
    br = os.environ.get('GITHUB_REF_NAME')
    if br:
        subprocess.run(['git', 'add', D], cwd=ROOT, check=True)
        subprocess.run(['git', 'commit', '-qm', 'Mixkit videos (free license): candidates for the site hero'], cwd=ROOT, check=True)
        for _ in range(3):
            subprocess.run(['git', 'pull', '-q', '--rebase', 'origin', br], cwd=ROOT)
            if subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:' + br], cwd=ROOT).returncode == 0:
                break


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], cwd=ROOT)
    subprocess.run(['git', 'config', 'user.email', '41898+github-actions[bot]@users.noreply.github.com'], cwd=ROOT)
    if what in ('lottie', 'all'):
        lottie()
    if what in ('mixkit', 'all'):
        mixkit()
    if what == 'video':
        video()
