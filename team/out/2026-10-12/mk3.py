"""Сборка части роликов 12.10 для задания Actions (лимит 20 мин): newfmt_make.py tape jarvis card."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "newfmt_make.py")] + "tape jarvis card".split()).returncode)
