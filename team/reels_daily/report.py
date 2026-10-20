# -*- coding: utf-8 -*-
"""Еженедельный отчёт по шортсам (владелец 20.10: идея из yutu — какие ролики, шаблоны и время набирают больше).

YouTube — Data API v3 (те же секреты YT_*, что у загрузки): ролики канала за N дней, просмотры, лайки, комментарии;
досмотр (средний % просмотра) — YouTube Analytics API, если у токена есть доступ yt-analytics.readonly (нет — без него).
Шаблон ролика — скрытый тег tpl_<шаблон> (ставит make.one с 20.10; у старых роликов шаблон неизвестен).
Instagram — Graph API (IG_TOKEN, IG_USER_ID): просмотры Reels за те же дни.
→ текст отчёта (владельцу в Telegram); печатает его и строки REPORT в лог.

    python team/reels_daily/report.py [дней=7]
"""
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import youtube  # noqa: E402

API = 'https://www.googleapis.com/youtube/v3/'
YTA = 'https://youtubeanalytics.googleapis.com/v2/reports'
MSK = timezone(timedelta(hours=3))
NAMES = {'tape': 'Лента', 'jarvis': 'Терминал', 'card': 'Карточка', 'jewel': 'Jewel', 'kinetic': 'Kinetic', 'radar': 'Радар',
         'race': 'Гонка', 'vhs': 'VHS', 'cinema': 'Кино', 'broadcast': 'Эфир', 'dashboard': 'Приборка', 'lineup': 'Состав',
         'simulate': '10 000 симуляций', 'numday': 'Цифра дня'}


def _get(url, **params):
    r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + youtube._token()}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError('%s %s' % (r.status_code, r.text[:300]))
    return r.json()


def yt_videos(days):
    ch = _get(API + 'channels', part='contentDetails', mine='true')['items'][0]
    pl = ch['contentDetails']['relatedPlaylists']['uploads']
    since = datetime.now(timezone.utc) - timedelta(days=days)
    ids, token = [], None
    while True:
        j = _get(API + 'playlistItems', part='contentDetails', playlistId=pl, maxResults=50, **({'pageToken': token} if token else {}))
        stop = False
        for it in j.get('items', []):
            t = datetime.fromisoformat(it['contentDetails'].get('videoPublishedAt', '1970-01-01T00:00:00Z').replace('Z', '+00:00'))
            if t < since:
                stop = True
                continue
            ids.append(it['contentDetails']['videoId'])
        token = j.get('nextPageToken')
        if stop or not token:
            break
    out = []
    for k in range(0, len(ids), 50):
        j = _get(API + 'videos', part='snippet,statistics', id=','.join(ids[k:k + 50]))
        for v in j.get('items', []):
            sn, st = v['snippet'], v.get('statistics', {})
            tpl = next((t[4:] for t in sn.get('tags') or [] if t.startswith('tpl_')), None)
            out.append(dict(id=v['id'], title=sn['title'], at=datetime.fromisoformat(sn['publishedAt'].replace('Z', '+00:00')),
                            views=int(st.get('viewCount', 0)), likes=int(st.get('likeCount', 0)),
                            comments=int(st.get('commentCount', 0)), tpl=tpl,
                            league='НХЛ' if 'НХЛ' in sn['title'] or 'нхл' in ' '.join(sn.get('tags') or []).lower() else 'КХЛ'))
    return out


def yt_retention(vids, days):
    """Средний % досмотра по роликам (YouTube Analytics). Нет доступа — {} и пояснение."""
    if not vids:
        return {}, ''
    end = datetime.now(MSK).date()
    try:
        j = _get(YTA, ids='channel==MINE', startDate=str(end - timedelta(days=days + 3)), endDate=str(end),
                 metrics='averageViewPercentage,averageViewDuration', dimensions='video',
                 filters='video==' + ','.join(v['id'] for v in vids[:200]))
        return {r[0]: (r[1], r[2]) for r in j.get('rows', [])}, ''
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        why = 'нет доступа к YouTube Analytics (нужен токен с правом yt-analytics.readonly)' if '403' in msg or '401' in msg \
            else 'YouTube Analytics не ответил'
        print('REPORTERR досмотр: %s' % msg[:300], flush=True)
        return {}, why


def base_tpl(t):
    return (t or '').split('_')[0] or None


def ig_views(days):
    tok, uid = os.environ.get('IG_TOKEN', '').strip(), os.environ.get('IG_USER_ID', '').strip()
    if not tok or not uid:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    r = requests.get('https://graph.facebook.com/v21.0/%s/media' % uid, timeout=30,
                     params=dict(fields='id,caption,media_type,timestamp,permalink', limit=50, access_token=tok)).json()
    out = []
    for m in r.get('data', []):
        t = datetime.fromisoformat(m['timestamp'].replace('+0000', '+00:00'))
        if t < since or m.get('media_type') not in ('VIDEO', 'REELS'):
            continue
        views = None
        for metric in ('views', 'plays'):
            ins = requests.get('https://graph.facebook.com/v21.0/%s/insights' % m['id'], timeout=30,
                               params=dict(metric=metric, access_token=tok)).json()
            if ins.get('data'):
                views = ins['data'][0]['values'][0]['value']
                break
        out.append(dict(link=m.get('permalink'), title=(m.get('caption') or '').split('\n')[0][:60], at=t, views=views))
    return out


def build(days=7):
    lines = ['Отчёт по шортсам за %d дней (до %s)' % (days, datetime.now(MSK).strftime('%d.%m %H:%M МСК'))]
    try:
        vids = yt_videos(days)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        print('REPORTERR YouTube: %s' % msg[:300], flush=True)
        vids = []
        lines.append('YouTube: не получил список роликов (%s)' % (
            'у токена нет права читать канал — нужен YT_REFRESH_TOKEN с youtube.readonly' if '403' in msg else msg[:120]))
    ret, why = yt_retention(vids, days)
    if vids:
        tot = sum(v['views'] for v in vids)
        lines += ['', 'YouTube: %d роликов, %d просмотров (в среднем %d), лайков %d' % (
            len(vids), tot, tot // len(vids), sum(v['likes'] for v in vids))]
        top = sorted(vids, key=lambda v: -v['views'])
        lines.append('Лучшие:')
        for v in top[:5]:
            r = ret.get(v['id'])
            lines.append('  %d · %s%s · youtu.be/%s' % (v['views'], v['title'][:55], (' · досмотр %d%%' % r[0]) if r else '', v['id']))
        if len(top) > 5:
            lines.append('Слабее всех:')
            for v in top[-3:]:
                lines.append('  %d · %s · youtu.be/%s' % (v['views'], v['title'][:55], v['id']))
        by = defaultdict(list)
        for v in vids:
            by[base_tpl(v['tpl'])].append(v)
        known = {k: x for k, x in by.items() if k}
        if known:
            lines += ['', 'Шаблоны (средние просмотры):']
            for k, x in sorted(known.items(), key=lambda kv: -sum(v['views'] for v in kv[1]) / len(kv[1])):
                rr = [ret[v['id']][0] for v in x if v['id'] in ret]
                lines.append('  %s — %d (%d роликов)%s' % (NAMES.get(k, k), sum(v['views'] for v in x) // len(x), len(x),
                                                          (', досмотр %d%%' % (sum(rr) / len(rr))) if rr else ''))
        if by.get(None):
            lines.append('  без отметки шаблона (до 20.10): %d роликов' % len(by[None]))
        hours = defaultdict(list)
        for v in vids:
            hours[v['at'].astimezone(MSK).hour // 3 * 3].append(v['views'])
        if len(hours) > 1:
            lines += ['', 'Время выхода (МСК, средние просмотры):'] + [
                '  %02d–%02d: %d (%d)' % (h, h + 3, sum(x) // len(x), len(x)) for h, x in sorted(hours.items())]
        lg = defaultdict(list)
        for v in vids:
            lg[v['league']].append(v['views'])
        lines.append('Лиги: ' + ', '.join('%s — %d в среднем (%d)' % (k, sum(x) // len(x), len(x)) for k, x in lg.items()))
    if why:
        lines.append('Досмотр: %s' % why)
    try:
        ig = ig_views(days)
    except Exception as e:  # noqa: BLE001
        print('REPORTERR Instagram: %r' % e, flush=True)
        ig = []
    if ig:
        known = [m for m in ig if m['views'] is not None]
        lines += ['', 'Instagram: %d роликов, %d просмотров' % (len(ig), sum(m['views'] for m in known))]
        for m in sorted(known, key=lambda m: -m['views'])[:5]:
            lines.append('  %d · %s · %s' % (m['views'], m['title'], m['link']))
    text = '\n'.join(lines)
    for ln in lines:
        print('REPORT ' + ln, flush=True)
    return text


if __name__ == '__main__':
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    t = build(d)
    tok = os.environ.get('TG_BOT_TOKEN')
    if tok and os.environ.get('REPORT_SEND', '1') == '1':
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'render'))
        import team_job as tj
        chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
        for k in range(0, len(t), 3900):
            tj._api(tok, 'sendMessage', dict(chat_id=chat, text=t[k:k + 3900], disable_web_page_preview='true'))
