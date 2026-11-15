# -*- coding: utf-8 -*-
"""Хайлайт Instagram «Экспресс» (владелец 15.11): все экспрессы, что вышли в канал, — по сторис на купон с итогом
(✅ / ❌ у каждой ноги, счёт матча, общий кэф) + обложка-кружок. Highlights через API Instagram не создаются: владелец
выкладывает кадры историями и собирает из них актуальное в приложении (README.md рядом).

Источники (только опубликованное в канале):
- team/picks/EXPRESS_RESULTS.md — купоны, чей «Итог экспресса» вышел в канал ответом на пост купона: номер, итог, ноги со счётом;
- текст поста купона (team/out/<день>/*.json, сообщение с тем же pid) — время, ставка и кэф каждой ноги;
- MANUAL — купоны, текста которых нет в team/out (взяты из team/LOG.md).

    PYTHONPATH=render python3 team/highlights/express.py <папка>           все кадры + обложка + express.json
    PYTHONPATH=render python3 team/highlights/express.py <папка> --data    только express.json (без картинок)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'render'))

MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
MANUAL = {   # team/LOG.md 12.11 21:30 — купон по скрину владельца, текст поста в team/out не сохранился
    '1211-e4': {'head': 'НХЛ · 13 ноября · экспресс', 'kef': 1.82, 'legs': [
        dict(home='Торонто', away='Миннесота', time='03:00', bet='фора Миннесоты +1,5', kef=1.21),
        dict(home='Бостон', away='Монреаль', time='03:00', bet='инд. тотал Бостона больше 1,5', kef=1.16),
        dict(home='Оттава', away='Колорадо', time='03:00', bet='тотал больше 4,5', kef=1.30)]},
}
STATUS = {'✅': 'win', '❌': 'loss', '↩️': 'push'}
TITLE = {'win': 'ЭКСПРЕСС ЗАШЁЛ', 'loss': 'ЭКСПРЕСС НЕ ЗАШЁЛ', 'push': 'ЭКСПРЕСС · ВОЗВРАТ'}


def num(s):
    try:
        return float(s.replace(',', '.'))
    except (ValueError, AttributeError):
        return None


def results():
    """EXPRESS_RESULTS.md → [{pid, status, kef, legs: [{home, away, score, bet, mark}]}], без повторов, по порядку."""
    out, seen = [], set()
    for line in open(os.path.join(ROOT, 'team/picks/EXPRESS_RESULTS.md'), encoding='utf-8'):
        m = re.match(r'- (\d\d\.\d\d) [\d:]+ · (\d{4}-e\d+) · (✅|❌|↩️) [^·]+· кэф ([\d,]+|—) ·\s*(.*)$', line.strip())
        if not m or m.group(2) in seen:
            continue
        seen.add(m.group(2))
        legs = []
        body = m.group(5).strip()
        for part in [p.strip() for p in body.split(';') if p.strip()]:
            # «Бостон — Вегас 3:2 · инд. тотал Бостона больше 1,5 ✅» или «… 2:3 (фора +2,5) ✅»
            lm = re.match(r'(.+?) — (.+?) (\d+:\d+)\s*(?:· (.+?)|\((.+?)\))?\s*(✅|❌|↩️)$', part)
            if lm:
                legs.append(dict(home=lm.group(1).strip(), away=lm.group(2).strip(), score=lm.group(3),
                                 bet=(lm.group(4) or lm.group(5) or '').strip(), mark=STATUS[lm.group(6)]))
        out.append(dict(pid=m.group(2), status=STATUS[m.group(3)], kef=num(m.group(4)), legs=legs))
    return out


def post_text(pid):
    """Текст поста купона (HTML) из team/out — сообщение владельцу с кнопкой и этим pid."""
    day = '2026-%s-%s' % (pid[2:4], pid[:2])
    files = sorted(glob.glob(os.path.join(ROOT, 'team/out', day, '*.json'))) + sorted(glob.glob(os.path.join(ROOT, 'team/out/*/*.json')))
    for f in files:
        try:
            d = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        stack = [d]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                t = o['html'] if isinstance(o.get('html'), str) else o.get('text')
                if o.get('pid') == pid and isinstance(t, str) and 'Общий кэф' in t:
                    return t
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
    return None


def short(bet):
    b = bet.replace('индивидуальный тотал', 'инд. тотал').replace('тотал матча', 'тотал')
    b = b.replace(' (с овертаймом и буллитами)', ' с ОТ').replace(' не проиграет в основное время', ' не проиграет')
    return re.sub(r'\s+в основное время$', '', b).strip()


def parse(text):
    """Текст поста → {head, kef, legs: [{home, away, time, bet, kef}]}."""
    lines = [re.sub(r'</?b>', '', x).strip() for x in text.split('\n')]
    legs, cur = [], None
    for ln in lines[1:]:
        m = re.match(r'\d+\. (.+?) — (.+?)(?:, (?:(\d+ \w+), )?(\d\d:\d\d) МСК)?$', ln)
        if m:
            cur = dict(home=m.group(1), away=m.group(2), time=m.group(4) or '')
            legs.append(cur)
            continue
        m = re.match(r'(.+) · ([\d,]+)$', ln)
        if cur is not None and m and 'bet' not in cur:
            cur['bet'], cur['kef'] = short(m.group(1)), num(m.group(2))
    k = re.search(r'Общий кэф: ([\d,]+)', ' '.join(lines))
    return dict(head=lines[0], kef=num(k.group(1)) if k else None, legs=legs)


def league_of(head, home):
    """Лига ноги: футбол / НХЛ / КХЛ (смешанная шапка — по клубу)."""
    if head.startswith('Футбол'):
        return 'Футбол'
    if 'КХЛ' in head and 'НХЛ' in head:
        import matchday_vs as mv
        name = mv.KHL_ALIAS.get(home, home)
        try:
            mv.vs._team(name, 'KHL')
            return 'КХЛ'
        except KeyError:
            return 'НХЛ'
    return 'КХЛ' if 'КХЛ' in head else 'НХЛ'


def key(s):
    return re.sub(r'[^а-яёa-z]', '', s.lower().replace('ё', 'е'))


def collect():
    data, miss = [], []
    for r in results():
        t = post_text(r['pid'])
        post = parse(t) if t else MANUAL.get(r['pid'])
        if not post:
            miss.append(r['pid'])
            continue
        by = {(key(x['home']), key(x['away'])): x for x in r['legs']}
        legs = []
        for x in post['legs']:
            res = by.get((key(x['home']), key(x['away'])))
            if res is None and r['legs']:
                miss.append('%s: нога %s — %s без итога' % (r['pid'], x['home'], x['away']))
            mark = res['mark'] if res else ('win' if r['status'] == 'win' else None)
            legs.append(dict(home=x['home'], away=x['away'], league=league_of(post['head'], x['home']),
                             time=res['score'] if res else '', bet=x.get('bet') or (res or {}).get('bet', ''),
                             kef=x.get('kef') or 0, mark=mark, score=res['score'] if res else None))
        if r['status'] == 'push' and legs and all(x['mark'] == 'win' for x in legs):
            r['status'] = 'win'   # 0111-e5, 0211-e1: все ноги ✅, «возврат» — бот не узнал правленый владельцем текст итога
        dd, mm = r['pid'][:2], r['pid'][2:4]
        hp = post['head'].split(' · ')          # «НХЛ · 10 ноября · экспресс» → дата матчей, как в посте
        dt = hp[-2] if len(hp) >= 3 else '%d %s' % (int(dd), MON[int(mm) - 1])
        data.append(dict(pid=r['pid'], day='2026-%s-%s' % (mm, dd), date_title=dt,
                         status=r['status'], kef=r['kef'] or post['kef'], legs=legs))
    data.sort(key=lambda c: (c['day'], int(c['pid'].split('e')[1])))
    return data, miss


def cover(path):
    """Обложка актуального: Instagram показывает круг по центру кадра — звенья цепи (экспресс) в круге, без текста."""
    import matchday_vs as mv
    import nhl
    from PIL import ImageDraw
    nhl.register()
    acc = nhl.ICE
    W, H = 1080, 1920
    img = mv._background(H).convert('RGB').resize((W, H))
    d = ImageDraw.Draw(img)
    cx, cy, R = W / 2, H / 2, 330
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(22, 24, 30), outline=acc, width=14)
    w, h, t = 250, 130, 34                       # два звена цепи под углом
    import math
    from PIL import Image
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for dx in (-95, 95):
        ld.rounded_rectangle((cx + dx - w / 2, cy - h / 2, cx + dx + w / 2, cy + h / 2), radius=h / 2, outline=acc, width=t)
    layer = layer.rotate(math.degrees(0.6), center=(cx, cy), resample=Image.BICUBIC)
    img.paste(layer, (0, 0), layer)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    img.save(path, quality=92)
    return path


def render(out):
    import express_card as ec
    data, miss = collect()
    os.makedirs(out, exist_ok=True)
    json.dump(data, open(os.path.join(out, 'express.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    files = [cover(os.path.join(out, '00_cover.jpg'))]
    for i, c in enumerate(data, 1):
        p = os.path.join(out, '%02d_%s.jpg' % (i, c['pid']))
        legs = [dict(x, kef=x['kef'] or 0) for x in c['legs']]
        ec.render(legs, p, fmt='story', title=TITLE[c['status']], date_title=c['date_title'], total=c['kef'],
                  cta='ВСЕ ЭКСПРЕССЫ — В TELEGRAM')
        files.append(p)
    for m in miss:
        print('HLMISS', m, flush=True)
    return files, data


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/highlights/express'
    if '--data' in sys.argv:
        d, miss = collect()
        print(json.dumps(d, ensure_ascii=False, indent=1))
        for m in miss:
            print('HLMISS', m)
    else:
        fs, d = render(out)
        w = sum(c['status'] == 'win' for c in d)
        print('HLSTAT %d купонов: зашло %d, не зашло %d, возврат %d' % (len(d), w, sum(c['status'] == 'loss' for c in d),
                                                                     sum(c['status'] == 'push' for c in d)))
        for f in fs:
            print('HLFILE', f)
