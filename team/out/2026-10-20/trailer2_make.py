"""Второй трейлер таблицы (владелец 20.10: «ещё один ролик, с другой музыкой и другим содержанием»): настоящие матчи КХЛ
сезона → render/sheet_data.build → render/reels/sheet_trailer2.py, трек too_fast. Ролик (с музыкой и без), обложка и
описание для YouTube — владельцу в Telegram. Никуда не выкладывается."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
import khl_data  # noqa: E402
import sheet_data  # noqa: E402
import team_job as tj  # noqa: E402
from reels import core as C  # noqa: E402
from reels import owner_tracks  # noqa: E402
from reels.sheet_trailer2 import SheetTrailer2, cover2  # noqa: E402

games, nxt = khl_data.fetch('2026-10-20')
data = sheet_data.build(games, nxt)
A = data['acc']
print('TRAILER2 матчей %d, угадано %d%% (%d), уверенные %d%% (%d из %d), прогнозов дня %d' % (
    A['n'], A['pct'], A['hits'], A['sure_pct'], A['sure_hits'], A['sure_n'], len(data['pred'])), flush=True)
U, TDROP = 1.061946, 33.576                                   # too_fast: доля и удар — пробы 19.10
r = SheetTrailer2(data, u=U)
os.makedirs('out/trailer2', exist_ok=True)
C.render(r, 'out/trailer2/trailer2.mp4', track=owner_tracks.wav('too_fast'), start=TDROP - r.drop,
         extra_out='out/trailer2/trailer2_clean.mp4')
cover2(data).save('out/trailer2/trailer2_cover.jpg', quality=92)
print('TRAILER2 готов: %.1f с' % r.dur, flush=True)
sure = A['sure_n'] >= 20 and A['sure_pct'] > A['pct']
desc = ('%d матчей сезона КХЛ в одной таблице — и вот что она видит.\n\n'
        'Точность модели за сезон: угадан исход в %d%% матчей (%d из %d)%s. Каждый матч проверен честно: прогноз — '
        'как был бы накануне игры.\n\nЧто внутри таблицы: что заходит у каждой команды (победа, тоталы, форы), сравнение '
        'модели с линией, рейтинг силы Elo, таблица лиги и прогноз на каждый матч.\n\nВсе прогнозы и полная таблица — '
        'в Telegram: @jarvibet\n\nЭто аналитика, а не гарантия результата.\n\n#кхл #хоккей #прогнозынаспорт #аналитика #shorts'
        % (A['n'], A['pct'], A['hits'], A['n'],
           ('; когда модель уверена (от 60%%) — %d%% (%d из %d)' % (A['sure_pct'], A['sure_hits'], A['sure_n'])) if sure else ''))
title = '%d матчей КХЛ в одной таблице — вот что она видит' % A['n']
tok = os.environ.get('TG_BOT_TOKEN')
if tok:
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    with open('out/trailer2/trailer2.mp4', 'rb') as f:
        tj._api(tok, 'sendVideo', dict(chat_id=chat, supports_streaming='true',
                                       caption='Трейлер таблицы №2 (музыка too_fast, %.0f с). Никуда не выложен.' % r.dur),
                files={'video': f})
    with open('out/trailer2/trailer2_cover.jpg', 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Обложка для YouTube и Instagram'), files={'document': f})
    with open('out/trailer2/trailer2_clean.mp4', 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Без музыки'), files={'document': f})
    tj._api(tok, 'sendMessage', dict(chat_id=chat, text='Название для YouTube:\n%s\n\nОписание:\n%s' % (title, desc)))
