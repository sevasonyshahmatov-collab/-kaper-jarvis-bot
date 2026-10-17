# -*- coding: utf-8 -*-
"""Проба голосов для озвучки длинных видео YouTube (владелец 17.10: «голос давай послушаю»).
Один и тот же текст разными нейросетевыми голосами — русский (канал КХЛ + НХЛ) и английский (канал НХЛ для США).

    python team/out/2026-10-17/voices/make_voices.py [base|chatterbox] --job <задание.json>

base — Microsoft (edge-tts), Silero, Piper, Kokoro; chatterbox — Chatterbox Multilingual (тяжёлый, отдельным заданием).
Каждый движок в своём try: упавший пропускается. Результат — out/<id>.mp3 и out/<id>.mp4 (чёрный кадр с подписью —
чтобы попасть в артефакт «videos»), в задание дописываются сообщения владельцу (по файлу на голос).
"""
import json
import os
import shutil
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

RU = ('Авангард принимает Автомобилист. Омичи выиграли два из трёх последних матчей и набрали двенадцать очков. '
      'Автомобилист в отличной форме: три победы подряд и лучшая разница шайб на Востоке. '
      'Наш прогноз — Автомобилист не проиграет в основное время. Коэффициент — один семьдесят один.')
EN = ('Tonight in Anaheim, the Ducks host the Boston Bruins. Boston has scored seventeen goals in its last three wins, '
      'while Anaheim is allowing nearly four goals a game at home. '
      'Our pick: Boston over two and a half team goals, at minus one fifty-nine.')

BASE = [
    ('ru_1_microsoft_dmitry', 'RU · Microsoft «Дмитрий» (мужской)', 'edge', 'ru-RU-DmitryNeural', RU),
    ('ru_2_microsoft_svetlana', 'RU · Microsoft «Светлана» (женский)', 'edge', 'ru-RU-SvetlanaNeural', RU),
    ('ru_3_silero_eugene', 'RU · Silero «Евгений» (мужской)', 'silero', 'eugene', RU),
    ('ru_4_piper_dmitri', 'RU · Piper «Дмитрий» (мужской)', 'piper', 'ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium', RU),
    ('en_1_microsoft_andrew', 'EN · Microsoft «Andrew» (мужской, США)', 'edge', 'en-US-AndrewNeural', EN),
    ('en_2_microsoft_christopher', 'EN · Microsoft «Christopher» (мужской, США)', 'edge', 'en-US-ChristopherNeural', EN),
    ('en_3_kokoro_michael', 'EN · Kokoro «Michael» (мужской, США)', 'kokoro', 'am_michael', EN),
    ('en_4_piper_ryan', 'EN · Piper «Ryan» (мужской, США)', 'piper', 'en/en_US/ryan/high/en_US-ryan-high', EN),
]
HEAVY = [
    ('ru_5_chatterbox', 'RU · Chatterbox (мужской)', 'chatterbox', 'ru', RU),
    ('en_5_chatterbox', 'EN · Chatterbox (мужской)', 'chatterbox', 'en', EN),
]


def sh(cmd, **kw):
    print('$', ' '.join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    return subprocess.run(cmd, check=True, **kw)


def pip(*pk, index=None):
    cmd = [sys.executable, '-m', 'pip', 'install', '-q'] + list(pk) + (['--index-url', index] if index else [])
    sh(cmd)


def to_mp3(src, dst):
    sh(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-ac', '1', '-ar', '44100', '-b:a', '160k', dst])


def save_wav(path, audio, sr):
    import numpy as np
    a = (np.clip(np.asarray(audio, dtype='float32').reshape(-1), -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())


def eng_edge(voice, text, wav):
    pip('edge-tts')
    mp3 = wav[:-4] + '_e.mp3'
    sh([sys.executable, '-m', 'edge_tts', '--voice', voice, '--rate=-4%', '--text', text, '--write-media', mp3])
    sh(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp3, wav])


def eng_silero(speaker, text, wav):
    pip('torch', index='https://download.pytorch.org/whl/cpu')
    pip('omegaconf')
    import torch
    model, _ = torch.hub.load('snakers4/silero-models', 'silero_tts', language='ru', speaker='v4_ru', trust_repo=True)
    audio = model.apply_tts(text=text, speaker=speaker, sample_rate=48000, put_accent=True, put_yo=True)
    save_wav(wav, audio.numpy(), 48000)


def eng_piper(path, text, wav):
    pip('piper-tts')
    base = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/' + path
    model = os.path.join(OUT, os.path.basename(path) + '.onnx')
    for ext in ('.onnx', '.onnx.json'):
        sh(['curl', '-sSL', '-o', model[:-5] + ext, base + ext])
    from piper import PiperVoice
    v = PiperVoice.load(model)
    with wave.open(wav, 'wb') as w:
        if hasattr(v, 'synthesize_wav'):
            v.synthesize_wav(text, w)
        else:
            v.synthesize(text, w)


def eng_kokoro(voice, text, wav):
    pip('torch', index='https://download.pytorch.org/whl/cpu')
    pip('kokoro>=0.9', 'soundfile')
    import numpy as np
    from kokoro import KPipeline
    pl = KPipeline(lang_code='a')
    parts = [a for _, _, a in pl(text, voice=voice, speed=0.95)]
    save_wav(wav, np.concatenate([np.asarray(p) for p in parts]), 24000)


def eng_chatterbox(lang, text, wav):
    pip('chatterbox-tts')
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    m = ChatterboxMultilingualTTS.from_pretrained(device='cpu')
    a = m.generate(text, language_id=lang)
    torchaudio.save(wav, a, m.sr)


ENGINES = dict(edge=eng_edge, silero=eng_silero, piper=eng_piper, kokoro=eng_kokoro, chatterbox=eng_chatterbox)


def card(title, mp3, mp4):
    """Чёрный кадр с подписью + звук — чтобы файл попал в артефакт «videos» и его можно было переслать в чат."""
    sys.path.insert(0, os.path.join(ROOT, 'render'))
    from reels import core as C
    from PIL import Image
    im = Image.new('RGB', (1080, 1080), (12, 12, 14))
    C.put(im, C.lines(title.upper(), 'mont', 54, 940, (240, 240, 244), 800), 540, 540)
    png = mp4[:-4] + '.png'
    im.save(png)
    sh(['ffmpeg', '-loglevel', 'error', '-y', '-loop', '1', '-i', png, '-i', mp3, '-c:v', 'libx264', '-tune', 'stillimage',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', mp4])
    os.remove(png)


def main():
    which = sys.argv[1]
    job = sys.argv[sys.argv.index('--job') + 1]
    need = [p for p in ('ffmpeg', 'espeak-ng') if not shutil.which(p)]
    if need:
        pre = [] if os.geteuid() == 0 else ['sudo']
        sh(pre + ['apt-get', 'update', '-qq'])
        sh(pre + ['apt-get', 'install', '-y', '-qq'] + need)
    os.makedirs(OUT, exist_ok=True)
    msgs, done = [], []
    for vid, title, eng, arg, text in (BASE if which == 'base' else HEAVY):
        wav, mp3 = os.path.join(OUT, vid + '.wav'), os.path.join(OUT, vid + '.mp3')
        try:
            ENGINES[eng](arg, text, wav)
            to_mp3(wav, mp3)
            card(title, mp3, os.path.join(OUT, vid + '.mp4'))
            msgs.append({'to': 'owner', 'type': 'documents', 'files': [os.path.relpath(mp3, ROOT)], 'captions': [title]})
            done.append(vid)
        except Exception as e:                       # noqa: BLE001 — остальные голоса всё равно делаем
            print('ГОЛОС НЕ ПОЛУЧИЛСЯ:', vid, repr(e)[:300], flush=True)
    intro = {'to': 'owner', 'type': 'text', 'text': 'Проба голосов для озвучки YouTube (%s): один текст разными голосами. '
             'Послушайте и напишите номера, которые нравятся.' % ('русский и английский' if which == 'base' else 'Chatterbox')}
    with open(os.path.join(ROOT, job), encoding='utf-8') as f:
        j = json.load(f)
    j['messages'] = [intro] + msgs
    with open(os.path.join(ROOT, job), 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    print('готово:', ', '.join(done) or 'ничего')


if __name__ == '__main__':
    main()
