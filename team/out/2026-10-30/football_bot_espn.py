# -*- coding: utf-8 -*-
"""Проверка бота на живом ESPN (docs/handoff/FOOTBALL_BOT.md): табло 9 турниров за прошлые дни → код бота (Код.js через
tools/gas_mock) находит каждый матч по времени и названию (АПЛ — по-русски из apps-script/epl/10_teams.js), считает счёт за 90 минут.
В лог — строки FB*."""
import json, os, subprocess, sys, tempfile, urllib.error, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CODES = ['eng.1', 'esp.1', 'ita.1', 'ger.1', 'fra.1', 'uefa.champions', 'uefa.europa', 'uefa.europa.conf', 'por.1']
DAYS = (sys.argv[1] if len(sys.argv) > 1 else '20261021,20261022,20261023,20261024,20261025,20261026').split(',')
tmp = tempfile.mkdtemp()
E = 'https://site.api.espn.com/apis/site/v2/sports/soccer/'


def get(u):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30)), 200
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)


for form in ('20261024', '20261024-20261026', '20261017-20261029', '202610', '202610&limit=400'):
    d, code = get(E + 'eng.1/scoreboard?dates=' + form)
    print('FBFORM dates=%s → %s, событий %s' % (form, code, len((d or {}).get('events') or [])), flush=True)
for c in CODES:
    evs = {}
    for day in DAYS:
        d, code = get(E + c + '/scoreboard?dates=' + day)
        if d is None:
            print('FBERR', c, day, code, flush=True)
        for e in (d or {}).get('events') or []:
            evs[e['id']] = e
    ev = list(evs.values())
    json.dump({'events': ev}, open(os.path.join(tmp, c + '.json'), 'w'))
    names = sorted({((e.get('competitions') or [{}])[0].get('status') or e.get('status') or {}).get('type', {}).get('name', '?') for e in ev})
    ls = sum(1 for e in ev if any(t.get('linescores') for t in (e.get('competitions') or [{}])[0].get('competitors', [])))
    print('FBRAW %s | событий %d | с таймами %d | статусы %s' % (c, len(ev), ls, ', '.join(names)), flush=True)
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
