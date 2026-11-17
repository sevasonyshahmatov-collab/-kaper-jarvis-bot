"""Итог экспресса 1611-e4 (владелец 17.11: бот не прислал): только если все ноги доиграны."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'team', 'picks'))
import express_result as er
SRC, K, OUT, JOB = 'team/out/2026-11-16/express_coupons.json', '4', 'out/express/2026-11-16', 'team/out/2026-11-16/exres_e4.json'
os.environ.pop('EXPRESS_FORCE_LIVE', None)
_, _, _, st = er.compute(SRC, K, OUT)
print('EXPRSTATUS', st, flush=True)
if st == 'pending':
    sys.exit('EXPRERR не все матчи доиграны')
sys.exit(er.manual(SRC, K, OUT, JOB, '1611-e4'))
