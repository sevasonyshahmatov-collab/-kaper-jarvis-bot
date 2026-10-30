# -*- coding: utf-8 -*-
"""Недельные ролики (team/reels_weekly/BRIEF.md, README.md): данные (data.py) → шаблон render/reels/countdown.py → трек
владельца → владельцу в бот: ролик, обложка, версия без музыки и SEO-пакет. Никуда не выкладывается.

  python team/reels_weekly/make.py week khl 2026-10-19     «Топ недели» КХЛ за неделю с понедельника 19.10
  python team/reels_weekly/make.py under khl 2026-10-30    антирейтинг «худшие для тотала больше 5,5» на дату
  python team/reels_weekly/make.py over|defense nhl 2026-10-30    чаще всех больше 5,5 / меньше всех пропускают
  python team/reels_weekly/make.py daily [2026-10-31] [--ig]      тема дня по очереди DAILY; --ig — выложить в Instagram
Запуск — в Actions через задание itogi.yml (make с аргументами), локально — только кадры (--frames, нужны данные: --spec).
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in ('team/picks', 'render', 'team/reels_weekly'):
    sys.path.insert(0, os.path.join(ROOT, p))

MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября',
          'декабря']
# треки владельца: ключ, доля (с), дроп в треке (с) — как в team/reels_daily/make.py TEMPLATES; №1 открывается ровно на дроп.
# Только треки с долей ~1 с (место — 3 доли ≈ 3 с) и дропом позже 16 с; по очереди день за днём.
TRACKS = [('too_fast', 1.061946, 33.576), ('militant', 0.952381, 29.733), ('kilo', 0.9375, 60.082), ('quantum', 1.0, 55.147)]
# очередь на каждый день (владелец 30.10: «по 1 такому ролику в день в Instagram, для YouTube — мне в Telegram»):
# день недели (МСК) → (тема, лига); вс — оборона, лига через неделю
DAILY = {0: ('week', 'KHL'), 1: ('week', 'NHL'), 2: ('under', 'KHL'), 3: ('under', 'NHL'), 4: ('over', 'KHL'), 5: ('over', 'NHL')}
WHAT = {'week': 'Топ недели', 'under': 'Антирейтинг для тотала больше', 'over': 'Чаще всех тотал больше', 'defense': 'Лучшая оборона'}
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


def asof(r):
    d = date.fromisoformat(r.get('last') or r['upto'])
    return '%02d.%02d' % (d.day, d.month)


def spec_season(r, kind):
    lg = LG[r['league']]
    items = []
    for x in reversed(r['top']):                           # от 5-го к 1-му
        if kind == 'defense':
            items.append(dict(team=x['team'], n=None, big=dec(x['avg']), sub='ПРОПУСКАЮТ ЗА ИГРУ', share=None,
                              chip='%d ЗА %d %s' % (x['ga'], x['gp'], plural(x['gp'], 'МАТЧ', 'МАТЧА', 'МАТЧЕЙ'))))
        else:
            items.append(dict(team=x['team'], n=x['under'], big='%d ИЗ %d' % (x['under'], x['gp']),
                              sub='МАТЧЕЙ %s %s ШАЙБ' % ('БОЛЬШЕ' if kind == 'over' else 'МЕНЬШЕ', dec(r['line'])),
                              share=x['share'], chip='СРЕДНИЙ ТОТАЛ %s' % dec(x['avg'])))
    hook = {'under': ['ЭТИ 5 КОМАНД %s' % lg, 'ГУБЯТ ТОТАЛ', 'БОЛЬШЕ', 'НОМЕР ОДИН В КОНЦЕ'],
            'over': ['В МАТЧАХ ЭТИХ', '5 КОМАНД %s' % lg, 'ЛЕТЯТ ШАЙБЫ', 'НОМЕР ОДИН В КОНЦЕ'],
            'defense': ['5 САМЫХ', 'НАДЁЖНЫХ ОБОРОН', lg, 'ТВОЯ КОМАНДА В СПИСКЕ?']}[kind]
    src = ('без победных буллитов' if kind == 'defense' else 'основное время') + ' · %s · на %s' % (r['src'], asof(r))
    return dict(league=r['league'], hook=hook, tag='%s · СЕЗОН %s' % (lg, season(r['upto'])), items=items, ours=None,
                src=src, question=['КАКАЯ КОМАНДА', 'ДОЛЖНА БЫТЬ', 'ШЕСТОЙ?'])


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


TAIL = ('Какая команда должна быть шестой? Пиши в комментариях.\nПрогнозы на каждый матч дня в Telegram @jarvibet, '
        'ссылка в шапке профиля.\n\n#%s #хоккей #статистика')


def seo(kind, r):
    """→ (название, описание, поисковые фразы, закреп). Описание — и для Instagram, и для YouTube."""
    lg = LG[r['league']]
    low = lg.lower()
    t = r['top']
    if kind in ('under', 'over'):
        word = 'больше' if kind == 'over' else 'меньше'
        title = ('5 команд %s, в чьих матчах чаще всего больше 5,5 шайб' if kind == 'over' else
                 '5 команд %s, где тотал больше 5,5 почти не проходит') % lg
        lines = ['%d. %s: в %d из %d матчей %s 5,5 шайб, средний тотал %s' % (i + 1, x['team'], x['under'], x['gp'], word,
                                                                              dec(x['avg'])) for i, x in enumerate(t)]
        desc = ('Номер один списка: %s. В %d из %d матчей сезона %s 5,5 шайб.\n\n%s\n\n'
                'Статистика сезона %s %s по основному времени, %s, на %s. Команды от %d матчей. Это факты, не совет.\n\n'
                % (t[0]['team'], t[0]['under'], t[0]['gp'], word, '\n'.join(lines), lg, season(r['upto']), r['src'], asof(r),
                   {'KHL': 15, 'NHL': 20}[r['league']])) + TAIL % low
        search = 'тотал %s %s, статистика тоталов %s, тотал 5,5 %s' % (word, low, low, low)
        pin = 'Какая команда должна быть шестой в этом списке?'
    elif kind == 'defense':
        title = '5 самых надёжных оборон %s' % lg
        lines = ['%d. %s: %s за игру, %d за %d %s' % (i + 1, x['team'], dec(x['avg']), x['ga'], x['gp'],
                                                    plural(x['gp'], 'матч', 'матча', 'матчей')) for i, x in enumerate(t)]
        desc = ('Меньше всех в %s пропускает %s: %s шайбы за игру.\n\n%s\n\nСезон %s, %s, на %s, победные буллиты не '
                'считаем. Команды от %d матчей.\n\n' % (lg, t[0]['team'], dec(t[0]['avg']), '\n'.join(lines), season(r['upto']),
                                                         r['src'], asof(r), {'KHL': 15, 'NHL': 20}[r['league']])) + TAIL % low
        search = 'лучшая оборона %s, меньше всех пропускают %s, статистика %s' % (low, low, low)
        pin = 'Твоя команда в топе? Какая должна быть шестой?'
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
                % (lg, span(r['t0'], r['t1']), '\n'.join(lines), ours, r['src'])) + TAIL % low
        search = 'топ недели %s, самые результативные команды %s, итоги недели %s' % (low, low, low)
        pin = 'Твоя команда в топе? Какая должна быть шестой?'
    return title, desc, search, pin


def pick_daily(day):
    d = date.fromisoformat(day)
    kind, lg = DAILY.get(d.weekday(), ('defense', 'KHL' if d.isocalendar()[1] % 2 == 0 else 'NHL'))
    ref = (d - timedelta(days=7)).isoformat() if kind == 'week' else (d - timedelta(days=1)).isoformat()
    return kind, lg, ref, TRACKS[d.toordinal() % len(TRACKS)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ig = '--ig' in sys.argv
    if args[0] == 'daily':
        day = args[1] if len(args) > 1 else datetime.now(timezone(timedelta(hours=3))).date().isoformat()
        kind, lg, ref, track = pick_daily(day)
        print('WEEKDAILY %s: %s %s за %s, трек %s' % (day, kind, lg, ref, track[0]), flush=True)
    else:
        kind, lg, ref = args[0], args[1].upper(), args[2]
        track = TRACKS[0] if kind == 'under' else TRACKS[1]
    spec_file = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--spec=')), None)
    frames = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--frames=')), None)
    if spec_file:
        r = json.load(open(spec_file, encoding='utf-8'))
    else:
        import weekly_data as data
        r = data.build(kind, lg, ref)
        print('WEEKDATA ' + json.dumps(r, ensure_ascii=False, separators=(',', ':')), flush=True)
    if len(r['top']) < 5:
        raise SystemExit('мало команд для рейтинга: %d' % len(r['top']))
    from reels import core as C
    from reels.countdown import Countdown
    sp = spec_week(r) if kind == 'week' else spec_season(r, kind)
    key, u, tdrop = track
    reel = Countdown(sp, u=u, drop=14 * u + 1.6)
    name = '%s_%s_%s' % (kind, lg.lower(), ref)
    out = os.path.join(ROOT, 'out', 'reels_weekly', name)
    if frames:
        print(C.render(reel, out + '.mp4', frames=[int(float(x) * C.FPS) for x in frames.split(',')]))
        return
    import banners
    banners.ensure_ffmpeg()
    from reels import owner_tracks
    C.render(reel, out + '.mp4', track=owner_tracks.wav(key), start=tdrop - reel.drop, extra_out=out + '_clean.mp4')
    cover = out + '_cover.jpg'
    print('WEEKREEL %s готов: %.1f с, трек %s, №1 на %.2f с' % (name, reel.dur, key, reel.drop), flush=True)
    title, desc, search, pin = seo(kind, r)
    with open(out + '_seo.txt', 'w', encoding='utf-8') as f:
        f.write('Название: %s\n\nОписание:\n%s\n\nПоисковые фразы: %s\n\nЗакреп-комментарий: %s\n' % (title, desc, search, pin))
    note = 'никуда не выложен'
    if ig:
        sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_daily'))
        import instagram
        if not instagram.enabled():
            note = 'в Instagram не выложен: нет IG_TOKEN / IG_USER_ID'
        elif instagram.posted(desc.split('\n')[0]):
            note = 'в Instagram уже есть (та же первая строка) — второй раз не выкладываю'
        else:
            url, why = instagram.upload(out + '.mp4', desc[:2100], cover)
            note = ('выложен в Instagram: %s' % url) if url else ('в Instagram не вышло: %s' % why)
        print('WEEKIG ' + note, flush=True)
    tok = os.environ.get('TG_BOT_TOKEN')
    if not tok:
        print('WEEKREEL нет TG_BOT_TOKEN — владельцу не отправлено', flush=True)
        return
    import team_job as tj
    chat = os.environ.get('OWNER_CHAT') or tj.owner_chat(tok, '@jarvibet')
    with open(out + '.mp4', 'rb') as f:
        tj._api(tok, 'sendVideo', dict(chat_id=chat, supports_streaming='true',
                                       caption='«%s %s» (%.0f с, трек %s) — для YouTube. %s.'
                                       % (WHAT[kind], LG[lg], reel.dur, key, note[:1:].upper() + note[1:])), files={'video': f})
    with open(cover, 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Обложка (№1 ещё скрыт)'), files={'document': f})
    with open(out + '_clean.mp4', 'rb') as f:
        tj._api(tok, 'sendDocument', dict(chat_id=chat, caption='Без музыки (запасная)'), files={'document': f})
    tj._api(tok, 'sendMessage', dict(chat_id=chat, text=('Для YouTube\n\n' + open(out + '_seo.txt', encoding='utf-8').read())[:4000]))


if __name__ == '__main__':
    main()
