# -*- coding: utf-8 -*-
"""Собирает team/out/2026-10-31/picks_khl.json — прогнозы КХЛ на 31.10 (данные: run 632)."""
import json

D = '2026-10-31'
DATE = '31 октября'
N0 = 1
P = [
 # (home, away, time, bet, odds_str, prob, odds П1/Х/П2, quote, ending)
 ('Автомобилист', 'Металлург', '15:00', 'тотал матча больше 4,5', '1,65', '59,2 %', [2.81, 3.74, 2.23],
  'Автомобилист выиграл четыре матча подряд: 3:1 в Петербурге, а потом дома 5:1 ЦСКА, 4:1 Барысу и 3:2 по буллитам Торпедо. '
  'А в Екатеринбург в субботу днём приезжает лидер. У Металлурга 72 шайбы в 22 матчах, и он разгоняется сразу: '
  'первые периоды выигрывает 24:10. Я сначала прикинул, кто здесь фаворит, и честного ответа не нашёл — линия '
  'лишь чуть-чуть за гостей. Зато в том, что скучно не будет, я уверен куда больше. У обеих команд матчи в '
  'основное время набирают в среднем по пять шайб на двоих, а две недели назад в Магнитогорске они сыграли 4:2. '
  'Поэтому кто победит, я оставляю вопросом, а беру тотал больше 4,5: мне нужны пять шайб за шестьдесят минут.',
  'Самый жаркий отрезок у Автомобилиста — третий период: 23:21 за сезон.'),
]

posts = []
summary = []
for i, (h, a, t, bet, k, pr, odds, q, end) in enumerate(P):
    pid = '3110-%d' % (N0 + i)
    text = ('КХЛ · %s · %s МСК\n<b>%s — %s</b>\n\nПрогноз: <b>%s</b>\nКэф: <b>%s</b>\n\n<blockquote>%s</blockquote>\n\n'
            '<i>%s</i>\n\n#кхл #прогноз #jarvibet') % (DATE, t, h, a, bet, k, q, end)
    posts.append({'to': 'owner', 'type': 'animation', 'html': True, 'files': ['out/picks/khl-%s/vs_%d.mp4' % (D, i + 1)],
                  'text': text, 'buttons': 'post', 'pid': pid,
                  'vs': {'league': 'KHL', 'home': h, 'away': a, 'date': DATE, 'time': t, 'odds': odds}})
    summary.append('%d. %s %s — %s: %s · %s' % (i + 1, t, h, a, bet, k))
head = ('<b>Прогнозы КХЛ на 31 октября</b> — 1 матч\n\n' + '\n'.join(summary) +
        '\n\nПод постом: «Опубликовать» — выйдет в канал за полтора часа до матча; «Редактировать» — поправить текст; «Не надо».'
        '\n\nСегодня в КХЛ один матч. Уверенность модели 59 % — по порогу КХЛ это обычный «ВЫБОР», пометку «ниже 60 %» не ставил.')
job = {'day': D, 'make': ['team/picks/banners.py team/out/%s/picks_khl.json' % D], 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': head}] + posts}
json.dump(job, open('team/out/%s/picks_khl.json' % D, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    import sys
    if '--rows' in sys.argv:
        for i, (h, a, t, bet, k, pr, *_r) in enumerate(P):
            print('3110-%d|%s — %s|%s|%s|%s' % (N0 + i, h, a, t, bet, k + '|' + pr))
