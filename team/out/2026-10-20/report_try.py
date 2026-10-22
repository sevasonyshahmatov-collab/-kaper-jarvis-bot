"""Первый прогон еженедельного отчёта по шортсам (team/reels_daily/report.py) за 5 дней — владельцу в Telegram."""
import os
import runpy
import sys

sys.argv = ['report.py', '5']
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reels_daily', 'report.py'), run_name='__main__')
