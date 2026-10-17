# -*- coding: utf-8 -*-
"""Тексты для YouTube к ролику: название, описание, хэштеги (docs/handoff/CONVEYOR.md, п. 4).
Без «мнение автора», без букмекеров, промокодов и гарантий."""

MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
TG = 'Все прогнозы раньше всех — в Telegram: https://t.me/jarvibet'   # с https:// — в YouTube ссылка кликается


def tag(name):
    return '#' + ''.join(ch for ch in name if ch.isalnum())


def pick_in_text(pick):
    """«Победа Сибири …» → «победа Сибири …»; «Локомотив не проиграет …» — как есть (начинается с названия клуба)."""
    return pick if ' не проиграет ' in pick else pick[0].lower() + pick[1:]


def youtube(m, league='КХЛ'):
    """m — матч из pick.day_picks. → {title, description, tags}."""
    d, hm = m['d'][:10], m['d'][11:16]
    dd, mm, yy = d[8:10], d[5:7], d[:4]
    title = '%s — %s: прогноз на матч %s.%s.%s' % (m['h'], m['a'], dd, mm, yy)
    tags = ['#хоккей', '#' + league, '#прогноз', tag(m['h']), tag(m['a'])]
    desc = '\n'.join([
        '%s — %s, %s, %d %s, %s МСК.' % (m['h'], m['a'], league, int(dd), MONTHS[int(mm) - 1], hm),
        'Прогноз: %s, кэф %s.' % (pick_in_text(m['pick']), ('%.2f' % m['odds']).replace('.', ',')),
        '',
        'Форма команд: последние 3 игры, очки и место в таблице, линия основного времени.',
        '',
        TG,
        '',
        ' '.join(tags),
    ])
    return dict(title=title[:100], description=desc, tags=tags)


def block(m, league='КХЛ'):
    """Одним сообщением для Telegram: удобно копировать в YouTube Studio."""
    y = youtube(m, league)
    return 'Название:\n%s\n\nОписание:\n%s' % (y['title'], y['description'])
