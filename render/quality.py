"""Размер готовых баннеров.

Текст, эмблемы и плашки всегда рисуются вдвое крупнее базового размера (S = 2). Раньше в конце картинка уменьшалась
до базового (1280×640 у «Боков», 1080×1350 у постеров); при SCALE = 2 уменьшения нет: «Бока» 2560×1280,
постер 2160×2700 — это предел, который Telegram показывает у фото в режиме HD (2560 по длинной стороне).
Плавный фон (шёлк, лёд) просто увеличивается, а зерно и «нити» холста накладываются так, чтобы на глаз
выглядеть как раньше. SCALE = 1 (или переменная окружения JARVIS_SCALE=1) — прежний размер.
"""
import os

import numpy as np
from PIL import Image

import poster

SCALE = 2 if os.environ.get('JARVIS_SCALE', '2') != '1' else 1


def texture(img, strength, seed=3):
    """Текстура холста poster._canvas_texture, но в масштабе базового размера: при SCALE = 2 нити и зерно
    считаются на уменьшенной копии и переносятся на большую картинку — тот же вид, что у баннера 1×."""
    if not strength:
        return img.convert('RGB')
    if SCALE == 1:
        return poster._canvas_texture(img, strength, seed)
    big = img.convert('RGB')
    W, H = big.size
    small = big.resize((W // SCALE, H // SCALE), Image.LANCZOS)
    d = np.asarray(poster._canvas_texture(small, strength, seed), np.float32) - np.asarray(small, np.float32)
    d = np.stack([np.asarray(Image.fromarray(d[..., c]).resize((W, H), Image.BICUBIC)) for c in range(3)], -1)
    return Image.fromarray(np.clip(np.asarray(big, np.float32) + d, 0, 255).astype('uint8'), 'RGB')


def compose(bg, ov):
    """Фон + слой с текстом и эмблемами: при SCALE = 2 фон увеличивается до слоя, иначе слой уменьшается до фона."""
    if SCALE == 2 and ov.size != bg.size:
        return Image.alpha_composite(bg.convert('RGBA').resize(ov.size, Image.LANCZOS), ov)
    return Image.alpha_composite(bg.convert('RGBA'), ov.resize(bg.size, Image.LANCZOS) if ov.size != bg.size else ov)
