# -*- coding: utf-8 -*-
"""Текст послематчевого разбора пишет нейросеть по хронике матча (владелец 18.10: «нужно давать аналитику… как будто
писал человек, а не по шаблону»).
Основной — Gemini по бесплатному ключу Google AI Studio (секрет GEMINI_API_KEY, решение владельца 18.10: счёт Claude API
не пополняем). Запасной — Claude API (секрет ANTHROPIC_API_KEY), если на его счёте есть деньги. Оба передаёт itogi.yml.
write(...) → (рассказ, вывод) или None — тогда run.py пост не собирает (владелец 19.10: заготовки не слать), а пишет
владельцу, что текста нет.
"""
import os
import random
import re
import time

import requests

MODEL = os.environ.get('PM_MODEL', 'claude-opus-5-5')
GEMINI_API = 'https://generativelanguage.googleapis.com/v1beta/'
GEMINI_URL = GEMINI_API + 'models/%s:generateContent'

SYSTEM = """Ты пишешь послематчевый пост для Telegram-канала @jarvibet о хоккее (КХЛ и НХЛ). Пост выходит от лица \
владельца канала: он сам выбрал ставку перед матчем, сам смотрел игру и теперь рассказывает подписчикам, как всё было.

Как писать:
- от первого лица: «я смотрел», «я ждал», «я ошибся», «мне понравилось», «ставил на…»; живо и спокойно, как человек, \
который разбирается в хоккее и говорит с друзьями;
- тон спокойный и взрослый: без надрыва и пафоса («шок», «пусто на душе», «полнейшее разочарование», «похоронили»), \
и в минус, и в плюс — ровно, по делу;
- точно понимай ставку: тотал меньше — это ставка на малое число голов в матче (не на «сухарь» и не на «сухие серии»), \
тотал больше — на результативный матч, фора — на разницу в счёте; не приписывай мне доводов, которых нет \
в обосновании из поста-прогноза;
- рассказ — это рисунок матча по хронике: кто как начал, где был перелом, что решило исход (большинство, вратарь, \
снятие вратаря, игрок, броски, концовка). Конкретные минуты, фамилии, цифры — только из хроники, ничего не выдумывай;
- свяжи рассказ со ставкой: почему ставили (обоснование из поста-прогноза, если оно дано) и подтвердилось ли это \
на льду; если ставка не зашла — честно скажи, в чём ошибся или что сломало расчёт, без оправданий;
- фамилии игроков НХЛ — по-русски, как пишут sports.ru и «Чемпионат» (Овечкин, Макдэвид, Капризов); не уверен \
в написании — опиши без фамилии («их первый центр», «вратарь гостей»);
- каждый пост по-своему: разное начало, разный порядок, без штампов «матч получился…», «как говорится», \
«что ж», «в итоге», «выдохнул», «финальная сирена», «понервничать», «сработал идеально», «расчёт оправдался», \
«берём на вооружение»; не начинай с названий команд и счёта — шапку со счётом добавят отдельно; ни одной фразы \
из моих недавних постов — даже в другом порядке слов;
- без эмодзи, без markdown, без хэштегов, без кавычек-ёлочек вокруг всего текста;
- нельзя: слово «Джарвис», названия букмекеров, обещания и гарантии выигрыша, «верняк», 100 %.

Формат ответа — ровно две части, разделённые строкой из трёх дефисов (---):
1) рассказ о матче и ставке: 5–7 предложений, 450–650 знаков;
2) вывод владельца: одно-два коротких предложения, 60–160 знаков — что берём на заметку или настрой на следующие матчи.
Больше ничего не пиши."""

def system(p):
    """Подсказка под вид спорта: футбол (владелец 31.10) — те же правила, но про поле, голы и тайм."""
    if (p or {}).get('league') != 'FOOT':
        return SYSTEM
    s = SYSTEM.replace('о хоккее (КХЛ и НХЛ)', 'о футболе (топ-лиги Европы и еврокубки)')
    s = s.replace('разбирается в хоккее', 'разбирается в футболе').replace('на льду', 'на поле')
    s = re.sub(r'\(большинство, вратарь,\s*снятие вратаря, игрок, броски, концовка\)', '(гол, пенальти, удаление, вратарь, удары, концовка)', s)
    s = s.replace('фамилии игроков НХЛ', 'фамилии игроков').replace('(Овечкин, Макдэвид, Капризов)', '(Холанд, Мбаппе, Гримальдо)')
    return s


_sport = [None]


ANGLES = ['начни с момента, который решил матч',
          'начни с того, чего я ждал от матча перед игрой, и сравни с тем, что случилось',
          'начни с игрока или вратаря, который сделал этот матч',
          'начни с цифры из хроники, которая лучше всего объясняет игру (броски, большинство, удаления)',
          'начни с концовки матча и вернись к тому, как к ней пришли',
          'начни с того, как команды начали игру',
          'начни с тактики: кто чем давил и как соперник отвечал']
# владелец 21.10: «текст по сути дублируется» — посты начинались одинаково («выдохнул после финальной сирены…
# понервничать»). Эти обороты не пропускаем, и с недавними постами текст не должен делить фразы (3 слова подряд).
STOCK = ('выдохн', 'сирен', 'понервнич', 'нервничать', 'сработал идеально', 'оправдал', 'на вооружение', 'что ж',
         'как говорится', 'в итоге', 'матч получился')
SHARED_MAX = 2


def _prompt(p, res_word, chronicle, why, recent):
    rnd = random.Random(p['pid'])
    kef = ('%.2f' % p['kef']).replace('.', ',') if p.get('kef') else '—'
    user = ['Ставка: %s, кэф %s. Итог ставки: %s.' % (p['pick'], kef, res_word),
            'Как подать: %s.' % rnd.choice(ANGLES)]
    if why:
        user.append('Обоснование из моего поста-прогноза перед матчем:\n' + why)
    if recent:
        user.append('Мои недавние послематчевые посты — не повторяй их начало, обороты и концовки:\n' +
                    '\n\n'.join(r[:500] for r in recent[:6]))
    user.append('Хроника матча:\n' + chronicle)
    return user


def _grams(t):
    w = re.findall(r'[а-яёa-z0-9]+', t.lower().replace('ё', 'е'))
    return {' '.join(w[i:i + 3]) for i in range(len(w) - 2)}


def shared(txt, recent):
    """Фразы из 3 слов подряд, которые текст делит с недавними постами (без самых общих — «в основное время» и т. п.)."""
    common = {'в основное время', 'тотал матча больше', 'тотал матча меньше', 'в большинстве и', 'за три минуты'}
    mine = _grams(txt)
    return sorted({g for r in recent for g in mine & _grams(r)} - common)


def _check(txt, recent=()):
    """Ответ нейросети → (рассказ, вывод) или (None, почему не подошёл — это же уходит нейросети при повторе)."""
    parts = [re.sub(r'\s+', ' ', x).strip().strip('*') for x in re.split(r'\n\s*-{3,}\s*\n', txt.strip())]
    low = txt.lower().replace('ё', 'е')
    bad = [w for w in ('джарвис', 'букмекер', 'фонбет', 'гарант', 'верняк') if w in low]
    stock = [w for w in STOCK if w.replace('ё', 'е') in low]
    rep = shared(txt, recent)
    if len(parts) != 2 or not all(parts) or len(parts[0]) + len(parts[1]) > 820:
        return None, 'нужно ровно две части через ---, вместе не больше 800 знаков (частей %d, знаков %d)' % (len(parts), len(txt))
    if bad:
        return None, 'запрещённые слова: %s' % ', '.join(bad)
    if stock:
        return None, 'штампы, которых не должно быть: %s' % ', '.join(stock)
    if len(rep) > SHARED_MAX:
        return None, 'повторяет мои недавние посты фразами: %s — напиши иначе' % '; '.join('«%s»' % g for g in rep[:8])
    return (parts[0], parts[1]), ''


def _retry(why):
    return 'Предыдущий вариант не подошёл: %s. Перепиши полностью, другими словами и с другого начала.' % why


RETRIES = 3


def _gemini_models(key):
    """Модели, доступные по ключу: сначала GEMINI_MODEL, затем свежие Flash (имена у Google меняются — список берём у них)."""
    names = []
    try:
        r = requests.get(GEMINI_API + 'models', headers={'x-goog-api-key': key}, params={'pageSize': 200}, timeout=30)
        for m in r.json().get('models') or []:
            n = m.get('name', '').split('/')[-1]
            if 'generateContent' in (m.get('supportedGenerationMethods') or []) and 'flash' in n \
                    and not re.search(r'image|tts|audio|live|lite|exp|preview|thinking|omni', n):
                names.append(n)
        print('POSTMATCH Gemini: модели по ключу — %s' % ', '.join(names[:12]), flush=True)
    except (requests.RequestException, ValueError) as e:
        print('POSTMATCHERR Gemini список моделей: %r' % e, flush=True)

    def ver(n):
        return [int(x) for x in re.findall(r'\d+', n)[:2]] + [n.endswith('latest')]
    names.sort(key=ver, reverse=True)
    # самая новая Flash бывает не на бесплатном тарифе (429) — первым пробуем псевдоним gemini-flash-latest
    first = [m for m in (os.environ.get('GEMINI_MODEL', '').strip(), 'gemini-flash-latest') if m and (m in names or not names)]
    return first + [n for n in names if n not in first][:5]


def _gemini(key, user):
    for model in _gemini_models(key):
        busy = 0
        for attempt in range(5):
            if time.time() > _deadline[0]:
                print('POSTMATCHERR Gemini: вышло время на текст', flush=True)
                return None
            try:
                r = requests.post(GEMINI_URL % model, headers={'x-goog-api-key': key}, timeout=90, json={
                    'systemInstruction': {'parts': [{'text': system(_sport[0])}]},
                    'contents': [{'role': 'user', 'parts': [{'text': '\n\n'.join(user)}]}],
                    'generationConfig': {'temperature': 1.0, 'maxOutputTokens': 8192}})
            except requests.RequestException as e:
                print('POSTMATCHERR Gemini %s связь: %r — пробую следующую модель' % (model, e), flush=True)
                break
            if r.status_code in (403, 404, 429):
                print('POSTMATCHERR Gemini %s: %s (%s) — пробую следующую модель' % (
                    model, r.status_code, 'нет на бесплатном тарифе или лимит' if r.status_code == 429 else 'недоступна'), flush=True)
                break
            if r.status_code >= 500 and busy < 3:       # «high demand» у Google обычно проходит за минуту
                busy += 1
                print('POSTMATCHERR Gemini %s: %s, перегружена — жду %d с' % (model, r.status_code, 20 * busy), flush=True)
                time.sleep(20 * busy)
                continue
            if r.status_code >= 500:
                print('POSTMATCHERR Gemini %s: %s — пробую следующую модель' % (model, r.status_code), flush=True)
                break
            if r.status_code != 200:
                print('POSTMATCHERR Gemini %s %s: %s' % (model, r.status_code, r.text[:300]), flush=True)
                return None
            j = r.json()
            cand = (j.get('candidates') or [{}])[0]
            txt = ''.join(x.get('text', '') for x in (cand.get('content') or {}).get('parts') or [] if not x.get('thought'))
            body, why = _check(txt, _recent[0]) if txt else (None, 'пустой ответ (%s)' % cand.get('finishReason'))
            if body:
                print('POSTMATCH текст: Gemini (%s), %d знаков' % (model, len(body[0]) + len(body[1])), flush=True)
                return body
            print('POSTMATCHERR текст Gemini не подошёл (%s)' % why, flush=True)
            tries = sum(1 for u in user if u.startswith('Предыдущий вариант'))
            if tries >= RETRIES:
                return None
            user = user + [_retry(why)]
        else:
            return None
    return None


def write(p, g, res_word, chronicle, why='', recent=()):
    if not chronicle:
        print('POSTMATCH текст: нет хроники — по заготовкам', flush=True)
        return None
    user = _prompt(p, res_word, chronicle, why, recent)
    _recent[0] = list(recent)
    _sport[0] = p
    gkey = os.environ.get('GEMINI_API_KEY', '').strip()
    _deadline[0] = time.time() + BUDGET
    # владелец 19.10: пост по заготовке не отправлять — у Google перегрузка обычно проходит за минуты, пробуем ещё раунды
    for rnd, pause in enumerate(ROUNDS):
        if pause:
            if time.time() + pause > _deadline[0]:
                break
            print('POSTMATCH текст: нейросеть не ответила — жду %d с, раунд %d' % (pause, rnd + 1), flush=True)
            time.sleep(pause)
        if gkey:
            body = _gemini(gkey, user)
            if body:
                return body
        body = _claude(p, user)
        if body:
            return body
    return None


ROUNDS = (0, 120)
BUDGET = 8 * 60           # 31.10: нет ответа — пост по шаблону из фактов, долго не ждём
_deadline = [0.0]
_recent = [[]]


def _claude(p, user):
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        print('POSTMATCH текст: нет ключа нейросети — по заготовкам', flush=True)
        return None
    try:
        import anthropic
    except ImportError:
        print('POSTMATCHERR нет пакета anthropic — текст по заготовкам', flush=True)
        return None
    client = anthropic.Anthropic(api_key=key)
    for attempt in range(RETRIES + 1):
        try:
            r = client.beta.messages.create(
                model=MODEL, max_tokens=16000, system=system(_sport[0]),
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
        txt = ''.join(b.text for b in r.content if getattr(b, 'type', '') == 'text')
        body, why = _check(txt, _recent[0])
        if body:
            print('POSTMATCH текст: Claude (%s), %d знаков' % (r.model, len(body[0]) + len(body[1])), flush=True)
            return body
        print('POSTMATCHERR текст Claude не подошёл (%s) — попытка %d' % (why, attempt + 1), flush=True)
        user = user + [_retry(why)]
    return None
