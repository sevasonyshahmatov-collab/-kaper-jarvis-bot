# -*- coding: utf-8 -*-
"""Премиум-серия (render/reels/premium.py): восемь подач под восемь треков владельца (16.10.2026).

Треки лежат у владельца / в скретчпаде сессии — в репозиторий не кладём. Дроп и доля посчитаны по треку
(спектральный поток → сетка долей, дроп — самый сильный рост баса и громкости), ролик начинается за ~4,5 с до дропа.

    python -m reels.run_premium <папка треков> <папка вывода> [стиль …] [--frames]   (запуск из render/)
--frames — только контрольные кадры (вступление, дроп, кэф, факты, финал) для проверки раскладки.
"""
import os
import sys

from reels import core as C
from reels import premium as P

MATCHES = {
    'neft': dict(league='KHL', date='16 октября', time='19:00', home='Нефтехимик', away='Трактор',
                 pick='итоговая победа Нефтехимика', kef=1.84,
                 facts=['Трактор проигрывает третьи периоды 6:14', 'Дома Нефтехимик забивает 3,5 шайбы за матч']),
    'col': dict(league='NHL', date='17 октября', time='04:00', home='Колорадо', away='Питтсбург',
                pick='фора Питтсбурга +1,5', kef=1.75,
                facts=['Колорадо дома пропускает 3,5 шайбы за игру', '3 из 7 матчей Питтсбурга дошли до ОТ или буллитов']),
    'adm': dict(league='KHL', date='16 октября', time='12:30', home='Адмирал', away='Спартак',
                pick='победа Спартака в основное время', kef=1.95,
                facts=['Все 8 побед Спартака — в основное время', '6 побед в 7 выездных матчах']),
    'avg': dict(league='KHL', date='16 октября', time='16:30', home='Авангард', away='Автомобилист',
                pick='Автомобилист не проиграет в основное время', kef=1.71,
                facts=['6 октября — 4:0 в пользу Автомобилиста', 'Авангард забивает 1,46 шайбы за игру']),
    'sha': dict(league='KHL', date='16 октября', time='19:30', home='Шанхайские Драконы', away='Ак Барс',
                pick='тотал матча меньше 5,5', kef=1.64,
                facts=['В 13 из 15 матчей Ак Барса — не больше 5 шайб', '4 поражения подряд, и везде не больше 2 голов']),
    'ana': dict(league='NHL', date='17 октября', time='05:00', home='Анахайм', away='Бостон',
                pick='индивидуальный тотал Бостона больше 2,5', kef=1.63,
                facts=['17 шайб за 3 победы подряд у Бостона', 'Анахайм дома пропускает 3,67 за игру']),
}

# стиль: (трек, дроп в треке, доля, матч)
PLAN = {
    'editorial': ('doomsday', 43.181, 0.4444, 'neft'),
    'spotlight': ('demons', 86.296, 0.6522, 'col'),
    'broadcast': ('say', 49.161, 0.3871, 'adm'),
    'split': ('twofaced', 33.871, 0.4839, 'avg'),
    'card': ('militant', 8.060, 0.4762, 'sha'),
    'kinetic': ('toofast', 33.982, 0.5310, 'ana'),
    'glass': ('twoface', 24.216, 0.7317, 'adm'),
    'film': ('vampire', 92.101, 0.8219, 'neft'),
    'storm': ('doomsday', 43.181, 0.4444, 'sha'),
}


def build(style):
    track, drop_t, u, mk = PLAN[style]
    pre = max(1, round(4.5 / u)) * u
    reel = P.STYLES[style](MATCHES[mk], u=u, drop=pre)
    return reel, track, drop_t - pre


def main():
    tracks, out = sys.argv[1], sys.argv[2]
    rest = [a for a in sys.argv[3:] if not a.startswith('--')]
    styles = rest or list(PLAN)
    frames_only = '--frames' in sys.argv
    os.makedirs(out, exist_ok=True)
    for st in styles:
        reel, track, start = build(st)
        base = os.path.join(out, '%02d_%s_%s' % (list(PLAN).index(st) + 1, st, PLAN[st][0]))
        if frames_only:
            D = reel.drop
            ts = [1.0, D - 0.6, D + 0.6, reel.t_kef + 0.7, reel.t_f2 + 0.8, reel.t_end + 1.2]
            print(C.render(reel, base + '.mp4', frames=[int(t * C.FPS) for t in ts]))
            continue
        tr = os.path.join(tracks, track + '.m4a')
        C.render(reel, base + '_preview.mp4', track=tr, start=start, extra_out=base + '_clean.mp4')
        print(base, '%.1f с' % reel.dur, flush=True)


if __name__ == '__main__':
    main()
