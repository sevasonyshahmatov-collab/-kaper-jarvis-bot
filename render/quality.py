"""Размер готовых баннеров.

Текст, эмблемы и плашки рисуются в S раз крупнее базового размера (1280×640 у «Боков», 1080×1350 у постеров).
С 10.10.2026 S = 3 — «4К»: «Бока» 3840×1920, постер 3240×4050. Было S = 2 (2560×1280, 2160×2700).
Плавный фон (шёлк, лёд) рисуется в базовом размере и просто увеличивается, а зерно и «нити» холста накладываются так,
чтобы на глаз выглядеть как раньше. Переменные окружения: JARVIS_S=2 — прежний размер 2×; JARVIS_SCALE=1 — уменьшить до базового.
Telegram показывает фото не больше 2560 по длинной стороне: 4К-файл он сожмёт сам, полный размер — если отправить файлом.
"""
import os

import numpy as np
from PIL import Image, ImageFile

ImageFile.MAXBLOCK = max(ImageFile.MAXBLOCK, 1 << 24)   # 4К-JPEG с optimize=True: иначе «Suspension not allowed here»

import poster

S = max(1, int(os.environ.get('JARVIS_S', '3') or 3))                # во сколько раз крупнее базового рисуем
SCALE = 1 if os.environ.get('JARVIS_SCALE') == '1' else S         # итоговый размер: 1 — уменьшить до базового


def texture(img, strength, seed=3):
    """Текстура холста poster._canvas_texture, но в масштабе базового размера: при SCALE > 1 нити и зерно
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
    """Фон + слой с текстом и эмблемами: при SCALE > 1 фон увеличивается до слоя, иначе слой уменьшается до фона."""
    if SCALE > 1 and ov.size != bg.size:
        return Image.alpha_composite(bg.convert('RGBA').resize(ov.size, Image.LANCZOS), ov)
    return Image.alpha_composite(bg.convert('RGBA'), ov.resize(bg.size, Image.LANCZOS) if ov.size != bg.size else ov)
