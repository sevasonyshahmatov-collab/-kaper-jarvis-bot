# -*- coding: utf-8 -*-
"""Разборы всех сыгранных матчей КХЛ и НХЛ для сайта и мини-приложения (владелец 26.10: «послематчевая аналитика даже
для матчей, на которые не ставили, и связывать это со ставками и трендами — чтобы люди возвращались на сайт»).

На каждый матч:
  - хроника матча — team/postmatch/chronicle.py (та же, что у послематчевых постов канала);
  - тренды обеих команд по матчам сезона: форма, серия, тоталы и голы за последние 10 игр, дом/выезд;
  - «как сыграли бы ставки» — тотал, исход, фора по итоговому счёту (считаем сами, без нейросети);
  - прогноз из канала, если был (site/stats/published.json — team/site/months.py);
  - следующие матчи обеих команд;
  - текст: заголовок, рассказ о матче и «что это значит для ставок» — Gemini (бесплатный ключ GEMINI_API_KEY, как у
    team/postmatch/writer.py). Не ответил — короткая сводка по цифрам (ai: false), при следующем запуске пробуем снова.
Результат — <сайт>/razbor/data/<день МСК>.json: {ключ: разбор}. Страницы собирает team/site/razbor_pages.py.

    python team/site/razbor.py <папка сайта> [--hours 40] [--limit 30] [--minutes 10]
"""
import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in ('team/daily', 'team/picks', 'team/postmatch'):
    sys.path.insert(0, os.path.join(ROOT, p))

import requests  # noqa: E402

import chronicle  # noqa: E402
import data  # noqa: E402
import writer  # noqa: E402  модели Gemini по ключу — writer._gemini_models

MSK = data.MSK
LINE = 5.5                 # тотал для трендов: самая частая линия и в КХЛ, и в НХЛ
GAP = 13                   # секунд между запросами к Gemini: бесплатный тариф — около 5 запросов в минуту

SYSTEM = """Ты — хоккейный аналитик сайта прогнозов JARVIS (КХЛ и НХЛ). Пишешь разбор сыгранного матча для болельщиков \
и тех, кто ставит на хоккей.

Как писать:
- от третьего лица, спокойно и по делу, как хороший спортивный журналист; живой язык, без канцелярита и пафоса;
- рассказ — рисунок матча по хронике: как начали, где перелом, что решило исход (большинство, вратарь, броски, игрок, \
концовка). Минуты, фамилии, цифры — только из хроники и трендов, ничего не выдумывай;
- блок про ставки — свяжи матч с трендами команд: какая серия продолжилась или прервалась, что говорит этот матч о \
следующих играх команд (тоталы, форма, большинство). Это наблюдения, а не советы: без «ставьте», «берите», гарантий;
- если был наш прогноз из канала — коротко скажи, зашёл ли он и почему; если не было — не упоминай прогноз вообще;
- фамилии игроков НХЛ — по-русски, как пишут sports.ru и «Чемпионат» (Овечкин, Макдэвид, Капризов); не уверен — \
опиши без фамилии («первый центр гостей», «вратарь хозяев»);
- без штампов: «матч получился», «как говорится», «что ж», «в итоге», «финальная сирена», «не подвёл», «расставил \
все точки»; каждый разбор начинай по-своему;
- без эмодзи, markdown, хэштегов; нельзя: названия букмекеров, «верняк», «гарантия», 100 %.

Формат ответа — ровно три части, разделённые строкой из трёх дефисов (---):
1) заголовок разбора: 40–90 знаков, без точки в конце, суть матча (не просто «Команда обыграла команду»);
2) рассказ о матче: 2 абзаца, 600–1000 знаков;
3) что это значит для ставок: 3–4 предложения, 250–500 знаков.
Больше ничего не пиши."""

ANGLES = ['начни с момента, который решил матч', 'начни с игрока или вратаря, который сделал этот матч',
          'начни с цифры, которая лучше всего объясняет игру', 'начни с того, как команды подошли к матчу (форма, серии)',
          'начни с концовки и вернись к тому, как к ней пришли', 'начни с того, как команды начали игру',
          'начни с тактики: кто чем давил и как соперник отвечал']
BAD = ('букмекер', 'фонбет', 'верняк', 'гарант', 'ставьте', 'джарвис', 'матч получился', 'как говорится', 'что ж,',
       'в итоге', 'финальная сирена')


# ───────────────────────────── матчи и тренды

def norm(t):
    return re.sub(r'[^0-9a-zа-я]+', ' ', str(t or '').lower().replace('ё', 'е')).strip()


def key_of(g):
    return '%s-%s-%s-%s' % (g['league'].lower(), g['start'].strftime('%Y-%m-%d'), norm(g['home']), norm(g['away']))


def season_start(now):
    return datetime(now.year if now.month >= 8 else now.year - 1, 8, 1, tzinfo=MSK)


def khl_season(now):
    """Все матчи сезона КХЛ до now+10 дней (сыгранные — со счётом, будущие — для «следующего матча»)."""
    return data.khl_games(season_start(now), now + timedelta(days=10))


_nhl_sched = {}


def nhl_team_games(ab):
    """Матчи клуба НХЛ за сезон (club-schedule-season) в общем виде data.py."""
    if ab in _nhl_sched:
        return _nhl_sched[ab]
    out = []
    try:
        j = data.nhl_get('club-schedule-season/%s/now' % ab)
    except Exception as e:  # noqa: BLE001
        print('RAZBORERR расписание %s: %r' % (ab, e), flush=True)
        j = {}
    for g in j.get('games') or []:
        if g.get('gameType') not in (2, 3):
            continue
        h, a = g['homeTeam'], g['awayTeam']
        fin = g.get('gameState') in ('OFF', 'FINAL')
        lp = (g.get('gameOutcome') or {}).get('lastPeriodType')
        out.append(dict(league='NHL', id=g.get('id'), start=data._msk_dt(g['startTimeUTC']),
                        home=data.teams.NHL_RU.get(h['abbrev'], h['abbrev']), away=data.teams.NHL_RU.get(a['abbrev'], a['abbrev']),
                        state='final' if fin else 'future', hg=h.get('score') if fin else None, ag=a.get('score') if fin else None,
                        end={'OT': 'ОТ', 'SO': 'Б'}.get(lp, '')))
    _nhl_sched[ab] = out
    return out


def plural(n, one, few, many):
    n = abs(n)
    w = one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many
    return '%d %s' % (n, w)


def trend(team, games, upto):
    """Тренды команды по сыгранным матчам до upto включительно."""
    gs = sorted((g for g in games if g['state'] == 'final' and g.get('hg') is not None and team in (g['home'], g['away'])
                 and g['start'] <= upto), key=lambda g: g['start'])
    if not gs:
        return None
    res, gf, ga, home, away = [], [], [], [0, 0], [0, 0]
    for g in gs:
        h = g['home'] == team
        f, a = (g['hg'], g['ag']) if h else (g['ag'], g['hg'])
        res.append('В' if f > a else 'П')
        gf.append(f)
        ga.append(a)
        rec = home if h else away
        rec[0 if f > a else 1] += 1
    last = res[-1]
    streak = len(res) - len(''.join(res).rstrip(last))
    l10 = list(zip(gf[-10:], ga[-10:]))
    over = sum(f + a > LINE for f, a in l10)
    return dict(gp=len(gs), form=''.join(res[-5:]),
                streak=('победа в последнем матче' if streak == 1 else '%s подряд' % plural(streak, 'победа', 'победы', 'побед'))
                if last == 'В' else ('поражение в последнем матче' if streak == 1 else
                                    '%s подряд' % plural(streak, 'поражение', 'поражения', 'поражений')),
                sn=streak if last == 'В' else -streak,
                over='%d из %d' % (over, len(l10)), n10=len(l10),
                gf10=round(sum(f for f, _ in l10) / len(l10), 1), ga10=round(sum(a for _, a in l10) / len(l10), 1),
                home='%d–%d' % tuple(home), away='%d–%d' % tuple(away))


def next_game(team, games, after):
    fut = sorted((g for g in games if g['start'] > after and team in (g['home'], g['away']) and g['state'] != 'final'),
                 key=lambda g: g['start'])
    if not fut:
        return None
    g = fut[0]
    home = g['home'] == team
    return dict(d=g['start'].strftime('%Y-%m-%d %H:%M'), opp=g['away'] if home else g['home'], home=home)


def bets(g):
    """Как сыграли бы основные ставки по итоговому счёту (тотал с ОТ, исход с ОТ; исход в осн. время — по g['end'])."""
    h, a, end = g['hg'], g['ag'], g.get('end') or ''
    tot = h + a
    win = g['home'] if h > a else g['away']
    out = [dict(t='Тотал', v='%s %s' % (plural(tot, 'гол', 'гола', 'голов'), '— больше 5,5' if tot > 5.5 else '— меньше 5,5'))]
    if end:
        out.append(dict(t='Основное время', v='ничья, решил %s' % ('овертайм' if end == 'ОТ' else 'буллиты')))
        out.append(dict(t='Победа с ОТ', v=win))
    else:
        out.append(dict(t='Основное время', v='победа: %s' % win))
        d = abs(h - a)
        out.append(dict(t='Фора', v='%s −1,5 %s' % (win, 'зашла' if d >= 2 else 'не зашла (победа в одну шайбу)')))
    out.append(dict(t='Обе забьют', v='да' if h and a else 'нет'))
    return out


# ───────────────────────────── текст

def facts_text(g, tr, nx, pick, chron):
    lines = ['Лига: %s. Матч: %s (дома) — %s, итог %d:%d%s.' % (
        'КХЛ' if g['league'] == 'KHL' else 'НХЛ', g['home'], g['away'], g['hg'], g['ag'],
        {'ОТ': ' в овертайме', 'Б': ' по буллитам'}.get(g.get('end') or '', ''))]
    for t in (g['home'], g['away']):
        x = tr.get(t)
        if x:
            lines.append('Тренды %s (с учётом этого матча, %s сезона): последние 5 — %s; серия — %s; в последних %d играх '
                         'тотал больше 5,5 — %s; забивает в среднем %s, пропускает %s; дома %s, в гостях %s.' % (
                             t, plural(x['gp'], 'матч', 'матча', 'матчей'), x['form'], x['streak'], x['n10'], x['over'],
                             x['gf10'], x['ga10'], x['home'], x['away']))
        n = nx.get(t)
        if n:
            lines.append('Следующий матч %s: %s, %s, %s.' % (t, n['d'], 'дома' if n['home'] else 'в гостях', n['opp']))
    if pick:
        lines.append('Наш прогноз в канале на этот матч: %s, кэф %s — %s.' % (
            pick['bet'], pick.get('kef') or '—', {'win': 'зашёл', 'loss': 'не зашёл', 'push': 'возврат'}.get(pick.get('r'), 'итог не подведён')))
    else:
        lines.append('Нашего прогноза на этот матч не было.')
    lines += ['', chron]
    return '\n'.join(lines)


def check(txt):
    parts = [re.sub(r'[ \t]+', ' ', x).strip().strip('*#').strip() for x in re.split(r'\n\s*-{3,}\s*\n', txt.strip())]
    low = txt.lower().replace('ё', 'е')
    if len(parts) != 3 or not all(parts):
        return None, 'нужно ровно три части через --- (сейчас %d)' % len(parts)
    t, s, b = parts
    if not 25 <= len(t) <= 110:
        return None, 'заголовок %d знаков, нужно 40–90' % len(t)
    if not 450 <= len(s) <= 1400 or not 180 <= len(b) <= 700:
        return None, 'длина рассказа %d (нужно 600–1000) и блока о ставках %d (нужно 250–500)' % (len(s), len(b))
    bad = [w for w in BAD if w in low]
    if bad:
        return None, 'запрещённые слова и штампы: %s' % ', '.join(bad)
    paras = [re.sub(r'\s+', ' ', x).strip() for x in re.split(r'\n\s*\n', s) if x.strip()]
    return dict(title=t.rstrip('.'), story=paras, bets=re.sub(r'\s+', ' ', b)), ''


def quota(r):
    """Ответ 429 → (дневной ли лимит, сколько секунд ждать по совету Google, название лимита)."""
    try:
        det = (r.json().get('error') or {}).get('details') or []
    except ValueError:
        det = []
    ids, wait = [], 60
    for d in det:
        for v in d.get('violations') or []:
            ids.append(str(v.get('quotaId') or v.get('quotaMetric') or ''))
        m = re.match(r'(\d+)', str(d.get('retryDelay') or ''))
        if m:
            wait = int(m.group(1)) + 2
    return any('PerDay' in q for q in ids), wait, ','.join(ids)[:160]


_dead = set()                  # модели, у которых на сегодня кончился дневной лимит
DEADLINE = [0.0]


def gemini(key, models, user):
    for model in models:
        if model in _dead:
            continue
        msgs = list(user)
        for attempt in range(3):
            if time.time() > DEADLINE[0]:
                return None
            time.sleep(GAP)
            try:
                r = requests.post(writer.GEMINI_URL % model, headers={'x-goog-api-key': key}, timeout=90, json={
                    'systemInstruction': {'parts': [{'text': SYSTEM}]},
                    'contents': [{'role': 'user', 'parts': [{'text': '\n\n'.join(msgs)}]}],
                    'generationConfig': {'temperature': 0.9, 'maxOutputTokens': 8192}})
            except requests.RequestException as e:
                print('RAZBORERR Gemini %s связь: %r' % (model, e), flush=True)
                break
            if r.status_code == 429:
                day, wait, ids = quota(r)
                print('RAZBORERR Gemini %s: лимит %s (%s)' % (model, 'на день' if day else 'в минуту, жду %d с' % wait, ids), flush=True)
                if day:
                    _dead.add(model)
                    break
                if attempt < 2 and wait <= 90:
                    time.sleep(wait)
                    continue
                break
            if r.status_code >= 500 and attempt < 2:
                time.sleep(20)
                continue
            if r.status_code != 200:
                if r.status_code == 404:
                    _dead.add(model)
                print('RAZBORERR Gemini %s: %s %s' % (model, r.status_code, r.text[:200].replace('\n', ' ')), flush=True)
                break
            cand = (r.json().get('candidates') or [{}])[0]
            txt = ''.join(x.get('text', '') for x in (cand.get('content') or {}).get('parts') or [] if not x.get('thought'))
            body, why = check(txt) if txt else (None, 'пустой ответ')
            if body:
                body['model'] = model
                return body
            print('RAZBORERR текст не подошёл (%s)' % why, flush=True)
            msgs.append('Предыдущий вариант не подошёл: %s. Перепиши полностью.' % why)
    return None


def plain_text(g, tr):
    """Сводка без нейросети: нейросеть не ответила."""
    h, a = g['home'], g['away']
    win, los = (h, a) if g['hg'] > g['ag'] else (a, h)
    end = {'ОТ': ' в овертайме', 'Б': ' по буллитам'}.get(g.get('end') or '', '')
    s = ['%s обыграл %s со счётом %d:%d%s.' % (win, los, max(g['hg'], g['ag']), min(g['hg'], g['ag']), end)]
    for t in (h, a):
        x = tr.get(t)
        if x:
            s.append('У %s %s, в последних %d играх тотал больше 5,5 — %s.' % (t, x['streak'], x['n10'], x['over']))
    return dict(title='%s — %s: %d:%d%s' % (h, a, g['hg'], g['ag'], end), story=[' '.join(s)], bets='')


# ───────────────────────────── запуск

def load(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def finals(now, hours):
    """Сыгранные матчи КХЛ и НХЛ с началом за последние hours часов + все матчи сезона для трендов."""
    t0 = now - timedelta(hours=hours)
    out, season = [], {'KHL': [], 'NHL': []}
    try:
        season['KHL'] = khl_season(now)
        win = data.khl_games(t0, now, detail_if=lambda h, a: True)       # ОТ/Б — из карточки матча
        out += [g for g in win if g['state'] == 'final']
    except Exception as e:  # noqa: BLE001
        print('RAZBORERR КХЛ: %r' % e, flush=True)
    for k in range(3):
        day = (now - timedelta(days=k)).date().isoformat()
        try:
            out += [g for g in data.nhl_day(day) if g['state'] == 'final' and g['start'] >= t0]
        except Exception as e:  # noqa: BLE001
            print('RAZBORERR НХЛ %s: %r' % (day, e), flush=True)
    seen, uniq = set(), []
    for g in out:
        if (g['league'], g['id']) not in seen:
            seen.add((g['league'], g['id']))
            uniq.append(g)
    abs_ = sorted({ab for g in uniq if g['league'] == 'NHL' for ab in (g.get('ab_h'), g.get('ab_a')) if ab})
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(nhl_team_games, abs_))
    return sorted(uniq, key=lambda g: g['start']), season


def published(site):
    pub = load(os.path.join(site, 'stats', 'published.json')) or []
    return {('%s-%s-%s-%s' % (x['lg'], x['d'][:10], norm(x['h']), norm(x['a']))): x for x in pub}


def make(site, hours=40, limit=30, budget=10 * 60):
    now = data.now_msk()
    games, season = finals(now, hours)
    pub = published(site)
    print('RAZBOR сыграно за %d ч: %d (КХЛ %d, НХЛ %d)' % (hours, len(games), sum(g['league'] == 'KHL' for g in games),
                                                          sum(g['league'] == 'NHL' for g in games)), flush=True)
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    models = writer._gemini_models(key) if key else []
    if not key:
        print('RAZBORERR нет GEMINI_API_KEY — только сводки по цифрам', flush=True)
    done = ai = 0
    DEADLINE[0] = time.time() + budget
    for g in games:
        if models and all(m in _dead for m in models):
            print('RAZBOR у всех моделей кончился дневной лимит — остальные разборы в следующий запуск', flush=True)
            break
        if time.time() > DEADLINE[0]:
            print('RAZBOR вышло время — остальные разборы в следующий запуск', flush=True)
            break
        k = key_of(g)
        path = os.path.join(site, 'razbor', 'data', g['start'].strftime('%Y-%m-%d') + '.json')
        day = load(path) or {}
        if day.get(k, {}).get('ai') or (day.get(k) and not models):
            continue
        if day.get(k) and all(m in _dead for m in models):
            continue
        if done >= limit:
            break
        if g['league'] == 'KHL':
            pool = season['KHL']
        else:
            pool = nhl_team_games(g.get('ab_h')) + nhl_team_games(g.get('ab_a'))
        pool = [x for x in pool if not (x['home'] == g['home'] and x['away'] == g['away'] and x['start'].date() == g['start'].date())] + [g]
        tr = {t: trend(t, pool, g['start']) for t in (g['home'], g['away'])}
        nx = {t: next_game(t, pool, g['start'] + timedelta(hours=3)) for t in (g['home'], g['away'])}
        pick = pub.get(k)
        p = dict(league=g['league'], home=g['home'], away=g['away'])
        chron = chronicle.facts(p, g)
        text = None
        if models and chron:
            rnd = random.Random(k)
            user = ['Как подать: %s.' % rnd.choice(ANGLES), facts_text(g, tr, nx, pick, chron)]
            text = gemini(key, models, user)
        rec = dict(text or plain_text(g, tr), ai=bool(text), lg=g['league'].lower(), d=g['start'].strftime('%Y-%m-%d %H:%M'),
                   h=g['home'], a=g['away'], hg=g['hg'], ag=g['ag'], end=g.get('end') or '', tr=tr, nx=nx, bets_t=bets(g),
                   pick=dict(bet=pick['bet'], kef=pick.get('kef'), r=pick.get('r')) if pick else None,
                   built=now.strftime('%Y-%m-%d %H:%M'))
        day[k] = rec
        save(path, day)
        done += 1
        ai += bool(text)
        print('RAZBOR %s — %s %d:%d: %s' % (g['home'], g['away'], g['hg'], g['ag'],
                                           ('нейросеть (%s): %s' % (text['model'], text['title'])) if text else 'сводка по цифрам'), flush=True)
    print('RAZBOR итого: новых разборов %d, из них нейросетью %d' % (done, ai), flush=True)


def main():
    a = sys.argv[1:]
    opt = lambda n, d: int(a[a.index(n) + 1]) if n in a else d  # noqa: E731
    make(a[0], opt('--hours', 40), opt('--limit', 30), opt('--minutes', 10) * 60)


if __name__ == '__main__':
    main()
