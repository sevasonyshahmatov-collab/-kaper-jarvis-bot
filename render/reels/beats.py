# -*- coding: utf-8 -*-
"""Собственная музыка для роликов (фонк-бит, синтез кодом) — без чужих треков, без претензий Content ID.

beat(path, bpm, drop, length=None, seed=1, key=0) → wav 44,1 кГц стерео:
    до drop — вступление (пэд, приглушённая мелодия коубелла, хэты), за долю до дропа — подъём шума и тишина,
    на drop — удар: бочка, 808 с глайдом, клэп, хэты, коубелл в полную силу.
bpm — темп «на долю» как в reels/run.py TRACKS (60/u), drop — секунда дропа в треке (как вторая цифра TRACKS).
Ролик ставит трек со старта start = drop - drop_ролика, поэтому удар совпадает с дропом ролика.
"""
import wave

import numpy as np

SR = 44100
# минорная пентатоника от ре (Гц) — коубелл и 808
ROOT = 73.42
PENTA = [0, 3, 5, 7, 10, 12, 15]


def _note(semi, base=ROOT):
    return base * 2 ** (semi / 12.0)


def _env(n, a, d):
    t = np.arange(n) / SR
    e = np.exp(-t / max(d, 1e-4))
    na = int(a * SR)
    if na > 0:
        e[:na] *= np.linspace(0, 1, na)
    return e


def _kick(n=int(0.45 * SR)):
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * _env(n, 0.001, 0.22) + 0.25 * np.random.default_rng(1).standard_normal(n) * _env(n, 0, 0.004)


def _808(freq, dur, glide_to=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.full(n, freq) if glide_to is None else freq + (glide_to - freq) * np.clip((t - dur * 0.55) / (dur * 0.3), 0, 1)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return np.tanh(2.2 * s) * _env(n, 0.004, dur * 0.6)


def _noise_hit(rng, dur, decay, hp=True):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    if hp:
        x = np.diff(x, prepend=0)
    return x * _env(n, 0.0005, decay)


def _clap(rng):
    n = int(0.3 * SR)
    out = np.zeros(n)
    for k, off in enumerate((0, 0.009, 0.018)):
        h = _noise_hit(rng, 0.25, 0.012 if k < 2 else 0.09)
        o = int(off * SR)
        out[o:o + len(h)] += h[:n - o]
    return out * 0.6


def _cowbell(freq, dur=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * freq * t)) + np.sign(np.sin(2 * np.pi * freq * 1.48 * t))
    s = np.convolve(s, np.ones(6) / 6, mode='same')                 # мягче квадрат
    return s * _env(n, 0.001, 0.07) * 0.5


def _pad(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * freq * m * (1 + d) * t) / m for m, d in ((1, 0), (1, 0.004), (2, -0.003), (3, 0.002)))
    a = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return s * np.clip(a, 0, 1) * 0.18


def _put(buf, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= buf.shape[0] or i + len(x) <= 0:
        return
    j = min(buf.shape[0], i + len(x))
    seg = x[:j - i] * gain
    buf[i:j, 0] += seg * (1 - max(0, pan))
    buf[i:j, 1] += seg * (1 + min(0, pan))


def beat(path, bpm, drop, length=None, seed=1, key=0):
    rng = np.random.default_rng(seed)
    beat_s = 60.0 / bpm
    step = beat_s / 4                                               # шестнадцатые
    length = length or drop + 32 * beat_s
    buf = np.zeros((int(length * SR) + SR, 2))
    base = ROOT * 2 ** (key / 12.0)
    # мелодия коубелла: 16 шагов, повтор каждые 4 доли
    mel = [PENTA[i] for i in rng.integers(0, len(PENTA), 16)]
    hits = [s for s in range(16) if s % 4 == 0 or rng.random() < 0.45]
    bass = [PENTA[i] for i in rng.integers(0, 4, 4)]
    pre = drop - beat_s * 0.5                                        # тишина последние полдоли перед дропом
    # вступление: пэд по аккордам и тихий коубелл
    t = 0.0
    k = 0
    while t < pre:
        _put(buf, _pad(base * 2 * 2 ** (bass[k % 4] / 12), min(beat_s * 4, pre - t)), t, 1.0)
        t += beat_s * 4
        k += 1
    s0 = int(np.ceil(drop / step))                                   # сетка привязана к дропу: шаг 0 — ровно на drop
    n_steps = s0 + int((length - drop) / step)
    for s in range(n_steps):
        at = drop + (s - s0) * step
        if at < 0:
            continue
        if pre <= at < drop:
            continue
        intro = at < drop
        ss = (s - s0) % 16
        if ss in hits:
            g = 0.2 if intro else 0.6
            _put(buf, _cowbell(_note(mel[ss] + 24, base)), at, g, pan=0.25 if ss % 2 else -0.25)
        if not intro or at > drop - 4 * beat_s:                      # хэты: во вступлении — последние 4 доли
            hg = 0.05 if intro else (0.09 if s % 2 == 0 else 0.06)
            _put(buf, _noise_hit(rng, 0.06, 0.012), at, hg, pan=0.4 if s % 2 else -0.4)
            if not intro and rng.random() < 0.18:                    # дробь хэтов
                for r in range(1, 3):
                    _put(buf, _noise_hit(rng, 0.04, 0.008), at + r * step / 3, 0.05, pan=0.3)
        if intro:
            continue
        if ss in (0, 7, 10) or (ss == 14 and rng.random() < 0.5):
            _put(buf, _kick(), at, 0.95)
        if ss == 8:
            _put(buf, _clap(rng), at, 0.55)
        if ss in (0, 10):
            bar = ((s - s0) // 16) % 4
            f = _note(bass[bar] - 12 + 12, base)
            glide = _note(bass[(bar + 1) % 4] - 12 + 12, base) if ss == 10 and rng.random() < 0.6 else None
            _put(buf, _808(f, beat_s * (2.4 if ss == 0 else 1.4), glide), at, 0.5)
    # подъём перед дропом: шум нарастает 2 доли, затем тишина
    n = int(beat_s * 2 * SR)
    sw = np.diff(rng.standard_normal(n), prepend=0) * np.linspace(0, 1, n) ** 2
    _put(buf, sw, pre - beat_s * 2, 0.25)
    buf[int(pre * SR):int(drop * SR)] *= 0.0
    # мастер: мягкий лимитер, нормировка
    buf = np.tanh(buf * 1.4) / np.tanh(1.4)
    buf /= max(1e-6, np.abs(buf).max()) / 0.89
    data = (buf[:int(length * SR)] * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path


# собственные треки под темп и дроп размеченных треков из run.py (те же доли и дропы — ролики не меняются)
OWN = {
    'refl': dict(bpm=65, drop=7.25, seed=11, key=0),
    'kizaru': dict(bpm=60, drop=16.04, seed=23, key=-2),
    'vace': dict(bpm=64, drop=12.05, seed=37, key=3),
}


def own(key, path):
    return beat(path, **OWN[key])
