# -*- coding: utf-8 -*-
"""Пакет роликов дня владельцу в Telegram — разом, после всех частей (владелец 22.10: «чтобы я сразу их получил, все разом»).
Квоты YouTube хватает на ~6 автозагрузок в сутки (make.yt_priority), остальные ролики владелец грузит в YouTube Studio сам
(до 15 файлов за раз, квоту не тратит). Порядок сообщений:
  1) альбомы по 10: ролики для ручной загрузки (со звуком), в подписи первого — сводка дня;
  2) текст: по каждому ролику — номер в альбоме, YouTube (ссылка или «вручную»), название и описание для Studio;
  3) ссылка на запуск в GitHub: там архив со всеми роликами, версиями без музыки и обложками (2 дня).
Данные — <ролик>.json рядом с каждым .mp4 (make.one).

    python team/reels_daily/pack.py khl 2026-10-23        (TG_BOT_TOKEN; нет — только печать)
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
LG = {'khl': 'КХЛ', 'nhl': 'НХЛ'}
TG_VIDEO_MAX = 49 * 1024 * 1024                    # предел Bot API на файл — 50 МБ


def items(league, day):
    out = []
    for p in glob.glob(os.path.join(ROOT, 'out', 'reels_daily', '%s-%s' % (league, day), '**', '*.json'), recursive=True):
        if os.path.basename(p) == 'plan.json':
            continue
        with open(p, encoding='utf-8') as f:
            j = json.load(f)
        j['path'] = os.path.join(os.path.dirname(p), j['video'])
        if os.path.exists(j['path']):
            out.append(j)
    return sorted(out, key=lambda j: (j['d'], j['i']))


def texts(league, day, js, manual):
    lg = LG[league]
    head = 'Шортсы %s · %s.%s: %d. На YouTube сами: %d, вручную: %d.' % (
        lg, day[8:10], day[5:7], len(js), len(js) - len(manual), len(manual))
    lines = [head, '']
    n = 0
    for j in js:
        if j in manual:
            n += 1
            yt = 'загрузить вручную — №%d в альбоме' % n
            why = (j.get('yt_note') or '').split('\n')[0].replace(' — загрузите вручную', '')
            if why and not why.startswith('загрузите вручную'):          # автозагрузка была, но YouTube отказал
                yt += ' (%s)' % why[:120]
        else:
            yt = j['yt'] or j.get('yt_note') or '—'
        lines += ['%s %s — %s' % (j['d'][11:16], j['h'], j['a']), 'YouTube: %s' % yt]
        if j in manual:
            lines += ['', 'Название:', j['title'], '', 'Описание:', j['description']]
        lines += ['', '———', '']
    run = os.environ.get('GITHUB_RUN_ID')
    if run:
        lines.append('Все ролики, версии без музыки и обложки одним архивом (2 дня): %s/%s/actions/runs/%s' % (
            os.environ.get('GITHUB_SERVER_URL', 'https://github.com'), os.environ.get('GITHUB_REPOSITORY', ''), run))
    return head, '\n'.join(lines)


def send(league, day):
    js = items(league, day)
    if not js:
        print('PACK %s %s: роликов нет' % (league, day), flush=True)
        return
    manual = [j for j in js if not j.get('yt')]
    head, text = texts(league, day, js, manual)
    print(text, flush=True)
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено', flush=True)
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    pool = js if os.environ.get('PACK_ALL') == '1' else manual          # PACK_ALL=1 — все ролики дня (повторная отправка)
    vids = [j for j in pool if os.path.getsize(j['path']) <= TG_VIDEO_MAX]
    # по одному: альбом из нескольких роликов по ~27 МБ упирается в предел Bot API 50 МБ на запрос (23.10)
    tj._api(tok, 'sendMessage', dict(chat_id=chat, text=head))
    for n, j in enumerate(vids, 1):
        cap = '%d/%d · %s\n\n%s' % (n, len(vids), j['title'], j['description'])
        with open(j['path'], 'rb') as f:
            tj._api(tok, 'sendVideo', dict(chat_id=chat, caption=cap[:tj.CAPTION_MAX], supports_streaming='true'),
                    {'video': f}, timeout=600)
    tj._api(tok, 'sendMessage', dict(chat_id=chat, text=text[:tj.TEXT_MAX], disable_web_page_preview='true'))
    for k in range(tj.TEXT_MAX, len(text), tj.TEXT_MAX):
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text=text[k:k + tj.TEXT_MAX], disable_web_page_preview='true'))
    print('PACK %s %s: роликов %d, вручную %d' % (league, day, len(js), len(manual)), flush=True)


if __name__ == '__main__':
    send(sys.argv[1].lower(), sys.argv[2])
