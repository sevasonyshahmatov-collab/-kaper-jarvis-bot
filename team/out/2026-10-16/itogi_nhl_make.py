# -*- coding: utf-8 -*-
"""«Итоги дня» НХЛ за ночь на 16.10 (игровой день НХЛ 2026-10-15 по Нью-Йорку) в новом шаблоне «Матчи дня»
(render/matchday_vs.py, results=True): все 6 вариантов → out/itogi/nhl-2026-10-16/<вариант>.jpg
(больше 5 матчей — несколько постеров: <вариант>_1.jpg, <вариант>_2.jpg…, деление как у itogi_job.split_matchi).

Счёт — из официального API НХЛ (api-web.nhle.com/v1/score/2026-10-15, как team/picks/nhl_data.py); ОТ/Б — по
gameOutcome.lastPeriodType (запасной путь — periodDescriptor.periodType). Названия — team/picks/teams.NHL_RU.
Печатает счёт строками «NHLRES …». Число постеров известно только после загрузки, поэтому скрипт дописывает в
задание team/out/2026-10-16/itogi_nhl.json настоящие списки файлов и подпись со счётом (team_job.py перечитывает
сообщения задания после make).

Запуск из корня: PYTHONPATH=render python team/out/2026-10-16/itogi_nhl_make.py [папка]
Без сети (проверка в сессии): NHL_SCORE_JSON=<файл с ответом score/2026-10-15> — читать счёт из файла;
NHL_NO_JOB_UPDATE=1 — не трогать задание."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'render'), os.path.join(ROOT, 'team', 'picks')]

import itogi_job                # noqa: E402  split_matchi
import matchday_vs as mv        # noqa: E402
import teams                    # noqa: E402  NHL_RU

GAME_DAY = '2026-10-15'                        # игровой день НХЛ (дата по Нью-Йорку)
DATE_TITLE = 'ночь на 16 октября'
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join('out', 'itogi', 'nhl-2026-10-16')
JOB = os.path.join(ROOT, 'team', 'out', '2026-10-16', 'itogi_nhl.json')
NAMES = dict(strips='полосы', diagonal='диагональ', cards='карточки', center='центр', fav='фаворит', minimal='минимал')


def load_scores():
    path = os.environ.get('NHL_SCORE_JSON')
    if path:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    import requests
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0'
    for k in range(3):
        try:
            r = s.get('https://api-web.nhle.com/v1/score/' + GAME_DAY, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if k == 2:
                raise
            print('NHLERR повтор: %r' % e, flush=True)


def results(data):
    """→ (сыгранные матчи [{home, away, sh, sa, mark, start}], не доигранные/перенесённые [строки])."""
    items, skipped = [], []
    for g in data.get('games') or []:
        if g.get('gameType') not in (2, 3):                      # регулярка и плей-офф; предсезонку не берём
            continue
        h, a = g['homeTeam'], g['awayTeam']
        pair = '%s — %s' % (teams.NHL_RU.get(h['abbrev'], h['abbrev']), teams.NHL_RU.get(a['abbrev'], a['abbrev']))
        if g.get('gameState') not in ('OFF', 'FINAL'):
            if (g.get('gameScheduleState') or 'OK') == 'OK':          # перенесённый (PPD/CNCL) — не ошибка
                skipped.append('%s (%s)' % (pair, g.get('gameState')))
            else:
                print('NHLRES перенесён: %s (%s)' % (pair, g.get('gameScheduleState')), flush=True)
            continue
        last = (g.get('gameOutcome') or {}).get('lastPeriodType') or (g.get('periodDescriptor') or {}).get('periodType')
        items.append(dict(home=teams.NHL_RU.get(h['abbrev'], h['abbrev']), away=teams.NHL_RU.get(a['abbrev'], a['abbrev']),
                          sh=int(h.get('score') or 0), sa=int(a.get('score') or 0),
                          mark={'OT': 'ОТ', 'SO': 'Б'}.get(last, ''), start=str(g.get('startTimeUTC') or ''),
                          id=g.get('id') or 0))
    items.sort(key=lambda x: (x['start'], x['id']))
    return items, skipped


def caption(items):
    """Подпись к посту в канал: счёт по строке на матч; хэштег итогов — только «#нхл»."""
    lines = ['%s — %s %d:%d%s' % (i['home'], i['away'], i['sh'], i['sa'], ' ' + i['mark'] if i['mark'] else '')
             for i in items]
    return 'НХЛ · итоги ночи на 16 октября\n\n' + '\n'.join(lines) + '\n\n#нхл'


def update_job(files, text):
    """Настоящие списки файлов (их число зависит от числа матчей) и подпись — в сообщения задания."""
    with open(JOB, encoding='utf-8') as f:
        job = json.load(f)
    for m in job.get('messages') or []:
        st = m.get('style')
        if st in files:
            m['files'] = files[st]
            m['type'] = 'album' if len(files[st]) > 1 else 'photo'     # в альбоме Telegram — от 2 файлов
        if m.get('caption_slot'):
            m['text'] = m['text'].split('\n\n— Подпись')[0] + '\n\n— Подпись к посту —\n' + text
    tmp = JOB + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    os.replace(tmp, JOB)
    print('задание обновлено:', os.path.relpath(JOB, ROOT))


def main():
    items, skipped = results(load_scores())
    for i in items:
        print('NHLRES %s — %s %d:%d%s' % (i['home'], i['away'], i['sh'], i['sa'], ' ' + i['mark'] if i['mark'] else ''),
              flush=True)
    for x in skipped:
        print('NHLRES не доигран: %s' % x, flush=True)
    if not items:
        raise SystemExit('НХЛ %s: нет ни одного доигранного матча' % GAME_DAY)
    groups = itogi_job.split_matchi(items)
    rows = max(len(g) for g in groups)
    os.makedirs(OUT, exist_ok=True)
    files = {}
    for st in mv.STYLES:
        paths = [os.path.join(OUT, '%s%s.jpg' % (st, '_%d' % (k + 1) if len(groups) > 1 else ''))
                 for k in range(len(groups))]
        for k, (grp, p) in enumerate(zip(groups, paths)):
            mv.render(grp, p, league='NHL', date_title=DATE_TITLE, cont=k > 0, rows=rows, style=st, results=True)
        files[st] = [os.path.relpath(os.path.abspath(p), ROOT) for p in paths]
        print('нарисовано %s: %s' % (st, ', '.join(files[st])), flush=True)
    text = caption(items)
    print('подпись:\n' + text)
    if not os.environ.get('NHL_NO_JOB_UPDATE'):
        update_job(files, text)
    if skipped:                                  # нарисовали доигранные, но отметим ошибкой — владелец увидит в отчёте
        raise SystemExit('не все матчи доиграны: %s' % '; '.join(skipped))


if __name__ == '__main__':
    main()
