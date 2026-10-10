"""Послематчевые баннеры к прогнозам (ice_more2, style='verdict'): КХЛ 9 октября и НХЛ в ночь на 10 октября.

КХЛ — счёт из таблицы, сверено со «Спорт-Экспрессом» и Sports.ru: Металлург — Салават Юлаев 7:1, Динамо Москва — ЦСКА 2:5.
НХЛ — таблица результат ещё не подтянула; по отчётам (Russian Machine Never Breaks, Blueshirt Banter): Вашингтон — Рейнджерс 3:1,
основное время (третий гол — в пустые ворота на последней секунде). Кэфы — из прогнозов владельца канала.
Запуск из папки render: python make_picks_1010.py → out/0910/pick_*.jpg (КХЛ), out/1010/pick_*.jpg (НХЛ)
"""
import os

import ice_more2 as im2
import nhl

nhl.register()

KHL = ('0910', 'пятница, 9 октября', 'КХЛ', 'KHL', [
    ('metallurg_salavat', dict(home='Металлург', away='Салават Юлаев', sh=7, sa=1, mark='', pick=dict(
        text='ИНДИВИДУАЛЬНЫЙ ТОТАЛ МЕТАЛЛУРГА БОЛЬШЕ 2,5', odds=1.68, hit=True,
        checks=[('МЕТАЛЛУРГ ЗАБИЛ 7 ГОЛОВ', True)]))),
    ('dinamo_cska', dict(home='Динамо Москва', away='ЦСКА', sh=2, sa=5, mark='', pick=dict(
        text='ПОБЕДА ЦСКА С УЧЁТОМ ОТ', odds=1.67, hit=True,
        checks=[('ЦСКА ВЫИГРАЛ 5:2', True)]))),
])
NHL = ('1010', 'суббота, 10 октября', 'НХЛ', 'NHL', [
    ('washington_rangers', dict(home='Вашингтон', away='Рейнджерс', sh=3, sa=1, mark='', pick=dict(
        text='ТОТАЛ МАТЧА МЕНЬШЕ 6', odds=1.69, hit=True,
        checks=[('3:1 — 4 ГОЛА В МАТЧЕ', True)]))),
])

for day, date, tag, league, banners in (KHL, NHL):
    out = 'out/' + day
    os.makedirs(out, exist_ok=True)
    for name, m in banners:
        m.update(date=date, tag=tag)
        path = '%s/pick_%s.jpg' % (out, name)
        im2.single(m, path, style='verdict', league=league)
        print(path)
