"""Баннеры итогов ЛЧ 03.11: итог экспресса 0311-e6 и «Итоги прогнозов» → out/ucl0311/."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'daily'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')]
OUT = os.path.join(ROOT, 'out', 'ucl0311')
os.makedirs(OUT, exist_ok=True)
import express_card as ec
import banner
legs = [dict(home='Вильярреал', away='ПСЖ', time='23:00', bet='ИТБ ПСЖ 1,5', kef=1.49, league='Футбол', mark='win', score='0:6'),
        dict(home='Манчестер Юнайтед', away='Рома', time='23:00', bet='ИТБ Ромы 1', kef=1.39, league='Футбол', mark='win', score='3:2'),
        dict(home='Барселона', away='Астон Вилла', time='23:00', bet='ИТБ Барселоны 2', kef=1.23, league='Футбол', mark='win', score='3:0')]
print(ec.render(legs, os.path.join(OUT, 'e6_result.jpg'), fmt='feed', title='ИТОГ ЭКСПРЕССА', date_title='3 ноября', total=2.54))
import football
football.register()
R = [('FOOT', 'Будё-Глимт', 'Лилль', 0, 0, 'win', 'фора 0 Будё-Глимт', 1.64),
     ('FOOT', 'Вильярреал', 'ПСЖ', 0, 6, 'win', 'тотал ударов ПСЖ больше 7', 1.74),
     ('FOOT', 'Атлетико', 'Бавария', 0, 2, 'loss', 'Атлетико не проиграет + тотал меньше 4,5', 2.01),
     ('FOOT', 'Барселона', 'Астон Вилла', 3, 0, 'loss', 'удары в створ Виллы больше 3,5', 1.80)]
rows = [dict(league=lg, home=h, away=a, g=dict(hg=hg, ag=ag, end=''), res=res, bet=bet, kef=k) for lg, h, a, hg, ag, res, bet, k in R]
print(banner.render(rows, OUT, '3 ноября · зашло 2 из 4'))
