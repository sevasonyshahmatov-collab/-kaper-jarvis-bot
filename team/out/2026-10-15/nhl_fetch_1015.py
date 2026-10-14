# -*- coding: utf-8 -*-
"""Данные НХЛ на ночь 14→15.10 (ET 14.10: Вашингтон — Монреаль, Колорадо — Даллас) для роликов 15.10:
тот же сбор, что team/out/2026-10-13/nhl_fetch.py (строки «NHLDATA {json}» в логе Actions), только на другой день."""
import os
import runpy
import sys

sys.argv = [sys.argv[0], '2026-10-14']
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '2026-10-13', 'nhl_fetch.py'),
               run_name='__main__')
