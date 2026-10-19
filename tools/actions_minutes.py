# -*- coding: utf-8 -*-
"""Расход минут GitHub Actions за месяц и прогноз до конца месяца (владелец 19.10: «если по прикидкам не будет хватать
до конца месяца — сообщи заранее»). Закрытый репозиторий — 2000 мин/мес бесплатно (Linux ×1).
Считает «оплачиваемое» время всех запусков с 1-го числа (API /actions/runs/{id}/timing), прогноз — по среднему за день.
Владельцу в Telegram: предупреждение, если прогноз > LIMIT_WARN; по понедельникам — сводка всегда.
Секреты/переменные: GITHUB_TOKEN (actions: read), GITHUB_REPOSITORY, TG_BOT_TOKEN."""
import calendar
import os
import sys
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


def main():
    now = datetime.now(timezone.utc)
    start = now.replace(day=1).strftime('%Y-%m-%d')
    total_ms, n, page = 0, 0, 1
    while True:
        runs = gh('actions/runs', created='>=' + start, per_page=100, page=page).get('workflow_runs') or []
        for r in runs:
            if r.get('status') != 'completed':
                continue
            b = gh('actions/runs/%d/timing' % r['id']).get('billable') or {}
            total_ms += sum((v or {}).get('total_ms', 0) for v in b.values())
            n += 1
        if len(runs) < 100:
            break
        page += 1
    used = total_ms / 60000
    days = calendar.monthrange(now.year, now.month)[1]
    elapsed = now.day - 1 + now.hour / 24
    forecast = used / max(elapsed, 0.5) * days
    text = ('Минуты GitHub Actions за %s: потрачено %.0f из %d (запусков %d). Прогноз до конца месяца: ~%.0f.'
            % (now.strftime('%m.%Y'), used, LIMIT, n, forecast))
    print(text, flush=True)
    warn = forecast > LIMIT_WARN
    if warn:
        text = ('⚠️ Минут GitHub может не хватить до конца месяца.\n' + text +
                '\nВарианты: ограничить число роликов в день, GitHub Pro (~$4/мес, 3000 мин) или подождать 1-го числа.')
    if (warn or now.weekday() == 0) and os.environ.get('TG_BOT_TOKEN'):
        import team_job as tj
        tok = os.environ['TG_BOT_TOKEN']
        tj._api(tok, 'sendMessage', dict(chat_id=tj.owner_chat(tok, '@jarvibet'), text=text))


if __name__ == '__main__':
    main()
