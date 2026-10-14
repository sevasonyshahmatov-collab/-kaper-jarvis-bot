"""Матчи НХЛ ночи 14→15.10 в шаблоне «Versus» (versus.py), 4К. Расписание — официальный API НХЛ
(team/out/2026-10-14/nhl_sched.py, run 122): WSH–MTL 23:30 UTC, COL–DAL 00:30 UTC. Линии нет — без плашек П1/Х/П2.
Запуск из папки render: python make_versus_1510.py → out/1510/vs_*.jpg
"""
import versus

for home, away, time, name in (('Вашингтон', 'Монреаль', '02:30', 'wsh_mtl'), ('Колорадо', 'Даллас', '03:30', 'col_dal')):
    print(versus.render(home, away, 'out/1510/vs_%s.jpg' % name, date='15 октября', time=time, league='NHL'))
