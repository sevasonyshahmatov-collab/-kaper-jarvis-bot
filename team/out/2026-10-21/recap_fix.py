"""Итоги вчерашних ставок за 20.10 с общим баннером — заново (владелец 21.10: по СКА — Автомобилисту ставка была «тотал
матча меньше 4,5» за 1,73, а не «больше 4,5»). Прогнозы — из ленты канала, как у team/daily/jobs/recap_auto.json; у этого
матча ставка и кэф подменяются на верные. Владельцу с кнопкой «Опубликовать»."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'daily'))
import channel  # noqa: E402

_orig = channel.pick_of


def pick_of(post):
    q, why = _orig(post)
    if q and q['home'] == 'СКА' and q['away'] == 'Автомобилист':
        print('RECAPFIX было: %s · %s → тотал матча меньше 4,5 · 1,73' % (q['bet'], q['kef']), flush=True)
        q = dict(q, bet='тотал матча меньше 4,5', kef=1.73)
    return q, why


channel.pick_of = pick_of
sys.argv = ['morning.py', '2026-10-21', '--recap-only', '--source', 'channel', '--job-file',
            os.path.join(ROOT, 'team', 'out', '2026-10-21', 'recap_fix.json')]
import morning  # noqa: E402
morning.main()
