# -*- coding: utf-8 -*-
"""Отправка express_nhl.json по одному сообщению с итогом пометкой ::notice EXSEND (логи Actions из облака закрыты)."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'render'))
import team_job as tj  # noqa: E402
tok = os.environ['TG_BOT_TOKEN']
owner = tj.owner_chat(tok, '@jarvibet')
job = json.load(open(os.path.join(ROOT, 'team/out/2026-10-31/express_nhl.json'), encoding='utf-8'))
bad = 0
for i, m in enumerate(job['messages']):
    try:
        tj.send(tok, owner, m, False)
        print('::notice title=EXSEND_%d::ok %s' % (i, m['type']), flush=True)
    except Exception as e:  # noqa: BLE001
        bad += 1
        print('::notice title=EXSEND_%d::ОШИБКА %s %s' % (i, m['type'], str(e)[:300].replace('\n', ' ')), flush=True)
sys.exit(1 if bad else 0)
