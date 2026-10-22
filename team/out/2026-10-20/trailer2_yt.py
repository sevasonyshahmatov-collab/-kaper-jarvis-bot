"""Трейлер таблицы №2 → только YouTube (после сброса дневного лимита загрузок)."""
import os
import runpy

os.environ['PUB2_ONLY'] = 'yt'
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trailer2_publish.py'), run_name='pub')
