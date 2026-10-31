# -*- coding: utf-8 -*-
"""Проба рубрики «Экспресс» (владелец 31.10): 2 черновика владельцу, без кнопки. Данные: run 41177963858
(team/out/2026-10-31/express_nhl_data.json). Правило рубрики — team/picks/EXPRESS.md."""
import json, re
D = '2026-10-31'
def html(t):
    t = re.sub(r'^(Экспресс на .+)$', r'<b>\1</b>', t, flags=re.M)
    t = re.sub(r'^(\d\. )(.+?), (.*МСК)$', r'\1<b>\2</b>, \3', t, flags=re.M)
    t = re.sub(r'Общий кэф: (\S+)', r'Общий кэф: <b>\1</b>', t)
    head, rest = t.split('\n\nОбщий кэф', 1)
    kef, rest = rest.split('\n\n', 1)
    body, tail = rest.split('\n\nЭкспресс не зайдёт', 1)
    end, tags = tail.split('\n\n', 1)
    return '%s\n\nОбщий кэф%s\n\n<blockquote>%s</blockquote>\n\n<i>Экспресс не зайдёт%s</i>\n\n%s' % (head, kef, body, end, tags.strip())
E1 = open('team/out/%s/express_nhl_1.txt' % D).read().strip()
E2 = open('team/out/%s/express_nhl_2.txt' % D).read().strip()
note = ('<b>Проба рубрики «Экспресс» — НХЛ, 31 октября</b>\n\n'
        'Выше два черновика: на два матча (общий кэф 1,85) и на три (2,00). Как отбирал: только исходы, которые модель '
        'считает вероятными от 65 %, с кэфом 1,25–1,75, из матча одно событие, матчи в двух экспрессах не повторяются.\n\n'
        'Честно по модели: экспресс на два — 54 % при 54 %, которые «зашиты» в кэф 1,85; на три — 45 % при 50 % в кэфе 2,00. '
        'Преимущества над линией у экспрессов нет: маржа перемножается, и чем больше событий, тем заметнее. '
        'Проценты в посты не ставил (ваше правило 27.10).\n\n'
        'Первые матчи сегодня в 21:00 МСК.\n\n'
        'Проба рубрики “Экспресс”: нравится формат? кнопку публикации добавим после “да”')
job = {'day': D, 'messages': [
    {'to': 'owner', 'type': 'text', 'html': True, 'text': html(E1)},
    {'to': 'owner', 'type': 'text', 'html': True, 'text': html(E2)},
    {'to': 'owner', 'type': 'text', 'html': True, 'text': note}]}
json.dump(job, open('team/out/%s/express_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
for m in job['messages']: print(len(m['text']), '\n', m['text'], '\n----')
