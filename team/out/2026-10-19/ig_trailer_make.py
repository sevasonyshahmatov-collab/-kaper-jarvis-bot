"""Трейлер таблицы v2 → Instagram Reels (владелец 19.10: «загрузи новый ролик с таблицей в Инстаграм»).
Собирает тот же ролик (trailer_make.py: данные КХЛ, трек depto, обложка) и выкладывает с обложкой; ссылку — в лог IGTRAILER."""
import os
import runpy
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trailer_make.py'), run_name='trailer')
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
import instagram  # noqa: E402
import make  # noqa: E402

TEXT = ('Я сделал таблицу, которая прогнозирует лучше букмекера 👀\n\n'
        'Шансы на каждый матч КХЛ, что заходит у команд, рейтинг Elo и честная статистика — что зашло, а что нет.\n\n'
        'Прогнозы каждый день — ссылка на Telegram в профиле.\n\n'
        '#кхл #хоккей #прогнозынахоккей #аналитика #статистика')
url, note = instagram.upload('out/trailer/trailer.mp4', TEXT, 'out/trailer/trailer_cover.jpg')
print('IGTRAILER %s %s' % (url, note), flush=True)
make.tg_text('Трейлер таблицы в Instagram: %s' % (url or ('не загрузился — ' + note)))
