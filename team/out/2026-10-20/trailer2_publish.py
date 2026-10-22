"""Трейлер таблицы №2 → YouTube и Instagram (владелец 20.10: «да, нужно выложить этот ролик» — версия 39,7 с).
Собирает тот же ролик (trailer2_make.py, без повторной отправки в Telegram), выкладывает с обложкой, названием и
описанием оттуда же; ссылки — владельцу и в лог PUB2."""
import os
import runpy
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
tok = os.environ.pop('TG_BOT_TOKEN', None)             # ролик владелец уже видел — второй раз не шлём
g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trailer2_make.py'), run_name='trailer2')
if tok:
    os.environ['TG_BOT_TOKEN'] = tok
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
import instagram  # noqa: E402
import make  # noqa: E402
import youtube  # noqa: E402

video, cover = 'out/trailer2/trailer2.mp4', 'out/trailer2/trailer2_cover.jpg'
if os.environ.get('PUB2_ONLY') == 'ig':                  # YouTube — отдельно, когда обновится дневной лимит
    yt, ytnote = None, 'позже — дневной лимит YouTube'
else:
    yt, ytnote = youtube.upload(video, g['title'], g['desc'], ['кхл', 'хоккей', 'прогнозы на спорт', 'аналитика', 'таблица'])
tnote = youtube.thumbnail(yt, cover) if yt else ''
print('PUB2 YouTube %s %s %s' % (yt, ytnote, tnote), flush=True)
ig_text = g['desc'].replace('в Telegram: @jarvibet', 'в Telegram — ссылка в профиле')
if os.environ.get('PUB2_ONLY') == 'yt':
    ig, ignote = None, 'уже выложен раньше'
else:
    ig, ignote = instagram.upload(video, ig_text, cover)
print('PUB2 Instagram %s %s' % (ig, ignote), flush=True)
make.tg_text('Трейлер таблицы №2 выложен:\nYouTube: %s\nInstagram: %s' % (
    yt or ('не загрузился — ' + ytnote), ig or ('не загрузился — ' + ignote)) + (('\nОбложка YouTube: ' + tnote) if tnote else ''))
