"""Озвучка Yandex SpeechKit — превью трёх голосов на выбор (владелец 20.10: «уверенная, бодрая, ровная, притягательная»):
один и тот же ролик «10 000 симуляций» (Вегас — Тампа-Бэй) с голосами Ермил, Захар, Филипп. Ролики — владельцу в
Telegram с подписью, какой голос. На YouTube и в Instagram ничего не выкладывается."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
os.environ['REELS_ONLY'] = 'Вегас'
os.environ['OUT'] = 'out/tpl_yvoice'
os.environ['REELS_TTS'] = '1'
import make  # noqa: E402
import voice  # noqa: E402
import team_job as tj  # noqa: E402

tok, chat = make._tg()
if voice.engine() != 'yandex':
    print('YVOICE нет секрета YANDEX_TTS_KEY', flush=True)
    if tok:
        tj._api(tok, 'sendMessage', dict(chat_id=chat, text='Озвучка Яндекса: секрет YANDEX_TTS_KEY в GitHub не найден — превью не собраны.'))
    sys.exit(0)
make.tg_text = lambda text: None
make.youtube.upload = lambda *a, **k: (None, '')
make.youtube.thumbnail = lambda *a, **k: ''
make.instagram.upload = lambda *a, **k: (None, '')
make.instagram.posted = lambda *a, **k: False
P = make.plan('nhl', '2026-10-20', 0, 3)
m = P['matches'][0]
m['tpl'] = 'simulate'
sent = []
make.tg_reel = lambda path, clean, text, title, cover: sent.append(path)
VOICES = [('ermil:good@1.12', 'Ермил — деловой, бодрый'), ('zahar:neutral@1.1', 'Захар — низкий, ровный'),
          ('filipp@1.12', 'Филипп — живее')]
base_out = os.environ['OUT']
for i, (spec, name) in enumerate(VOICES, 1):
    voice.YVOICE = spec
    os.environ['OUT'] = '%s/%d' % (base_out, i)
    try:
        make.one(P, 0, 'nhl', '2026-10-20', 'NHL', 'НХЛ', None)
    except Exception as e:  # noqa: BLE001
        print('YVOICEERR %s %r' % (spec, e), flush=True)
        continue
    print('YVOICE %s %s' % (spec, sent[-1]), flush=True)
    if tok:
        with open(sent[-1], 'rb') as f:
            tj._api(tok, 'sendVideo', dict(chat_id=chat, supports_streaming='true',
                                           caption='Голос %d: %s (Yandex SpeechKit). Какой оставить?' % (i, name)),
                    files={'video': f})
