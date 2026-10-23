# -*- coding: utf-8 -*-
"""Расход минут GitHub Actions за месяц и прогноз до конца месяца (владелец 19.10: «если по прикидкам не будет хватать
до конца месяца — сообщи заранее»). Закрытый репозиторий — 2000 мин/мес бесплатно (Linux ×1).
Считает время всех заданий с 1-го числа так, как GitHub списывает минуты: каждое задание — вверх до целой минуты
(API /actions/runs/{id}/jobs; /timing после перехода GitHub на новый биллинг отдаёт 0 — 23.10 скрипт показал «0 из 2000»
в день, когда лимит кончился). Прогноз — по среднему за день; в сообщении — 5 самых затратных заданий.
Владельцу в Telegram: предупреждение, если прогноз > LIMIT_WARN; по понедельникам — сводка всегда.
Секреты/переменные: GITHUB_TOKEN (actions: read), GITHUB_REPOSITORY, TG_BOT_TOKEN."""
import calendar
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import requests

LIMIT, LIMIT_WARN = 2000, 1800
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'render'))


def gh(path, **params):
    r = requests.get('https://api.github.com/repos/%s/%s' % (os.environ['GITHUB_REPOSITORY'], path), params=params,
                     headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                              'Accept': 'application/vnd.github+json'}, timeout=30)
    r.raise_for_status()
    return r.json()


def _ts(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def main():
    now = datetime.now(timezone.utc)
    start = now.replace(day=1).strftime('%Y-%m-%d')
    by_wf, n, page = Counter(), 0, 1
    while True:
        runs = gh('actions/runs', created='>=' + start, per_page=100, page=page).get('workflow_runs') or []
        for r in runs:
            if r.get('status') != 'completed':
                continue
            for j in gh('actions/runs/%d/jobs' % r['id'], per_page=100).get('jobs') or []:
                if not (j.get('started_at') and j.get('completed_at')) or not j.get('runner_id'):
                    continue                                     # задание без сервера (лимит, отмена) — не списывается
                sec = (_ts(j['completed_at']) - _ts(j['started_at'])).total_seconds()
                by_wf[r.get('name') or '?'] += max(1, math.ceil(sec / 60))
            n += 1
        if len(runs) < 100:
            break
        page += 1
    used = sum(by_wf.values())
    days = calendar.monthrange(now.year, now.month)[1]
    elapsed = now.day - 1 + now.hour / 24
    forecast = used / max(elapsed, 0.5) * days
    text = ('Минуты GitHub Actions за %s: потрачено %.0f из %d (запусков %d). Прогноз до конца месяца: ~%.0f.'
            % (now.strftime('%m.%Y'), used, LIMIT, n, forecast))
    top = '\n'.join('· %s — %d' % kv for kv in by_wf.most_common(5))
    if top:
        text += '\nБольше всего:\n' + top
    print(text, flush=True)
    warn = forecast > LIMIT_WARN
    if warn:
        text = ('⚠️ Минут GitHub может не хватить до конца месяца.\n' + text +
                '\nВарианты: реже запускать самые затратные задания, лимит расходов в Billing → Budgets and alerts '
                '(сумму выбираете сами), GitHub Pro (~$4/мес, 3000 мин) или подождать 1-го числа.')
    if (warn or now.weekday() == 0) and os.environ.get('TG_BOT_TOKEN'):
        import team_job as tj
        tok = os.environ['TG_BOT_TOKEN']
        tj._api(tok, 'sendMessage', dict(chat_id=tj.owner_chat(tok, '@jarvibet'), text=text))


if __name__ == '__main__':
    main()
