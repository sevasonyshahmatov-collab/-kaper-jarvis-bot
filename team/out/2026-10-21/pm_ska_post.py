"""СКА — Автомобилист 1:3, 20.10: послематчевый пост заново (владелец 21.10: ставка была «тотал меньше 4,5» за 1,73, а
автопост вышел по «больше 4,5» за 1,65 и с «не зашёл»). Текст — по хронике матча, баннер с «зашёл»; отправка владельцу с
кнопкой «Опубликовать», как у team/postmatch/run.py."""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path[:0] = [os.path.join(ROOT, 'team', 'postmatch'), os.path.join(ROOT, 'team', 'daily')]
import run  # noqa: E402
import settle  # noqa: E402

STORY = ('Ставку на скромный тотал матч отработал от первой до последней минуты. Первый период прошёл вовсе без шайб: '
         'Автомобилист плотно закрыл центр, а Евгений Аликин спокойно забирал всё, что долетало. '
         'Во втором команды обменялись голами, и при 1:1 ничего не мешало держаться ниже линии. Екатеринбуржцы за матч '
         'заблокировали тридцать один бросок — для такой игры это почти стена перед воротами. Под конец третьего Тарасов '
         'снова вывел гостей вперёд, СКА снял вратаря, и Горбунов забросил в пустые ворота — 1:3, четыре шайбы на двоих. '
         'Пятой так и не случилось: даже концовка с шестым полевым не разогнала счёт выше линии.')
OUTRO = 'Когда у гостей так работает оборона, низовой тотал защищён лучше любого прогноза на голы. Идём к следующим матчам.'

job_file = os.path.join(ROOT, 'team', 'out', '2026-10-21', 'pm_ska_post.json')
p = run.load_pick({'pid': '2010-3', 'league': 'KHL', 'home': 'СКА', 'away': 'Автомобилист', 'start': '2026-10-20 19:30',
                   'pick': 'тотал матча меньше 4,5', 'kef': '1,73'})
run.WAIT_MIN = 0
g = run.final_game(p)
res, legs, why = settle.settle(p['pick'], p['home'], p['away'], g)
res_legs = [settle.settle_leg(l_, g) for l_ in legs]
ch, _, _ = run.channel_post(p)
text = run.post_text(p, g, run.goals_of(p, g), res, why, legs, (STORY, OUTRO))
print('PMRES', res, why, 'счёт', g and (g.get('hg'), g.get('ag')), flush=True)
assert res == 'win', 'ставка не зашла по расчёту: %s' % res
print('PMPOST', len(STORY) + len(OUTRO), 'знаков, пост прогноза №%s' % ch, flush=True)
print(text, flush=True)
path = os.path.join('out', 'postmatch', '%s.mp4' % p['pid'])
run.render(p, g, legs, res, res_legs, path)
with open(job_file, encoding='utf-8') as f:
    job = json.load(f)
job['messages'] = [{'to': 'owner', 'type': 'animation', 'files': [path], 'text': text, 'html': True, 'emoji': True,
                    'buttons': 'post', 'pid': '%sr%s' % (p['pid'], ch or '')}]
with open(job_file, 'w', encoding='utf-8') as f:
    json.dump(job, f, ensure_ascii=False, indent=1)
