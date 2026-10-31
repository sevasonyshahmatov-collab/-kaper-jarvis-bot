# -*- coding: utf-8 -*-
"""Баннеры купонов «Экспресс» 31.10 (render/express_card.py): лента 1080×1350 и сторис 1080×1920 для обоих купонов.
    PYTHONPATH=render python3 team/out/2026-10-31/express_render.py"""
import os
import express_card as ec
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'express')
E = {
 'e2': dict(date_title='НХЛ · 31 октября · на два матча', total=1.81, chance=0.763 * 0.709, legs=[
     dict(home='Детройт', away='Сент-Луис', time='20:00', bet='фора Детройта +1,5', kef=1.38),
     dict(home='Нэшвилл', away='Тампа-Бэй', time='21:00', bet='инд. тотал Нэшвилла больше 1,5', kef=1.31)]),
 'e3': dict(date_title='НХЛ · 31 октября – 1 ноября · на три матча', total=1.83, chance=0.805 * 0.809 * 0.806, legs=[
     dict(home='Лос-Анджелес', away='Баффало', time='23:00', bet='фора Лос-Анджелеса +2,5', kef=1.22),
     dict(home='Монреаль', away='Питтсбург', time='02:00', bet='инд. тотал Питтсбурга больше 1,5', kef=1.22),
     dict(home='Ванкувер', away='Торонто', time='02:00', bet='инд. тотал Ванкувера больше 1,5', kef=1.23)]),
}
for k, e in E.items():
    for fmt in ('feed', 'story'):
        p = ec.render(e['legs'], os.path.join(OUT, '%s_%s.jpg' % (k, fmt)), date_title=e['date_title'], total=e['total'],
                      chance=e['chance'], fmt=fmt, cta='Разбор — в Telegram @jarvibet' if fmt == 'story' else None)
        print(p, os.path.getsize(p) // 1024, 'КБ')
