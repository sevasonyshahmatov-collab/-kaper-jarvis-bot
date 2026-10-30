# -*- coding: utf-8 -*-
"""Снимок листа «Футбол» для владельца (PR #131): макет tools/gas_mock на тестовых матчах → HTML → JPG (Playwright).
Результат — team/out/2026-10-30/foot_sheet.jpg (в репозиторий не кладётся, сразу уходит заданием)."""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'team', 'out', '2026-10-30')
tmp = os.path.join(OUT, 'foot_shot')
subprocess.run(['node', os.path.join(ROOT, 'tools/gas_mock/team_football_test.js'), tmp], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'playwright'], check=True)
subprocess.run([sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True, stdout=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1760, 'height': 460}, device_scale_factor=2)
    pg.goto('file://' + os.path.join(tmp, '1.html'))
    pg.screenshot(path=os.path.join(tmp, 'shot.png'), full_page=False)
    b.close()
Image.open(os.path.join(tmp, 'shot.png')).convert('RGB').save(os.path.join(OUT, 'foot_sheet.jpg'), quality=90)
print('FBSHOT ok')
