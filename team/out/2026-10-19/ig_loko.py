"""Локомотив — Нефтехимик 20.10 → только Instagram (в ночной выкладке Instagram ответил «обработка не удалась»; на YouTube
ролик уже есть — RWZV4O1EdFc). Тот же ролик: прогноз владельца (owner_picks.json), шаблон по очереди дня. YouTube и
повторная отправка в Telegram выключены, владельцу — только ссылка."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
os.environ['REELS_ONLY'] = 'Локомотив'
import make  # noqa: E402

sent = []
make.tg_text = lambda text: None
make.tg_reel = lambda *a, **k: None
make.youtube.upload = lambda *a, **k: (None, '')
make.youtube.thumbnail = lambda *a, **k: ''
real = make.instagram.upload


def ig(*a, **k):
    r = real(*a, **k)
    sent.append(r)
    return r


make.instagram.upload = ig
os.environ['OUT'] = 'out/ig_loko'
P = make.plan('khl', '2026-10-20', 0, 3)
for i, m in enumerate(P['matches']):
    make.one(P, i, 'khl', '2026-10-20', 'KHL', 'КХЛ', None)
url, note = sent[0] if sent else (None, 'ролик уже есть в Instagram или не собрался')
print('IGLOKO', url, note, flush=True)
import team_job as tj  # noqa: E402
tok, chat = make._tg()
if tok:
    tj._api(tok, 'sendMessage', dict(chat_id=chat, disable_web_page_preview='true',
                                     text='Локомотив — Нефтехимик (ваш прогноз, 1,85):\nYouTube: https://youtu.be/RWZV4O1EdFc\n'
                                          'Instagram: %s' % (url or 'не загрузился — ' + note)))
