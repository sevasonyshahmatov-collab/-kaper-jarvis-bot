# -*- coding: utf-8 -*-
"""Рубрика «Экспресс» 31.10, версия 3 (правки владельца: не больше одной форы в купоне, без строки «не зайдёт, если…»,
пост = картинка + подпись, анимация на выбор). Купоны — team/picks/express.py → express_coupons.json (данные run 41177963858),
картинки рисует Actions (team/picks/express_render.py → out/express/2026-10-31/). Без кнопки — проба."""
import json
import re
D = '2026-10-31'
X = 'out/express/%s/' % D


def html(t):
    """Текст поста (express_nhl_N.txt) → HTML подписи: заголовок и матчи жирным, общий кэф жирным, «почему» — цитатой."""
    t = re.sub(r'^(Экспресс на .+)$', r'<b>\1</b>', t, flags=re.M)
    t = re.sub(r'^(\d\. )(.+?), (.*МСК)$', r'\1<b>\2</b>, \3', t, flags=re.M)
    t = re.sub(r'Общий кэф: (\S+)', r'Общий кэф: <b>\1</b>', t)
    head, rest = t.split('\n\nОбщий кэф', 1)
    kef, rest = rest.split('\n\n', 1)
    body, tags = rest.rsplit('\n\n', 1)
    return '%s\n\nОбщий кэф%s\n\n<blockquote>%s</blockquote>\n\n%s' % (head, kef, body, tags.strip())


E1 = html(open('team/out/%s/express_nhl_1.txt' % D).read().strip())   # на три
E2 = html(open('team/out/%s/express_nhl_2.txt' % D).read().strip())   # на два
note = ('<b>Экспресс НХЛ — версия 3</b>\n\n'
        'Выше: купон на три (картинка и тот же пост с анимацией — выберите, что нравится), купон на два, сторис для Instagram.\n\n'
        'Что поменял по вашим правкам:\n'
        '— в купоне не больше одной форы, остальные ноги — индивидуальные тоталы (самые вероятные по модели);\n'
        '— из поста убрал строку «экспресс не зайдёт, если…»;\n'
        '— каждый купон — пост с картинкой.\n\n'
        '1. На три: фора Лос-Анджелеса +2,5 (1,22) + Питтсбург больше 1,5 (1,22) + Ванкувер больше 1,5 (1,23) = <b>1,83</b>, шанс по модели 52 %.\n'
        '2. На два: Нэшвилл больше 1,5 (1,31) + Коламбус больше 1,5 (1,39) = <b>1,82</b>, шанс 53 %. Нога Коламбуса '
        'самая слабая из пяти (69 %): в шести последних матчах две шайбы в основное время он забил трижды.\n\n'
        'Честно: в кэфы 1,82–1,83 заложено ~55 %, модель чуть ниже — перевеса нет, берём надёжность ног.\n\n'
        'Одобряете — напишите “да купон” в чат руководителя, опубликую в Instagram пост + сторис (купон на три; '
        'скажете «на два» — опубликую его).\n\n'
        'Проба рубрики “Экспресс”: нравится формат? кнопку публикации добавим после “да”')
# Схема (с 31.10): сообщения — в express_msgs.json, задание — make: картинки (express_render.py), затем отправка
# по одному с пометками EXSEND (express_send.py); jpg/mp4 в git не попадают, логи Actions из облака закрыты.
msgs = {'day': D, 'messages': [
    {'to': 'owner', 'type': 'photo', 'html': True, 'files': [X + 'e1_feed.jpg'], 'text': E1},
    {'to': 'owner', 'type': 'animation', 'html': True, 'files': [X + 'e1_anim.mp4'], 'text': E1},
    {'to': 'owner', 'type': 'photo', 'html': True, 'files': [X + 'e2_feed.jpg'], 'text': E2},
    {'to': 'owner', 'type': 'album', 'files': [X + 'e1_story.jpg', X + 'e2_story.jpg'],
     'text': 'Сторис для Instagram (1080×1920): купон на три и на два'},
    {'to': 'owner', 'type': 'text', 'html': True, 'text': note}]}
json.dump(msgs, open('team/out/%s/express_msgs.json' % D, 'w'), ensure_ascii=False, indent=1)
job = {'day': D, 'make': ['team/picks/express_render.py team/out/%s/express_coupons.json %s' % (D, X.rstrip('/')),
                          'team/picks/express_send.py team/out/%s/express_msgs.json' % D], 'messages': []}
json.dump(job, open('team/out/%s/express.json' % D, 'w'), ensure_ascii=False, indent=1)
for m in msgs['messages']:
    print(m['type'], len(m['text']))
print(E2)
