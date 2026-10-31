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
X = 'team/out/%s/express/' % D
note = ('<b>Экспресс НХЛ — обновлено: ноги 1,20–1,65</b>\n\n'
        'Выше два готовых поста, как они выйдут в канал: баннер и подпись. Ноги — самые вероятные исходы матча по модели '
        '(от 65 %, кэф 1,20–1,65), из матча одно событие, матчи в двух купонах не повторяются; общий кэф — около 1,80–2,00.\n\n'
        '1. На два: фора Детройта +1,5 (1,38) + Нэшвилл забьёт больше 1,5 (1,31) = <b>1,81</b>, шанс по модели 54 %.\n'
        '2. На три: фора Лос-Анджелеса +2,5 (1,22) + Питтсбург больше 1,5 (1,22) + Ванкувер больше 1,5 (1,23) = <b>1,83</b>, шанс 52 %.\n\n'
        'Честно: кэф 1,81 «закладывает» 55 %, 1,83 — 55 %; модель чуть ниже линии, перевеса нет — экспресс берём ради надёжных ног, '
        'а не ради выгоды. Шанс по модели стоит на баннере (вы просили); в подписи процентов нет.\n\n'
        'Первые матчи сегодня в 20:00 МСК.\n\n'
        'Одобряете — напишите “да купон” в чат руководителя, опубликую в Instagram пост + сторис (купон на три; '
        'скажете «на два» — опубликую его).\n\n'
        'Проба рубрики “Экспресс”: нравится формат? кнопку публикации добавим после “да”')
job = {'day': D, 'messages': [
    {'to': 'owner', 'type': 'photo', 'html': True, 'files': [X + 'e2_feed.jpg'], 'text': html(E1)},
    {'to': 'owner', 'type': 'photo', 'html': True, 'files': [X + 'e3_feed.jpg'], 'text': html(E2)},
    {'to': 'owner', 'type': 'album', 'files': [X + 'e3_story.jpg', X + 'e2_story.jpg'],
     'text': 'Сторис для Instagram (1080×1920): купон на три и на два'},
    {'to': 'owner', 'type': 'text', 'html': True, 'text': note}]}
json.dump(job, open('team/out/%s/express_nhl.json' % D, 'w'), ensure_ascii=False, indent=1)
for m in job['messages']: print(len(m['text']), '\n', m['text'], '\n----')
