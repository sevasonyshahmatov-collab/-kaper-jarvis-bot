"""Превью-2 (владелец 20.10: Mixkit и LottieFiles «берём»): те же два шаблона с треками Mixkit, иконками Phosphor и анимациями
LottieFiles, на матче КХЛ 21.10. Было: превью двух новых шаблонов (владелец 20.10: «давай попробуем» — «10 000 симуляций» и «Цифра дня») на настоящем матче
НХЛ ночи на 21.10 (Вегас — Тампа-Бэй): план дня с настоящими данными, ролики со звуком — владельцу в Telegram.
На YouTube и в Instagram ничего не выкладывается."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
os.environ['OUT'] = 'out/tpl_preview2'
import make  # noqa: E402

make.tg_text = lambda text: None
make.youtube.upload = lambda *a, **k: (None, '')
make.youtube.thumbnail = lambda *a, **k: ''
make.instagram.upload = lambda *a, **k: (None, '')
make.instagram.posted = lambda *a, **k: False
P = make.plan('khl', '2026-10-21', 0, 6)
i0 = next(i for i, x in enumerate(P['matches']) if x.get('sim') and x.get('fact'))
m = P['matches'][i0]
print('TPLDATA', m['h'], m['a'], m['pick'], m['odds'], 'sim', m.get('sim') and (m['sim']['hits'], m['sim']['top']),
      'fact', m.get('fact') and (m['fact']['team'], m['fact']['k'], m['fact']['n']), flush=True)
sent = []
make.tg_reel = lambda path, clean, text, title, cover: sent.append(path)
import team_job as tj  # noqa: E402
tok, chat = make._tg()
for tpl, name in (('simulate', '«10 000 симуляций»'), ('numday', '«Цифра дня»')):
    m['tpl'] = tpl
    m['pick'] = m['pick']
    make.one(P, i0, 'khl', '2026-10-21', 'KHL', 'КХЛ', None)
    path = sent[-1]
    print('TPLPREVIEW', tpl, path, flush=True)
    if tok:
        with open(path, 'rb') as f:
            tj._api(tok, 'sendVideo', dict(chat_id=chat, supports_streaming='true',
                                           caption='%s с музыкой Mixkit и анимациями — превью на %s — %s (никуда не выложен)' % (name, m['h'], m['a'])),
                    files={'video': f})
