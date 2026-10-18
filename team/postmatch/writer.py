# -*- coding: utf-8 -*-
"""Текст послематчевого разбора пишет Claude по хронике матча (владелец 18.10: «нужно давать аналитику… как будто
писал человек, а не по шаблону»). Ключ — секрет репозитория ANTHROPIC_API_KEY (передаёт itogi.yml).
write(...) → (рассказ, вывод) или None — тогда run.py собирает текст по-старому, из заготовок.
"""
import os
import random
import re

MODEL = os.environ.get('PM_MODEL', 'claude-opus-5-5')

SYSTEM = """Ты пишешь послематчевый пост для Telegram-канала @jarvibet о хоккее (КХЛ и НХЛ). Пост выходит от лица \
владельца канала: он сам выбрал ставку перед матчем, сам смотрел игру и теперь рассказывает подписчикам, как всё было.

Как писать:
- от первого лица: «я смотрел», «я ждал», «я ошибся», «мне понравилось», «ставил на…»; живо и спокойно, как человек, \
который разбирается в хоккее и говорит с друзьями;
- рассказ — это рисунок матча по хронике: кто как начал, где был перелом, что решило исход (большинство, вратарь, \
снятие вратаря, игрок, броски, концовка). Конкретные минуты, фамилии, цифры — только из хроники, ничего не выдумывай;
- свяжи рассказ со ставкой: почему ставили (обоснование из поста-прогноза, если оно дано) и подтвердилось ли это \
на льду; если ставка не зашла — честно скажи, в чём ошибся или что сломало расчёт, без оправданий;
- фамилии игроков НХЛ — по-русски, как пишут sports.ru и «Чемпионат» (Овечкин, Макдэвид, Капризов); не уверен \
в написании — опиши без фамилии («их первый центр», «вратарь гостей»);
- каждый пост по-своему: разное начало, разный порядок, без штампов «матч получился…», «как говорится», \
«что ж», «в итоге»; не начинай с названий команд и счёта — шапку со счётом добавят отдельно;
- без эмодзи, без markdown, без хэштегов, без кавычек-ёлочек вокруг всего текста;
- нельзя: слово «Джарвис», названия букмекеров, обещания и гарантии выигрыша, «верняк», 100 %.

Формат ответа — ровно две части, разделённые строкой из трёх дефисов (---):
1) рассказ о матче и ставке: 5–7 предложений, 450–650 знаков;
2) вывод владельца: одно-два коротких предложения, 60–160 знаков — что берём на заметку или настрой на следующие матчи.
Больше ничего не пиши."""

ANGLES = ['начни с момента, который решил матч',
          'начни с того, чего я ждал от матча перед игрой, и сравни с тем, что случилось',
          'начни с игрока или вратаря, который сделал этот матч',
          'начни с цифры из хроники, которая лучше всего объясняет игру (броски, большинство, удаления)',
          'начни с концовки матча и вернись к тому, как к ней пришли',
          'начни с того, как команды начали игру',
          'начни с короткой эмоции после финальной сирены, потом разбор']


def write(p, g, res_word, chronicle, why='', recent=()):
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key or not chronicle:
        print('POSTMATCH текст: %s — по заготовкам' % ('нет ключа ANTHROPIC_API_KEY' if not key else 'нет хроники'), flush=True)
        return None
    try:
        import anthropic
    except ImportError:
        print('POSTMATCHERR нет пакета anthropic — текст по заготовкам', flush=True)
        return None
    rnd = random.Random(p['pid'])
    kef = ('%.2f' % p['kef']).replace('.', ',') if p.get('kef') else '—'
    user = ['Ставка: %s, кэф %s. Итог ставки: %s.' % (p['pick'], kef, res_word),
            'Как подать: %s.' % rnd.choice(ANGLES)]
    if why:
        user.append('Обоснование из моего поста-прогноза перед матчем:\n' + why)
    if recent:
        user.append('Мои недавние послематчевые посты — не повторяй их начало, обороты и концовки:\n' +
                    '\n\n'.join(r[:500] for r in recent[:4]))
    user.append('Хроника матча:\n' + chronicle)
    client = anthropic.Anthropic(api_key=key)
    for attempt in range(2):
        try:
            r = client.beta.messages.create(
                model=MODEL, max_tokens=16000, system=SYSTEM,
                betas=['server-side-fallback-2026-07-01'], fallbacks='default',
                output_config={'effort': 'medium'},
                messages=[{'role': 'user', 'content': '\n\n'.join(user)}])
        except anthropic.APIStatusError as e:
            print('POSTMATCHERR Claude API %s: %s' % (e.status_code, str(e)[:300]), flush=True)
            return None
        except anthropic.APIConnectionError as e:
            print('POSTMATCHERR Claude API связь: %r' % e, flush=True)
            return None
        if r.stop_reason == 'refusal':
            print('POSTMATCHERR Claude отказался писать текст', flush=True)
            return None
        txt = ''.join(b.text for b in r.content if getattr(b, 'type', '') == 'text').strip()
        parts = [re.sub(r'\s+', ' ', x).strip() for x in re.split(r'\n\s*-{3,}\s*\n', txt)]
        bad = [w for w in ('джарвис', 'букмекер', 'фонбет', 'гарант', 'верняк') if w in txt.lower()]
        if len(parts) == 2 and all(parts) and len(parts[0]) + len(parts[1]) <= 820 and not bad:
            print('POSTMATCH текст: Claude (%s), %d знаков' % (r.model, len(parts[0]) + len(parts[1])), flush=True)
            return parts[0], parts[1]
        print('POSTMATCHERR текст Claude не подошёл (частей %d, знаков %d, запрещённое %s) — попытка %d' % (
            len(parts), len(txt), bad, attempt + 1), flush=True)
        user.append('Предыдущий вариант не подошёл: нужно ровно две части через ---, вместе не больше 800 знаков, '
                    'без запрещённых слов.')
    return None
