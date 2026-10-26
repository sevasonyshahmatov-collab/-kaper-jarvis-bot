# -*- coding: utf-8 -*-
"""Страница /trendy/ (владелец 26.10: «давай сделаем тренды»): тренды команд КХЛ и НХЛ за сезон — кто чаще уходит в большой
и малый тотал, у кого матчи с голами обеих команд, овертаймы, серии, игра дома и в гостях. Данные — поле tr у команд
(team/site/app_data/trends.py через app_data/build.py). Вызывает team/site/build.py → page(...).
"""
import build as B

MIN_GAMES = 5


def pct(k, n):
    return '%d%%' % round(100 * k / n) if n else '—'


def streak(sn):
    if not sn:
        return '—'
    return ('%d В' % sn) if sn > 0 else ('%d П' % -sn)


BOARDS = [
    ('Тотал больше 5,5', 'матчей с 6+ голами', lambda t: t['o']['5.5'] / t['n'], lambda t: '%d из %d' % (t['o']['5.5'], t['n'])),
    ('Тотал меньше 5,5', 'матчей с 5 голами и меньше', lambda t: 1 - t['o']['5.5'] / t['n'],
     lambda t: '%d из %d' % (t['n'] - t['o']['5.5'], t['n'])),
    ('Обе забьют', 'обе команды забили', lambda t: t['btts'] / t['n'], lambda t: '%d из %d' % (t['btts'], t['n'])),
    ('Овертаймы и буллиты', 'ничья в основное время', lambda t: t['ot'] / t['n'], lambda t: '%d из %d' % (t['ot'], t['n'])),
    ('Серия побед', 'идёт сейчас', lambda t: t['sn'], lambda t: B.plural(t['sn'], 'победа', 'победы', 'побед')),
    ('Серия поражений', 'идёт сейчас', lambda t: -t['sn'], lambda t: B.plural(-t['sn'], 'поражение', 'поражения', 'поражений')),
    ('Сильнее всех дома', 'побед на своём льду', lambda t: t['home'][0] / max(1, sum(t['home'])),
     lambda t: '%d из %d' % (t['home'][0], sum(t['home']))),
    ('Сильнее всех в гостях', 'побед на выезде', lambda t: t['away'][0] / max(1, sum(t['away'])),
     lambda t: '%d из %d' % (t['away'][0], sum(t['away']))),
]


def boards(rows, logos):
    out = []
    icon = lambda n: ('<img src="../%s" alt="" width="26" height="26">' % logos[n]) if n in logos else '<i></i>'  # noqa: E731
    for title, sub, key, txt in BOARDS:
        top = sorted(rows, key=lambda r: -key(r['tr']))[:5]
        top = [r for r in top if key(r['tr']) > 0]
        if not top:
            continue
        li = ''.join('<li>%s<span>%s</span><b>%s</b></li>' % (icon(r['name']), B.esc(r['name']), txt(r['tr'])) for r in top)
        out.append('<div class="board"><h3>%s</h3><small>%s</small><ol>%s</ol></div>' % (title, sub, li))
    return '<div class="boards">%s</div>' % ''.join(out)


def table(rows, logos):
    icon = lambda n: ('<img src="../%s" alt="" width="22" height="22">' % logos[n]) if n in logos else ''  # noqa: E731
    head = '<tr><th>Команда</th><th>И</th><th>Ср. тотал</th><th>ТБ 4,5</th><th>ТБ 5,5</th><th>ТБ 6,5</th><th>Обе забьют</th><th>ОТ/Б</th><th>Серия</th><th>Дома</th><th>В гостях</th></tr>'
    body = ''
    for r in sorted(rows, key=lambda r: -r['tr']['o']['5.5'] / r['tr']['n']):
        t = r['tr']
        body += '<tr><td>%s<a href="../app/#team/%s">%s</a></td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td><td>%d–%d</td><td>%d–%d</td></tr>' % (
            icon(r['name']), B.esc(r['name']), B.esc(r['name']), t['n'], ('%.1f' % t['tot']).replace('.', ','),
            pct(t['o']['4.5'], t['n']), pct(t['o']['5.5'], t['n']), pct(t['o']['6.5'], t['n']), pct(t['btts'], t['n']),
            pct(t['ot'], t['n']), 'w' if t['sn'] > 0 else 'l', streak(t['sn']), t['home'][0], t['home'][1], t['away'][0], t['away'][1])
    return '<div class="tscroll"><table class="trt"><thead>%s</thead><tbody>%s</tbody></table></div>' % (head, body)


def page(T, base, logos, updated):
    secs = []
    for lg in ('khl', 'nhl'):
        rows = [r for r in (T.get(lg) or []) if r.get('tr') and r['tr']['n'] >= MIN_GAMES]
        if not rows:
            continue
        secs.append('<section id="%s"><h2>%s</h2>%s<h3 class="tt">Все команды</h3><p class="hint">Доля матчей сезона. Нажмите на команду — её страница в приложении.</p>%s</section>' % (
            lg, B.LG[lg], boards(rows, logos), table(rows, logos)))
    title = 'Тренды КХЛ и НХЛ: тоталы, обе забьют, овертаймы и серии команд'
    desc = 'Статистика трендов команд КХЛ и НХЛ за сезон: как часто матчи уходят в тотал больше 4,5, 5,5 и 6,5, обе забьют, овертаймы, серии побед и поражений.'
    body = '''<main class="wrap page"><nav class="crumbs"><a href="../">Главная</a> › Тренды</nav>
<h1>Тренды команд КХЛ и НХЛ</h1>
<p class="when">Регулярный чемпионат · обновлено %s · <a href="#khl">КХЛ</a> · <a href="#nhl">НХЛ</a></p>
<p class="lead2">Кто чаще всех уходит в большой тотал, у кого почти всегда забивают обе команды, кто тянет игры в овертайм и чья серия идёт прямо сейчас. Тотал считаем по итоговому счёту, с овертаймом и буллитами.</p>
%s</main>
''' % (B.esc(updated or ''), ''.join(secs) or '<p>Тренды появятся после ближайшего обновления данных.</p>')
    return B.head(title, desc, base + 'trendy/', '../') + body + B.FOOT
