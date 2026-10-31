# -*- coding: utf-8 -*-
"""Отправка задания по одному сообщению с итогом пометкой ::notice EXSEND_<i> (логи Actions из облака закрыты).
    team/picks/express_send.py team/out/D/express.json            — отправить все сообщения
    team/picks/express_send.py team/out/D/express.json 0 2        — только эти номера
    team/picks/express_send.py team/out/D/express.json --dry      — ничего не слать: есть ли файлы, размеры
В задании: {"make": ["team/picks/express_render.py …", "team/picks/express_send.py <задание> …"], "messages": []}."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'render'))
args = sys.argv[1:]
job = json.load(open(os.path.join(ROOT, args[0]), encoding='utf-8'))
dry = '--dry' in args
only = {int(a) for a in args[1:] if a.isdigit()}
bad = 0
if not dry:
    import team_job as tj
    tok = os.environ['TG_BOT_TOKEN']
    owner = tj.owner_chat(tok, '@jarvibet')
for i, m in enumerate(job['messages']):
    if only and i not in only:
        continue
    files = [os.path.join(ROOT, f) for f in m.get('files') or []]
    miss = [f for f in files if not os.path.exists(f)]
    info = ' '.join('%s %dКБ' % (os.path.basename(f), os.path.getsize(f) // 1024) for f in files if os.path.exists(f))
    if miss or dry:
        bad += bool(miss)
        print('::notice title=EXSEND_%d::%s %s %s' % (i, m['type'], 'НЕТ ФАЙЛОВ ' + ' '.join(map(os.path.basename, miss))
                                                     if miss else 'файлы есть', info), flush=True)
        continue
    try:
        tj.send(tok, owner, m, False)
        print('::notice title=EXSEND_%d::ok %s %s' % (i, m['type'], info), flush=True)
    except Exception as e:  # noqa: BLE001
        bad += 1
        print('::notice title=EXSEND_%d::ОШИБКА %s %s' % (i, m['type'], str(e)[:300].replace('\n', ' ')), flush=True)
sys.exit(1 if bad else 0)
