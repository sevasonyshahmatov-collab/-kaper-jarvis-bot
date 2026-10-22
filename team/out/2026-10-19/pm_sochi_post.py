"""Сочи — Шанхайские Драконы 2:5, 19.10: послематчевый пост с текстом по хронике матча (владелец 19.10: пост из заготовок
получился маленьким и однотипным; нейросеть в тот вечер не ответила — текст написан вручную по хронике).
Баннер, шапка и номер поста прогноза — как у team/postmatch/run.py; отправка владельцу с кнопкой «Опубликовать»."""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path[:0] = [os.path.join(ROOT, 'team', 'postmatch'), os.path.join(ROOT, 'team', 'daily')]
import run  # noqa: E402
import settle  # noqa: E402

STORY = ('Всё решили первые четыре минуты: Чичек и Мюррэй забили с разницей в 38 секунд, и дальше Драконы спокойно '
         'играли от счёта. Сочи не сдался — Венгрыжановский в начале второго периода отыграл одну, но Эддисон через '
         'четыре минуты вернул разницу в две шайбы, а гол Александрова в большинстве на 36-й минуте фактически закрыл '
         'вопрос. Чен в самом начале третьего сделал 1:5, и Андреянова поменяли на Шаймарданова. Броски в створ — 35 на 29 '
         'в пользу гостей, Мифтахов отстоял без нервов. Второй гол Венгрыжановского в большинстве за пять минут до конца '
         'уже ничего не менял: ставка на победу в основное время ни разу не была под угрозой.')
OUTRO = 'Беру на заметку: если Драконы забивают первыми, игру они не отпускают. Идём к следующим матчам.'

job_file = os.path.join(ROOT, 'team', 'out', '2026-10-19', 'pm_sochi_post.json')
p = run.load_pick({'pid': '1910-4', 'league': 'KHL', 'home': 'Сочи', 'away': 'Шанхайские Драконы', 'start': '2026-10-19 19:30',
                   'pick': 'победа Шанхайских Драконов в основное время', 'kef': '1,94'})
run.WAIT_MIN = 0
g = run.final_game(p)
res, legs, why = settle.settle(p['pick'], p['home'], p['away'], g)
res_legs = [settle.settle_leg(l_, g) for l_ in legs]
ch, _, _ = run.channel_post(p)
text = run.post_text(p, g, run.goals_of(p, g), res, why, legs, (STORY, OUTRO))
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
