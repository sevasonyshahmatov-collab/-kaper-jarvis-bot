# -*- coding: utf-8 -*-
"""Будильник тика соцсетей без внешнего сервиса (27.10: на cron-job.org будильник так и не завели, расписание GitHub
в этом репозитории срабатывает редко). Запуск ждёт ближайший слот (UTC, как в docs/handoff/SMM_AGENT.md) и запускает
«Соцсети — тик», потом запускает себя снова. Слот дальше RUN_FOR — ждёт RUN_FOR и перезапускает себя без тика.
workflow_dispatch с GITHUB_TOKEN — разрешённое исключение GitHub; workflow_run не годится (не больше 3 звеньев цепочки).

    python team/social/tick_chain.py
"""
import os
import time
from datetime import datetime, timedelta, timezone

import requests

SLOTS = ((6, 0), (8, 30), (9, 30), (11, 0), (13, 30), (16, 0), (19, 30))    # UTC: слоты историй и карусель
RUN_FOR = 5 * 3600 + 30 * 60                                             # предел задания GitHub — 6 ч


def next_slot(now):
    for d in (0, 1):
        for h, m in SLOTS:
            t = (now + timedelta(days=d)).replace(hour=h, minute=m, second=0, microsecond=0)
            if t > now:
                return t


def dispatch(wf):
    r = requests.post('https://api.github.com/repos/%s/actions/workflows/%s/dispatches' % (os.environ['GITHUB_REPOSITORY'], wf),
                      json={'ref': 'main'}, timeout=60,
                      headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'})
    print('CHAIN запуск %s: %s' % (wf, 'ok' if r.status_code == 204 else '%s %s' % (r.status_code, r.text[:200])), flush=True)
    print('::notice title=CHAIN::%s %s' % (wf, r.status_code), flush=True)


def main():
    now = datetime.now(timezone.utc)
    t = next_slot(now)
    wait = (t - now).total_seconds()
    if wait > RUN_FOR:
        print('CHAIN до слота %s UTC больше %d ч — жду и перезапускаюсь' % (t.strftime('%H:%M'), RUN_FOR // 3600), flush=True)
        time.sleep(RUN_FOR)
    else:
        print('CHAIN жду слот %s UTC (%d мин)' % (t.strftime('%H:%M'), wait // 60), flush=True)
        time.sleep(wait)
        dispatch('social-tick.yml')
    dispatch('social-chain.yml')


if __name__ == '__main__':
    main()
