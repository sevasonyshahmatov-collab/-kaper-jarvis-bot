# -*- coding: utf-8 -*-
"""Ролики v3: 3 пробы бесплатного русского голоса одной фразой → владельцу в бот (ТЗ REELS_V3_BRIEF.md, шаг 3).

Запуск в Actions как make-скрипт задания: python team/reels_v3/voice_probe.py <задание.json>
Каждая проба — короткое видео (карточка + голос); удачные дописываются в messages задания, неудачные — строкой в отчёт.
"""
import json
import os
import subprocess
import sys
import time
import traceback
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_v3'))
import tts  # noqa: E402

PHRASE = ('Что будет, если весь сезон ставить на тотал больше четырёх с половиной в матчах Адмирала? '
          'Семнадцать матчей. Считаем. И вот итог.')
PROBES = [
    ('A', 'edge:ru-RU-DmitryNeural', 'Edge TTS · Дмитрий (мужской)', 'нейроголос Microsoft, бесплатно; условия коммерческого использования не прописаны'),
    ('B', 'qwen', 'Qwen3-TTS · голос по описанию', 'открытая модель Alibaba, Apache-2.0 — можно в коммерции'),
    ('C', 'vosk:2', 'Vosk TTS (Alpha Cephei)', 'открытая модель, Apache-2.0, работает без интернета'),
    ('D', 'edge:ru-RU-SvetlanaNeural', 'Edge TTS · Светлана (женский)', 'тот же движок, что A, — женский вариант'),
]
FONT = os.path.join(ROOT, 'render', 'fonts', 'Unbounded[wght].ttf')
FONT2 = os.path.join(ROOT, 'render', 'fonts', 'GolosText[wght].ttf')


def card(path, letter, title, note):
    im = Image.new('RGB', (1080, 1080), (12, 14, 20))
    d = ImageDraw.Draw(im)
    d.text((540, 380), letter, font=ImageFont.truetype(FONT, 330), fill=(232, 190, 92), anchor='mm')
    d.text((540, 680), title, font=ImageFont.truetype(FONT2, 52), fill=(240, 240, 240), anchor='mm')
    d.text((540, 760), note[:60], font=ImageFont.truetype(FONT2, 32), fill=(150, 150, 160), anchor='mm')
    d.text((540, 990), 'Проба голоса · ролики v3 · @jarvibet', font=ImageFont.truetype(FONT2, 30),
           fill=(110, 110, 120), anchor='mm')
    im.save(path)


def to_mp4(png, wav, sr, out):
    w16 = (np.clip(wav / max(1e-6, np.abs(wav).max()) * 0.9, -1, 1) * 32767).astype(np.int16)
    wp = out[:-4] + '.wav'
    with wave.open(wp, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(w16.tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', png, '-i', wp, '-c:v', 'libx264', '-tune',
                    'stillimage', '-pix_fmt', 'yuv420p', '-r', '10', '-c:a', 'aac', '-b:a', '160k', '-shortest', out],
                   check=True)


def main(job_path):
    tts.ensure_ffmpeg()
    outdir = os.path.join(os.path.dirname(job_path), 'voice_probe')
    os.makedirs(outdir, exist_ok=True)
    msgs, report = [], []
    for letter, spec, title, note in PROBES:
        t0 = time.time()
        try:
            try:
                wav = tts.say(PHRASE, spec)
            except Exception:
                if spec != 'qwen':
                    raise
                traceback.print_exc()
                spec, title, note = 'chat', 'Chatterbox · мультиязычный', 'открытая модель Resemble AI, MIT — можно в коммерции'
                wav = tts.say(PHRASE, spec)
            png = os.path.join(outdir, '%s.png' % letter)
            mp4 = os.path.join(outdir, 'voice_%s.mp4' % letter)
            card(png, letter, title, note)
            to_mp4(png, wav, tts.SR, mp4)
            print('VOICE %s ok %s %.1f с звука, %.0f с синтеза' % (letter, spec, len(wav) / tts.SR, time.time() - t0),
                  flush=True)
            msgs.append({'to': 'owner', 'type': 'video', 'files': [os.path.relpath(mp4, ROOT)],
                         'text': '%s — %s\n%s' % (letter, title, note)})
        except Exception as e:
            traceback.print_exc()
            print('VOICE %s fail %s %s' % (letter, spec, e), flush=True)
            report.append('%s (%s) — не собрался: %s' % (letter, title, str(e)[:120]))
    with open(job_path, encoding='utf-8') as f:
        job = json.load(f)
    head = job['messages'][0]
    if report:
        head['text'] += '\n\nНе получилось: ' + '; '.join(report)
    job['messages'] = [head] + msgs + job['messages'][1:]
    with open(job_path, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
