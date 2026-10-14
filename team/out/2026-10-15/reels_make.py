# -*- coding: utf-8 -*-
"""Пять новых форматов роликов 15.10 (ночь НХЛ 14→15 октября: Вашингтон — Монреаль 02:30, Колорадо — Даллас 03:30 МСК),
у каждого своё наполнение (просьба владельца 14.10: разная информация, история зашедших ставок в кэфах 1,6–2,2, экспрессы):
  flap   «Табло»  (truck, 65 BPM, удар 104,34 с)     — что заходило у канала в кэфах 1,60–2,20 (team/PICKS.md, честный итог
                                                      9 из 16) → прогноз на Колорадо;
  pulse  «Пульс»  (xperience, 60 BPM, дроп 18,01 с)  — форма Колорадо кардиограммой: 6 последних матчей, высота зубца — шайбы;
  scales «Весы»   (bats, 73 BPM, дроп 39,46 с)       — Вашингтон и Монреаль на весах: 6 показателей сезона, перевес 4:2;
  vault  «Сейф»   (skywalker, 67,5 BPM, дроп 28,54 с) — очные встречи прошлого сезона как код сейфа;
  chain  «Цепь»   (rodeo, 67 BPM, дроп 34,27 с)       — экспресс из двух событий: звенья цепи, замок с общим кэфом.
Линия П1/Х/П2 — из таблицы владельца (событие «matchi» 14.10, 18:04 МСК). Цифры клубов — официальный API НХЛ
(team/out/2026-10-15/nhl_fetch_1015.py, run 128, 14.10 21:21 МСК). Прогнозы в образцах — фавориты линии в основное время
(в вилке кэфов ≈2,2); публикует и выбирает прогнозы владелец.
Запуск из корня: TRACKS_DIR=<папка с треками .wav> OUT=<папка> PYTHONPATH=render python team/out/2026-10-15/reels_make.py [flap …]
Треки в репозиторий не кладём; в OUT: <имя>.mp4 (с треком), <имя>_clean.mp4 (без музыки), <имя>_cover.jpg."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
import nhl  # noqa: E402
nhl.register()
from reels import core as C  # noqa: E402
from reels.chain import Chain  # noqa: E402
from reels.flap import Flap  # noqa: E402
from reels.pulse import Pulse  # noqa: E402
from reels.scales import Scales  # noqa: E402
from reels.vault import Vault  # noqa: E402

OUT = os.environ.get('OUT') or os.path.join(ROOT, 'team', 'out', '2026-10-15', 'reels')
TR = os.environ.get('TRACKS_DIR', '')
WSH_MTL = dict(when='ЧТ 15.10 · 02:30 МСК', line=(2.27, 4.30, 2.65))
COL_DAL = dict(when='ЧТ 15.10 · 03:30 МСК', line=(2.18, 4.24, 2.81))

# прогнозы канала в кэфах 1,60–2,20, которые зашли (PICKS.md, 10–14.10); всего в вилке 16, зашло 9
HISTORY = [('КАРОЛИНА', 'П2', 1.66), ('КОЛОРАДО', 'ТБ6.5', 2.08), ('АНАХАЙМ', 'П2+ОТ', 1.87), ('АМУР', 'П1', 1.84),
           ('ОТТАВА', '2Х+ТБ', 2.12), ('БОСТОН', 'П2+ОТ', 1.84), ('АДМИРАЛ', 'П1+ОТ', 1.67), ('БАРЫС', 'ИТБ2.5', 1.79),
           ('ФЛА-МИН', 'ТМ6', 1.67)]


def build(name):
    if name == 'flap':
        u = 60 / 65
        r = Flap('Колорадо', 'Даллас', 'NHL', COL_DAL['when'], COL_DAL['line'], HISTORY, (9, 16, 'КЭФ 1.6-2.2 С 10.10'),
                 'КОЛОРАДО', 'home', 'ПОБЕДА', 'В ОСНОВНОЕ ВРЕМЯ', 2.18, '15 ОКТЯБРЯ', u=u, drop=11.5 * u)
        return r, 'truck', 104.34          # удар баса на 0,36 с позже точки 103,98 (проверено по огибающей)
    if name == 'pulse':
        games = [('Лос-Анджелес', 'В', 8, 4, ''), ('Сент-Луис', 'В', 6, 1, ''), ('Виннипег', 'П', 2, 3, ''),
                 ('Калгари', 'В', 7, 3, ''), ('Торонто', 'П', 3, 6, ''), ('Даллас', 'В', 3, 2, '')]
        tiles = [('ПОБЕДЫ', '4 ИЗ 6'), ('ШАЙБ ЗА ИГРУ', '4.83'), ('БОЛЬШИНСТВО', '23.8%'), ('МАККИННОН', '5+7 ЗА 6 ИГР')]
        r = Pulse('Колорадо', 'Даллас', 'NHL', COL_DAL['when'], COL_DAL['line'], games, tiles, 'home', 'ПОБЕДА КОЛОРАДО',
                  'В ОСНОВНОЕ ВРЕМЯ', 2.18, u=1.0, drop=12.0)
        return r, 'xperience', 18.01
    if name == 'scales':
        st = [('ЗАБИВАЮТ ЗА ИГРУ', '3.17', '2.83', 'home', 'ГОЛЫ'), ('СЕРИЯ', '2 ПОРАЖ.', '2 ПОБЕДЫ', 'away', 'СЕРИЯ'),
              ('ПРОПУСКАЮТ ЗА ИГРУ', '3.00', '3.67', 'home', 'ОБОРОНА'), ('ВБРАСЫВАНИЯ', '50.9%', '53.1%', 'away', 'ВБРАС.'),
              ('БОЛЬШИНСТВО', '13.3%', '10.0%', 'home', 'БОЛЬШ.'), ('МЕНЬШИНСТВО', '86.4%', '80.8%', 'home', 'МЕНЬШ.')]
        r = Scales('Вашингтон', 'Монреаль', 'NHL', WSH_MTL['when'], WSH_MTL['line'], st, 'home', 'ПОБЕДА ВАШИНГТОНА',
                   'В ОСНОВНОЕ ВРЕМЯ', 2.27, u=60 / 73)
        return r, 'bats', 39.46
    if name == 'vault':
        m = [('20.11.25', 'МОНРЕАЛЬ', 'ВАШИНГТОН', 4, 8, '', True), ('13.01.26', 'ВАШИНГТОН', 'МОНРЕАЛЬ', 3, 2, 'ОТ', True),
             ('28.02.26', 'МОНРЕАЛЬ', 'ВАШИНГТОН', 6, 2, '', False)]
        f = ['ВАШИНГТОН ВЗЯЛ 2 ИЗ 3', '8.3 ШАЙБЫ ЗА МАТЧ', 'ОБЕ ИГРАЛИ ВЧЕРА']
        r = Vault('Вашингтон', 'Монреаль', 'NHL', WSH_MTL['when'], WSH_MTL['line'], m, f, 'home', 'ПОБЕДА ВАШИНГТОНА',
                  'В ОСНОВНОЕ ВРЕМЯ', 2.27, u=60 / 67.5)
        return r, 'skywalker', 28.54
    if name == 'chain':
        legs = [('Вашингтон', 'Монреаль', 'NHL', 'ПОБЕДА ВАШИНГТОНА', 2.27, 'ДОМА 2 ПОБЕДЫ В 3 МАТЧАХ', 'ЧТ 02:30 МСК'),
                ('Колорадо', 'Даллас', 'NHL', 'ПОБЕДА КОЛОРАДО', 2.18, '29 ШАЙБ ЗА 6 МАТЧЕЙ — ЛУЧШЕЕ НАПАДЕНИЕ', 'ЧТ 03:30 МСК')]
        r = Chain(legs, 'ЭКСПРЕСС ДНЯ', 'ЧТ 15.10 · НХЛ', u=60 / 67)
        return r, 'rodeo', 34.27
    raise KeyError(name)


FILES = {'flap': 'flap_colorado', 'pulse': 'pulse_colorado', 'scales': 'scales_washington', 'vault': 'vault_washington',
         'chain': 'chain_express'}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name in (sys.argv[1:] or list(FILES)):
        r, track, tdrop = build(name)
        start = tdrop - r.drop
        wav = os.path.join(TR, track + '.wav') if TR else None
        base = os.path.join(OUT, FILES[name])
        C.render(r, base + '.mp4', track=wav if wav and os.path.exists(wav) else None, start=start,
                 extra_out=base + '_clean.mp4')
        print('%s: %.2f с, дроп %.2f с, трек %s с %.2f с' % (FILES[name], r.dur, r.drop, track, start), flush=True)
