"""Данные к прогнозу на 16.10 (КХЛ) одним заданием: матчи дня и линия Фонбета из приложения КХЛ (khl_fetch.py),
«Что заходит» по каждой паре (khl_picks_calc.py next), линия Pinnacle на матчи 16.10 по МСК (pin_fetch.py day:…).
Всё — в лог Actions (строки KHLNEXT, CALC, TEAM, LAST, PER, H2H, PIN)."""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for script, args in (('khl_fetch.py', ['2026-10-16']), ('khl_picks_calc.py', ['next']), ('pin_fetch.py', ['day:2026-10-16'])):
    sys.argv = [script] + args
    runpy.run_path(os.path.join(HERE, script), run_name='__main__')
