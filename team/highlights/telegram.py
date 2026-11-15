# -*- coding: utf-8 -*-
"""Сторис «Переходи в Telegram» для актуального + обложка в стиле «ЭКСПРЕСС · ИТОГИ» (владелец 15.11).
Внизу кадра — свободное место со стрелкой под стикер «Ссылка» (через API не ставится — владелец добавляет в приложении).
    PYTHONPATH=render python3 team/highlights/telegram.py out/highlights/telegram"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covers as C  # noqa: E402
from covers import CX, CY, W, H, ICE, WIN, WHITE, DARK, base, check, font, ring, mv  # noqa: E402,F401
from PIL import ImageDraw  # noqa: E402

ROWS = ['Прогноз на каждый матч КХЛ и НХЛ', 'Экспрессы дня — и их итоги', 'Итоги прогнозов каждое утро',
        'Зашло или нет — ничего не удаляю']


def plane(d, cx, cy, s, col, shade):
    """Бумажный самолётик (не логотип Telegram)."""
    d.polygon([(cx - s, cy - s * .05), (cx + s * .95, cy - s * .8), (cx + s * .55, cy + s * .85), (cx - s * .05, cy + s * .3)], fill=col)
    d.polygon([(cx - s * .05, cy + s * .3), (cx + s * .95, cy - s * .8), (cx + s * .05, cy + s * .72)], fill=shade)


def story(out):
    img, d = base()
    mv._brand(d, CX, 250, 'KHL+NHL', 15, ICE)
    r = 120                                               # значок
    d.ellipse((CX - r, 360, CX + r, 360 + 2 * r), fill=ICE)
    plane(d, CX - 8, 360 + r, 70, WHITE, (205, 232, 250))
    mv._txt(d, CX, 760, 'ВСЁ — В TELEGRAM', mv._fit_w('ВСЁ — В TELEGRAM', 'AlumniSans[wght].ttf', 900, 150, W - 140), WHITE)
    f = font('Manrope[wght].ttf', 40, 700)
    y = 880
    for t in ROWS:
        d.rounded_rectangle((90, y, W - 90, y + 104), radius=52, fill=(34, 37, 46), outline=(64, 70, 86), width=3)
        d.ellipse((116, y + 24, 172, y + 80), fill=WIN)
        check(d, 144, y + 54, 30, WHITE, 7)
        d.text((200, y + 52), t, font=f, fill=WHITE, anchor='lm')
        y += 128
    fb = font('Oswald[wght].ttf', 46, 600)
    d.text((CX, y + 40), 'БЕСПЛАТНО  ·  @JARVIBET', font=fb, fill=ICE, anchor='mm')
    # место под стикер «Ссылка»: подпись и стрелка, ниже пусто
    fl = font('Oswald[wght].ttf', 54, 700)
    d.text((CX, 1560), 'ЖМИ НА ССЫЛКУ', font=fl, fill=WHITE, anchor='mm')
    d.line([(CX - 40, 1610), (CX, 1650), (CX + 40, 1610)], fill=ICE, width=12, joint='curve')
    img.save(out, quality=95)


def cover(out):
    """Обложка актуального: как «ЭКСПРЕСС · ИТОГИ» — кольцо, слово крупно, подпись и значок."""
    img, d = base()
    ring(d)
    mv._txt(d, CX, CY - 60, 'TELEGRAM', mv._fit_w('TELEGRAM', 'AlumniSans[wght].ttf', 900, 210, 620), WHITE)
    f2 = font('Oswald[wght].ttf', 64, 600)
    d.text((CX, CY + 75), 'П Е Р Е Й Т И', font=f2, fill=ICE, anchor='mm')
    d.ellipse((CX - 52, CY + 140, CX + 52, CY + 244), fill=ICE)
    plane(d, CX - 4, CY + 192, 34, WHITE, (205, 232, 250))
    img.save(out, quality=95)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/highlights/telegram'
    os.makedirs(out, exist_ok=True)
    s, c = os.path.join(out, 'tg_story.jpg'), os.path.join(out, 'tg_cover.jpg')
    story(s)
    cover(c)
    C.preview([os.path.join(HERE, '..', '..', 'out/highlights/covers/cover_2_tekst.jpg'), c], os.path.join(out, 'preview.jpg'),
              ['Экспресс', 'Telegram'])
    print(s, c, sep='\n')
