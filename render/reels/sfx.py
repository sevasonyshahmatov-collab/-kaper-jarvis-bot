# -*- coding: utf-8 -*-
"""Звуковые эффекты роликов (саунд-дизайн из урока по монтажу, владелец 26.10) — синтез кодом, без чужих сэмплов.

Работает для любого шаблона без его правки: core.render() по ходу сборки кадров отдаёт сюда уменьшенные кадры (Cuts),
здесь находим резкие смены картинки → «вжух» (whoosh), пик которого совпадает со сменой; на reel.drop (дроп /
кульминация ролика) — удар (hit). Щелчок (tick) — только по явному списку reel.sfx_ticks (секунды) у шаблона:
общего признака «появились цифры» по кадрам нет, автоматически не ставим.
Включение: REELS_SFX=1 или render(..., sfx=True); по умолчанию выключено.

Уровни — в дБ относительно пика музыки (ref в core._audio): эффекты на 6–9 дБ тише, смешиваются до loudnorm.
"""
import numpy as np
from PIL import Image

SR = 44100
# смена картинки: средняя |разница| соседних кадров 45×80 (0–255) ≥ CUT_DIFF (склейка, вспышка) или её сумма за 6 кадров
# (0,2 с) ≥ CUT_SUM (влёт карточки, шторка — 8–15 на кадр несколько кадров подряд). Фон, зерно, мелкая анимация — 0,4–3.
CUT_DIFF, CUT_SUM = 20.0, 45.0
CUT_GAP = 0.6                                              # не чаще одного вжуха за CUT_GAP с
GAIN = {'whoosh': -8.0, 'hit': -6.0, 'tick': -12.0}       # пик эффекта относительно пика музыки, дБ
_CACHE = {}


def _svf_bp(x, fc, q):
    """Полосовой фильтр (TPT state-variable) с меняющейся по сэмплам частотой fc — чистый свип без ступенек."""
    g = np.tan(np.pi * np.clip(fc, 20, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    y = np.empty_like(x)
    s1 = s2 = 0.0
    for i in range(len(x)):
        v3 = x[i] - s2
        v1 = a1[i] * s1 + g[i] * a1[i] * v3
        v2 = s2 + g[i] * v1
        s1, s2 = 2 * v1 - s1, 2 * v2 - s2
        y[i] = v1
    return y * k                                          # нормированный полосовой: усиление 1 на fc


def _lp1(x, fc):
    """Однополюсный ФНЧ — смягчить шумовой щелчок."""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


def _norm(x):
    return x / max(1e-9, np.abs(x).max())


def whoosh(d=0.32, seed=0):
    """Вжух: шум через полосовой свип 250 Гц → ~3,5 кГц к пику и вниз в хвосте, панорама слева направо.
    → (стерео (n, 2) с пиком 1, секунда пика от начала)."""
    key = ('w', round(d, 3), seed)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(100 + seed)
    n = int(d * SR)
    t = np.arange(n) / SR
    tp = 0.72 * d                                         # пик — ближе к концу: «влетает» в смену
    hi = 3200 + 600 * (seed % 3)
    fc = np.where(t < tp, 250 * (hi / 250) ** ((t / tp) ** 1.6), hi * np.exp(-(t - tp) / 0.12) + 900)
    env = np.where(t < tp, (t / tp) ** 2.4, np.exp(-(t - tp) / 0.055))
    env[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))   # хвост без щелчка
    common = rng.standard_normal(n)
    ch = []
    for _ in range(2):                                    # 80 % общего шума — ширина без «каши»
        x = 0.8 * common + 0.2 * rng.standard_normal(n)
        ch.append(_svf_bp(_svf_bp(x, fc, 1.1), fc, 1.1) * env)     # два звена — 12 дБ/окт: свип слышен, шипа меньше
    pan = np.clip((t / d) * 1.2 - 0.6, -0.6, 0.6)         # −0,6 → +0,6, равная мощность
    th = (pan + 1) * np.pi / 4
    out = np.stack([ch[0] * np.cos(th), ch[1] * np.sin(th)], axis=1) * np.sqrt(2)
    _CACHE[key] = (_norm(out), tp)
    return _CACHE[key]


def hit(seed=0):
    """Удар на кульминацию: синус с падением высоты 130 → 45 Гц (+2-я гармоника — слышно на телефоне),
    плотный «тамп» ~180 Гц и короткий мягкий шумовой щелчок атаки. → (стерео (n, 2), секунда пика ≈ 0)."""
    key = ('h', seed)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(200 + seed)
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    att = np.clip(t / 0.003, 0, 1)
    body = (np.sin(ph) + 0.22 * np.sin(2 * ph)) * np.exp(-t / 0.26) * att
    thump = _svf_bp(rng.standard_normal(n), np.full(n, 180.0), 1.4) * np.exp(-t / 0.06) * att
    click = _lp1(rng.standard_normal(n), 3500) * np.exp(-t / 0.012) * att
    air = _lp1(_lp1(rng.standard_normal(n), 700), 700) * np.exp(-t / 0.3) * att
    m = body + 0.4 * _norm(thump) + 0.35 * _norm(click) + 0.06 * _norm(air)
    m[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    m = _norm(m)
    _CACHE[key] = (np.stack([m, m], axis=1), 0.0)
    return _CACHE[key]


def tick(seed=0):
    """Щелчок для появления цифры/строки: два коротких синуса (3,2 и 1,6 кГц) с затуханием в миллисекунды."""
    key = ('t', seed)
    if key in _CACHE:
        return _CACHE[key]
    n = int(0.045 * SR)
    t = np.arange(n) / SR
    f = 3200 * (1 + 0.04 * (seed % 3))
    att = np.clip(t / 0.0005, 0, 1)
    m = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) + 0.4 * np.sin(np.pi * f * t) * np.exp(-t / 0.01)) * att
    m = _norm(m)
    _CACHE[key] = (np.stack([m, m], axis=1), 0.0)
    return _CACHE[key]


class Cuts:
    """Ищет резкие смены картинки: средняя |разница| соседних кадров, уменьшенных до 45×80 (усреднение блоков 24×24 —
    зерно и мелкое движение почти не дают разницы, смена сцены, вспышка, влёт карточки — дают)."""

    def __init__(self, size):
        self.size, self.prev, self.diff = size, None, []

    def feed(self, rgb_bytes):
        small = np.asarray(Image.frombytes('RGB', self.size, rgb_bytes).reduce(24), dtype=np.float32)
        self.diff.append(0.0 if self.prev is None else float(np.abs(small - self.prev).mean()))
        self.prev = small

    def times(self, fps, dur):
        """Секунды смен: кадры выше порога, по убыванию разницы (вжух — на самый резкий кадр перехода), с промежутком
        не меньше CUT_GAP."""
        d = np.array(self.diff)
        s = np.convolve(d, np.ones(6), 'same')
        cand = [i for i in np.argsort(-d, kind='stable')
                if (d[i] >= CUT_DIFF or s[i] >= CUT_SUM) and 0.25 <= i / fps <= dur - 0.15]
        out = []
        for i in cand:
            if all(abs(i - j) >= CUT_GAP * fps for j in out):
                out.append(int(i))
        return sorted(i / fps for i in out)


def events(reel, cuts):
    """Список (вид, секунда «попадания»): вжухи на сменах, удар на дропе (если он внутри ролика), щелчки по
    reel.sfx_ticks. Смену в пределах CUT_GAP от дропа забирает удар (вжух + удар вместе — на 3 дБ громче нормы)."""
    drop = getattr(reel, 'drop', None)
    drop = float(drop) if drop is not None and 0.5 <= drop <= reel.dur - 0.3 else None
    ev = [('whoosh', c) for c in cuts if drop is None or abs(c - drop) >= CUT_GAP]
    if drop is not None:
        ev.append(('hit', drop))
    ev += [('tick', float(x)) for x in (getattr(reel, 'sfx_ticks', None) or ())]
    return sorted(ev, key=lambda e: e[1])


def track(ev, dur):
    """Дорожка эффектов (n, 2) float32: пик каждого эффекта = 10^(GAIN/20) (относительно пика музыки = 1)."""
    n = int(round(dur * SR))
    buf = np.zeros((n, 2), np.float32)
    for k, (kind, at) in enumerate(ev):
        x, tp = whoosh(0.30 + 0.05 * (k % 3), seed=k % 3) if kind == 'whoosh' else {'hit': hit, 'tick': tick}[kind](k % 3)
        x = x * 10 ** (GAIN[kind] / 20)
        a = int(round((at - tp) * SR))
        s0 = max(0, -a)                                   # смена в самом начале — вжух без начала
        a, b = max(0, a), min(n, a + len(x))
        if b > a:
            buf[a:b] += x[s0:s0 + b - a]
    return buf
