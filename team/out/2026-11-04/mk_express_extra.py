# -*- coding: utf-8 -*-
"""04.11 по просьбе владельца: (1) его экспресс со скрина (ЛЧ) 0411-e8 с инфографикой; (2) варианты экспрессов НХЛ
на ночь 04→05.11 — 0411-e9…e11 (кандидаты team/picks/express.py по brief run 885, линия Фонбета утренняя)."""
import json, os, sys
D = '2026-11-04'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'picks'))
import express as ex  # noqa: E402
import express_post as ep  # noqa: E402

# --- 1. экспресс владельца (скрин, 04.11)
def fl(h, a, t, bf, bs, k):
    return dict(home=h, away=a, date=D, time=t, league='Футбол', p=None, bet=bs, kef=k, src='скрин владельца',
                cat='it', bet_full=bf, bet_short=bs)

own = [fl('АЕК', 'Реал Мадрид', '20:45', 'индивидуальный тотал Реал Мадрида больше 2,5', 'ИТБ Реала 2,5', 1.70),
       fl('Славия Прага', 'Арсенал', '23:00', 'победа Арсенала', 'победа Арсенала', 1.22),
       fl('РБ Лейпциг', 'Манчестер Сити', '23:00', 'индивидуальный тотал Манчестер Сити больше 2', 'ИТБ Сити 2', 1.48)]
own[1]['cat'] = 'win'

# --- 2. НХЛ: кандидаты из brief.md
legs = ex.parse_brief(os.path.join(ROOT, 'out/picks/nhl-2026-11-04/brief.md'), 'НХЛ')
cand = ex.candidates(legs)
flat = [l for v in (cand.values() if isinstance(cand, dict) else cand) for l in (v if isinstance(v, list) else [v])]


def pick(home, bet):
    for l in flat:
        if l['home'] == home and l['bet'] == bet:
            full, short = ex.human(l['bet'], l['home'], l['away'], l['league'])
            return dict(l, bet_full=full, bet_short=short)
    raise SystemExit('нет ноги %s %s' % (home, bet))


N0 = [
 [pick('Баффало', 'Ф2(+2,5) Оттава'), pick('Лос-Анджелес', 'ИТБ 1,5 Сан-Хосе в осн. время'), pick('Сиэтл', 'Ф1(+1,5) Сиэтл')],
 [pick('Лос-Анджелес', 'ТБ 4,5 в осн. время'), pick('Флорида', 'ИТБ 1,5 Чикаго в осн. время'), pick('Баффало', 'Ф1(+1,5) Баффало')],
 [pick('Баффало', 'ТБ 4,5 в осн. время'), pick('Лос-Анджелес', 'ТБ 4,5 в осн. время'), pick('Флорида', 'ТБ 4,5 в осн. время'),
  pick('Сиэтл', 'ИТБ 1,5 Калгари в осн. время')],
]
N = [sorted(c, key=lambda x: (x['date'], x['time'])) for c in N0]

cs = [{'size': 3, 'legs': [], 'note': 'e1–e7 заняты'} for _ in range(7)]
X = 'out/express/%s-extra/' % D
xm = []
for k, lg in enumerate([own] + N, 8):
    kef = 1.0
    p = 1.0
    for l in lg:
        kef *= l['kef']
        p = p * l['p'] if (p is not None and l.get('p')) else None
    c = dict(size=len(lg), legs=lg, kef=round(kef, 2), p=round(p, 4) if p else None, in_target=False)
    cs.append(c)
    html = ep.caption(c)
    if k == 8:
        html = html.replace('#футбол #экспресс', '#футбол #лигачемпионов #экспресс')
    xm.append(dict(to='owner', type='animation', html=True, files=[X + 'e%d_anim.mp4' % k], text=html,
                   buttons='post', pid='0411-e%d' % k))
    print('--- 0411-e%d кэф %.2f шанс %s\n%s' % (k, kef, ('%.1f %%' % (p * 100)) if p else '—', html))

ov = ('<b>Экспрессы — 4 ноября</b>\n\n'
      '1. Ваш экспресс со скрина (ЛЧ): ИТБ Реала 2,5 · 1,70 + победа Арсенала · 1,22 + ИТБ Сити 2 · 1,48 — общий <b>%s</b>. '
      'Кэфы с вашего скрина. ИТБ Сити 2: ровно два гола — возврат этой ноги.\n\n'
      'НХЛ, ночь на 5 ноября (4 матча; линия Фонбета утренняя, могла сдвинуться):\n'
      '2. 0411-e9 · %s · шанс по модели %.0f %% — надёжный: Оттава +2,5, ИТБ Сан-Хосе 1,5, Сиэтл +1,5\n'
      '3. 0411-e10 · %s · %.0f %% — ТБ 4,5 ЛА — Сан-Хосе, ИТБ Чикаго 1,5, Баффало +1,5\n'
      '4. 0411-e11 · %s · %.0f %% — все 4 матча на голы (смелый)\n\n'
      'Утренние e2 (1,91) и e3 (1,82) с НХЛ остаются в силе — новые купоны с ними ноги не повторяют, кроме e11.\n'
      'Под купоном: «Опубликовать» — выйдет в канал сразу.') % (
    ep._k(cs[7]['kef']), ep._k(cs[8]['kef']), cs[8]['p'] * 100, ep._k(cs[9]['kef']), cs[9]['p'] * 100,
    ep._k(cs[10]['kef']), cs[10]['p'] * 100)
json.dump({'coupons': cs}, open(os.path.join(HERE, 'express_extra_coupons.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'day': D, 'messages': [{'to': 'owner', 'type': 'text', 'html': True, 'text': ov}] + xm},
          open(os.path.join(HERE, 'express_extra_msgs.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'day': D, 'make': ['team/picks/express_render.py team/out/%s/express_extra_coupons.json %s' % (D, X.rstrip('/')),
                              'team/picks/express_send.py team/out/%s/express_extra_msgs.json' % D], 'messages': []},
          open(os.path.join(HERE, 'express_extra.json'), 'w'), ensure_ascii=False, indent=1)
print(ov)
