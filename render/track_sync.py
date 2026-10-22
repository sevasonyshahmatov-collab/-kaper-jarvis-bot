# -*- coding: utf-8 -*-
"""Подогнать ролик (render/shorts.py, style='bars') под трек: темп, дропы, сетка долей и откуда начинать трек.

    python track_sync.py трек.mp3|mp4|wav [--map] [--drop 27.1]

--map — карта громкости и баса по секундам; --drop — свой дроп (по карте), уточняется до самого удара баса.

Темп — по всему треку (где на сетке больше всего ударов). Дроп — где громкость и бас резко вырастают
(следующие 2 с против предыдущих 2 с), уточнённый до самого удара баса. Сетка долей отсчитывается от первого дропа:
так точнее всего там, где важно (столкновение эмблем — ровно на ударе). Доля сцены (unit) — 1 или 2 доли трека,
чтобы такт-сцена шла 2,4–4,6 с (быстрый трек режем через долю). Старт трека — такт-сцена до дропа: крючок под нарастание.
Сам трек в репозиторий не кладём: в загружаемый ролик музыку добавляют в редакторе YouTube Shorts / VK Клипов.
Предпросмотр с треком: shorts.pick(..., style='bars', beat=unit, track='трек.wav', track_start=start) —
wav 44,1 кГц стерео (ffmpeg -i трек.mp3 -ac 2 -ar 44100 трек.wav).
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np


def load(path, sr=22050):
    """Моно-сигнал трека (любой формат — через ffmpeg)."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-vn', '-ac', '1', '-ar', str(sr), tmp], check=True)
        with wave.open(tmp) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float32) / 32768
    finally:
        os.unlink(tmp)
    return x, sr


def analyze(path, manual=None):
    """{'bpm', 'beat', 'unit', 'drops': [с], 'first', 'start'}; manual — дроп вручную (с), уточняется до удара баса."""
    x, sr = load(path)
    hop, win = 256, 1024
    n = 1 + (len(x) - win) // hop
    fr = np.lib.stride_tricks.as_strided(x, (n, win), (x.strides[0] * hop, x.strides[0]))
    spec = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    f = np.fft.rfftfreq(win, 1 / sr)
    fps = sr / hop
    # темп: спектральный поток на сетке, 60–180 уд/мин
    flux = np.maximum(0, np.diff(np.log1p(spec * 10), axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux = np.maximum(0, flux - np.convolve(flux, np.ones(32) / 32, mode='same'))
    fl2 = flux[: (len(flux) // 2) * 2].reshape(-1, 2).sum(axis=1)       # шаг 2 кадра — быстрее перебор
    fps2 = fps / 2
    best = (-1.0, 120.0)
    for bpm in np.arange(60, 181, 0.05):
        period = fps2 * 60 / bpm
        m = int((len(fl2) - period) / period)
        base = period * np.arange(m)
        sc = max(fl2[(ph + base).astype(int)].mean() for ph in np.arange(0, period, 1.0))
        if sc > best[0]:
            best = (sc, bpm)
    bpm = float(best[1])
    beat = 60 / bpm
    # кандидаты в дропы: бас за секунду после доли заметно больше, чем за 2 с до неё
    low = spec[:, f < 150].sum(axis=1)
    onset = np.maximum(0, np.diff(np.log1p(low), prepend=0))
    k = int(fps)
    lo = np.convolve(low, np.ones(k) / k, mode='same')
    out = []
    for i in range(2 * k, n - k):
        if i % max(1, int(beat * fps / 2)):
            continue
        before, after = lo[i - 2 * k:i - k // 2].mean(), lo[i + k // 4:i + k].mean()
        if after > 0.35 * lo.max() and after > 2.0 * max(before, 1e-6) and (not out or i / fps - out[-1] > 8):
            a0, b0 = max(0, i - int(0.4 * fps)), min(n, i + int(0.4 * fps))
            out.append(round(float((a0 + int(np.argmax(onset[a0:b0]))) / fps), 3))
    if manual is not None:                                             # дроп по карте громкости — уточнить до удара баса
        i = int(manual * fps)
        a0, b0 = max(0, i - int(0.3 * fps)), min(n, i + int(0.3 * fps))
        out = [round(float((a0 + int(np.argmax(onset[a0:b0]))) / fps), 3)]
    unit = beat
    while unit * 4 < 2.4:
        unit *= 2
    while unit * 4 > 4.6:
        unit /= 2
    lb = _librosa_check(x, sr, bpm, out)                              # вторая проверка (владелец 20.10: librosa)
    if lb:
        out = lb['drops']
    d0 = out[0] if out else 0.0
    first = d0 - int(d0 / beat) * beat
    start = max(0.0, d0 - 4 * unit)
    return dict(bpm=round(bpm, 2), beat=round(beat, 6), unit=round(unit, 6), drops=out, first=round(first, 3), start=round(start, 3),
                librosa=lb and dict(bpm=lb['bpm'], agree=lb['agree'], snapped=lb['snapped']))


def _librosa_check(x, sr, bpm, drops):
    """librosa (если установлена): свой темп по огибающей атак и сетка долей. Темп сверяем с нашим (с точностью до ×2,
    расхождение до 2 %) — при согласии дропы притягиваем к ближайшей доле librosa (не дальше 70 мс), иначе оставляем как
    есть и пишем расхождение. → dict(bpm, agree, snapped, drops) | None."""
    try:
        import librosa
    except ImportError:
        return None
    env = librosa.onset.onset_strength(y=x, sr=sr, hop_length=256)
    tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=256, start_bpm=bpm, tightness=200)
    lbpm = float(np.atleast_1d(tempo)[0])
    bt = librosa.frames_to_time(beats, sr=sr, hop_length=256)
    agree = lbpm > 0 and any(abs(lbpm * k / bpm - 1) < 0.02 for k in (0.5, 1, 2))
    out, snapped = list(drops), 0
    if agree and len(bt):
        for i, d in enumerate(out):
            j = int(np.argmin(np.abs(bt - d)))
            if abs(bt[j] - d) <= 0.07:
                out[i] = round(float(bt[j]), 3)
                snapped += 1
    return dict(bpm=round(lbpm, 2), agree=bool(agree), snapped=snapped, drops=out)


def energy_map(path, step=1.0):
    """Карта громкости и баса по секундам — по ней видно вступление, дропы и затишья."""
    x, sr = load(path)
    hop, win = 512, 2048
    n = 1 + (len(x) - win) // hop
    fr = np.lib.stride_tricks.as_strided(x, (n, win), (x.strides[0] * hop, x.strides[0]))
    spec = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    f = np.fft.rfftfreq(win, 1 / sr)
    fps = sr / hop
    low, rms = spec[:, f < 150].sum(axis=1), np.sqrt((fr ** 2).mean(axis=1))
    k = int(fps * step)
    return ['%5.0f %-26s %s' % (i / fps, '#' * int(rms[i:i + k].mean() * 60), '|' * int(low[i:i + k].mean() / low.max() * 30))
            for i in range(0, n, k)]


if __name__ == '__main__':
    manual = float(sys.argv[sys.argv.index('--drop') + 1]) if '--drop' in sys.argv else None
    if '--map' in sys.argv:
        print('\n'.join(energy_map(sys.argv[1])))
    r = analyze(sys.argv[1], manual)
    print('темп %.2f уд/мин, доля %.4f с; сцена = 4 × %.4f с' % (r['bpm'], r['beat'], r['unit']))
    print('дропы (вход громкой части):', ', '.join('%.2f с' % d for d in r['drops']) or 'не найдены')
    print('старт трека для ролика: %.2f с (такт-сцена до первого дропа)' % r['start'])
    if r.get('librosa'):
        print('librosa: темп %.2f, %s; дропов притянуто к доле: %d' % (r['librosa']['bpm'], 'совпадает' if r['librosa']['agree']
                                                                      else 'НЕ совпадает — проверить на слух', r['librosa']['snapped']))
