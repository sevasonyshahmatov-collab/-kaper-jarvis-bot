# -*- coding: utf-8 -*-
"""Недельные ролики (team/reels_weekly/BRIEF.md, README.md): данные (data.py) → шаблон render/reels/countdown.py → трек
владельца → владельцу в бот: ролик, обложка, версия без музыки и SEO-пакет. Никуда не выкладывается.

  python team/reels_weekly/make.py week khl 2026-10-19     «Топ недели» КХЛ за неделю с понедельника 19.10
  python team/reels_weekly/make.py under khl 2026-10-30    антирейтинг «худшие для тотала больше 5,5» на дату
Запуск — в Actions через задание itogi.yml (make с аргументами), локально — только кадры (--frames, нужны данные: --spec).
"""
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in ('team/picks', 'render', 'team/reels_weekly'):
    sys.path.insert(0, os.path.join(ROOT, p))

MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября',
          'декабря']
# трек, доля (с), дроп в треке (с) — как в team/reels_daily/make.py TEMPLATES; №1 открывается ровно на дроп
TRACK = {'under': ('too_fast', 1.061946, 33.576), 'week': ('militant', 0.952381, 29.733)}
LG = {'KHL': 'КХЛ', 'NHL': 'НХЛ'}


def plural(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


def dec(x):
    return ('%.1f' % x).replace('.', ',')


def span(t0, t1):
    a, b = date.fromisoformat(t0), date.fromisoformat(t1)
    if a.month == b.month:
        return '%d-%d %s' % (a.day, b.day, MONTHS[b.month - 1])
    return '%d %s - %d %s' % (a.day, MONTHS[a.month - 1], b.day, MONTHS[b.month - 1])


def season(day):
    d = date.fromisoformat(day)
    y = d.year if d.month >= 8 else d.year - 1
    return '%d/%02d' % (y, (y + 1) % 100)


def spec_under(r):
    lg = LG[r['league']]
    line = dec(r['line'])
    items = []
    for x in reversed(r['top']):                           # от 5-го к 1-му
        items.append(dict(team=x['team'], n=x['under'], big='%d ИЗ %d' % (x['under'], x['gp']),
                          sub='МАТЧЕЙ МЕНЬШЕ %s ШАЙБ' % line, share=x['share'], chip='СРЕДНИЙ ТОТАЛ %s' % dec(x['avg'])))
    d = date.fromisoformat(r['last'] or r['upto'])
    return dict(league=r['league'], hook=['ЭТИ 5 КОМАНД %s' % lg, 'ГУБЯТ ТОТАЛ', 'БОЛЬШЕ', 'НОМЕР ОДИН В КОНЦЕ'],
                tag='%s · СЕЗОН %s' % (lg, season(r['upto'])), items=items, ours=None,
                src='основное время · %s · на %02d.%02d' % (r['src'], d.day, d.month),
                question=['КАКАЯ КОМАНДА', 'ДОЛЖНА БЫТЬ', 'ШЕСТОЙ?'])


def spec_week(r):
    lg = LG[r['league']]
    items = []
    for x in reversed(r['top']):
        items.append(dict(team=x['team'], n=x['gf'], big='%d %s' % (x['gf'], plural(x['gf'], 'ШАЙБА', 'ШАЙБЫ', 'ШАЙБ')),
                          sub='ЗА %d %s' % (x['gp'], plural(x['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ')), share=None,
                          chip='%s ЗА ИГРУ · ПРОПУЩЕНО %d' % (dec(x['gf'] / x['gp']), x['ga'])))
    o, ours = r.get('ours'), None
    if o and o['win'] + o['loss'] > 0:
        ours = dict(title=['НАШИ ПРОГНОЗЫ %s' % lg, 'ЗА %s' % span(r['t0'], r['t1']).upper()],
                    big='%d ИЗ %d' % (o['win'], o['win'] + o['loss']), sub='ЗАШЛО',
                    note=('и %d %s' % (o['push'], plural(o['push'], 'возврат', 'возврата', 'возвратов'))) if o['push'] else None,
                    src='итоги прогнозов @jarvibet')
    return dict(league=r['league'], hook=['ТОП-5 АТАК', '%s ЗА НЕДЕЛЮ' % lg, 'ТВОЯ КОМАНДА В СПИСКЕ?'],
                tag='%s · %s' % (lg, span(r['t0'], r['t1']).upper()), items=items, ours=ours,
                src='без победных буллитов · %s' % r['src'],
                question=['КАКАЯ КОМАНДА', 'ДОЛЖНА БЫТЬ', 'ШЕСТОЙ?'])


def seo(kind, r):
    lg = LG[r['league']]
    t = r['top']
    if kind == 'under':
        one = t[0]
        title = '5 команд %s, где тотал больше 5,5 почти не проходит' % lg
        lines = ['%d. %s: в %d из %d матчей меньше 5,5 шайб, средний тотал %s' % (i + 1, x['team'], x['under'], x['gp'],
                                                                                  dec(x['avg'])) for i, x in enumerate(t)]
        desc = ('Номер один списка: %s. В %d из %d матчей сезона меньше 5,5 шайб.\n\n%s\n\n'
                'Статистика сезона %s %s по основному времени, приложение КХЛ, на %s. Команды от %d матчей. '
                'Это факты, не совет.\n\nКакая команда должна быть шестой? Пиши в комментариях.\n'
                'Прогнозы на каждый матч дня в Telegram @jarvibet, ссылка в шапке профиля.\n\n'
                '#кхл #хоккей #статистика'
                % (one['team'], one['under'], one['gp'], '\n'.join(lines), lg, season(r['upto']),
                   '.'.join(reversed((r['last'] or r['upto']).split('-')[1:])), {'KHL': 15, 'NHL': 20}[r['league']]))
        search = 'тотал меньше кхл, статистика тоталов кхл, команды кхл мало забивают, тотал больше 5,5 кхл'
        pin = 'Какая команда должна быть шестой в этом списке?'
    else:
        title = 'Топ-5 атак %s за %s' % (lg, span(r['t0'], r['t1']))
        lines = ['%d. %s: %d %s за %d %s' % (i + 1, x['team'], x['gf'], plural(x['gf'], 'шайба', 'шайбы', 'шайб'), x['gp'],
                                             plural(x['gp'], 'матч', 'матча', 'матчей')) for i, x in enumerate(t)]
        o = r.get('ours')
        ours = ''
        if o and o['win'] + o['loss'] > 0:
            ours = '\n\nНаши прогнозы %s за неделю: зашло %d из %d%s.' % (
                lg, o['win'], o['win'] + o['loss'], (', ещё %d возврат' % o['push']) if o['push'] else '')
        desc = ('Кто забивал больше всех в %s за %s.\n\n%s%s\n\nДанные: %s, победные буллиты не считаем.\n\n'
                'Какая команда должна быть шестой? Пиши в комментариях.\nПрогнозы на каждый матч дня в Telegram @jarvibet, '
                'ссылка в шапке профиля.\n\n#%s #хоккей #статистика'
                % (lg, span(r['t0'], r['t1']), '\n'.join(lines), ours, r['src'], lg.lower()))
        search = 'топ недели %s, самые результативные команды %s, итоги недели %s' % (lg.lower(), lg.lower(), lg.lower())
        pin = 'Твоя команда в топе? Какая должна быть шестой?'
    return title, desc, search, pin


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    kind, lg, day = args[0], args[1].upper(), args[2]
    spec_file = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--spec=')), None)
    frames = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--frames=')), None)
    if spec_file:
        r = json.load(open(spec_file, encoding='utf-8'))
    else:
        import weekly_data as data
        r = data.week(lg, day) if kind == 'week' else data.under(lg, day)
        print('WEEKDATA ' + json.dumps(r, ensure_ascii=False, separators=(',', ':')), flush=True)
    if len(r['top']) < 5:
        raise SystemExit('мало команд для рейтинга: %d' % len(r['top']))
    from reels import core as C
    from reels.countdown import Countdown
    sp = spec_under(r) if kind == 'under' else spec_week(r)
    key, u, tdrop = TRACK[kind]
    reel = Countdown(sp, u=u, drop=14 * u + 1.6)
    name = '%s_%s_%s' % (kind, lg.lower(), day)
    out = os.path.join(ROOT, 'out', 'reels_weekly', name)
    if frames:
        print(C.render(reel, out + '.mp4', frames=[int(float(x) * C.FPS) for x in frames.split(',')]))
        return
    import banners
    banners.ensure_ffmpeg()
    from reels import owner_tracks
    C.render(reel, out + '.mp4', track=owner_tracks.wav(key), start=tdrop - reel.drop, extra_out=out + '_clean.mp4')
    print('WEEKREEL %s готов: %.1f с, трек %s, №1 на %.2f с' % (name, reel.dur, key, reel.drop), flush=True)
    title, desc, search, pin = seo(kind, r)
    with open(out + '_seo.txt', 'w', encoding='utf-8') as f:
        f.write('Название: %s\n\nОписание:\n%s\n\nПоисковые фразы: %s\n\nЗакреп-комментарий: %s\n' % (title, desc, search, pin))
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('WEEKREEL нет TG_BOT_TOKEN — владельцу не отправлено', flush=True)
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    what = 'Антирейтинг' if kind == 'under' else 'Топ недели'
    with open(out + '.mp4', 'rb') as f:
        tj._api(tok, 'sendVideo', dict(chat_id=chat, supports_streaming='true',
                                       caption='Новый ролик «%s %s» (%.0f с, трек %s), пробный. Никуда не выложен.'
                                       % (what, LG[lg], reel.dur, key)), files={'video': f})
    with open(os.path.splitext(out + '.mp4')[0] + '_cover.jpg', 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Обложка (№1 ещё скрыт)'), files={'document': f})
    with open(out + '_clean.mp4', 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Без музыки (запасная)'), files={'document': f})
    tj._api(tok, 'sendMessage', dict(chat_id=chat, text=open(out + '_seo.txt', encoding='utf-8').read()[:4000]))


if __name__ == '__main__':
    main()
