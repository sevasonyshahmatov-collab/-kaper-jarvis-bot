# -*- coding: utf-8 -*-
"""Проверка шаблонов шортсов на неудобных данных (владелец 19.10: «чтобы нигде текст не налезал на другой»).
Все шаблоны конвейера (team/reels_daily/make.py TEMPLATES) × худшие случаи: длинные названия клубов, длинный прогноз
с «в основное время», тотал на обе команды, длинные соперники и счёт с ОТ/Б в последних играх. По каждому шаблону —
лист кадров (6 моментов × случаи) в <папка>/<шаблон>.jpg. Треки не нужны (только кадры).

    PYTHONPATH=render python tools/reels_stress.py <папка> [шаблон …]
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('team/reels_daily', 'team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import make  # noqa: E402
from reels import core as C  # noqa: E402


def club(league, opp, pts, gp, place, gd, res='ППВ', ot=True):
    last = []
    for i, r in enumerate(res):
        last.append(dict(date='%02d.10' % (16 - 2 * i), opp=opp[i % len(opp)], home=i % 2 == 0,
                         score=('2:3 ОТ' if (ot and i == 0) else ('5:4' if r == 'В' else '1:6')),
                         res=r if not (ot and i == 0) else 'П'))
    return dict(league=league, last3=last, points=pts, games=gp, place=place, gd=gd)


CASES = [
    ('KHL', dict(h='Шанхайские Драконы', a='Салават Юлаев', d='2026-10-19 19:30', x1x2=[3.42, 3.77, 1.94], odds=1.94,
                 pick='Победа Салавата Юлаева в основное время'),
     {'Шанхайские Драконы': club('KHL', ['Динамо Москва', 'Автомобилист', 'Металлург'], 18, 14, '6 на Западе', 2),
      'Салават Юлаев': club('KHL', ['Шанхайские Драконы', 'Нефтехимик', 'Динамо Минск'], 22, 16, '11 на Востоке',
                            -12, 'ВПВ')}),
    ('NHL', dict(h='Филадельфия', a='Коламбус', d='2026-10-20 02:00', x1x2=[2.15, 4.22, 2.81], odds=2.04,
                 pick='Индивидуальный тотал Коламбуса меньше 2,5 в основное время'),
     {'Филадельфия': club('NHL', ['Лос-Анджелес', 'Тампа-Бэй', 'Нью-Джерси'], 11, 9, '12 на Востоке', -4),
      'Коламбус': club('NHL', ['Рейнджерс', 'Питтсбург', 'Филадельфия'], 6, 6, '15 на Востоке', -4, 'ВВП')}),
    ('NHL', dict(h='Юта', a='Питтсбург', d='2026-10-20 04:00', x1x2=[1.90, 4.43, 3.26], odds=2.07,
                 pick='Тотал матча больше 6,5 в основное время'),
     {'Юта': club('NHL', ['Сан-Хосе', 'Сент-Луис', 'Ванкувер'], 12, 9, '4 на Западе', 6, 'ВВВ', False),
      'Питтсбург': club('NHL', ['Филадельфия', 'Айлендерс', 'Монреаль'], 9, 8, '9 на Востоке', -3)}),
]
MOMENTS = (0.08, 0.3, 0.5, 0.66, 0.8, 0.9)
TW, TH = 270, 480


def sheet(tpl, out):
    rows = []
    for k, (code, m, stats) in enumerate(CASES):
        m = dict(m, tpl=tpl)
        if code == 'NHL':
            import nhl
            nhl.register()
        r, _, _ = make.reel(m, stats, code)
        P = dict(matches=[m], all=[dict(d=m['d'], h=m['h'], a=m['a']), dict(d=m['d'], h='Динамо Москва', a='Автомобилист')])
        r.ticker_tag, r.ticker = make.ticker(P, 'КХЛ' if code == 'KHL' else 'НХЛ')
        fr = [int(round(r.dur * q * C.FPS)) for q in MOMENTS]
        files = C.render(r, os.path.join(out, '_%s_%d.mp4' % (tpl, k)), frames=fr)
        rows.append([Image.open(f).convert('RGB').resize((TW, TH)) for f in files])
        for f in files:
            os.remove(f)
    s = Image.new('RGB', (TW * len(MOMENTS) + 4 * (len(MOMENTS) - 1), TH * len(rows) + 6 * (len(rows) - 1)), 'white')
    for i, row in enumerate(rows):
        for j, im in enumerate(row):
            s.paste(im, (j * (TW + 4), i * (TH + 6)))
    p = os.path.join(out, tpl + '.jpg')
    s.save(p, quality=86)
    return p


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for tpl in sys.argv[2:] or list(make.TEMPLATES):
        try:
            print(sheet(tpl, out), flush=True)
        except Exception as e:  # noqa: BLE001
            print('ERR', tpl, repr(e), flush=True)


if __name__ == '__main__':
    main()
