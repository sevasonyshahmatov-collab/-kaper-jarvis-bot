"""Пробные ролики для Shorts / VK Клипов (render/shorts.py) на реальных прогнозах канала за 08–09.10.

Линия Вегас — Торонто 1.95 / 4.28 / 3.21 — из таблицы НХЛ 08.10 (~12:40 МСК). Счета сверены с отчётами матчей.
Запуск из папки render: python make_shorts_demo.py → out/shorts/*.mp4 (+ *_cover.jpg — обложка)
"""
import shorts

OUT = 'out/shorts'
print(shorts.pick('Вегас', 'Торонто', 'ПТ 09.10 · 05:00 МСК', 'Тотал матча больше 5,5', 1.67, OUT + '/pick_vgk_tor.mp4',
                  league='NHL', odds=(1.95, 4.28, 3.21)))
print(shorts.result('Вегас', 'Торонто', 4, 3, OUT + '/result_vgk_tor.mp4', mark='Б', when='ПТ 09.10',
                    pred='Тотал матча больше 5,5', coef=1.67, won=True, note='3:3 в основное время — 6 шайб', league='NHL'))
print(shorts.result('Нефтехимик', 'Авангард', 0, 1, OUT + '/result_neft_avg.mp4', when='ЧТ 08.10',
                    pred='Победа Нефтехимика', won=False, league='KHL'))
