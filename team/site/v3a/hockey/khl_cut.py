# -*- coding: utf-8 -*-
"""Фото игроков КХЛ без белого фона (владелец 14.11: «у игроков КХЛ сзади белый фон — убрать у всех»).
Берёт адреса фото из hockey/data/pp/khl/*.json (www.khl.ru), убирает фон (rembg, модель для людей), пишет
hockey/data/kph/<папка>_<номер>.webp по адресу фото на khl.ru (…/teamplayers_db/<папка>/<номер>.jpg) — так любая страница находит
вырезку прямо по адресу фото (assets/kph.js); index.json — список готовых.
Готовые не пересчитывает; бюджет времени — KPH_BUDGET сек, следующий запуск продолжит. Запуск — site-v3a-khlcut.yml."""
import glob, io, json, os, re, time
import requests
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'data', 'kph'); os.makedirs(OUT, exist_ok=True)
IDX = os.path.join(OUT, 'index.json')
idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
BUDGET = float(os.environ.get('KPH_BUDGET', 40 * 60)); T0 = time.time()
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0 (JarvisSiteBot; player photos)'
import rembg
sess = rembg.new_session('u2net_human_seg')
todo, seen = [], set(idx)
V3A = os.path.dirname(H)
files = glob.glob(os.path.join(H, 'data', '**', '*.js*'), recursive=True) + glob.glob(os.path.join(V3A, 'data', '*.js*'))
for f in sorted(files):
    if os.sep + 'kph' + os.sep in f: continue
    try: txt = open(f, encoding='utf-8', errors='ignore').read()
    except Exception: continue  # noqa: BLE001
    for m in re.finditer(r'https?://www\.khl\.ru/img/teamplayers_db/(\d+)/(\d+)\.jpg', txt):
        pid = m.group(1) + '_' + m.group(2)
        if pid not in seen: seen.add(pid); todo.append((pid, m.group(0)))
print('к обработке', len(todo), 'готово раньше', len(idx), flush=True)
ok = bad = 0
for pid, u in todo:
    if time.time() - T0 > BUDGET: print('бюджет времени исчерпан'); break
    try:
        r = S.get(u, timeout=40)
        if r.status_code != 200: bad += 1; print('нет', pid, r.status_code); continue
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
        cut = rembg.remove(im, session=sess, post_process_mask=True)
        bb = cut.getchannel('A').point(lambda v: 255 if v > 30 else 0).getbbox()
        if not bb: bad += 1; continue
        # обрезаем только по бокам и сверху — низ (плечи) оставляем как в исходнике
        cut = cut.crop((bb[0], bb[1], bb[2], cut.height))
        if cut.height > 600: cut = cut.resize((round(cut.width * 600 / cut.height), 600), Image.LANCZOS)
        cut.save(os.path.join(OUT, pid + '.webp'), 'WEBP', quality=88, method=6)
        idx[pid] = pid + '.webp'; ok += 1
        if ok % 50 == 0:
            json.dump(idx, open(IDX, 'w'), separators=(',', ':')); print('ok', ok, flush=True)
    except Exception as e:  # noqa: BLE001
        bad += 1; print('err', pid, repr(e)[:100])
json.dump(idx, open(IDX, 'w'), separators=(',', ':'))
print('готово', ok, 'ошибок', bad, 'всего в индексе', len(idx))
