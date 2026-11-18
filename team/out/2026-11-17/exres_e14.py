"""Итог экспресса 1711-e14 (владелец 18.11 попросил): только если все ноги доиграны."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'team', 'picks'))
import express_result as er
SRC, K, OUT, JOB = 'team/out/2026-11-17/express_coupons.json', '14', 'out/express/2026-11-17', 'team/out/2026-11-17/exres_e14.json'
os.environ.pop('EXPRESS_FORCE_LIVE', None)
_, _, _, st = er.compute(SRC, K, OUT)
print('EXPRSTATUS', st, flush=True)
if st == 'pending':
    sys.exit('EXPRERR не все матчи доиграны')
sys.exit(er.manual(SRC, K, OUT, JOB, '1711-e14'))
