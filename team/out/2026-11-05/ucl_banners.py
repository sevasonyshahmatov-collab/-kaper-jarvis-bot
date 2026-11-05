"""Баннеры итогов ЛЧ 04.11: итог экспресса 0411-e8 и «Итоги прогнозов» (0411-10/13/16/17) → out/ucl0411/."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'daily'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')]
OUT = os.path.join(ROOT, 'out', 'ucl0411')
os.makedirs(OUT, exist_ok=True)
import express_card as ec
import banner
legs = [dict(home='АЕК', away='Реал Мадрид', time='2:3', bet='ИТБ Реала 2,5', kef=1.70, league='Футбол', mark='win', score='2:3'),
        dict(home='Славия Прага', away='Арсенал', time='1:2', bet='победа Арсенала', kef=1.22, league='Футбол', mark='win', score='1:2'),
        dict(home='РБ Лейпциг', away='Манчестер Сити', time='2:3', bet='ИТБ Сити 2', kef=1.48, league='Футбол', mark='win', score='2:3')]
print(ec.render(legs, os.path.join(OUT, 'e8_result.jpg'), fmt='feed', title='ИТОГ ЭКСПРЕССА', date_title='4 ноября', total=3.07))
import football
football.register()
R = [('FOOT', 'АЕК', 'Реал Мадрид', 2, 3, 'win', 'победа Реала + тотал больше 2,5', 1.59),
     ('FOOT', 'ПСВ', 'Брюгге', 1, 2, 'win', 'обе забьют', 1.60),
     ('FOOT', 'Боруссия Дортмунд', 'Бетис', 2, 1, 'win', 'удары в створ больше 8', 1.71),
     ('FOOT', 'РБ Лейпциг', 'Манчестер Сити', 2, 3, 'win', 'победа Манчестер Сити', 1.55)]
rows = [dict(league=lg, home=h, away=a, g=dict(hg=hg, ag=ag, end=''), res=res, bet=bet, kef=k) for lg, h, a, hg, ag, res, bet, k in R]
print(banner.render(rows, OUT, '4 ноября · зашло 4 из 4'))
