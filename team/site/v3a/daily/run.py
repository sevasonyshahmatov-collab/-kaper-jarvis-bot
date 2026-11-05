# -*- coding: utf-8 -*-
"""Ежедневный конвейер данных макета v3a (владелец 04.11: «грузить реальные данные и реальные линии, ежедневное обновление»).
Запуск — в Actions (site-v3a-daily.yml): сеть к ESPN / НХЛ / КХЛ / Фонбету / Pinnacle есть только там.
    python team/site/v3a/daily/run.py [шаг …]      без аргументов — все шаги по порядку

Шаги (каждый в своём try: упал — следующие идут дальше, итог в data/daily_log.json):
  teamcode      код команды (ветка claude/project-migration-…: team/picks, team_season.py, render/football.py) → /tmp/teamcode
  live          клон живого сайта (app/data.json, data/*.json — таблицы и наши итоги) → /tmp/live
  hockey_season матчи сезона и игроки КХЛ/НХЛ + расписание КХЛ → team/season.json
  foot_raw      ESPN: матчи/таблицы/линии → football/data/raw.json.gz
  foot_build    football/build_data.py → football.json/js (таблицы, оси силы, модель Пуассона, линии ESPN)
  foot_lineups  составы новых матчей (ESPN summary) → lineups.json.gz;  foot_photos — фото
  foot_players  players_build.py → players.js;  foot_trends  trends_build.py → trends.js
  nhl_players, khl_players  игроки лиг → hockey/data/*.json
  lines_model   линии и вероятности модели → data/lines.json, model.json, today.json
  teams_build   team/build_data.py → assets/data/teams.json/js (без примеров, где есть настоящие данные; линии из lines.json)
  split         daily/split.py: нарезка тяжёлых данных на лёгкие файлы (teams-lite, club/<slug>, football-lite, games, pl/*, plite_*) — для скорости на телефоне
  deck_bg       daily/deck_bg.py: фоны «Колоды матчей» тем же кодом, что баннеры Telegram (render/poster.py) → data/deckbg/*.webp + index.json
  search        search/build_index.py (без сети, после пересборки данных) → data/search.json
  seo           seo/build_seo.py: «Прогноз на сегодня», словарь, title/canonical/og/JSON-LD, sitemap.xml, robots.txt (SITE_ORIGIN — seo/seo_config.py)
  check         сводка и data/daily_log.json
"""
import json, os, shutil, subprocess, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PY = sys.executable
FB = os.path.join(C.V3A, 'football')
HK = os.path.join(C.V3A, 'hockey')
LOG = []
STATE = {}


def guarded(files, fn, min_ratio=0.8):
    """Выполнить fn; если файлы после стали заметно меньше (источник вернул пусто) — вернуть прежние."""
    bak = {}
    for f in files:
        if os.path.exists(f):
            bak[f] = open(f, 'rb').read()
    note = fn()
    for f, b in bak.items():
        if not os.path.exists(f) or os.path.getsize(f) < min_ratio * len(b):
            open(f, 'wb').write(b)
            raise RuntimeError('%s стал заметно меньше (%s → %s) — прежний файл возвращён' % (os.path.basename(f), len(b), os.path.getsize(f) if os.path.exists(f) else 0))
    return note


def sh(cmd, **kw):
    rc, out = C.run(cmd, **kw)
    if rc != 0:
        raise RuntimeError('код %d: %s' % (rc, out[-300:].replace('\n', ' | ')))
    return out


def step_teamcode():
    if os.path.isdir(os.path.join(C.TEAMCODE, 'team', 'picks')) and os.environ.get('TEAMCODE_REUSE'):
        return 'уже есть'
    shutil.rmtree(C.TEAMCODE, ignore_errors=True)
    os.makedirs(C.TEAMCODE)
    for i in range(3):
        rc, _ = C.run(['git', 'fetch', '-q', '--depth=1', 'origin', C.TEAM_BRANCH], cwd=C.REPO, timeout=300)
        if rc == 0:
            break
        time.sleep(5)
    else:
        raise RuntimeError('git fetch ветки команды не удался')
    p1 = subprocess.Popen(['git', 'archive', 'FETCH_HEAD', 'team/picks', 'team/out/2026-11-03/team_season.py', 'render/football.py'],
                          cwd=C.REPO, stdout=subprocess.PIPE)
    subprocess.check_call(['tar', '-x', '-C', C.TEAMCODE], stdin=p1.stdout)
    p1.wait()
    sha = subprocess.check_output(['git', 'rev-parse', '--short', 'FETCH_HEAD'], cwd=C.REPO, text=True).strip()
    STATE['teamcode'] = sha
    return 'ветка команды @%s' % sha


def step_live():
    shutil.rmtree(C.LIVE, ignore_errors=True)
    for i in range(3):
        rc, _ = C.run(['git', 'clone', '-q', '--depth', '1', 'https://github.com/sevasonyshahmatov-collab/sevasonyshahmatov-collab.github.io', C.LIVE], timeout=300)
        if rc == 0:
            db = C.jload(os.path.join(C.LIVE, 'app', 'data.json'), {})
            return 'живой сайт: built %s' % db.get('built')
        time.sleep(5)
    raise RuntimeError('клон живого сайта не удался (оставлен прежний teams.json)')


def step_hockey_season():
    import hockey_season
    return guarded([os.path.join(C.V3A, 'team', 'season.json')], hockey_season.main, 0.9)


def step_foot_raw():
    return guarded([os.path.join(FB, 'data', 'raw.json.gz')], lambda: sh([PY, os.path.join(C.HERE, 'foot_raw.py')], timeout=1500)[-200:], 0.9)


def step_foot_build():
    fp = os.path.join(C.REPO, 'render', 'football.py')
    if not os.path.exists(fp):
        fp = os.path.join(C.TEAMCODE, 'render', 'football.py')      # в ветке макета render/ нет — берём из ветки команды
    out = sh([PY, os.path.join(FB, 'build_data.py'), fp], cwd=FB)
    return out.strip().split('\n')[-1]


def step_foot_lineups():
    out = sh([PY, os.path.join(FB, 'players_lineups_fetch.py')], cwd=C.REPO, timeout=1800)
    return out.strip().split('\n')[-1]


def step_foot_photos():
    out = sh([PY, os.path.join(FB, 'players_photos_fetch.py')], cwd=C.REPO, timeout=900)
    return out.strip().split('\n')[-1]


def step_foot_players():
    return sh([PY, os.path.join(FB, 'players_build.py')], cwd=FB).strip().split('\n')[-1]


def step_foot_trends():
    return sh([PY, os.path.join(FB, 'trends_build.py')], cwd=FB).strip().split('\n')[-1]


def step_nhl_players():
    f = os.path.join(HK, 'data', 'nhl_players.json')
    return guarded([f], lambda: sh([PY, os.path.join(HK, 'nhl_players_fetch.py')], cwd=C.REPO, timeout=1500).strip().split('\n')[-1])


def step_khl_players():
    f = os.path.join(HK, 'data', 'khl_players.json')
    return guarded([f], lambda: sh([PY, os.path.join(HK, 'khl_players_fetch.py')], cwd=C.REPO, timeout=1500).strip().split('\n')[-1])


def step_lines_model():
    import lines_model
    cnt, notes = lines_model.main()
    STATE['lines_notes'] = notes
    return cnt + ('; замечания: ' + ' || '.join(notes)[:900] if notes else '')


def step_teams_build():
    if not os.path.exists(os.path.join(C.LIVE, 'app', 'data.json')):
        raise RuntimeError('нет клона живого сайта — teams.json не пересобран')
    return guarded([os.path.join(C.V3A, 'assets', 'data', 'teams.json')],
                   lambda: sh([PY, os.path.join(C.V3A, 'team', 'build_data.py'), C.LIVE], cwd=C.REPO).strip().split('\n')[-1], 0.7)


def step_split():
    import split
    return split.main()


def step_deck_bg():
    import deck_bg
    return deck_bg.main()


def step_search():
    return sh([PY, os.path.join(C.V3A, 'search', 'build_index.py')], cwd=C.REPO).strip().split('\n')[-1]


def step_seo():
    """seo/build_seo.py: страницы «Прогноз на сегодня», словарь, title/canonical/JSON-LD, sitemap.xml, robots.txt (без сети, после search)."""
    return sh([PY, os.path.join(C.V3A, 'seo', 'build_seo.py')], cwd=C.REPO).strip().split('\n')[-1]


def step_check():
    t = C.jload(os.path.join(C.V3A, 'assets', 'data', 'teams.json'), {})
    games = [g for x in (t.get('teams') or {}).values() for g in x['games']]
    lines, model = C.jload(os.path.join(C.DATA, 'lines.json'), {}), C.jload(os.path.join(C.DATA, 'model.json'), {})
    fb = C.jload(os.path.join(FB, 'data', 'football.json'), {})
    STATE['summary'] = {
        'teams_built': t.get('built'), 'football_built': fb.get('built') or (fb.get('elo') or {}).get('date'),
        'hockey_sample_games_s1': sum(1 for g in games if g.get('s')),
        'hockey_future_games': sum(1 for g in games if 'gf' not in g),
        'hockey_future_with_real_line': sum(1 for g in games if 'gf' not in g and g.get('k') and not g.get('ks')),
        'hockey_future_estimated_line_ks1': sum(1 for g in games if g.get('ks')),
        'lines': len(lines), 'lines_by_src': {s: sum(1 for v in lines.values() if v.get('src') == s) for s in sorted({v.get('src') for v in lines.values()})},
        'model': len(model), 'model_by_ver': {s: sum(1 for v in model.values() if v.get('ver') == s) for s in sorted({v.get('ver') for v in model.values()})},
    }
    return json.dumps(STATE['summary'], ensure_ascii=False)


STEPS = [('teamcode', step_teamcode), ('live', step_live), ('hockey_season', step_hockey_season), ('foot_raw', step_foot_raw),
         ('foot_build', step_foot_build), ('foot_lineups', step_foot_lineups), ('foot_photos', step_foot_photos),
         ('foot_players', step_foot_players), ('foot_trends', step_foot_trends), ('nhl_players', step_nhl_players),
         ('khl_players', step_khl_players), ('lines_model', step_lines_model), ('teams_build', step_teams_build), ('split', step_split), ('deck_bg', step_deck_bg), ('search', step_search), ('seo', step_seo), ('check', step_check)]


def write_log():
    path = os.path.join(C.DATA, 'daily_log.json')
    C.jsave(path, {'built': C.now_msk().strftime('%Y-%m-%d %H:%M'), 'teamcode': STATE.get('teamcode'), 'steps': LOG,
                   'summary': STATE.get('summary'), 'ok': all(s['ok'] for s in LOG)})


def main():
    only = sys.argv[1:]
    for name, fn in STEPS:
        if only and name not in only:
            continue
        t0 = time.time()
        print('\n===== %s =====' % name, flush=True)
        try:
            note = fn()
            LOG.append({'step': name, 'ok': True, 'sec': round(time.time() - t0), 'note': str(note)[:1200]})
        except Exception as e:  # noqa: BLE001
            print(traceback.format_exc(), flush=True)
            LOG.append({'step': name, 'ok': False, 'sec': round(time.time() - t0), 'note': ('%s: %s' % (type(e).__name__, e))[:1200]})
        print('-> %s %s' % (name, 'ok' if LOG[-1]['ok'] else 'ОШИБКА'), LOG[-1]['note'][:300], flush=True)
        write_log()
    bad = [s['step'] for s in LOG if not s['ok']]
    print('\nИТОГ: упало шагов %d %s' % (len(bad), bad), flush=True)
    # критичные шаги: без них данных нет вообще
    crit = {'teamcode', 'teams_build'}
    sys.exit(1 if crit & set(bad) else 0)


if __name__ == '__main__':
    main()
