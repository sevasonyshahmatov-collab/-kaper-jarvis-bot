"""Команда JARVIS → Telegram (событие kind='team' в itogi.yml, ручной запуск workflow_dispatch).

Облачные сессии команды до Telegram не достают, GitHub Actions — достаёт (секрет TG_BOT_TOKEN уже есть).
Руководитель команды кладёт в репозиторий задание team/out/<день>/job.json и запускает itogi.yml на своей ветке
с payload {"kind": "team", "job": "team/out/<день>/job.json"}. Здесь: выполнить скрипты рисования из задания
и отправить сообщения по порядку.

job.json:
{
  "day": "2026-10-12",
  "qa": "ok",                              # без «ok» в канал не уходит ничего (только владельцу)
  "make": ["team/out/2026-10-12/make.py"], # скрипты рисования (запуск из корня репозитория, PYTHONPATH=render)
  "channel": "@jarvibet",                  # необязательно
  "messages": [
    {"to": "owner", "type": "text", "text": "Отчёт планёрки …"},
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


def send(token, chat, msg, to_channel):
    import itogi_job as ij
    kind = msg.get('type', 'text')
    text = str(msg.get('text') or '')
    if to_channel:
        text = ij.no_emoji(text)
    mode = {'parse_mode': 'HTML'} if msg.get('html') else {}
    files = [_path(p) for p in msg.get('files') or []]
    if kind == 'text':
        for part in _chunks(text, TEXT_MAX):
            _api(token, 'sendMessage', dict(chat_id=chat, text=part, disable_web_page_preview='true', **mode))
    elif kind == 'photo':
        with open(ij.tg_ready(files[0]), 'rb') as f:
            _api(token, 'sendPhoto', dict(chat_id=chat, caption=text[:CAPTION_MAX], **mode), {'photo': f})
    elif kind == 'album':
        media, opened = [], {}
        for i, p in enumerate(files[:10]):
            m = {'type': 'photo', 'media': 'attach://p%d' % i}
            if i == 0 and text:
                m.update(caption=text[:CAPTION_MAX], **mode)
            media.append(m)
            opened['p%d' % i] = open(ij.tg_ready(p), 'rb')
        try:
            _api(token, 'sendMediaGroup', {'chat_id': chat, 'media': json.dumps(media, ensure_ascii=False)}, opened)
        finally:
            for f in opened.values():
                f.close()
    elif kind == 'documents':
        caps = list(msg.get('captions') or [])
        ij.send_documents(token, chat, [(p, (caps[i] if i < len(caps) else '')[:CAPTION_MAX]) for i, p in enumerate(files)])
        if text:
            _api(token, 'sendMessage', dict(chat_id=chat, text=text[:TEXT_MAX], **mode))
    elif kind == 'video':
        with open(files[0], 'rb') as f:
            _api(token, 'sendVideo', dict(chat_id=chat, caption=text[:CAPTION_MAX], supports_streaming='true', **mode),
                 {'video': f}, timeout=300)
    elif kind == 'poll':
        opts = [str(o)[:100] for o in msg.get('options') or []][:10]
        _api(token, 'sendPoll', {'chat_id': chat, 'question': str(msg.get('question', ''))[:300],
                                 'options': json.dumps(opts, ensure_ascii=False), 'is_anonymous': 'true'})
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
    qa_ok = str(job.get('qa', '')).lower() == 'ok'
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
            errors.append('в канал не отправлено (нет qa=ok или превышен лимит): %s' % (m.get('text') or m.get('question') or '')[:60])
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
