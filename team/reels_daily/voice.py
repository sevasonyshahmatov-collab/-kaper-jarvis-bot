# -*- coding: utf-8 -*-
"""Озвучка и субтитры шортсов (владелец 20.10: «давай воспользуемся всеми» — голос и субтитры как в CapCut).

Голос — Yandex SpeechKit (владелец 20.10: Piper «неестественный», берём Яндекс): секрет YANDEX_TTS_KEY, голос и подача —
REELS_YVOICE «имя:роль@скорость» (по умолчанию ermil:good@1.12). Без ключа — запасной Piper (ниже).

Голос — Piper (github.com/rhasspy/piper, синтез речи на своём раннере, без внешних сервисов), русский голос из
rhasspy/piper-voices (лицензия голоса — его MODEL_CARD, печатается в лог при загрузке). Silero не берём: русские голоса
у него только для некоммерческого использования.

Сценарий — по сценам шаблона (script_simulate / script_numday): фраза ставится на свою долю, а если предыдущая ещё
звучит — сдвигается за неё. Музыка под голосом приглушается (сайдчейн), чистая версия ролика — только голос.
Субтитры — по 1–4 слова крупно внизу безопасной зоны, текущее слово подсвечено (время слова — пропорционально длине
внутри фразы). Всё собирается обёрткой Voiced вокруг готового ролика: кадр = кадр шаблона + субтитр.
"""
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

VOICE = os.environ.get('REELS_VOICE', 'ru_RU-denis-medium')
HF = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/%s/%s/%s'
CACHE = os.path.expanduser('~/.cache/piper')
SR = 22050

HALF = {'1,5': ('полтора', 'полутора'), '2,5': ('два с половиной', 'двух с половиной'),
        '3,5': ('три с половиной', 'трёх с половиной'), '4,5': ('четыре с половиной', 'четырёх с половиной'),
        '5,5': ('пять с половиной', 'пяти с половиной'), '6,5': ('шесть с половиной', 'шести с половиной'),
        '7,5': ('семь с половиной', 'семи с половиной')}


# ── синтез ──
def _ensure():
    try:
        import piper  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'piper-tts'], check=True)
    name, q = VOICE.split('-')[1], VOICE.split('-')[2]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, VOICE + '.onnx')
    if not os.path.exists(path):
        import requests
        for suf in ('.onnx', '.onnx.json', 'MODEL_CARD'):
            fn = VOICE + suf if suf != 'MODEL_CARD' else 'MODEL_CARD'
            r = requests.get(HF % (name, q, fn), timeout=120)
            r.raise_for_status()
            with open(os.path.join(CACHE, fn if suf != 'MODEL_CARD' else VOICE + '.card'), 'wb') as f:
                f.write(r.content)
        card = open(os.path.join(CACHE, VOICE + '.card'), encoding='utf-8', errors='replace').read()
        print('VOICECARD %s\n%s' % (VOICE, card[:1500]), flush=True)
    return path


_V = {}


YANDEX = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
# голос Яндекса: имя[:роль][@скорость] — владелец 20.10: «уверенная, бодрая, ровная», выбор на слух из превью
YVOICE = os.environ.get('REELS_YVOICE', 'ermil:good@1.12')


def engine():
    return 'yandex' if os.environ.get('YANDEX_TTS_KEY', '').strip() else 'piper'


def say_yandex(text, spec=None):
    """Yandex SpeechKit (секрет YANDEX_TTS_KEY — API-ключ сервисного аккаунта). → float32 моно SR Гц."""
    import requests
    spec = spec or YVOICE
    name, _, speed = spec.partition('@')
    name, _, role = name.partition(':')
    data = dict(text=text, lang='ru-RU', voice=name, speed=speed or '1.0', format='lpcm', sampleRateHertz=str(SR))
    if role:
        data['emotion'] = role
    r = requests.post(YANDEX, headers={'Authorization': 'Api-Key ' + os.environ['YANDEX_TTS_KEY'].strip()}, data=data,
                      timeout=60)
    if r.status_code != 200:
        raise RuntimeError('Yandex SpeechKit %s: %s' % (r.status_code, r.text[:300]))
    x = np.frombuffer(r.content, '<i2').astype(np.float32) / 32768
    nz = np.where(np.abs(x) > 0.02)[0]
    return x[max(0, nz[0] - 200):nz[-1] + 400] if len(nz) else x


def say(text):
    """Фраза → float32 моно SR Гц (тишина по краям обрезана). Есть ключ Яндекса — Yandex SpeechKit, нет — Piper."""
    if engine() == 'yandex':
        return say_yandex(text)
    path = _ensure()
    from piper import PiperVoice
    if 'v' not in _V:
        _V['v'] = PiperVoice.load(path)
    v = _V['v']
    tmp = os.path.join(CACHE, 'say.wav')
    with wave.open(tmp, 'wb') as w:
        if hasattr(v, 'synthesize_wav'):
            v.synthesize_wav(text, w)
        else:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v.config.sample_rate)
            v.synthesize(text, w)
    with wave.open(tmp) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x).astype(np.float32)
    nz = np.where(np.abs(x) > 0.02)[0]
    return x[max(0, nz[0] - 200):nz[-1] + 400] if len(nz) else x


# ── текст для голоса ──
ONES = ('ноль один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать тринадцать четырнадцать '
        'пятнадцать шестнадцать семнадцать восемнадцать девятнадцать').split()
TENS = ('', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто')
HUND = ('', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот', 'семьсот', 'восемьсот', 'девятьсот')


def words_num(n):
    """0–999 прописью (мужской род) — больше в роликах не бывает."""
    n = int(n)
    if n < 20:
        return ONES[n]
    out = []
    if n >= 100:
        out.append(HUND[n // 100])
        n %= 100
    if n >= 20:
        out.append(TENS[n // 10])
        n %= 10
        if n:
            out.append(ONES[n])
    elif n:
        out.append(ONES[n])
    return ' '.join(out)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def speak_pick(pick):
    """«Тотал Вегаса больше 2,5 в основное время» → «тотал Вегаса больше двух с половиной в основное время»."""
    p = pick.replace('−', '-')

    def half(mt):
        sign, num = mt.group(1), mt.group(2)
        pre = p[:mt.start()].rstrip().lower()
        nom, gen = HALF.get(num, (num, num))
        word = gen if pre.endswith(('больше', 'меньше')) else nom
        return ('плюс ' if sign == '+' else 'минус ' if sign == '-' else '') + word
    p = re.sub(r'([+-]?)(\d,5)', half, p)
    return p[0].lower() + p[1:] if p else p


def speak_kef(k):
    a, b = ('%.2f' % k).split('.')
    tail = 'ровно' if b == '00' else ('ноль ' + words_num(b[1])) if b[0] == '0' else words_num(b)
    return '%s %s' % (words_num(a), tail)


def speak_pct(x):
    return '%s %s' % (words_num(x), plural(x, 'процент', 'процента', 'процентов'))


# ── сценарии по шаблонам: [(время, текст для голоса, текст субтитра)] ──
def script_simulate(r, m):
    pct = round(100 * r.hits / r.n)
    h, a = r.h.short, r.a.short
    return [(0.3, '%s против %s.' % (h, a), '%s — %s' % (h, a)),
            (1.3, 'Модель разыгрывает этот матч десять тысяч раз.', 'Модель разыгрывает матч 10 000 раз'),
            (r.ts + 0.3, 'Проверяем: %s.' % speak_pick(m['pick']), 'Проверяем: %s' % m['pick'].lower()),
            (r.drop + 0.2, 'Итог: %s.' % speak_pct(pct), 'Итог: %d%%' % pct),
            (r.drop + 2 * r.u, 'Коэффициент %s.' % speak_kef(m['odds']), 'Кэф %s' % ('%.2f' % m['odds']).replace('.', ','))]


def script_numday(r, m):
    from reels import core as C
    team = C.gen_case(r.team.short, 'g')
    return [(0.3, 'Цифра дня.', 'Цифра дня'),
            (r.t1 + 0.2, '%s из %s.' % (words_num(r.k), words_num(r.n)), '%d из %d' % (r.k, r.n)),
            (r.t1 + 1.6 * r.u, 'Столько раз этот прогноз заходил в матчах %s в сезоне.' % team,
             'Столько раз прогноз заходил в матчах %s' % team),
            (r.tp + 0.1, 'А сегодня?', 'А сегодня?'),
            (r.drop + 0.2, '%s.' % speak_pick(m['pick']).capitalize(), m['pick']),
            (r.drop + 2.2 * r.u, 'Коэффициент %s.' % speak_kef(m['odds']), 'Кэф %s' % ('%.2f' % m['odds']).replace('.', ','))]


SCRIPTS = {'simulate': script_simulate, 'numday': script_numday}


# ── сборка звука ──
def build(r, m, mod, music, start, out):
    """Голос по сценарию шаблона + музыка (приглушена под голосом). → (микс wav, только голос wav, субтитры).
    Субтитры: [(t0, t1, [(слово, w0, w1)…])] — по кускам до 4 слов."""
    lines = SCRIPTS[mod](r, m)
    dur = r.dur
    voice = np.zeros(int(SR * (dur + 1)), np.float32)
    caps, t_free = [], 0.0
    for t, spoken, shown in lines:
        x = say(spoken)
        t = max(t, t_free + 0.08)
        if t + len(x) / SR > dur - 0.2:
            continue
        i = int(t * SR)
        voice[i:i + len(x)] += x
        t1 = t + len(x) / SR
        t_free = t1
        words = shown.split()
        total = sum(len(w) + 1 for w in words)
        acc, timed = t, []
        for w in words:
            d = (t1 - t) * (len(w) + 1) / total
            timed.append((w, acc, acc + d))
            acc += d
        for k in range(0, len(timed), 4):
            chunk = timed[k:k + 4]
            caps.append((chunk[0][1], chunk[-1][2] + 0.15, chunk))
    voice = voice[:int(SR * dur)]
    vpath, mpath = out + '_voice.wav', out + '_mix.wav'
    _wav(vpath, voice)
    # музыка: кусок трека, приглушение под голосом (огибающая голоса, атака 30 мс, отпуск 250 мс)
    raw = out + '_music.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.3f' % start, '-t', '%.3f' % dur, '-i', music, '-ac', '1',
                    '-ar', str(SR), raw], check=True)
    with wave.open(raw) as w:
        mus = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    mus = np.pad(mus, (0, max(0, len(voice) - len(mus))))[:len(voice)]
    env = np.abs(voice)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, mode='same')
    duck = 1 - 0.7 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
    mix = 0.8 * mus * duck + 1.4 * voice
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    _wav(mpath, mix)
    os.unlink(raw)
    return mpath, vpath, caps


def _wav(path, x):
    y = (np.clip(x, -1, 1) * 32767).astype('<i2')
    st = np.repeat(y[:, None], 2, axis=1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ── субтитры поверх кадра ──
class Voiced:
    """Ролик шаблона + субтитры. Остальные атрибуты (dur, cover_t, drop, ticker…) — от ролика шаблона."""
    Y = 1395

    def __init__(self, base, caps, voice_only=None):
        self.__dict__['base'] = base
        self.__dict__['caps'] = caps
        self.__dict__['voice_only'] = voice_only
        self.__dict__['_cache'] = {}

    def __getattr__(self, k):
        return getattr(self.base, k)

    def __setattr__(self, k, v):
        setattr(self.base, k, v)

    def _word(self, w, on):
        from reels import core as C
        key = (w, on)
        if key not in self._cache:
            self._cache[key] = C.text(w.upper(), 'unb', 58, (255, 214, 64) if on else (255, 255, 255), 900, stroke=6,
                                      stroke_fill=(0, 0, 0))
        return self._cache[key]

    def frame(self, t):
        from reels import core as C
        fr = self.base.frame(t)
        for t0, t1, chunk in self.caps:
            if t0 <= t < t1:
                ims = [self._word(w, w0 <= t < w1 + 0.05) for w, w0, w1 in chunk]
                gap = 22
                tw = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
                s = min(1.0, (C.W - 80) / max(1, tw))
                q = C.out_back(C.seg(t, t0, t0 + 0.18), 1.6)
                x = C.W / 2 - tw * s / 2
                fr = fr.convert('RGBA')
                for im in ims:
                    C.put(fr, C.scale(im, s * (0.85 + 0.15 * q)), x + im.size[0] * s / 2, self.Y, min(1.0, q * 1.6))
                    x += (im.size[0] + gap) * s
                break
        return fr


def voiced(r, m, mod, music, start, out):
    """→ (ролик с субтитрами, путь к миксу для render(track=…, start=0)) — или (r, None), если для шаблона нет сценария."""
    if mod not in SCRIPTS:
        return r, None
    mix, vo, caps = build(r, m, mod, music, start, out)
    print('VOICE %s: %d фраз, субтитров %d' % (mod, len(SCRIPTS[mod](r, m)), len(caps)), flush=True)
    return Voiced(r, caps, vo), mix


if __name__ == '__main__':
    print(json.dumps([speak_pick(x) for x in ('Тотал Вегаса больше 2,5 в основное время', 'Фора Сан-Хосе +1,5',
                                               'Тотал матча меньше 5,5')], ensure_ascii=False))
