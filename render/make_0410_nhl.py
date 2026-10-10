"""Детройт — Виннипег, 4 октября 20:00 МСК, в шаблоне «Бока» (nhl_kit.preview).

У таблицы НХЛ на этот матч не было ни времени, ни линии Pinnacle (в «Матчах дня» он вышел без них),
время — со слов автора, баннер без строки кэфов.
Запуск из папки render: python make_0410_nhl.py → out/0410/nhl_detroit_winnipeg.jpg
"""
import os

import nhl
import nhl_kit

nhl.register()

os.makedirs('out/0410', exist_ok=True)
print(nhl_kit.preview('Детройт', 'Виннипег', dict(when='ВС 04.10 · 20:00 МСК', odds=None), 'out/0410/nhl_detroit_winnipeg.jpg'))
