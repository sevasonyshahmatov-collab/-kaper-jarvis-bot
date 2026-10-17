# -*- coding: utf-8 -*-
"""Разбор прогноза 1610-6 (Анахайм — Бостон, ИТБ Бостона 2,5 в осн. время, 1,63): счёт из API НХЛ → баннер
ice_more2 verdict (утверждённый шаблон) + текст поста в задание. Запуск в Actions из корня (PYTHONPATH=render)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily')); sys.path.insert(0, os.path.join(ROOT, 'render'))
import data, ice_more2 as im2, nhl
nhl.register()
g = next(x for x in data.nhl_day('2026-10-16') if x['home'] == 'Анахайм' and x['away'] == 'Бостон')
print('SCORE', json.dumps({k: str(v) for k, v in g.items()}, ensure_ascii=False), flush=True)
assert g['state'] == 'final', 'матч не закончен'
rh, ra = g.get('reg') or (g['hg'], g['ag'])
hit = ra > 2.5
end = g['end']
score = '%d:%d%s' % (g['hg'], g['ag'], (' ' + end) if end else '')
check = ('В ОСНОВНОЕ ВРЕМЯ У БОСТОНА %d %s' % (ra, 'ШАЙБЫ' if ra in (2, 3, 4) else 'ШАЙБ' if ra != 1 else 'ШАЙБА'), hit)
m = dict(home='Анахайм', away='Бостон', sh=g['hg'], sa=g['ag'], mark=end, date='пятница, 17 октября', tag='НХЛ',
         pick=dict(text='ИНД. ТОТАЛ БОСТОНА БОЛЬШЕ 2,5', odds=1.63, hit=hit, checks=[check]))
os.makedirs(os.path.join(ROOT, 'out', 'verdict'), exist_ok=True)
im2.single(m, os.path.join(ROOT, 'out', 'verdict', 'ana_bos.jpg'), style='verdict', league='NHL')
job_path = os.path.join(ROOT, 'team', 'out', '2026-10-17', 'verdict_ana_bos.json')
job = json.load(open(job_path, encoding='utf-8'))
job['messages'] = [{'to': 'owner', 'type': 'photo', 'files': ['out/verdict/ana_bos.jpg'], 'buttons': 'post', 'pid': '1710-v1',
                    'emoji': True, 'text': 'НХЛ · итог прогноза\n\nАнахайм — Бостон %s\n%sПрогноз: индивидуальный тотал Бостона больше 2,5 в основное время · 1,63 — %s\n\n#нхл'
                    % (score, '' , 'зашёл ✅' if hit else 'не зашёл ❌')}]
json.dump(job, open(job_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('готово', score, 'hit' if hit else 'miss', flush=True)
