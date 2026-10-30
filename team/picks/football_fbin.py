# -*- coding: utf-8 -*-
"""FootballBin — чужие прогнозы на АПЛ и ЛЧ только для сравнения «кто точнее» (владелец 30.10 через руководителя:
«давай попробуем, как минимум для сравнения»). Публичный MCP без ключа (streamable HTTP, JSON-RPC). В канал и посты не идёт.
Каждый игровой день до матчей сохраняет их прогнозы в .lines/football_fbin/<день>.json (кэш Actions) и печатает FBIN.
Запуск: python team/picks/football_fbin.py [--probe] [день]"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

URL = 'https://ru7m5svay1.execute-api.eu-central-1.amazonaws.com/prod/mcp'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HDR = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def rpc(method, params=None, sid=None, i=[0]):
    i[0] += 1
    h = dict(HDR)
    if sid:
        h['Mcp-Session-Id'] = sid
    r = requests.post(URL, headers=h, json=dict(jsonrpc='2.0', id=i[0], method=method, params=params or {}), timeout=60)
    txt = r.text
    if 'text/event-stream' in r.headers.get('Content-Type', ''):
        txt = '\n'.join(l[5:].strip() for l in txt.splitlines() if l.startswith('data:'))
    try:
        j = json.loads(txt.splitlines()[-1] if txt else '{}')
    except ValueError:
        j = {'raw': txt[:300]}
    return r.status_code, j, r.headers.get('Mcp-Session-Id') or sid


def main():
    st, j, sid = rpc('initialize', dict(protocolVersion='2025-03-26', capabilities={},
                                         clientInfo=dict(name='jarvibet', version='1')))
    out('FBIN', 'initialize %s %s' % (st, json.dumps(j, ensure_ascii=False)[:300]))
    try:
        requests.post(URL, headers=dict(HDR, **({'Mcp-Session-Id': sid} if sid else {})),
                      json=dict(jsonrpc='2.0', method='notifications/initialized'), timeout=30)
    except Exception:
        pass
    st, j, sid = rpc('tools/list', sid=sid)
    tools = (j.get('result') or {}).get('tools') or []
    for t in tools:
        out('FBINTOOL', '%s | %s | %s' % (t.get('name'), (t.get('description') or '')[:200],
                                          json.dumps(t.get('inputSchema') or {}, ensure_ascii=False)[:400]))
    if '--probe' in sys.argv and not tools:
        out('FBIN', 'tools/list %s %s' % (st, json.dumps(j, ensure_ascii=False)[:400]))
    day = next((a for a in sys.argv[1:] if a[:2] == '20'), datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d'))
    saved = {}
    for t in tools:
        nm = t.get('name') or ''
        props = (t.get('inputSchema') or {}).get('properties') or {}
        if not any(w in nm.lower() for w in ('predict', 'match', 'fixture')):
            continue
        for lg in ('premier_league', 'champions_league', 'EPL', 'UCL'):
            args = {}
            for k in props:
                if 'league' in k.lower() or 'competition' in k.lower():
                    args[k] = lg
                elif 'date' in k.lower():
                    args[k] = day
            if not args and props:
                continue
            st, j, sid = rpc('tools/call', dict(name=nm, arguments=args), sid=sid)
            res = j.get('result') or j.get('error') or j
            txt = json.dumps(res, ensure_ascii=False)
            out('FBINCALL', '%s %s → %s %s' % (nm, json.dumps(args, ensure_ascii=False), st, txt[:1500]))
            if j.get('result') and not (j['result'].get('isError')):
                saved['%s|%s' % (nm, lg)] = j['result']
            if not args:
                break
    if saved:
        path = os.path.join(ROOT, '.lines', 'football_fbin', day + '.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(dict(day=day, saved_at=datetime.now(timezone.utc).isoformat(), data=saved), open(path, 'w'), ensure_ascii=False)
        out('FBIN', 'сохранено %s (%d ответов)' % (path, len(saved)))


if __name__ == '__main__':
    main()
