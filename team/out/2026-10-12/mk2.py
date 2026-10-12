"""Сборка части роликов 12.10 для задания Actions (лимит 20 мин): lineup_make.py devils."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "lineup_make.py")] + "devils".split()).returncode)
