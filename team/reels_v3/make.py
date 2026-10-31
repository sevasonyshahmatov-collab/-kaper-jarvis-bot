# -*- coding: utf-8 -*-
"""Ролики v3 — сборка проб (ТЗ docs/handoff/REELS_V3_BRIEF.md): python team/reels_v3/make.py <задание.json> <id> [<id> …]

Для каждого id из PROBES: озвучка по сценам (team/reels_v3/tts.py, по умолчанию Edge «Дмитрий»), длина сцен — по голосу,
кадры — render/reels/v3.py, звук: голос + лёгкий фон (синтезирован здесь же, без чужих треков) и чистая версия
(_clean — только голос, для Content ID). Данные форматов 2–4 — team/reels_v3/data/season.json (season.py в том же
задании, до этого скрипта). Готовые ролики дописываются сообщениями в задание (владельцу, без кнопки «Опубликовать»).
Локально без сети: REELS_V3_NOVOICE=1 — тишина и оценка длины по тексту (для проверки кадров).
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'render'))
sys.path.insert(0, os.path.join(ROOT, 'team', 'reels_v3'))
from reels import core as C  # noqa: E402
from reels import v3  # noqa: E402

SR = 24000
OUT = os.path.join(ROOT, 'team', 'out', 'reels_v3')
SEASON = os.environ.get('REELS_V3_SEASON') or os.path.join(ROOT, 'team', 'reels_v3', 'data', 'season.json')


def S(k, say, sub=None, **kw):
    return dict(k=k, say=say, sub=sub if sub is not None else say, **kw)


def season():
    with open(SEASON, encoding='utf-8') as f:
        return json.load(f)


def bet_of(lg, team, key):
    d = season()[lg]
    b = next(x for x in d['teams'][team]['bets'] if x['key'] == key)
    c = d['teams'][team]['club']
    assert b['m'] == c['gp'], 'число матчей ставки ≠ числу игр команды'      # проверка ТЗ
    assert b['n'] == sum(1 for ch in b['seq'] if ch == '1')
    return b, d


# ───────────────────────────── пробы: 2 на формат ─────────────────────────────
def p11():
    legs = [dict(team='Лос-Анджелес', bet='Фора Лос-Анджелеса +2,5', kef=1.22),
            dict(team='Питтсбург', bet='Питтсбург забьёт 2+ в основное время', kef=1.22),
            dict(team='Ванкувер', bet='Ванкувер забьёт 2+ в основное время', kef=1.23)]
    sc = [S('hook', 'Три матча — один кэф: один восемьдесят три.', '3 матча — один кэф: 1,83', min=1.8),
          S('leg', 'Лос-Анджелес, фора плюс два с половиной.', 'Лос-Анджелес, фора +2,5', i=0, min=1.8),
          S('leg', 'Питтсбург забьёт две.', 'Питтсбург забьёт 2+', i=1, min=1.6),
          S('leg', 'Ванкувер — тоже две.', 'Ванкувер — тоже 2+', i=2, min=1.6),
          S('total', 'Вместе — один восемьдесят три.', 'Вместе — 1,83', min=1.6),
          S('cta', 'Все купоны и итоги — в канале.', min=2.5)]
    return v3.Formula(sc, legs, 1.83, '31.10', league='NHL'), 'Экспресс дня — «Формула»', 'НХЛ, купон 31.10 на 3 события'


def p12():
    legs = [dict(team='Нэшвилл', bet='Нэшвилл забьёт 2+ в основное время', kef=1.31),
            dict(team='Коламбус', bet='Коламбус забьёт 2+ в основное время', kef=1.39)]
    sc = [S('hook', 'Два матча. Один кэф — один восемьдесят два.', '2 матча. Один кэф — 1,82', min=1.8),
          S('leg', 'Нэшвилл забьёт минимум две.', 'Нэшвилл забьёт 2+', i=0),
          S('leg', 'И Коламбус — минимум две.', 'И Коламбус — 2+', i=1),
          S('total', 'Итого — один восемьдесят два.', 'Итого — 1,82', min=1.9),
          S('cta', 'Все купоны и итоги — в канале.', min=2.5)]
    return v3.Formula(sc, legs, 1.82, '31.10', league='NHL'), 'Экспресс дня — «Формула»', 'НХЛ, купон 31.10 на 2 события'


def cardio(lg, team, key, bet, say_hook, sub_hook, say_res, sub_res):
    b, d = bet_of(lg, team, key)
    league = 'KHL' if lg == 'khl' else 'NHL'
    ss = '%s %d/%02d' % (d['league'], d['season'], (d['season'] + 1) % 100)
    sc = [S('hook', say_hook, sub_hook, min=2.0),
          S('run', '%s. Считаем.' % v3_num_games(b['m']), '%d матчей. Считаем.' % b['m'], min=5.2),
          S('result', say_res % (b['n'], b['m']), sub_res % (b['n'], b['m']), min=2.2),
          S('cta', 'Какую команду посчитать завтра?', min=2.6)]
    r = v3.Cardio(sc, team, bet, b['games'], b['seq'], b['n'], b['m'], None, ss,
                  '%s · %d матчей · основное время · история, не совет' % (ss, b['m']), league=league)
    return r, b


def v3_num_games(m):
    return '%d %s' % (m, 'матч' if m % 10 == 1 and m % 100 != 11 else
                      'матча' if 2 <= m % 10 <= 4 and not 12 <= m % 100 <= 14 else 'матчей')


def p21():
    r, b = cardio('khl', 'Ак Барс', 'o55', 'Тотал больше 5,5',
                  'Весь сезон ставим тотал больше пяти с половиной в матчах Ак Барса. Что вышло?',
                  'Весь сезон ставим ТБ 5,5 на Ак Барс. Что вышло?',
                  'Зашло %d из %d.', 'Зашло %d из %d.')
    return r, '«Весь сезон ставим…» — «Кардиограмма»', 'КХЛ, Ак Барс, ТБ 5,5 в осн. время: %d из %d' % (b['n'], b['m'])


def p22():
    r, b = cardio('nhl', 'Сиэтл', 'o55', 'Тотал больше 5,5',
                  'Весь сезон ставим тотал больше пяти с половиной в матчах Сиэтла. Что вышло?',
                  'Весь сезон ставим ТБ 5,5 на Сиэтл. Что вышло?',
                  'Зашло %d из %d.', 'Зашло %d из %d.')
    return r, '«Весь сезон ставим…» — «Кардиограмма»', 'НХЛ, Сиэтл, ТБ 5,5 в осн. время: %d из %d' % (b['n'], b['m'])


def pat(lg, key, team):
    d = season()[lg]
    row = next(r for r in d['patterns'][key] if r[0] == team)
    return row[1], row[2], d


def p31():
    lead = pat('khl', 'blown_lead', 'Динамо Москва')
    s2 = pat('khl', 'blown_lead', 'Сибирь')
    best = pat('khl', 'blown_lead', 'Шанхайские Драконы')
    d = lead[2]
    note = '%s %d/%02d · %d матчей' % (d['league'], d['season'], (d['season'] + 1) % 100, d['n_games'])
    sc = [S('q', 'Кто в КХЛ чаще всех упускает победу в третьем периоде?', min=1.8),
          S('guess', 'Угадаешь?', min=1.9),
          S('reveal', 'Динамо Москва: вело %d раз — %d раз не выиграло.' % (lead[1], lead[0]),
            'Динамо Москва: вело %d раз — %d раз не выиграло' % (lead[1], lead[0]), min=2.4),
          S('worst', 'Надёжнее всех — Шанхай: %d из %d.' % (best[0], best[1]),
            'Надёжнее всех — Шанхай: %d из %d' % (best[0], best[1]), min=2.2),
          S('cta', 'А твоя команда? Пиши в комментариях.', min=2.5)]
    r = v3.Guess(sc, 'Кто в КХЛ чаще всех упускает победу в 3-м периоде?', ['Сибирь', 'Динамо Москва', 'Адмирал'],
                 ('Динамо Москва', lead[0], lead[1]), ('Шанхайские Драконы', best[0], best[1]), note, league='KHL')
    r.worst_label = 'А надёжнее всех —'
    r.lead_label = 'не выиграло, ведя после двух периодов'
    return r, 'Закономерность сезона — «Угадай»', 'КХЛ: упущенная победа в 3-м периоде (вели после 2-х), Динамо М %d из %d, Сибирь %d из %d' % (lead[0], lead[1], s2[0], s2[1])


def p32():
    lead = pat('nhl', 'comeback3', 'Баффало')
    worst = pat('nhl', 'comeback3', 'Рейнджерс')
    d = lead[2]
    note = '%s %d/%02d · %d матчей' % (d['league'], d['season'], (d['season'] + 1) % 100, d['n_games'])
    sc = [S('q', 'Кто в НХЛ чаще всех отыгрывается в третьем периоде?', min=1.8),
          S('guess', 'Угадаешь?', min=1.9),
          S('reveal', 'Баффало: уступал %d раз — %d раз отыгрался.' % (lead[1], lead[0]),
            'Баффало: уступал %d раз — %d раз отыгрался' % (lead[1], lead[0]), min=2.4),
          S('worst', 'Хуже всех — Рейнджерс: %d из %d.' % (worst[0], worst[1]),
            'Хуже всех — Рейнджерс: %d из %d' % (worst[0], worst[1]), min=2.2),
          S('cta', 'А твоя команда? Пиши в комментариях.', min=2.5)]
    r = v3.Guess(sc, 'Кто в НХЛ чаще всех отыгрывается в 3-м периоде?', ['Флорида', 'Баффало', 'Детройт'],
                 ('Баффало', lead[0], lead[1]), ('Рейнджерс', worst[0], worst[1]), note, league='NHL')
    r.lead_label = 'отыгрался, уступая после двух периодов'
    return r, 'Закономерность сезона — «Угадай»', 'НХЛ: отыгрыш в 3-м периоде, Баффало %d из %d' % (lead[0], lead[1])


def club(lg, team):
    d = season()[lg]
    return d['teams'][team]['club'], d


def p41():
    c, d = club('khl', 'Спартак')
    st = c['noloss_streak'][1]
    pf = c['periods_for']
    aw = c['away']
    facts = [(str(st), 'матчей подряд без поражений в основное время'),
             (str(pf[2]), 'шайб в третьих периодах (в первых — %d и %d)' % (pf[0], pf[1])),
             ('%d из %d' % tuple(aw), 'побед в гостях')]
    sc = [S('hook', 'Болеешь за Спартак? Это тебе.', min=1.8),
          S('fact', '%d матчей подряд без поражений в основное время.' % st, i=0, min=2.2),
          S('fact', 'В третьих периодах — %d шайб. %s в первых двух вместе.' % (
              pf[2], 'Больше, чем' if pf[2] > pf[0] + pf[1] else 'Столько же, сколько'),
            'В третьих периодах — %d шайб' % pf[2], i=1, min=2.2),
          S('fact', 'И %d побед в %d гостевых матчах.' % tuple(aw), '%d побед в %d матчах в гостях' % tuple(aw), i=2, min=2.2),
          S('cta', 'Отправь тому, кто болеет за Спартак.', min=2.8)]
    assert pf[2] >= pf[0] + pf[1]
    r = v3.Postcard(sc, 'Спартак', facts, '%s %d/%02d · %d матчей' % (d['league'], d['season'], (d['season'] + 1) % 100,
                                                                     c['gp']), league='KHL')
    return r, 'Клубный — «Открытка»', 'КХЛ, Спартак: серия %d, 3-и периоды %d, гости %d/%d' % (st, pf[2], aw[0], aw[1])


def p42():
    c, d = club('nhl', 'Вашингтон')
    hm = c['home']
    sc = [S('hook', 'Болеешь за Вашингтон? Это тебе.', min=1.8),
          S('fact', '%d победы подряд.' % c['win_streak'][1], '%d победы подряд' % c['win_streak'][1], i=0, min=2.0),
          S('fact', '%d побед в %d домашних матчах.' % tuple(hm), i=1, min=2.0),
          S('fact', 'И в %d матчах из %d — шесть и больше шайб за основное время.' % (c['o55'], c['gp']),
            'В %d из %d матчей — 6+ шайб' % (c['o55'], c['gp']), i=2, min=2.2),
          S('cta', 'Отправь тому, кто болеет за Вашингтон.', min=2.8)]
    facts = [(str(c['win_streak'][1]), 'победы подряд'), ('%d из %d' % tuple(hm), 'побед дома'),
             ('%d из %d' % (c['o55'], c['gp']), 'матчей — 6+ шайб в основное время')]
    r = v3.Postcard(sc, 'Вашингтон', facts, '%s %d/%02d · %d матчей' % (d['league'], d['season'], (d['season'] + 1) % 100,
                                                                       c['gp']), league='NHL')
    return r, 'Клубный — «Открытка»', 'НХЛ, Вашингтон: серия %d, дома %d/%d, 6+ шайб %d/%d' % (
        c['win_streak'][1], hm[0], hm[1], c['o55'], c['gp'])


def p51():
    c, d = club('khl', 'Автомобилист')
    n = c['noloss_streak'][1]
    dots = [x.split(' ')[-2] if x.endswith(('ОТ', 'Б')) else x.split(' ')[-1] for x in c['last5']][-n:]
    sc = [S('hook', '%s без поражений в основное время.' % v3_num_games(n), '%d матча без поражений' % n, min=1.8),
          S('dots', 'Три один, пять один, четыре один, три два.', '3:1, 5:1, 4:1, 3:2', min=2.6),
          S('empty', 'Сегодня — Металлург. Будет пятый?', min=2.0),
          S('bet', 'Наш прогноз: Автомобилист не проиграет в основное время. Кэф — один шестьдесят девять.',
            'Автомобилист не проиграет в основное время. Кэф 1,69', min=3.2)]
    r = v3.Series(sc, 'Автомобилист', n, 'матча подряд без поражений в основное время', dots,
                  'Автомобилист не проиграет в основное время', 1.69, 'сегодня · 15:00 МСК · против Металлурга',
                  league='KHL')
    r.today = 'Сегодня — пятый?'
    return r, 'Прогноз с крючком — «Серия»', 'КХЛ, прогноз 3110-1 (принят владельцем): серия %d' % n


def p52():
    c, d = club('nhl', 'Ванкувер')
    b = next(x for x in d['teams']['Ванкувер']['bets'] if x['key'] == 'regwin')
    last = c['last5']
    dots = [x.split(' ')[-2] if x.endswith(('ОТ', 'Б')) else x.split(' ')[-1] for x in last]
    sc = [S('hook', 'Одна. Столько побед в основное время у Ванкувера за %d матчей.' % b['m'],
            '1 победа в основное время за %d матчей' % b['m'], min=2.2),
          S('dots', 'Последние пять — четыре поражения.', min=2.4),
          S('empty', 'Сегодня ночью к ним едет Торонто.', min=2.0),
          S('bet', 'Наш прогноз: итоговая победа Торонто. Кэф — один шестьдесят.',
            'Итоговая победа Торонто. Кэф 1,60', min=3.0)]
    r = v3.Series(sc, 'Торонто', b['n'], 'победа в основное время у Ванкувера за %d матчей' % b['m'], dots,
                  'Итоговая победа Торонто', 1.60, 'ночью · 02:00 МСК · Ванкувер — Торонто', league='NHL')
    r.dot_team = 'Ванкувер'
    r.today = 'Сегодня — Торонто'
    r.hits = []
    for x in last:
        sc_ = x.split(' ')[-2] if x.endswith(('ОТ', 'Б')) else x.split(' ')[-1]
        a, b_ = map(int, sc_.split(':'))
        r.hits.append(a > b_)
    return r, 'Прогноз с крючком — «Серия»', 'НХЛ, прогноз Ванкувер — Торонто (черновик 31.10, ещё не принят): 1 из %d' % b['m']


PROBES = {'1.1': p11, '1.2': p12, '2.1': p21, '2.2': p22, '3.1': p31, '3.2': p32, '4.1': p41, '4.2': p42,
          '5.1': p51, '5.2': p52}


# ───────────────────────────── звук ─────────────────────────────
SWOOSH = os.environ.get('REELS_V3_SWOOSH') == '1'   # «вжухи» на сменах владелец отклонил 26.10 — по умолчанию нет


def bed(dur, cuts, seed=3):
    """Лёгкий фон: тёплый аккорд (ля минор 9) с медленным дыханием + мягкий «вжух» на смене сцен. Синтез, без треков."""
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for f, a in ((110.0, 0.5), (164.81, 0.35), (196.0, 0.3), (246.94, 0.22), (261.63, 0.16)):
        out += a * np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.11 * t) * 0.6)
    out *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.17 * t) ** 2
    rnd = np.random.default_rng(seed)
    for c in (cuts[1:] if SWOOSH else []):
        n = int(0.35 * SR)
        i = int(max(0, c - 0.25) * SR)
        if i + n > len(out):
            continue
        noise = rnd.standard_normal(n)
        noise = np.convolve(noise, np.ones(40) / 40, 'same')
        env = np.sin(np.linspace(0, np.pi, n)) ** 2
        out[i:i + n] += noise * env * 2.2
    fade = np.minimum(1, np.minimum(t / 0.4, (dur - t) / 0.6))
    out *= np.clip(fade, 0, 1)
    return out / (np.abs(out).max() + 1e-9)


def wav_write(path, x):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x16.tobytes())


def voice_track(reel, wavs):
    n = int(reel.dur * SR)
    v = np.zeros(n, np.float32)
    for a, w in zip(reel.T, wavs):
        i = int((a + 0.06) * SR)
        w = w[:max(0, n - i)]
        v[i:i + len(w)] += w
    pk = np.abs(v).max()
    return v / pk * 0.89 if pk > 0 else v


def build(pid, job_path):
    reel, title, what = PROBES[pid]()
    novoice = os.environ.get('REELS_V3_VOICE_ON') != '1'   # владелец 31.10: «забудем про озвучку» — по умолчанию без голоса
    reel.subs = not novoice
    wavs = []
    if not novoice:
        import tts
        for s in reel.scenes:
            wavs.append(tts.say(s['say']))
        reel.timing([len(w) / SR for w in wavs])
    print('V3MAKE %s %s %.1f с, сцены %s' % (pid, title, reel.dur, [round(x, 2) for x in reel.T]), flush=True)
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, 'v3-%s' % pid.replace('.', '_'))
    silent = base + '_silent.mp4'
    C.render(reel, silent, track=None)
    v = voice_track(reel, wavs) if wavs else np.zeros(int(reel.dur * SR), np.float32)
    mix = v + (0.075 if wavs else 0.35) * bed(reel.dur, reel.T)
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    paths = {}
    for suf, audio in (('', mix), ('_clean', v)):
        wp = tempfile.mktemp(suffix='.wav')
        wav_write(wp, audio)
        p = base + suf + '.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wp, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar',
                        '44100', '-shortest', '-movflags', '+faststart', p], check=True)
        paths[suf] = p
    os.unlink(silent)
    return paths, title, what, reel.dur


def main(job_path, ids):
    import tts
    tts.ensure_ffmpeg()
    msgs = []
    for pid in ids:
        try:
            paths, title, what, dur = build(pid, job_path)
            msgs.append({'to': 'owner', 'type': 'video', 'files': [os.path.relpath(paths[''], ROOT)],
                         'text': '%s · %s · %.0f с\n%s' % (pid, title, dur, what)})
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print('V3MAKE %s ошибка %r' % (pid, e), flush=True)
            msgs.append({'to': 'owner', 'type': 'text', 'text': '%s — проба не собралась: %s' % (pid, str(e)[:200])})
    if job_path and os.path.exists(job_path):
        with open(job_path, encoding='utf-8') as f:
            job = json.load(f)
        job['messages'] = (job.get('messages') or [])[:1] + msgs + (job.get('messages') or [])[1:]
        with open(job_path, 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
