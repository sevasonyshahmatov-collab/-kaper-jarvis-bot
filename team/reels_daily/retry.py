# -*- coding: utf-8 -*-
"""Догрузка на YouTube роликов, которым утром отказал лимит канала (владелец 23.10: «через 2–3 часа попробуй заново»).
YouTube считает лимит загрузок канала за последние 24 часа, а утренний запуск идёт каждый день примерно в одно время —
и иногда начинает на несколько минут раньше, чем прошли сутки со вчерашних загрузок. Запускает reels-retry.yml.

Берёт <ролик>.json из артефактов утреннего запуска (make.one): автозагрузка была (приоритетный матч), но YouTube отказал
(yt пусто, yt_note «не загружен…»). Остальные ролики (ручная загрузка) не трогает. Итог — владельцу в Telegram.

    python team/reels_daily/retry.py khl 2026-10-23        (YT_*, TG_BOT_TOKEN; нет — только печать)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'render'))
sys.path.insert(0, HERE)

import pack  # noqa: E402
import youtube  # noqa: E402


def todo(js):
    return [j for j in js if not j.get('yt') and (j.get('yt_note') or '').startswith('не загружен')]


def main():
    league, day = sys.argv[1].lower(), sys.argv[2]
    js = todo(pack.items(league, day))
    print('RETRY %s %s: к догрузке %d' % (league, day, len(js)), flush=True)
    if not js:
        return
    lines = []
    for j in js:
        tags = [w for w in j['description'].strip().split('\n')[-1].split() if w.startswith('#')]
        url, note = youtube.upload(j['path'], j['title'], j['description'], tags)
        cover = j['path'][:-4] + '_cover.jpg'
        if url and os.path.exists(cover):
            youtube.thumbnail(url, cover)
        print('RETRY %s — %s: %s' % (j['h'], j['a'], url or note), flush=True)
        lines.append('%s %s — %s: %s' % (j['d'][11:16], j['h'], j['a'], url or note))
    tok = os.environ.get('TG_BOT_TOKEN')
    if tok:
        import team_job as tj
        chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
        text = 'Догрузка на YouTube (%s, %s.%s) — утром отказал лимит канала:\n\n%s' % (
            pack.LG[league], day[8:10], day[5:7], '\n'.join(lines))
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text=text[:tj.TEXT_MAX], disable_web_page_preview='true'))


if __name__ == '__main__':
    main()
