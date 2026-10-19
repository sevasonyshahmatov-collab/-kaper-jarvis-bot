# -*- coding: utf-8 -*-
"""Два ролика владельцу в Telegram (владелец 19.10): Адмирал — Салават Юлаев и Северсталь — Торпедо в шаблонах,
которых конвейер ещё не брал («Карточка» и «Плёнка», утверждены 12.10). Прогнозы — как в постах канала 1910-2 и 1910-3
(facts_khl.md, Pinnacle run 248). Только Telegram: на YouTube не загружаем (ключи YT_* убраны из окружения).
Сборка — функциями конвейера team/reels_daily/make.py (форма клубов, бегущая строка, трек, подписи)."""
import os
import shutil
import subprocess
import sys

for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN'):
    os.environ.pop(k, None)
if not shutil.which('ffmpeg'):
    subprocess.run('sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg >/dev/null', shell=True, check=True)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
sys.path.insert(0, os.path.join(ROOT, 'render'))
import form  # noqa: E402
import khl_data  # noqa: E402
import make  # noqa: E402

DAY = '2026-10-19'
MATCHES = [
    dict(h='Адмирал', a='Салават Юлаев', pick='Адмирал не проиграет в основное время', odds=1.87,
         x1x2=[3.29, 3.92, 1.95], tpl='card'),
    dict(h='Северсталь', a='Торпедо', pick='Тотал матча меньше 4,5', odds=2.07, x1x2=[2.33, 3.61, 2.74], tpl='tape'),
]

games, nxt = khl_data.fetch(DAY)
when = {(x['h'], x['a']): x['d'] for x in nxt}
for m in MATCHES:
    m['d'] = when.get((m['h'], m['a'])) or '%s %s' % (DAY, {'Адмирал': '12:30', 'Северсталь': '19:00'}[m['h']])
names = [t for m in MATCHES for t in (m['h'], m['a'])]
P = dict(day=DAY, league='khl', matches=MATCHES, stats=form.khl(games, DAY, names),
         all=[dict(d=x['d'], h=x['h'], a=x['a']) for x in sorted(nxt, key=lambda x: x['d'])])
os.makedirs(make.out_dir('khl', DAY), exist_ok=True)
errors = []
for i in range(len(MATCHES)):
    try:
        make.one(P, i, 'khl', DAY, 'KHL', 'КХЛ', None)
    except Exception as e:  # noqa: BLE001 — второй ролик всё равно собираем
        errors.append('%s — %s: %r' % (MATCHES[i]['h'], MATCHES[i]['a'], e))
        print('REELERR', errors[-1], flush=True)
if errors:
    make.tg_text('Ролики: не собрались\n' + '\n'.join(errors))
    raise SystemExit('; '.join(errors))
