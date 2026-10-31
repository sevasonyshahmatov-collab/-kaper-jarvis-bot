# Факты футбольных матчей 31.10 для «Итога матча» (ESPN: счёт, голы, удаления, статистика) — печать в лог, владельцу ничего.
import requests
LG = {'eng.1': ['Manchester City', 'Tottenham'], 'esp.1': ['Levante', 'Rayo'], 'ger.1': ['Schalke', 'Leipzig']}
H = {'User-Agent': 'Mozilla/5.0'}
def note(s): print('::notice title=FOOTPM::' + str(s).replace('\n', ' | ')[:1500], flush=True)
for lg, keys in LG.items():
    try:
        sb = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard' % lg, params={'dates': '20261031'}, headers=H, timeout=30).json()
    except Exception as e:
        note('ERR %s %s' % (lg, e)); continue
    for ev in sb.get('events', []):
        if not any(k in ev.get('name', '') for k in keys):
            continue
        c = ev['competitions'][0]; st = ev['status']['type']
        tm = {x['team']['id']: x['team']['displayName'] for x in c['competitors']}
        sc = ' — '.join('%s %s' % (x['team']['displayName'], x.get('score')) for x in sorted(c['competitors'], key=lambda x: x['homeAway'] != 'home'))
        note('%s | %s | %s | completed=%s' % (lg, sc, st.get('detail'), st.get('completed')))
        for d in c.get('details', []):
            who = ', '.join(a.get('displayName', '') for a in d.get('athletesInvolved', []))
            note('  %s %s %s (%s)%s%s' % (d.get('clock', {}).get('displayValue'), d.get('type', {}).get('text'), who, tm.get(d.get('team', {}).get('id'), '?'),
                 ' пен' if d.get('penaltyKick') else '', ' автогол' if d.get('ownGoal') else ''))
        try:
            sm = requests.get('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/summary' % lg, params={'event': ev['id']}, headers=H, timeout=30).json()
            for t in sm.get('boxscore', {}).get('teams', []):
                s = {x['name']: x.get('displayValue') for x in t.get('statistics', [])}
                note('  СТАТ %s: владение %s, удары %s, в створ %s, угловые %s, xG %s' % (t['team']['displayName'], s.get('possessionPct'), s.get('totalShots'),
                     s.get('shotsOnTarget'), s.get('wonCorners'), s.get('expectedGoals', s.get('xG'))))
        except Exception as e:
            note('  ERR summary %s' % e)
