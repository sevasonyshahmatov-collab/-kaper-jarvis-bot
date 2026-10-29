# -*- coding: utf-8 -*-
"""Лог задания day.py → короткая сводка по матчам для написания прогнозов (в облачной сессии, без сети).
Вход — лог задания Actions (как его сохранил get_job_logs: JSON или текст). Выход — <папка>/brief.md (по матчам:
время, линия, ставки с кэфами и выбор, факты команд) и <папка>/matches.json (строки PICKJSON — для баннеров и задания).
Запуск: python team/picks/parse_log.py <файл лога> <папка, например out/picks/khl-2026-10-16>"""
import json
import os
import re
import sys

TAGS = ('DAYJOB', 'KHLSTAGE', 'KHLNEXT', 'KHLPAIR', 'KHLERR', 'NHLNEXT', 'NHLSTAND', 'NHLCLUB', 'NHLH2HPREV', 'NHLERR', 'NHLRATE', 'NHLGK', 'NHLLIVEERR', 'NHL ', 'KHL ',
        'PINERR', 'PINMISS', 'LEAGUE', 'TABLE', 'PAIR', 'CALC', 'BRIEF', 'TEAM', 'PER', 'LAST', 'H2H', 'PICKJSON')


def text_of(raw):
    try:
        j = json.loads(raw)
    except ValueError:
        return raw
    best = ''

    def walk(v):
        nonlocal best
        if isinstance(v, str) and len(v) > len(best):
            best = v
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(j)
    return best or raw


def lines_of(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    out = []
    for ln in text_of(raw).splitlines():
        ln = re.sub(r'^\d{4}-\d\d-\d\dT[\d:.]+Z\s?', '', ln.rstrip())
        if ln.startswith(TAGS):
            out.append(ln)
    return out


def pct(line):
    m = re.search(r'\|\s+([\d.]+)%', line)
    return float(m.group(1)) if m else 100.0


def main(path, folder):
    ls = lines_of(path)
    os.makedirs(folder, exist_ok=True)
    picks = [json.loads(ln[len('PICKJSON '):]) for ln in ls if ln.startswith('PICKJSON ')]
    json.dump(picks, open(os.path.join(folder, 'matches.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    by = lambda tag: [ln[len(tag) + 1:] for ln in ls if ln.startswith(tag + ' ')]  # noqa: E731
    md = ['# Сводка к прогнозам: ' + ' '.join(by('DAYJOB')), '']
    md += [ln for ln in ls if ln.startswith(('NHL ', 'KHL '))]
    for tag in ('KHLSTAGE', 'LEAGUE', 'TABLE', 'PINMISS', 'PINERR', 'KHLERR', 'NHLERR', 'NHLLIVEERR'):
        md += ['%s: %s' % (tag, x) for x in by(tag)]
    md.append('')
    for i, m in enumerate(picks, 1):
        h, a = m['h'], m['a']
        pair = '%s—%s' % (h, a)
        x1 = m.get('x1x2') or [None] * 3
        fin = m.get('fin') or [None] * 2
        f = lambda v: ('%.2f' % v) if v else '—'  # noqa: E731
        place = m.get('venue') or m.get('arena') or ''
        if isinstance(place, dict):
            place = place.get('name') or ''
        md += ['## %d. %s — %s · %s МСК%s' % (i, h, a, m.get('d', ''), ' · ' + str(place) if place else ''),
               'Линия: П1/Х/П2 осн. время %s / %s / %s · итоговая победа (с ОТ и Б) %s / %s' % (f(x1[0]), f(x1[1]), f(x1[2]), f(fin[0]), f(fin[1]))]
        if m.get('bets'):
            md.append('Фонбет (приложение КХЛ): %s' % json.dumps(m['bets'], ensure_ascii=False))
        md.append('Ставки с кэфом от 35 % — вероятность «Что заходит», кэф, p×k:')
        md += ['- ' + x for x in by('BRIEF') if x.startswith(pair + ' |') and (pct(x) >= 35 or 'ВЫБОР' in x or 'ВАРИАНТ' in x)]
        top = [x for x in by('CALC') if x.startswith(pair + ' |')][:4]
        md.append('Самые вероятные ставки (с кэфом и без):')
        md += ['- ' + x for x in top]
        md += [x for x in by('PAIR') if x.startswith(h + ' — ' + a + ' |')]
        md += ['NHLRATE ' + x for x in by('NHLRATE') if x.startswith(h + ' — ' + a + ' |')]   # новый рейтинг: сила, вратари
        for t in (h, a):
            md += ['%s %s' % (tag, x) for tag in ('TEAM', 'PER', 'LAST', 'NHLSTAND', 'NHLCLUB', 'NHLGK') for x in by(tag) if x.startswith(t + ' |')]
        md += ['H2H ' + x for x in by('H2H') if x.startswith(h + ' — ' + a + ' |')]
        md += ['NHLH2HPREV ' + x for x in by('NHLH2HPREV') if x.startswith(pair + ' |')]
        md += ['KHLPAIR ' + x[:1500] for x in by('KHLPAIR') if x.startswith(pair + ' ')]
        md.append('')
    open(os.path.join(folder, 'brief.md'), 'w', encoding='utf-8').write('\n'.join(md))
    print('матчей: %d → %s' % (len(picks), os.path.join(folder, 'brief.md')))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
