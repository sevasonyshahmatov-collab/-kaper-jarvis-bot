"""Итоги 23–24.10 заново (владелец 24.10: Чикаго — Монреаль — ставка «тотал меньше 5,5», а не «больше») → out/daily/recap_fix/."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'team', 'daily'), os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')]
import banner  # noqa: E402

W, L = 'win', 'loss'
ROWS = [('KHL', 'Автомобилист', 'ЦСКА', 5, 1, '', L, 'итоговая победа ЦСКА', 1.63),
        ('KHL', 'Лада', 'Шанхайские Драконы', 0, 2, '', W, 'победа Шанхайских Драконов в основное время', 1.77),
        ('KHL', 'Локомотив', 'Динамо Москва', 2, 1, 'ОТ', W, 'тотал матча меньше 5,5', 1.61),
        ('KHL', 'Спартак', 'Северсталь', 3, 1, '', W, 'тотал матча меньше 5,5', 1.70),
        ('NHL', 'Чикаго', 'Монреаль', 1, 4, '', W, 'тотал матча меньше 5,5', 1.66)]
rows = [dict(league=lg, home=h, away=a, g=dict(hg=hg, ag=ag, end=e), res=res, bet=bet, kef=k)
        for lg, h, a, hg, ag, e, res, bet, k in ROWS]
print(banner.render(rows, os.path.join(ROOT, 'out', 'daily', 'recap_fix'), '23–24 октября · зашло 4 из 5'))
