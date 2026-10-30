# -*- coding: utf-8 -*-
"""Проверка бота на живом ESPN (docs/handoff/FOOTBALL_BOT.md): табло 9 турниров за прошлые дни → код бота (Код.js через
tools/gas_mock) находит каждый матч по времени и названию (АПЛ — по-русски из apps-script/epl/10_teams.js), считает счёт за 90 минут.
В лог — строки FB*."""
import json, os, subprocess, sys, tempfile, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CODES = ['eng.1', 'esp.1', 'ita.1', 'ger.1', 'fra.1', 'uefa.champions', 'uefa.europa', 'uefa.europa.conf', 'por.1']
RANGE = sys.argv[1] if len(sys.argv) > 1 else '20261020-20261029'
tmp = tempfile.mkdtemp()
for c in CODES:
    u = 'https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=%s' % (c, RANGE)
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
    except Exception as e:
        print('FBERR', c, e, flush=True); d = {'events': []}
    json.dump(d, open(os.path.join(tmp, c + '.json'), 'w'))
    ev = d.get('events') or []
    names = sorted({((e.get('competitions') or [{}])[0].get('status') or e.get('status') or {}).get('type', {}).get('name', '?') for e in ev})
    print('FBRAW %s | событий %d | статусы %s' % (c, len(ev), ', '.join(names)), flush=True)
js = r'''
const path = require('path'), fs = require('fs');
const gm = require(path.join(process.argv[2], 'tools/gas_mock/gas_mock.js'));
const env = gm.makeEnv({ now: new Date().toISOString() });
gm.load(env, [path.join(process.argv[2], 'apps-script/project/Код.js'), path.join(process.argv[2], 'apps-script/epl/10_teams.js')]);
const ctx = env.ctx, dir = process.argv[3];
ctx.propJson_ = (k, d) => d;
ctx.UrlFetchApp = { fetch: u => { const c = String(u).match(/soccer\/([^/]+)\//)[1];
  return { getResponseCode: () => 200, getContentText: () => fs.readFileSync(path.join(dir, c + '.json'), 'utf8') }; } };
let ok = 0, bad = 0;
for (const [tour, code] of ctx.FOOT_TOURS) {
  const all = JSON.parse(fs.readFileSync(path.join(dir, code + '.json'), 'utf8')).events || [];
  const seen = new Set();
  for (const e of all) {
    const g0 = ctx.footEspnGames_(code, new Date(e.date).getTime());
    const key = e.id; if (seen.has(key)) continue; seen.add(key);
    const me = g0.find(g => g.start === new Date(e.date).getTime() && g.home.split(' | ')[0] === (e.competitions[0].competitors.find(t => t.homeAway === 'home').team.displayName));
    if (!me) { console.log('FBMISS ' + tour + ' | ' + e.name); bad++; continue; }
    const ru = n => code === 'eng.1' ? ctx.teamRu_(n.split(' | ')[0]) : n.split(' | ')[0];
    const w = { start: me.start, home: ru(me.home), away: ru(me.away) };
    const g = ctx.footPick_(w, g0);
    const same = g && g.home === me.home && g.away === me.away;
    same ? ok++ : bad++;
    console.log((same ? 'FBOK ' : 'FBBAD ') + tour + ' | ' + w.home + ' — ' + w.away + ' | ' + (g ? g.hg + ':' + g.ag + ' ' + g.name + (g.h90 !== undefined ? ' 90мин ' + g.h90 + ':' + g.a90 : '') : 'не нашёл') +
      ' | в это время ' + g0.filter(x => Math.abs(x.start - me.start) <= 900000).length);
  }
}
console.log('FBDONE найдено верно ' + ok + ', ошибок ' + bad);
'''
open(os.path.join(tmp, 'h.js'), 'w').write(js)
r = subprocess.run(['node', os.path.join(tmp, 'h.js'), ROOT, tmp])
sys.exit(r.returncode)
