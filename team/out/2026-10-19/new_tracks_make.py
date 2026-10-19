"""Пробы 7 треков, которых ещё не было в роликах (владелец 19.10, вариант Б): темп и удар — render/track_sync.py,
каждый трек со своим шаблоном, ролик целиком с музыкой → out/tr/<трек>.mp4; параметры — строкой NEWTRACK в лог
(по ним одобренные пары встают в TEMPLATES конвейера). Данные матча в пробе — условные (tools/reels_stress.py)."""
import json
import os
import sys
import wave

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/reels_daily', 'team/picks', 'render', 'tools'):
    sys.path.insert(0, os.path.join(ROOT, p))
import banners  # noqa: E402  (ставит ffmpeg на раннер)
banners.ensure_ffmpeg()
import make  # noqa: E402
import reels_stress as RS  # noqa: E402
import track_sync  # noqa: E402
from reels import core as C  # noqa: E402
from reels import owner_tracks  # noqa: E402

PAIRS = [('depto', 'broadcast'), ('kilo', 'kinetic'), ('quantum', 'radar'), ('militant', 'race'),
         ('too_fast', 'dashboard'), ('two_face', 'card'), ('demons', 'tape')]
os.makedirs('out/tr', exist_ok=True)
code, m0, stats = RS.CASES[0]
for key, tpl in PAIRS:
    try:
        wav = owner_tracks.wav(key)
        with wave.open(wav) as w:
            length = w.getnframes() / w.getframerate()
        a = track_sync.analyze(wav)
        u = a['beat']
        while u < 0.7:
            u *= 2
        while u > 1.1:
            u /= 2
        base = make.TEMPLATES[tpl]
        mod, cls = base[0], base[1]
        if len(base) > 5:                                     # 12.10: доли до дропа — свои
            need = base[5] * u
        else:
            c = json.load(open(os.path.join(make.CFG, mod + '.json'), encoding='utf-8'))
            need = c.get('drop_beats', 20) * u
        tail = 9.0                                            # после дропа в ролике ещё ~5–8 с
        ok = [d for d in a['drops'] if d >= need + 0.3 and d + tail <= length]
        tdrop = ok[0] if ok else max([d for d in a['drops'] if d >= need + 0.3] or [need + 0.3])
        name = '%s_%s' % (tpl, key)
        make.TEMPLATES[name] = (mod, cls, key, round(u, 6), tdrop) + tuple(base[5:])
        m = dict(m0, tpl=name)
        r, k2, start = make.reel(m, stats, code)
        P = dict(matches=[m], all=[dict(d=m['d'], h=m['h'], a=m['a'])])
        r.ticker_tag, r.ticker = make.ticker(P, 'КХЛ')
        C.render(r, 'out/tr/%s.mp4' % key, track=wav, start=start)
        print('NEWTRACK %s %s | bpm %.2f, доля %.4f, дроп %.3f (кандидаты %s), длина %.1f, старт %.2f | %s'
              % (key, tpl, a['bpm'], u, tdrop, a['drops'][:6], length, start,
                 repr((mod, cls, key, round(u, 6), tdrop) + tuple(base[5:]))), flush=True)
    except Exception as e:  # noqa: BLE001 — остальные пробы всё равно собираем
        print('NEWTRACKERR %s %s %r' % (key, tpl, e), flush=True)
