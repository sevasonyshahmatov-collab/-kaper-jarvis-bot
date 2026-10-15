# -*- coding: utf-8 -*-
"""Наборы эмодзи и стикеров канала в Telegram через бота (Bot API).
Владелец наборов — владелец канала @jarvibet (создатель канала по getChatAdministrators), имя набора —
<set>_by_<имя бота>. Что публиковать — manifest.json (team/emoji/build/ собирает team/emoji/build.py,
team/stickers/build/ — team/stickers/anim.py); файлы лежат рядом с манифестом.

Набор в манифесте: {"name", "title", "sticker_type": "custom_emoji" (по умолчанию) | "regular", "items": [...]},
элемент: {"key", "file", "format": "static" | "video", "emoji", "keywords"?: [...], "replace"?: true | "force"}.

Что делает (повторный запуск безопасен, прерванный — продолжает с места остановки):
  1. набора нет — createNewStickerSet (первые 50), остальные — addStickerToSet по порядку;
     набор есть — дописывает только недостающие в конец (по числу); при ошибке добавления набор останавливается,
     чтобы порядок не съехал (следующий запуск продолжит с того же места);
  2. замены: элемент с "replace" меняется на месте (replaceStickerInSet: тот же номер в наборе, ссылка та же).
     Сопоставление — по позиции; перед заменой проверяется, что в наборе столько же стикеров, сколько в манифесте,
     и эмодзи на позиции совпадает с эмодзи элемента — иначе набор не трогаем. Уже заменённый (формат в наборе
     совпадает: видео ↔ "video") пропускается; "replace": "force" — заменить и видео на видео, если размер файла
     в Telegram отличается от локального;
  3. бот присылает владельцу ссылки t.me/addemoji/<имя> (эмодзи) и t.me/addstickers/<имя> (стикеры).

Запуск в Actions заданием команды (нужен TG_BOT_TOKEN):
  "make": ["team/emoji/publish.py team/stickers/build/manifest.json team/emoji/build/manifest.json"]
Без аргументов — team/emoji/build/manifest.json. --dry-run — только читает наборы и печатает план, ничего не меняет.
Без TG_BOT_TOKEN — печатает локальный план по манифестам и выходит."""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT = os.path.join(ROOT, 'team', 'emoji', 'build', 'manifest.json')
TOKEN = os.environ.get('TG_BOT_TOKEN')
CHANNEL = '@jarvibet'
FIRST = 50                                   # createNewStickerSet принимает 1–50 стикеров
LIMIT = {'regular': 120, 'custom_emoji': 200}
LINK = {'regular': 'https://t.me/addstickers/%s', 'custom_emoji': 'https://t.me/addemoji/%s'}


def api(method, data=None, files=None):
    import requests
    for k in range(4):
        r = requests.post('https://api.telegram.org/bot%s/%s' % (TOKEN, method), data=data or {}, files=files, timeout=120)
        j = r.json()
        if j.get('ok'):
            return j['result']
        ra = (j.get('parameters') or {}).get('retry_after')
        if ra and k < 3:
            time.sleep(ra + 1)
            continue
        raise RuntimeError('%s: %s' % (method, j.get('description')))


def sticker(item, attach):
    s = {'sticker': 'attach://' + attach, 'format': item['format'], 'emoji_list': [item['emoji']]}
    if item.get('keywords'):
        s['keywords'] = item['keywords'][:20]
    return s


def load(path):
    with open(path, encoding='utf-8') as f:
        man = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    for s in man['sets']:
        s.setdefault('sticker_type', 'custom_emoji')
        for it in s['items']:
            it['path'] = os.path.join(base, it['file'])
            if not os.path.exists(it['path']):
                raise SystemExit('нет файла %s (манифест %s)' % (it['path'], path))
        if len(s['items']) > LIMIT[s['sticker_type']]:
            raise SystemExit('в наборе %s больше %d' % (s['name'], LIMIT[s['sticker_type']]))
    return man


def _norm(e):
    return (e or '').replace('️', '')


def needs_replace(it, st):
    """Нужна ли замена стикера st (из getStickerSet) на элемент it."""
    want_video = it['format'] == 'video'
    if bool(st.get('is_video')) != want_video or bool(st.get('is_animated')):
        return True
    return it.get('replace') == 'force' and st.get('file_size') not in (None, os.path.getsize(it['path']))


def publish_set(s, bot, owner, dry):
    """→ (ссылка, добавлено, заменено, ошибки)."""
    name = '%s_by_%s' % (s['name'], bot)
    items, kind = s['items'], s['sticker_type']
    errors, added, replaced = [], 0, 0
    try:
        have = api('getStickerSet', {'name': name})['stickers']
        print('набор %s уже есть: %d из %d' % (name, len(have), len(items)))
    except RuntimeError:
        have = None
    if have is None:
        first = items[:FIRST]
        print('создаю набор %s (%s): %d' % (name, kind, len(first)))
        if not dry:
            files = {'f%d' % i: open(it['path'], 'rb') for i, it in enumerate(first)}
            try:
                api('createNewStickerSet', {'user_id': owner, 'name': name, 'title': s['title'], 'sticker_type': kind,
                                            'stickers': json.dumps([sticker(it, 'f%d' % i) for i, it in enumerate(first)],
                                                                   ensure_ascii=False)}, files)
            finally:
                for f in files.values():
                    f.close()
        added += len(first)
        n_have = len(first)
    else:
        n_have = len(have)
    for it in items[n_have:]:
        print('добавляю', it['key'])
        if dry:
            added += 1
            continue
        with open(it['path'], 'rb') as f:
            try:
                api('addStickerToSet', {'user_id': owner, 'name': name,
                                        'sticker': json.dumps(sticker(it, 'f0'), ensure_ascii=False)}, {'f0': f})
            except RuntimeError as e:
                errors.append('%s %s: %s' % (name, it['file'], e))
                print('ОШИБКА', errors[-1], '— набор остановлен, следующий запуск продолжит отсюда')
                break
        added += 1
        time.sleep(0.4)
    # замены на месте
    todo = [i for i, it in enumerate(items) if it.get('replace')]
    if todo and not errors and have is not None:
        cur = have if dry else api('getStickerSet', {'name': name})['stickers']
        if len(cur) != len(items):
            errors.append('%s: в наборе %d, в манифесте %d — замены по позиции не делаю' % (name, len(cur), len(items)))
        else:
            bad = [items[i]['key'] for i in todo if _norm(cur[i].get('emoji')) != _norm(items[i]['emoji'])]
            if bad:
                errors.append('%s: эмодзи на позициях не совпадают (%s) — замены не делаю' % (name, ', '.join(bad[:5])))
            for i in ([] if bad else todo):
                it, st = items[i], cur[i]
                if not needs_replace(it, st):
                    continue
                print('заменяю #%d %s (%s → %s)' % (i, it['key'], 'video' if st.get('is_video') else 'static',
                                                     it['format']))
                if dry:
                    replaced += 1
                    continue
                with open(it['path'], 'rb') as f:
                    try:
                        api('replaceStickerInSet', {'user_id': owner, 'name': name, 'old_sticker': st['file_id'],
                                                    'sticker': json.dumps(sticker(it, 'f0'), ensure_ascii=False)},
                            {'f0': f})
                    except RuntimeError as e:
                        errors.append('%s #%d %s: %s' % (name, i, it['file'], e))
                        print('ОШИБКА', errors[-1])
                        continue
                replaced += 1
                time.sleep(0.4)
    link = '%s — %s (%d шт.)' % (s['title'], LINK[kind] % name, len(items))
    print('готово:', link, '· добавлено %d, заменено %d' % (added, replaced))
    return link, added, replaced, errors


def plan(mans):
    for path, man in mans:
        for s in man['sets']:
            items = s['items']
            print('%s · %s (%s): %d шт., видео %d, к замене %d' % (
                path, s['name'], s['sticker_type'], len(items), sum(i['format'] == 'video' for i in items),
                sum(bool(i.get('replace')) for i in items)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    mans = [(p, load(p)) for p in (args or [DEFAULT])]
    if not TOKEN:
        print('TG_BOT_TOKEN не задан — наборы не трогаю; план по манифестам:')
        plan(mans)
        return
    bot = api('getMe')['username']
    owner = next(m['user']['id'] for m in api('getChatAdministrators', {'chat_id': CHANNEL}) if m['status'] == 'creator')
    links, errors, n_rep = [], [], 0
    for _, man in mans:
        for s in man['sets']:
            link, _, rep, err = publish_set(s, bot, owner, dry)
            links.append(link)
            errors += err
            n_rep += rep
    if dry:
        print('dry-run: ничего не изменено')
        return
    text = 'Наборы канала готовы (владелец — вы):\n' + '\n'.join(links)
    if n_rep:
        text += '\n\nОбновлено на месте: %d (ссылки прежние).' % n_rep
    if errors:
        text += '\n\nНе всё получилось: %d — команда поправит.' % len(errors)
    api('sendMessage', {'chat_id': owner, 'text': text, 'disable_web_page_preview': 'true'})
    if errors:
        print('\n'.join(errors))
        sys.exit(1)


if __name__ == '__main__':
    main()
