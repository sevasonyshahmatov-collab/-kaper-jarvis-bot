# -*- coding: utf-8 -*-
"""Фоны команд для мини-приложения через Gemini (владелец 25.10: «отрисовать покрасивее — в Gemini / Nano Banana»).
Сцена каждой команды — team/site/app_data/bg_prompts.json (ассоциации: Колорадо — горы, Локомотив — поезд, ЦСКА — кони…),
общий стиль — STYLE ниже. Результат — team/site/app/bg/<эмблема>.webp (1600×900) и список готовых bg/photos.json — приложение
берёт картинку, а где её нет — нарисованный рисунок-маску (bg_art.py). Ключ — секрет GEMINI_API_KEY (Google AI Studio),
модель — GEMINI_IMAGE_MODEL (по умолчанию gemini-2.5-flash-image, «Nano Banana»). Генерация платная — по ключу владельца.

    python team/site/app_data/bg_ai.py nhl_col lokomotiv cska      # эти команды
    python team/site/app_data/bg_ai.py all [--force]                # все, у кого картинки ещё нет (--force — заново)
"""
import base64
import io
import json
import os
import sys
import time

import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'app', 'bg')
MODEL = os.environ.get('GEMINI_IMAGE_MODEL') or 'gemini-2.5-flash-image'
API = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % MODEL

STYLE = ('Cinematic wide digital painting used as a background for a sports app, landscape 16:9. Scene: {scene}. '
         'Mood: dramatic night or dusk, volumetric light, atmospheric haze, rich depth, premium illustration. '
         'Color palette dominated by {c1} and {c2} with deep dark shadows. Composition: the main subject on the right two thirds, '
         'a calmer darker area on the left for text overlay. No text, no letters, no numbers, no logos, no emblems, no watermarks, '
         'no recognizable people, no hockey players.')


def generate(key, slug, spec):
    body = {'contents': [{'parts': [{'text': STYLE.format(scene=spec['scene'], c1=spec['colors'][0], c2=spec['colors'][1])}]}],
            'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '16:9'}}}
    for k in range(3):
        r = requests.post(API, params={'key': key}, json=body, timeout=180)
        if r.status_code == 200:
            for c in r.json().get('candidates') or []:
                for p in (c.get('content') or {}).get('parts') or []:
                    data = (p.get('inlineData') or p.get('inline_data') or {}).get('data')
                    if data:
                        return Image.open(io.BytesIO(base64.b64decode(data)))
            raise RuntimeError('в ответе нет картинки: %s' % json.dumps(r.json(), ensure_ascii=False)[:300])
        if r.status_code in (429, 500, 503) and k < 2:
            time.sleep(20 * (k + 1))
            continue
        raise RuntimeError('HTTP %s: %s' % (r.status_code, r.text[:300]))


def save(im, slug):
    im = im.convert('RGB')
    w, h = im.size                                     # обрезка до 16:9 и 1600×900
    if w / h > 16 / 9:
        nw = int(h * 16 / 9)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * 9 / 16)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im.resize((1600, 900), Image.LANCZOS).save(os.path.join(OUT, slug + '.webp'), quality=80, method=6)


def main():
    a = sys.argv[1:]
    key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not key:
        raise SystemExit('BGERR нет секрета GEMINI_API_KEY')
    specs = json.load(open(os.path.join(HERE, 'bg_prompts.json'), encoding='utf-8'))
    force = '--force' in a
    want = [x for x in a if not x.startswith('--')]
    slugs = list(specs) if not want or want == ['all'] else [x for x in want if x in specs]
    os.makedirs(OUT, exist_ok=True)
    done, errs = [], []
    for slug in slugs:
        if not force and os.path.exists(os.path.join(OUT, slug + '.webp')):
            continue
        try:
            save(generate(key, slug, specs[slug]), slug)
            done.append(slug)
            print('BG %s готово' % slug, flush=True)
        except Exception as e:  # noqa: BLE001 — одна команда не вышла — остальные всё равно
            errs.append(slug)
            print('BGERR %s: %s' % (slug, e), flush=True)
    have = sorted(f[:-5] for f in os.listdir(OUT) if f.endswith('.webp'))
    with open(os.path.join(OUT, 'photos.json'), 'w', encoding='utf-8') as f:
        json.dump(have, f)
    print('BG итого: новых %d, ошибок %d, всего картинок %d' % (len(done), len(errs), len(have)), flush=True)


if __name__ == '__main__':
    main()
