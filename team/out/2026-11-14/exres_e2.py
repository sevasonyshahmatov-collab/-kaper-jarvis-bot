"""Итог экспресса 1411-e2 (владелец 15.11: итоги не пришли): только если все ноги доиграны (без засчёта по идущему матчу — в купоне ТМ6,5)."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'team', 'picks'))
import express_result as er
SRC, K, OUT, JOB = 'team/out/2026-11-14/express_coupons.json', '2', 'out/express/2026-11-14', 'team/out/2026-11-14/exres_e2.json'
os.environ.pop('EXPRESS_FORCE_LIVE', None)
_, _, _, st = er.compute(SRC, K, OUT)
print('EXPRSTATUS', st, flush=True)
if st == 'pending':
    sys.exit('EXPRERR не все матчи доиграны')
sys.exit(er.manual(SRC, K, OUT, JOB, '1411-e2'))
