# -*- coding: utf-8 -*-
"""Сборка серии роликов: python render/reels/run.py <формат|all> --tracks ПАПКА --out ПАПКА [--frames 0,90,300]

ПАПКА с треками — wav 44,1 кГц стерео с именами из TRACKS (tiki.wav, slx.wav, …); сами треки в репозиторий не кладём.
Для каждого формата — *_preview.mp4 (с треком, для проверки), *_clean.mp4 (без музыки, для загрузки) и *_cover.jpg.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reels import core as C  # noqa: E402

# трек: (доля сцены, с; дроп — секунда трека) — из track_sync (доля 1 или 2 доли трека)
TRACKS = {
    'tiki': (60 / 69, 10.41),        # TIKI TIKI (Slowed)
    'refl': (60 / 65, 7.25),         # Reflection
    'bbt': (60 / 77, 12.52),         # Big Baby Tape × Kizaru type beat
    'north': (120 / 142, 27.09),     # North Area (сцена — 2 доли)
    'vace': (60 / 64, 12.05),        # vacemadest
    'jefe': (60 / 81, 11.89),        # JEFE
    'rotten': (60 / 72, 15.25),      # ROTTEN (сильная доля 12,75 — за 3 доли до дропа)
    'kilo': (60 / 64, 10.08),        # Kilowatt
    'depto': (60 / 96.5, 9.98),      # DEPTO
    'kizaru': (1.0, 16.04),          # Kizaru × Alblak 52 type beat (такты по 4 с: 16,04 · 20,04 · 24,05)
    'quantum': (1.0, 8.01),          # EsDeeKid — QUANTUM (бас уходит 12,75–13,4)
    'slx': (60 / 95, 5.08),          # EsDeeKid — SLX (тишина с 12,4, второй удар 15,18)
}


def make(name):
    """→ (ролик, ключ трека, секунда трека на t=0)."""
    if name == 'pack':
        from reels import pack
        u, d = TRACKS['tiki']
        drop = 4 * u
        r = pack.Pack('Трактор', 'Сибирь', 'KHL', 'Победа Трактора', 1.85, 'СБ 10.10 · 14:00 МСК', 'Челябинск', u=u, drop=drop)
        return r, 'tiki', d - drop
    if name == 'coupon':
        from reels import coupon
        u, d = TRACKS['slx']
        legs = [('Адмирал', 'Лада', 'П1', 'победа Адмирала', 1.89, '10:00'),
                ('Трактор', 'Сибирь', 'П1', 'победа Трактора', 1.85, '14:00'),
                ('Локомотив', 'Динамо Минск', 'П1', 'победа Локомотива', 1.82, '17:00')]
        start = d - 4 * u
        r = coupon.Coupon(legs, '10.10.2026', 'KHL', u=u, drop=d - start, stop=12.40 - start, hit2=15.18 - start)
        return r, 'slx', start
    if name == 'sim':
        from reels import sim
        u, d = TRACKS['quantum']
        drop = 3 * u
        r = sim.Sim('Калгари', 'Колорадо', 'NHL', 'a', 'Победа Колорадо', 1.76, 'СБ 11.10 · 04:00 МСК', u=u, drop=drop)
        return r, 'quantum', d - drop
    if name == 'results':
        from reels import results
        u, d = TRACKS['kilo']
        drop = 2 * u
        bets = [('Бостон', 'Юта', '6:1', 'Юта не проиграет', -1.0),
                ('Оттава', 'Филадельфия', '2:1', 'Победа Оттавы', 1.05),
                ('Айлендерс', 'Чикаго', '4:1', 'Победа Айлендерс', 0.90),
                ('Сент-Луис', 'Сан-Хосе', '2:3 ОТ', 'ИТ Сент-Луиса больше 2,5', -1.0),
                ('Калгари', 'Колорадо', '3:7', 'Победа Колорадо', 0.76),
                ('Вегас', 'Торонто', '4:3 ОТ', 'Тотал больше 5,5', 0.67)]
        r = results.Results('НХЛ · ИТОГИ НОЧИ', '09→10.10', 'NHL', bets, u=u, drop=drop)
        return r, 'kilo', d - drop
    if name == 'chat':
        from reels import chat
        u, d = TRACKS['refl']
        drop = 3 * u
        r = chat.Chat('Локомотив', 'Динамо Минск', 'KHL', 'Победа Локомотива', 1.82, 'СБ 10.10 · 17:00 МСК', 67, u=u, drop=drop)
        return r, 'refl', d - drop
    if name == 'board':
        from reels import board
        u, d = TRACKS['bbt']
        drop = 3 * u
        r = board.Board('Ак Барс', 'Северсталь', 'KHL', 'Победа Ак Барса', 2.06, '10.10 · 17:00 МСК',
                        ['Ак Барс дома', 'фаворит линии: 2.06 vs 3.20'], u=u, drop=drop)
        return r, 'bbt', d - drop
    if name == 'pixel':
        from reels import pixel
        u, d = TRACKS['north']
        drop = 4 * u
        r = pixel.Pixel('Нью-Джерси', 'Ванкувер', 'NHL', 'h', 'Победа Нью-Джерси', 1.63, 'СБ 10.10 · 22:30 МСК', u=u, drop=drop)
        return r, 'north', d - drop
    if name == 'fight':
        from reels import fight
        u, d = TRACKS['jefe']
        drop = 4 * u
        roster = ['Бостон', 'Сан-Хосе', 'Торонто', 'Вегас', 'Колорадо', 'Эдмонтон', 'Нью-Джерси', 'Чикаго']
        r = fight.Fight('Сан-Хосе', 'Эдмонтон', 'NHL', 'a', 'Победа Эдмонтона', 2.04, 'СБ 10.10 · 23:00 МСК', roster, u=u, drop=drop)
        return r, 'jefe', d - drop
    if name == 'weather':
        from reels import weather
        u, d = TRACKS['vace']
        drop = 3 * u
        r = weather.Weather('Бостон', 'Филадельфия', 'NHL', 'h', 'Победа Бостона', 2.20, 'СБ 10.10 · 20:00 МСК', 58, u=u, drop=drop)
        return r, 'vace', d - drop
    if name == 'collage':
        from reels import collage
        u, d = TRACKS['rotten']
        drop = 4 * u
        r = collage.Collage('Локомотив', 'Динамо Минск', 'KHL', 'Победа Локомотива', 1.82, 'СБ 10.10 · 17:00 МСК', u=u, drop=drop)
        return r, 'rotten', d - drop
    if name == 'led':
        from reels import led
        u, d = TRACKS['depto']
        drop = 4 * u
        r = led.Led('Адмирал', 'Лада', 'KHL', 'П1', 'Победа Адмирала', 1.89, 'СБ 10.10 · 10:00 МСК', u=u, drop=drop)
        return r, 'depto', d - drop
    if name == 'top3':
        from reels import top3
        u, d = TRACKS['kizaru']
        drop = 2 * u
        picks = [('Ак Барс', 'Северсталь', 'KHL', 'Победа Ак Барса', 2.06, 'СБ 10.10 · 17:00 МСК', 'h', 58),
                 ('Трактор', 'Сибирь', 'KHL', 'Победа Трактора', 1.85, 'СБ 10.10 · 14:00 МСК', 'h', 62),
                 ('Нью-Джерси', 'Ванкувер', 'NHL', 'Победа Нью-Джерси', 1.63, 'СБ 10.10 · 22:30 МСК', 'h', 70)]
        r = top3.Top3('ТОП-3|ПРОГНОЗА|НА СУББОТУ', picks, u=u, drop=drop)
        return r, 'kizaru', d - drop
    if name == 'notify':
        from reels import notify
        u, d = TRACKS['vace']
        drop = 3 * u
        r = notify.Notify('Колорадо', 'Торонто', 'NHL', 'h', 'Победа Колорадо', 1.80, (1.80, 4.44, 3.62), 68,
                          'воскресенье, 11 октября', '01:59', '02:00', u=u, drop=drop)
        return r, 'vace', d - drop
    if name == 'channel':
        from reels import channel
        u, d = TRACKS['bbt']
        drop = 3 * u
        res = ('Итоги: 3 из 3 ✅', ['Металлург ИТБ 2,5 — 7:1 ✅', 'ЦСКА с учётом ОТ — 5:2 ✅', 'Вашингтон — Рейнджерс ТМ 6 — 3:1 ✅'])
        r = channel.Channel('Ак Барс', 'Северсталь', 'KHL', 'Победа Ак Барса', 2.06, 58, 'СБ 10.10 · 17:00 МСК', res,
                            'Главный матч дня — Ак Барс против Северстали. Прогноз ниже 👇', u=u, drop=drop)
        return r, 'bbt', d - drop
    if name == 'ticket':
        from reels import ticket
        u, d = TRACKS['jefe']
        drop = 4 * u
        flights = [('02:00', 'Монреаль', 'Детройт', 'П1', 1.81), ('02:00', 'Чикаго', 'Каролина', 'П2', 1.67),
                   ('02:00', 'Колорадо', 'Торонто', 'П1', 1.80), ('02:30', 'Айлендерс', 'Тампа-Бэй', 'П2', 1.97),
                   ('05:00', 'Калгари', 'Анахайм', 'П2', 2.29), ('05:00', 'Вегас', 'Лос-Анджелес', 'П1', 2.01)]
        r = ticket.Ticket(flights, 0, 'NHL', 65, '11.10', u=u, drop=drop)
        return r, 'jefe', d - drop
    if name == 'swipe':
        from reels import swipe
        u, d = TRACKS['tiki']
        drop = 6 * u
        cards = [('Сент-Луис', 'Коламбус', 'NHL', 'ВС 11.10 · 02:00', 53, 2.23, 'Победа Сент-Луиса', 'h', 'L',
                  'шанс 53% — почти монетка, пропускаем'),
                 ('Баффало', 'Юта', 'NHL', 'ВС 11.10 · 02:00', 51, 2.46, 'Победа Баффало', 'h', 'L', 'шанс 51% — монетка, пропускаем'),
                 ('Чикаго', 'Каролина', 'NHL', 'ВС 11.10 · 02:00', 72, 1.67, 'Победа Каролины', 'a', 'R',
                  'шанс 72% — уверенный фаворит, берём')]
        r = swipe.Swipe(cards, 'JARVIS · свайп', u=u, drop=drop)
        return r, 'tiki', d - drop
    if name == 'paper':
        from reels import paper
        u, d = TRACKS['kilo']
        drop = 3 * u
        story = ['Шанс «Вегаса» на победу — 60%, коэффициент — 2.01. Матч с «Лос-Анджелесом» начнётся в 05:00 по Москве.',
                 'Ночью «Вегас» принимает «Лос-Анджелес». Наш шанс хозяев — 60%, кэф на победу — 2.01.',
                 'Начало в 05:00 МСК. Прогнозы на все матчи ночи и честные итоги — в Telegram-канале JARVIS.']
        yday = ['3 ИЗ 3', 'Металлург ИТБ 2,5 — зашёл', 'ЦСКА с учётом ОТ — зашёл', 'Вашингтон ТМ 6 — зашёл']
        r = paper.Paper('Вегас', 'Лос-Анджелес', 'NHL', 'h', 'Победа Вегаса', 2.01, 60, '05:00', ['ВЕГАС —', 'ФАВОРИТ НОЧИ'],
                        story, yday, '№ 284', 'ВОСКРЕСЕНЬЕ, 11 ОКТЯБРЯ 2026 · № 284 · ЦЕНА — ПОДПИСКА', u=u, drop=drop)
        return r, 'kilo', d - drop
    if name == 'notes':
        from reels import notes
        u, d = TRACKS['rotten']
        drop = 4 * u
        items = [('Металлург ИТБ 2,5', 1.68, '7:1', True), ('ЦСКА с учётом ОТ', 1.67, '5:2', True),
                 ('Вашингтон — Рейнджерс ТМ 6', 1.69, '3:1', True)]
        r = notes.Notes('Итоги 9–10 октября 🏒', '10 октября 2026 г., 09:41', items, None,
                        'Сегодня в плане 👇', ['Адмирал П1 · 1.89', 'Трактор П1 · 1.85', 'Локомотив П1 · 1.82'], u=u, drop=drop)
        return r, 'rotten', d - drop
    if name == 'poll':
        from reels import poll
        u, d = TRACKS['depto']
        drop = 4 * u
        r = poll.Poll('Флорида', 'Миннесота', 'NHL', 'h', 'Победа Флориды', 2.17, 55, 'ВС 11.10 · 01:00', u=u, drop=drop)
        return r, 'depto', d - drop
    if name == 'keynote':
        from reels import keynote
        u, d = TRACKS['quantum']
        drop = 3 * u
        r = keynote.Keynote('Айлендерс', 'Тампа-Бэй', 'NHL', 'a', 'Победа Тампы', 1.97, 60, 'ВС 11.10', '02:30', 'Тампы', u=u, drop=drop)
        return r, 'quantum', d - drop
    # новая волна (11.10): матчи и «Лучший прогноз» с листа «Прогнозы — кратко» (обновлено 11.10 12:39–12:52 МСК)
    if name == 'particles':
        from reels import particles
        u, d = TRACKS['quantum']
        drop = 3 * u
        return particles.Particles(FRESH['rangers'], u=u, drop=drop), 'quantum', d - drop
    if name == 'liquid':
        from reels import liquid
        u, d = TRACKS['rotten']
        drop = 4 * u
        return liquid.Liquid(FRESH['akbars'], u=u, drop=drop), 'rotten', d - drop
    if name == 'visualizer':
        from reels import visualizer
        u, d = TRACKS['depto']
        drop = 4 * u
        return visualizer.Visualizer(FRESH['carolina'], u=u, drop=drop, track=TRACK_DIR and os.path.join(TRACK_DIR, 'depto.wav'),
                                     start=d - drop), 'depto', d - drop
    if name == 'ink':
        from reels import ink
        u, d = TRACKS['refl']
        drop = 3 * u
        return ink.Ink(FRESH['amur'], u=u, drop=drop), 'refl', d - drop
    raise SystemExit('нет формата: %s' % name)


FRESH = {
    'rangers': dict(home='Рейнджерс', away='Ванкувер', league='NHL', when='ПН 12.10 · 01:00', side='h',
                    pick='ПОБЕДА РЕЙНДЖЕРС', chance=70, line=(1.65, 4.68, 4.23)),
    'akbars': dict(home='Ак Барс', away='Сочи', league='KHL', when='ПН 12.10 · 19:00', side='h',
                   pick='ПОБЕДА АК БАРСА', chance=75, line=(1.49, 4.47, 5.70)),
    'carolina': dict(home='Филадельфия', away='Каролина', league='NHL', when='ПН 12.10 · 02:00', side='a',
                     pick='ПОБЕДА КАРОЛИНЫ', chance=64, line=(3.31, 4.27, 1.92)),
    'amur': dict(home='Амур', away='Лада', league='KHL', when='ПН 12.10 · 12:00', side='h',
                 pick='ПОБЕДА АМУРА', chance=68, line=(1.80, 3.76, 4.01)),
}
TRACK_DIR = None


ALL = ['pack', 'coupon', 'sim', 'results', 'chat', 'board', 'pixel', 'fight', 'weather', 'collage', 'led', 'top3',
       'notify', 'channel', 'ticket', 'swipe', 'paper', 'notes', 'poll', 'keynote',
       'particles', 'liquid', 'visualizer', 'ink']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--tracks', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--frames')
    a = ap.parse_args()
    global TRACK_DIR
    TRACK_DIR = a.tracks
    for name in (ALL if a.name == 'all' else a.name.split(',')):
        t0 = time.time()
        reel, key, start = make(name)
        base = os.path.join(a.out, name)
        if a.frames:
            fr = [int(round(float(x) * C.FPS)) for x in a.frames.split(',')]
            print(C.render(reel, base + '.mp4', frames=fr))
            continue
        C.render(reel, base + '_preview.mp4', track=os.path.join(a.tracks, key + '.wav'), start=start, extra_out=base + '_clean.mp4')
        print('%s: %.1f с ролика, %.0f с сборки, трек %s с %.2f с' % (name, reel.dur, time.time() - t0, key, start))


if __name__ == '__main__':
    main()
