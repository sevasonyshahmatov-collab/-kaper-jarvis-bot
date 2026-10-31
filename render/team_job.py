"""Команда JARVIS → Telegram (событие kind='team' в itogi.yml, ручной запуск workflow_dispatch).

Облачные сессии команды до Telegram не достают, GitHub Actions — достаёт (секрет TG_BOT_TOKEN уже есть).
Руководитель команды кладёт в репозиторий задание team/out/<день>/job.json и запускает itogi.yml на своей ветке
с payload {"kind": "team", "job": "team/out/<день>/job.json"}. Здесь: выполнить скрипты рисования из задания
и отправить сообщения по порядку.

Режим согласия: утром команда шлёт владельцу предложения с кнопками (бот таблицы КХЛ, teamCallback_):
  "buttons": "post"     — готовый пост ровно в том виде, как уйдёт в канал: «Опубликовать» (бот сразу копирует его в канал),
                          «Редактировать» (бот присылает текст поста, владелец правит и отправляет — пост меняется сразу),
                          «Не надо»; у альбома кнопки — следующим сообщением;
  "buttons": "proposal" — предложение работы: «Да» (согласие пишется в team/INBOX.md, команда выполнит), «Нет», «Поправить».
  "pid": "1012-3"       — номер предложения (месяц-день-№), по нему команда находит решение владельца в INBOX.
  "emoji": true         — не вычищать эмодзи из поста (по умолчанию в постах для канала их убираем); только для рубрик,
                          где владелец разрешил эмодзи: утренние посты team/daily (16.10).
Сама команда отправляет в канал только задания с "approved": "owner" и "qa": "ok" — то, что владелец одобрил кнопкой «Да».
Задания, которые запускает бот сам (team/daily/README.md): 06:00 МСК — morning_greet («Начало игрового дня»), 08:30 МСК —
recap_auto (итоги по постам канала); прежний утренний опрос — recap_ask. Если team/out/<день>/<имя>.json нет, а есть
заготовка team/daily/jobs/<имя>.json, задание создаётся из неё ({day} → день); поля payload pids / free / day / at (только
у recap_ask) уходят скриптам переменными RECAP_PIDS / RECAP_FREE / RECAP_DAY / RECAP_AT.

job.json:
{
  "day": "2026-10-12",
  "qa": "ok",                              # без «ok» в канал не уходит ничего (только владельцу)
  "approved": "owner",                     # только для заданий, одобренных владельцем; без него в канал — ничего
  "make": ["team/out/2026-10-12/make.py"], # скрипты рисования (запуск из корня репозитория, PYTHONPATH=render; можно с аргументами через пробел)
  "channel": "@jarvibet",                  # необязательно
  "messages": [
    {"to": "owner", "type": "text", "text": "Отчёт планёрки …"},
    {"to": "owner", "type": "photo", "files": ["…"], "text": "подпись для канала", "buttons": "post", "pid": "1012-1"},
    {"to": "owner", "type": "animation", "files": ["….mp4"], "text": "подпись", "buttons": "post", "pid": "1012-4"},
    {"to": "owner", "type": "text", "text": "Предложение 1012-2: …", "buttons": "proposal", "pid": "1012-2"},
    {"to": "owner", "type": "documents", "files": ["team/out/2026-10-12/a.jpg"], "captions": ["черновик"]},
    {"to": "channel", "type": "photo", "files": ["team/out/2026-10-12/b.jpg"], "text": "подпись"},
    {"to": "channel", "type": "album", "files": ["…", "…"], "text": "подпись"},
    {"to": "channel", "type": "poll", "question": "Кто победит?", "options": ["Барыс", "Авангард"]}
  ]
}
Владелец — создатель канала (getChatAdministrators), если в задании нет "owner_chat". В канал — не больше
CHANNEL_MAX сообщений за задание, подписи без эмодзи (правило канала). Проверка без отправки:
python render/itogi_job.py payload.json (без TG_BOT_TOKEN только рисует и печатает).
"""
import json
import os
import re
import subprocess
import sys

TEMPLATES = 'team/daily/jobs'   # заготовки заданий, которые запускает бот (morning_greet, recap_auto; recap_ask; postmatch_auto)
JOB_RE = re.compile(r'team/out/(\d{4}-\d\d-\d\d)/([a-z0-9_]+)\.json')
PID_RE = re.compile(r'\d{4}-[0-9a-z]+')
CHANNEL_MAX = 3
TEXT_MAX = 4000
CAPTION_MAX = 1024
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _api(token, method, data=None, files=None, timeout=120):
    import requests
    r = requests.post('https://api.telegram.org/bot%s/%s' % (token, method), data=data or {}, files=files,
                      timeout=timeout)
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise RuntimeError('%s: %s' % (method, j.get('description') or r.status_code))
    return j.get('result')


def owner_chat(token, channel):
    for m in _api(token, 'getChatAdministrators', {'chat_id': channel}):
        if m.get('status') == 'creator':
            return str(m['user']['id'])
    raise RuntimeError('не нашёл создателя канала %s' % channel)


def _chunks(text, n):
    text = text.strip()
    while text:
        cut = text.rfind('\n', 0, n) if len(text) > n else len(text)
        cut = cut if cut > n // 2 else min(n, len(text))
        yield text[:cut]
        text = text[cut:].strip()


def _path(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def markup(msg, album=None):
    """Кнопки под предложением владельцу (обрабатывает бот таблицы КХЛ — teamCallback_)."""
    pid, kind = str(msg.get('pid') or ''), msg.get('buttons')
    if kind == 'post':
        pub = 'tm|pubm|%s|%d|%d' % (pid, album[0], album[1]) if album else 'tm|pub|%s' % pid
        rows = [[{'text': 'Опубликовать', 'callback_data': pub}],
                [{'text': 'Редактировать', 'callback_data': 'tm|edit|' + pid}, {'text': 'Не надо', 'callback_data': 'tm|no|' + pid}]]
    elif kind == 'proposal':
        rows = [[{'text': 'Да', 'callback_data': 'tm|ok|' + pid}, {'text': 'Нет', 'callback_data': 'tm|no|' + pid},
                 {'text': 'Поправить', 'callback_data': 'tm|fix|' + pid}]]
    else:
        return {}
    return {'reply_markup': json.dumps({'inline_keyboard': rows}, ensure_ascii=False)}


def send(token, chat, msg, to_channel):
    import itogi_job as ij
    kind = msg.get('type', 'text')
    text = str(msg.get('text') or '')
    if (to_channel or msg.get('buttons') == 'post') and not msg.get('emoji'):   # пост для канала — без эмодзи (правило канала);
        text = ij.no_emoji(text)                     # "emoji": true — исключение владельца (утренние посты team/daily, 16.10)
    mode = {'parse_mode': 'HTML'} if msg.get('html') else {}
    kb = {} if to_channel else markup(msg)
    files = [_path(p) for p in msg.get('files') or []]
    if kind == 'text':
        parts = list(_chunks(text, TEXT_MAX))
        for i, part in enumerate(parts):
            extra = kb if i == len(parts) - 1 else {}
            _api(token, 'sendMessage', dict(chat_id=chat, text=part, disable_web_page_preview='true', **mode, **extra))
    elif kind == 'photo':
        with open(ij.tg_ready(files[0]), 'rb') as f:
            _api(token, 'sendPhoto', dict(chat_id=chat, caption=text[:CAPTION_MAX], **mode, **kb), {'photo': f})
    elif kind == 'album':
        media, opened = [], {}
        for i, p in enumerate(files[:10]):
            m = {'type': 'photo', 'media': 'attach://p%d' % i}
            if i == 0 and text:
                m.update(caption=text[:CAPTION_MAX], **mode)
            media.append(m)
            opened['p%d' % i] = open(ij.tg_ready(p), 'rb')
        try:
            res = _api(token, 'sendMediaGroup', {'chat_id': chat, 'media': json.dumps(media, ensure_ascii=False)}, opened)
        finally:
            for f in opened.values():
                f.close()
        if kb and res:                                       # у альбома кнопок нет — следующим сообщением
            ids = [r_['message_id'] for r_ in res]
            head = (text.split('\n')[0] or 'альбом')[:80]
            _api(token, 'sendMessage', dict(chat_id=chat, text='%s — альбом выше: %s' % (msg.get('pid', ''), head),
                                            **markup(msg, (ids[0], len(ids)))))
    elif kind == 'documents':
        caps = list(msg.get('captions') or [])
        ij.send_documents(token, chat, [(p, (caps[i] if i < len(caps) else '')[:CAPTION_MAX]) for i, p in enumerate(files)])
        if text:
            _api(token, 'sendMessage', dict(chat_id=chat, text=text[:TEXT_MAX], **mode))
    elif kind == 'video':
        with open(files[0], 'rb') as f:
            _api(token, 'sendVideo', dict(chat_id=chat, caption=text[:CAPTION_MAX], supports_streaming='true', **mode, **kb),
                 {'video': f}, timeout=300)
    elif kind == 'animation':                                # «гифка»: MP4 без звука, в Telegram крутится по кругу
        with open(files[0], 'rb') as f:
            _api(token, 'sendAnimation', dict(chat_id=chat, caption=text[:CAPTION_MAX], **mode, **kb),
                 {'animation': f}, timeout=300)
    elif kind == 'poll':
        opts = [str(o)[:100] for o in msg.get('options') or []][:10]
        _api(token, 'sendPoll', dict({'chat_id': chat, 'question': str(msg.get('question', ''))[:300],
                                      'options': json.dumps(opts, ensure_ascii=False), 'is_anonymous': 'true'}, **kb))
    else:
        raise RuntimeError('неизвестный тип сообщения: %s' % kind)


def from_template(job):
    """Задания team/out/<день>/<имя>.json нет в репозитории, а заготовка team/daily/jobs/<имя>.json есть — создать
    задание из неё, подставив день ({day}). Так бот запускает итоги без коммита задания на каждый день."""
    m = JOB_RE.fullmatch(job)
    tpl = _path(os.path.join(TEMPLATES, m.group(2) + '.json')) if m else ''
    if not m or os.path.exists(_path(job)) or not os.path.exists(tpl):
        return False
    with open(tpl, encoding='utf-8') as f:
        text = f.read().replace('{day}', m.group(1))
    os.makedirs(os.path.dirname(_path(job)), exist_ok=True)
    with open(_path(job), 'w', encoding='utf-8') as f:
        f.write(text)
    print('задание из заготовки:', job)
    return True


def recap_env(payload):
    """Выбор владельца из утреннего опроса (payload бота: pids, free, day, at) → переменные для make-скриптов.
    Только проверенные значения: номера ММДД-N, строки до 300 знаков (не больше 30), день и время по шаблону."""
    out = {}
    day = str(payload.get('day') or '')
    if not re.fullmatch(r'\d{4}-\d\d-\d\d', day) or not ('pids' in payload or 'free' in payload):
        return out
    pids = [str(x) for x in payload.get('pids') or [] if PID_RE.fullmatch(str(x))][:100]
    free = [str(x).replace('\n', ' ')[:300] for x in payload.get('free') or [] if str(x).strip()][:30]
    out = {'RECAP_DAY': day, 'RECAP_PIDS': ','.join(pids), 'RECAP_FREE': json.dumps(free, ensure_ascii=False)}
    at = str(payload.get('at') or '')
    if re.fullmatch(r'\d{4}-\d\d-\d\d \d\d:\d\d', at):
        out['RECAP_AT'] = at
    return out


def express_env(payload):
    """Купон опубликован владельцем кнопкой в боте (payload бота: express = {pid: 'ДДММ-eN'}) → EXPRESS_PID и
    EXPRESS_BY=owner-button — «замок» team/picks/express_ig.py (без нажатия кнопки в Instagram не публикуем)."""
    ex = payload.get('express')
    if not isinstance(ex, dict) or not re.fullmatch(r'\d{4}-e\d{1,2}', str(ex.get('pid') or '')):
        return {}
    return {'EXPRESS_PID': str(ex['pid']), 'EXPRESS_BY': 'owner-button'}


def postmatch_env(payload):
    """Прогноз для послематчевого поста (payload бота: pm = {pid, league, home, away, start, pick, kef, ch}) → POSTMATCH.
    Только проверенные значения: номер ММДД-N, лига, начало «ГГГГ-ММ-ДД ЧЧ:ММ», строки до 200 знаков."""
    pm = payload.get('pm')
    if not isinstance(pm, dict) or not PID_RE.fullmatch(str(pm.get('pid') or '')):
        return {}
    if not re.fullmatch(r'\d{4}-\d\d-\d\d \d\d:\d\d', str(pm.get('start') or '')):
        return {}
    out = {k: str(pm.get(k) or '').replace('\n', ' ')[:200] for k in ('pid', 'league', 'home', 'away', 'start', 'pick', 'kef')}
    if str(pm.get('ch') or '').isdigit():
        out['ch'] = int(pm['ch'])
    # текст из чата команды, когда нейросети недоступны (team/postmatch/README.md, 29.10)
    if pm.get('facts_only'):
        out['facts_only'] = 1
    for k, n in (('story', 900), ('outro', 300)):
        if pm.get(k):
            out[k] = str(pm[k]).replace('\n', ' ')[:n]
    return {'POSTMATCH': json.dumps(out, ensure_ascii=False)}


def main(payload):
    job = str(payload.get('job') or '')
    from_template(job)
    job_path = _path(job)
    with open(job_path, encoding='utf-8') as f:
        job = json.load(f)
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, 'render') + os.pathsep + os.environ.get('PYTHONPATH', ''))
    env.update(recap_env(payload))           # утренний опрос: RECAP_PIDS / RECAP_FREE / RECAP_DAY / RECAP_AT (team/daily/ask.py)
    env.update(postmatch_env(payload))       # послематчевый пост: POSTMATCH — прогноз из payload бота (team/postmatch/run.py)
    env.update(express_env(payload))         # купон «Экспресс» опубликован кнопкой → Instagram (team/picks/express_ig.py)
    errors = []
    for script in job.get('make') or []:
        print('рисую:', script)
        script, *args = str(script).split()                  # «скрипт аргументы…» — например team/picks/day.py khl 2026-10-16
        r = subprocess.run([sys.executable, _path(script)] + args, cwd=ROOT, env=env)
        if r.returncode:
            errors.append('скрипт %s завершился с кодом %d' % (script, r.returncode))
    if job.get('make'):         # скрипт рисования мог дописать сообщения (например, число картинок известно только после него);
        try:                    # берём только "messages" — согласие владельца и qa остаются из исходного задания
            with open(job_path, encoding='utf-8') as f:
                job['messages'] = json.load(f).get('messages') or job.get('messages')
        except (OSError, ValueError) as e:
            print('задание после make не перечитано:', e)
    token = os.environ.get('TG_BOT_TOKEN')
    msgs = job.get('messages') or []
    channel = str(job.get('channel') or '@jarvibet')
    qa_ok = str(job.get('qa', '')).lower() == 'ok' and str(job.get('approved', '')).lower() == 'owner'
    for m in msgs:
        print('→ %s · %s · %s' % (m.get('to'), m.get('type', 'text'), (m.get('text') or m.get('question') or '')[:80]))
    if not token:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        return
    owner = str(job.get('owner_chat') or '') or owner_chat(token, channel)
    sent_channel = 0
    for m in msgs:
        to_channel = m.get('to') == 'channel'
        if to_channel and (not qa_ok or sent_channel >= CHANNEL_MAX):
            errors.append('в канал не отправлено (нет согласия владельца / qa=ok или превышен лимит): %s'
                          % (m.get('text') or m.get('question') or '')[:60])
            continue
        try:
            send(token, channel if to_channel else owner, m, to_channel)
            sent_channel += to_channel
        except Exception as e:                       # noqa: BLE001 — остальные сообщения всё равно отправляем
            errors.append('%s/%s: %s' % (m.get('to'), m.get('type', 'text'), e))
    if errors:
        try:
            _api(token, 'sendMessage', {'chat_id': owner, 'text': 'Команда JARVIS: не всё отправилось\n' + '\n'.join(errors)[:3500]})
        except Exception:                            # noqa: BLE001
            pass
        raise SystemExit('; '.join(errors))
