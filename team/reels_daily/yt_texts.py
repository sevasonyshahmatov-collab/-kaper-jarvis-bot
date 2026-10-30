# -*- coding: utf-8 -*-
"""Тексты для YouTube к ролику: название, описание, хэштеги (docs/handoff/CONVEYOR.md, п. 4).
Без «мнение автора», без букмекеров, промокодов и гарантий."""

from datetime import date  # noqa: E402

MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
WD = ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье')
WD_NIGHT = ('понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье')   # «в ночь на …»
HEAD = 'Прогноз на матч '        # владелец 24.10: текст ролика начинается с «Прогноз на матч <матч>», дальше — как было
TG = 'Все прогнозы раньше всех — в Telegram: https://t.me/jarvibet'   # с https:// — в YouTube ссылка кликается


def tag(name):
    return '#' + ''.join(ch for ch in name if ch.isalnum())


def pick_in_text(pick):
    """«Победа Сибири …» → «победа Сибири …»; «Локомотив не проиграет …» — как есть (начинается с названия клуба)."""
    return pick if ' не проиграет ' in pick else pick[0].lower() + pick[1:]


def when(m, today=None):
    """Когда матч — явно, с днём недели (владелец 30.10: ролики выходят за день, не путать с сегодняшними):
    «Завтра, пятница, 31 октября, 19:30 МСК»; ночной матч НХЛ — «Завтра ночью — в ночь на субботу, 1 ноября, 03:00 МСК».
    today — дата запуска по Москве (по умолчанию сегодня)."""
    from datetime import date, datetime, timedelta, timezone
    today = today or datetime.now(timezone(timedelta(hours=3))).date()
    d, hm = date.fromisoformat(m['d'][:10]), m['d'][11:16]
    night = hm < '06:00'                          # ночной матч относится к вечеру предыдущего дня
    rel = ((d - timedelta(days=1) if night else d) - today).days
    word = {0: 'Сегодня', 1: 'Завтра', 2: 'Послезавтра'}.get(rel)
    dm = '%d %s' % (d.day, MONTHS[d.month - 1])
    if night:
        return '%s — в ночь на %s, %s, %s МСК' % (word + ' ночью' if word else 'Ночью', WD_NIGHT[d.weekday()], dm, hm)
    return '%s, %s, %s МСК' % ((word + ', ' if word else '') + WD[d.weekday()], dm, hm)


def youtube(m, league='КХЛ', today=None):
    """m — матч из pick.day_picks. → {title, description, tags}. Первая строка — без «завтра/сегодня» (по ней ищут
    повторы), «когда» — второй строкой."""
    d, hm = m['d'][:10], m['d'][11:16]
    dd, mm, yy = d[8:10], d[5:7], d[:4]
    title = '%s — %s: прогноз на матч %s.%s.%s' % (m['h'], m['a'], dd, mm, yy)
    tags = ['#хоккей', '#' + league, '#прогноз', tag(m['h']), tag(m['a'])]
    desc = '\n'.join([
        HEAD + '%s — %s, %s, %s, %d %s, %s МСК.' % (m['h'], m['a'], league, WD[date.fromisoformat(d).weekday()], int(dd),
                                                     MONTHS[int(mm) - 1], hm),
        'Матч: %s.' % (lambda w: w[0].lower() + w[1:])(when(m, today)),
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
