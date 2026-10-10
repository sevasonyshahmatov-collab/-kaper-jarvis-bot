# -*- coding: utf-8 -*-
"""Подогнать ролик (render/shorts.py, style='bars') под трек: темп, сетка долей, дропы и откуда начинать трек.

    python track_sync.py трек.mp3|mp4|wav

Печатает темп, длину доли, сильные доли входа баса (дропы) и старт трека для ролика: за такт до первого дропа —
крючок идёт под нарастание, эмблемы сталкиваются ровно на дропе. Сам трек в репозиторий не кладём:
в загружаемый ролик музыку добавляют в редакторе YouTube Shorts / VK Клипов (иначе Content ID).
Предпросмотр с треком: shorts.pick(..., style='bars', beat=доля, track='трек.wav', track_start=старт) —
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


def analyze(path):
    """{'bpm', 'beat', 'first', 'drops': [с], 'start'} — сетка долей и дропы (вход баса после тихого места)."""
    x, sr = load(path)
    hop, win = 512, 2048
    n = 1 + (len(x) - win) // hop
    fr = np.lib.stride_tricks.as_strided(x, (n, win), (x.strides[0] * hop, x.strides[0]))
    spec = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    f = np.fft.rfftfreq(win, 1 / sr)
    fps = sr / hop
    flux = np.maximum(0, np.diff(np.log1p(spec * 10), axis=0)).sum(axis=1)
    flux = np.maximum(0, np.concatenate([[0], flux]) - np.convolve(np.concatenate([[0], flux]), np.ones(16) / 16, mode='same'))
    best = (-1, 120.0, 0.0)
    for bpm in np.arange(60, 181, 0.1):                                # темп и фаза: где на сетке больше всего ударов
        period = fps * 60 / bpm
        for ph in np.arange(0, period, 1.0):
            idx = (ph + period * np.arange(int((n - ph) / period))).astype(int)
            sc = flux[idx].mean()
            if sc > best[0]:
                best = (sc, bpm, ph)
    _, bpm, ph = best
    beat = 60 / bpm
    first = ph / fps
    low = spec[:, f < 150].sum(axis=1)
    k = int(fps * 1.0)
    lo = np.convolve(low, np.ones(k) / k, mode='same')                 # бас за секунду
    grid = first + beat * np.arange(int((len(x) / sr - first) / beat))
    drops = []
    for t in grid:
        i = int(t * fps)
        if i - 2 * k < 0 or i + k >= n:
            continue
        before, after = lo[i - 2 * k:i - k // 2].mean(), lo[i + k // 4:i + k].mean()
        if after > 0.35 * lo.max() and after > 2.5 * max(before, 1e-6) and (not drops or t - drops[-1] > 8):
            drops.append(round(float(t), 3))
    start = max(0.0, drops[0] - 4 * beat) if drops else first
    return dict(bpm=round(float(bpm), 2), beat=round(float(beat), 6), first=round(float(first), 3), drops=drops, start=round(float(start), 3))


if __name__ == '__main__':
    r = analyze(sys.argv[1])
    print('темп %.2f уд/мин, доля %.4f с, первая доля %.3f с' % (r['bpm'], r['beat'], r['first']))
    print('дропы (вход баса):', ', '.join('%.2f с' % d for d in r['drops']) or 'не найдены')
    print('старт трека для ролика: %.2f с (такт до первого дропа)' % r['start'])
