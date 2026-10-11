"""Команда JARVIS → Telegram (событие kind='team' в itogi.yml, ручной запуск workflow_dispatch).

Облачные сессии команды до Telegram не достают, GitHub Actions — достаёт (секрет TG_BOT_TOKEN уже есть).
Руководитель команды кладёт в репозиторий задание team/out/<день>/job.json и запускает itogi.yml на своей ветке
с payload {"kind": "team", "job": "team/out/<день>/job.json"}. Здесь: выполнить скрипты рисования из задания
и отправить сообщения по порядку.

Режим согласия: утром команда шлёт владельцу предложения с кнопками (бот таблицы КХЛ, teamCallback_):
  "buttons": "post"     — готовый пост ровно в том виде, как уйдёт в канал: «Опубликовать» (бот сразу копирует его в канал),
                          «Поправить», «Не надо»; у альбома кнопки — следующим сообщением;
  "buttons": "proposal" — предложение работы: «Да» (согласие пишется в team/INBOX.md, команда выполнит), «Нет», «Поправить».
  "pid": "1012-3"       — номер предложения (месяц-день-№), по нему команда находит решение владельца в INBOX.
Сама команда отправляет в канал только задания с "approved": "owner" и "qa": "ok" — то, что владелец одобрил кнопкой «Да».

job.json:
{
  "day": "2026-10-12",
  "qa": "ok",                              # без «ok» в канал не уходит ничего (только владельцу)
  "approved": "owner",                     # только для заданий, одобренных владельцем; без него в канал — ничего
  "make": ["team/out/2026-10-12/make.py"], # скрипты рисования (запуск из корня репозитория, PYTHONPATH=render)
  "channel": "@jarvibet",                  # необязательно
  "messages": [
    {"to": "owner", "type": "text", "text": "Отчёт планёрки …"},
    {"to": "owner", "type": "photo", "files": ["…"], "text": "подпись для канала", "buttons": "post", "pid": "1012-1"},
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
import subprocess
import sys

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
                [{'text': 'Поправить', 'callback_data': 'tm|fix|' + pid}, {'text': 'Не надо', 'callback_data': 'tm|no|' + pid}]]
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
    if to_channel or msg.get('buttons') == 'post':          # пост для канала — без эмодзи (правило канала)
        text = ij.no_emoji(text)
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
    elif kind == 'poll':
        opts = [str(o)[:100] for o in msg.get('options') or []][:10]
        _api(token, 'sendPoll', dict({'chat_id': chat, 'question': str(msg.get('question', ''))[:300],
                                      'options': json.dumps(opts, ensure_ascii=False), 'is_anonymous': 'true'}, **kb))
    else:
        raise RuntimeError('неизвестный тип сообщения: %s' % kind)


def main(payload):
    job_path = _path(str(payload.get('job') or ''))
    with open(job_path, encoding='utf-8') as f:
        job = json.load(f)
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, 'render') + os.pathsep + os.environ.get('PYTHONPATH', ''))
    errors = []
    for script in job.get('make') or []:
        print('рисую:', script)
        r = subprocess.run([sys.executable, _path(script)], cwd=ROOT, env=env)
        if r.returncode:
            errors.append('скрипт %s завершился с кодом %d' % (script, r.returncode))
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
