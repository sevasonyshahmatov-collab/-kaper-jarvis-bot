# -*- coding: utf-8 -*-
"""Истории для хайлайтов Instagram (владелец 27.10): «Результаты», «Таблица», «Telegram», «YouTube» + обложки хайлайтов.
Кадр 1080×1920: сверху марка, в середине слайд закрепа (team/pins/make.py) или свой крупный текст, внизу — место под
стикер «Ссылка» со стрелкой. Стикер ссылки Instagram через API не ставится — владелец добавляет его в приложении.

    python team/pins/stories.py <каталог сайта> <куда>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make as P  # noqa: E402
from make import S, mv, W, ACC, INK, WHITE, GREY  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SH = 1920
LINKS = {'site': 'sevasonyshahmatov-collab.github.io', 'tg': 't.me/jarvibet', 'yt': 'youtube.com/@jarvibet'}


def frame(brand=True):
    img = mv._background(SH).convert('RGBA')
    d = ImageDraw.Draw(img)
    if brand:                                            # у слайда закрепа марка своя — второй не нужно
        mv._brand(d, W / 2, 150, 'KHL+NHL', 30, ACC)     # выше 120 px — значки Instagram
    return img, d


def link_zone(img, label, url):
    """Низ кадра: подпись и пунктирная рамка, куда ставить стикер «Ссылка»."""
    d = ImageDraw.Draw(img)
    mv._spaced(d, W / 2, 1560, label.upper(), mv._cap(mv.OSW, 700, 34), WHITE, 3)
    x0, x1, y0, y1 = 110, W - 110, 1660, 1790
    for x in range(x0, x1, 36):                          # пунктир
        d.line((x, y0, min(x + 20, x1), y0), fill=ACC, width=4)
        d.line((x, y1, min(x + 20, x1), y1), fill=ACC, width=4)
    for y in range(y0, y1, 36):
        d.line((x0, y, x0, min(y + 20, y1)), fill=ACC, width=4)
        d.line((x1, y, x1, min(y + 20, y1)), fill=ACC, width=4)
    mv._txt(d, W / 2, (y0 + y1) / 2, url, mv._fit_w(url, mv.MAN, 700, 30, x1 - x0 - 60), GREY)


def with_slide(slide_path, label, url, out):
    """Кадр со слайдом закрепа 1080×1350 (уменьшен до 92 %) и местом под ссылку."""
    img, d = frame(brand=False)
    sl = Image.open(slide_path).convert('RGBA')
    k = 0.92
    sl = sl.resize((int(sl.width * k), int(sl.height * k)), Image.LANCZOS)
    mask = Image.new('L', sl.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sl.width, sl.height), radius=36, fill=255)
    img.paste(sl, (int((W - sl.width) / 2), 160), mask)
    link_zone(img, label, url)
    return S._save(img, out)


def big(lines, sub, label, url, out, accent_last=True):
    """Свой кадр: крупные строки, подзаголовок, место под ссылку."""
    img, d = frame()
    y = 640 - 85 * (len(lines) - 1)
    for i, t in enumerate(lines):
        last = i == len(lines) - 1
        mv._txt(d, W / 2, y + i * 170, t, mv._fit_w(t, mv.ALU, 900, 150, W - 120), ACC if last and accent_last else WHITE)
    P.caption(img, sub, y + len(lines) * 170 + 60)
    link_zone(img, label, url)
    return S._save(img, out)


def cover(kind, out):
    """Обложка хайлайта: Instagram показывает круг по центру — значок в круге, без текста."""
    img = mv._background(SH).convert('RGBA')
    d = ImageDraw.Draw(img)
    cx, cy, R = W / 2, SH / 2, 330
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(28, 26, 32), outline=ACC, width=14)
    if kind == 'results':                                    # растущая линия
        pts = [(cx - 200, cy + 120), (cx - 90, cy + 20), (cx, cy + 70), (cx + 190, cy - 140)]
        d.line(pts, fill=ACC, width=34, joint='curve')
        d.polygon([(cx + 215, cy - 165), (cx + 110, cy - 150), (cx + 200, cy - 60)], fill=ACC)
    elif kind == 'table':                                    # сетка таблицы
        x0, y0, x1, y1 = cx - 190, cy - 150, cx + 190, cy + 150
        d.rounded_rectangle((x0, y0, x1, y1), radius=26, outline=ACC, width=24)
        d.line((x0, cy - 50, x1, cy - 50), fill=ACC, width=20)
        d.line((x0, cy + 50, x1, cy + 50), fill=ACC, width=20)
        d.line((cx - 60, y0, cx - 60, y1), fill=ACC, width=20)
    elif kind == 'tg':                                       # бумажный самолётик
        d.polygon([(cx - 200, cy - 10), (cx + 190, cy - 160), (cx + 110, cy + 170), (cx - 10, cy + 60)], fill=ACC)
        d.polygon([(cx - 10, cy + 60), (cx + 190, cy - 160), (cx + 10, cy + 140)], fill=(200, 160, 30))
    elif kind == 'yt':                                       # кнопка «play»
        d.rounded_rectangle((cx - 210, cy - 150, cx + 210, cy + 150), radius=70, fill=ACC)
        d.polygon([(cx - 60, cy - 85), (cx - 60, cy + 85), (cx + 95, cy)], fill=(28, 26, 32))
    return S._save(img, out)


def render(site, out_dir):
    tmp = os.path.join(out_dir, '_slides')
    os.makedirs(tmp, exist_ok=True)
    a = P.about(site, tmp)
    t = P.table(site, tmp)
    out = []
    o = lambda name: os.path.join(out_dir, name + '.jpg')  # noqa: E731
    # «Результаты»: обложка альбома, график, кольца, последние прогнозы → сайт
    for i, sl in enumerate(a[:4]):
        out.append(with_slide(sl, 'каждый прогноз со счётом', LINKS['site'], o('results_%d' % (i + 1))))
    out.append(big(['ВСЕ ПРОГНОЗЫ', 'СО СЧЁТОМ'], 'Каждый матч, и зашедшие прогнозы, и нет. Ничего не удаляю.',
                   'жми на ссылку', LINKS['site'], o('results_5')))
    # «Таблица»: обложка, что заходит, форма, рейтинг, ещё листы (скриншоты владельца добавим, когда пришлёт)
    for i, sl in enumerate([t[0], t[2], t[3], t[4], t[5]]):
        out.append(with_slide(sl, 'как получить доступ', LINKS['tg'], o('table_%d' % (i + 1))))
    # «Telegram» и «YouTube» — имиджевые
    out.append(big(['ПРОГНОЗ', 'НА КАЖДЫЙ', 'МАТЧ'], 'КХЛ и НХЛ каждый игровой день, бесплатно. Итоги — каждое утро.',
                   'подписаться в telegram', LINKS['tg'], o('tg_1')))
    out.append(with_slide(a[0], 'все прогнозы — в telegram', LINKS['tg'], o('tg_2')))
    out.append(big(['РОЛИК', 'НА КАЖДЫЙ', 'МАТЧ'], 'Разбор за 20 секунд: форма команд, линия и прогноз на дроп трека.',
                   'смотреть на youtube', LINKS['yt'], o('yt_1')))
    for k in ('results', 'table', 'tg', 'yt'):
        out.append(cover(k, o('cover_%s' % k)))
    return out


if __name__ == '__main__':
    os.makedirs(sys.argv[2], exist_ok=True)
    for p in render(sys.argv[1], sys.argv[2]):
        print('STORY', p, flush=True)
