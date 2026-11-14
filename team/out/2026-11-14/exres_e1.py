"""Итог экспресса 1411-e1 (владелец 14.11): только если все ноги доиграны (без засчёта по идущему матчу — в купоне ТМ6,5)."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'team', 'picks'))
import express_result as er
SRC, K, OUT, JOB = 'team/out/2026-11-14/express_bb_coupons.json', '1', 'out/express/2026-11-14-bb', 'team/out/2026-11-14/exres_e1.json'
os.environ.pop('EXPRESS_FORCE_LIVE', None)
_, _, _, st = er.compute(SRC, K, OUT)
print('EXPRSTATUS', st, flush=True)
if st == 'pending':
    sys.exit('EXPRERR не все матчи доиграны')
sys.exit(er.manual(SRC, K, OUT, JOB, '1411-e1'))
