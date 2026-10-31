import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily')); sys.path.insert(0, os.path.join(ROOT, 'team', 'postmatch'))
import data, run
from datetime import datetime, timedelta
def note(s): print('::notice title=PMDBG::' + str(s).replace('\n', ' | ')[:900], flush=True)
try:
    p = run.load_pick({"pid": "3110-1", "league": "KHL", "home": "Автомобилист", "away": "Металлург", "start": "2026-10-31 15:00", "pick": "Автомобилист не проиграет в основное время", "kef": "1,69"})
    note('pick %s' % {k: str(v) for k, v in p.items()})
    t0 = p['start'] - timedelta(days=1); t1 = p['start'] + timedelta(days=1)
    gs = data.khl_games(t0, t1, detail_if=lambda h, a: True)
    note('games %d' % len(gs))
    for g in gs:
        if 'втомоб' in g['home'] + g['away'] or 'еталлург' in g['home'] + g['away']:
            note('G %s' % {k: str(v) for k, v in g.items()})
    found, errs = data.games_for([p]); note('errs %s keys %s' % (errs, [k for k in found if 'втомоб' in k[1]+k[2]]))
    g = data.match_game(found, p); note('match %s' % g)
except Exception as e:
    import traceback; note('ERR ' + traceback.format_exc()[-800:])
try:
    import chronicle, requests
    note('FACTS ' + chronicle.facts(p, g))
    gk = os.environ.get('GEMINI_API_KEY', '').strip(); ak = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    note('keys gemini=%s anthropic=%s' % (bool(gk), bool(ak)))
    if gk:
        r = requests.post('https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent', headers={'x-goog-api-key': gk}, timeout=60,
                          json={'contents': [{'role': 'user', 'parts': [{'text': 'скажи ок'}]}]})
        note('gemini %s %s' % (r.status_code, r.text[:200]))
    if ak:
        r = requests.post('https://api.anthropic.com/v1/messages', headers={'x-api-key': ak, 'anthropic-version': '2023-06-01'}, timeout=60,
                          json={'model': 'claude-haiku-4-5', 'max_tokens': 10, 'messages': [{'role': 'user', 'content': 'ок'}]})
        note('claude %s %s' % (r.status_code, r.text[:200]))
except Exception as e:
    import traceback; note('ERR2 ' + traceback.format_exc()[-800:])
