# -*- coding: utf-8 -*-
"""Разведка источников для мини-приложения (владелец 25.10: «информация о командах и игроках — актуальная»): какие данные
по командам и игрокам отдают API КХЛ (khl.api.webcaster.pro, как team/picks/khl_data.py) и НХЛ (api-web.nhle.com и
api.nhle.com/stats). Ничего не публикует: печатает и пишет отчёт в out/app_probe/ (probe.md — коротко, probe.json — образцы).
Запуск — .github/workflows/app-probe.yml (облачная сессия до этих API не достаёт, Actions — достаёт).

    python team/site/app_data/probe.py out/app_probe
"""
import json
import os
import sys

import requests

S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'
KHL = 'https://khl.api.webcaster.pro/api/khl_mobile/'
NHL = 'https://api-web.nhle.com/v1/'
NHLSTATS = 'https://api.nhle.com/stats/rest/en/'
REPORT, SAMPLES = [], {}


def shape(x, depth=0):
    """Схема ответа: ключи словаря (с типами), у списка — длина и схема первого элемента."""
    if depth > 3:
        return type(x).__name__
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in list(x.items())[:60]}
    if isinstance(x, list):
        return ['%d шт.' % len(x)] + ([shape(x[0], depth + 1)] if x else [])
    return type(x).__name__


def probe(tag, url):
    try:
        r = S.get(url, timeout=40)
        ok = r.status_code == 200
        try:
            j = r.json()
        except ValueError:
            j = None
        line = '%s %s %s %s' % ('✓' if ok and j is not None else '✗', r.status_code, tag, url)
        if j is not None:
            txt = json.dumps(j, ensure_ascii=False)
            SAMPLES[tag] = {'url': url, 'shape': shape(j), 'sample': txt[:4000]}
            line += ' | %d байт' % len(txt)
    except Exception as e:  # noqa: BLE001
        line, j = '✗ ERR %s %s %r' % (tag, url, e), None
    print(line, flush=True)
    REPORT.append(line)
    return j


def main(out):
    os.makedirs(out, exist_ok=True)
    # ── КХЛ: стартовый файл (стадии, сезон), события, один сыгранный матч целиком, кандидаты на команды и игроков
    boot = probe('khl_boot', KHL + 'data.json') or {}
    stage = boot.get('current_stage_id')
    REPORT.append('КХЛ стадия: %s; ключи data.json: %s' % (stage, ', '.join(sorted(boot.keys()))[:600]))
    ev = probe('khl_events', KHL + 'events_v2.json?order_direction=desc&page=1&stage_id=%s' % stage) or []
    done = [w.get('event') or w for w in ev if (w.get('event') or w).get('game_state_key') == 'finished'] if isinstance(ev, list) else []
    team_id = None
    if done:
        e = done[0]
        team_id = (e.get('team_a') or {}).get('id')
        d = probe('khl_event_detail', KHL + 'event_v2.json?id=%s' % e['id']) or {}
        d = d.get('event') or d
        REPORT.append('КХЛ матч %s: ключи: %s' % (e['id'], ', '.join(sorted(d.keys()))[:900]))
    for tag, path in [('khl_teams', 'teams_v2.json?stage_id=%s' % stage), ('khl_teams_plain', 'teams.json'),
                      ('khl_team', 'team_v2.json?id=%s' % team_id), ('khl_players', 'players_v2.json?q[team_id_eq]=%s' % team_id),
                      ('khl_players_stage', 'players_v2.json?stage_id=%s&team_id=%s' % (stage, team_id)),
                      ('khl_player_stats', 'player_stats_v2.json?stage_id=%s&team_id=%s' % (stage, team_id)),
                      ('khl_team_stats', 'team_stats_v2.json?stage_id=%s' % stage), ('khl_standings', 'tournament_table_v2.json?stage_id=%s' % stage),
                      ('khl_table', 'table_v2.json?stage_id=%s' % stage), ('khl_stages', 'stages_v2.json')]:
        probe(tag, KHL + path)
    # ── НХЛ: таблица, статистика клуба (игроки, вратари), командная сводка (большинство/меньшинство), состав
    probe('nhl_standings', NHL + 'standings/now')
    probe('nhl_club_stats', NHL + 'club-stats/BOS/now')
    probe('nhl_roster', NHL + 'roster/BOS/current')
    probe('nhl_team_summary', NHLSTATS + 'team/summary?cayenneExp=seasonId=20262027%20and%20gameTypeId=2')
    with open(os.path.join(out, 'probe.md'), 'w', encoding='utf-8') as f:
        f.write('# Разведка данных для мини-приложения\n\n' + '\n'.join('- ' + x for x in REPORT) + '\n')
    with open(os.path.join(out, 'probe.json'), 'w', encoding='utf-8') as f:
        json.dump(SAMPLES, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/app_probe')
