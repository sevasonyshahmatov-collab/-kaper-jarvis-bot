"""Трейлер таблицы №2 → только Instagram (16:16 UTC: Instagram ответил ProcessingFailedError, YouTube — дневной лимит)."""
import os
import runpy

os.environ['PUB2_ONLY'] = 'ig'
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trailer2_publish.py'), run_name='pub')
