"""Сочи — Шанхайские Драконы 19.10: хроника матча и проверка нейросети для послематчевого текста — печатает в лог, ничего не шлёт
(владелец 19.10: пост получился маленьким и по заготовке)."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path[:0] = [os.path.join(ROOT, 'team', 'postmatch'), os.path.join(ROOT, 'team', 'daily')]
import chronicle  # noqa: E402
import run  # noqa: E402
import writer  # noqa: E402

p = run.load_pick({'pid': '1910-4', 'league': 'KHL', 'home': 'Сочи', 'away': 'Шанхайские Драконы', 'start': '2026-10-19 19:30',
                   'pick': 'победа Шанхайских Драконов в основное время', 'kef': '1,94'})
run.WAIT_MIN = 0
g = run.final_game(p)
print('PMGAME', g and {k: g.get(k) for k in ('home', 'away', 'hg', 'ag', 'state', 'end')}, flush=True)
ch = chronicle.facts(p, g) if g else ''
for line in (ch or '').split('\n'):
    print('PMCHRON', line, flush=True)
print('PMKEYS gemini=%s claude=%s' % (bool(os.environ.get('GEMINI_API_KEY')), bool(os.environ.get('ANTHROPIC_API_KEY'))), flush=True)
body = writer.write(p, g, 'зашла', ch) if ch else None
print('PMTEXT', body, flush=True)
