# -*- coding: utf-8 -*-
"""Ролики v3: бесплатная «живая» русская озвучка (ТЗ docs/handoff/REELS_V3_BRIEF.md, владелец 31.10).

Движки (выбор — REELS_V3_VOICE=<движок>[:<голос>]; по умолчанию edge:ru-RU-DmitryNeural до выбора владельца):
- edge  — нейроголоса Microsoft Edge (пакет edge-tts, MIT; сервис неофициальный, условия коммерческого использования
          не прописаны) — голоса ru-RU-DmitryNeural (м), ru-RU-SvetlanaNeural (ж), ru-RU-DariyaNeural (ж).
- qwen  — Qwen3-TTS (Alibaba, Apache-2.0, open weights, русский в списке языков): голос по описанию (VoiceDesign).
- chat  — Chatterbox Multilingual (Resemble AI, MIT, 23 языка, ru) — запасной к qwen.
- vosk  — Vosk TTS (Alpha Cephei, Apache-2.0), русская многоголосая модель, работает на процессоре.
Silero не берём: русские модели — CC BY-NC (только некоммерческое). Piper отверг владелец (20.10).
Всё ставится и качается в GitHub Actions (из облачной сессии HF и сервис Edge закрыты). Выход — float32 моно, SR Гц.
"""
import asyncio
import os
import subprocess
import sys
import tempfile

import numpy as np

SR = 24000
DEFAULT = os.environ.get('REELS_V3_VOICE', 'edge:ru-RU-DmitryNeural')
QWEN_INSTRUCT = ('Мужской голос, 30 лет, спортивный журналист: живо, уверенно, с лёгкой интригой, '
                 'естественные паузы, без пафоса и без радиодикторской манерности.')


def _torch_cpu():
    try:
        import torch  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'torch', 'torchaudio', '--index-url',
                        'https://download.pytorch.org/whl/cpu'], check=True)


def _pip(*pkgs):
    _torch_cpu() if any(p in ('qwen-tts', 'chatterbox-tts') for p in pkgs) else None
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', *pkgs], check=True)


def _read_any(path):
    """Любой аудиофайл → float32 моно SR (через ffmpeg)."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def _resample(wav, sr):
    if sr == SR:
        return wav.astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        path = f.name
    import wave
    w16 = (np.clip(wav, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr)); w.writeframes(w16.tobytes())
    return _read_any(path)


def say_edge(text, voice='ru-RU-DmitryNeural', rate='+6%', pitch='+0Hz'):
    try:
        import edge_tts
    except ImportError:
        _pip('edge-tts'); import edge_tts
    out = tempfile.mktemp(suffix='.mp3')

    async def go():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)
    asyncio.run(go())
    return _read_any(out)


_M = {}


def say_qwen(text, instruct=QWEN_INSTRUCT, model='Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign'):
    try:
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        _pip('qwen-tts'); from qwen_tts import Qwen3TTSModel
    import torch
    if model not in _M:
        _M[model] = Qwen3TTSModel.from_pretrained(model, device_map='cpu', dtype=torch.float32)
    wavs, sr = _M[model].generate_voice_design(text=text, language='Russian', instruct=instruct)
    return _resample(np.asarray(wavs[0], dtype=np.float32), sr)


def say_chat(text, ref=None):
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError:
        _pip('chatterbox-tts'); from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    if 'chat' not in _M:
        _M['chat'] = ChatterboxMultilingualTTS.from_pretrained(device='cpu')
    m = _M['chat']
    kw = dict(language_id='ru')
    if ref:
        kw['audio_prompt_path'] = ref
    wav = m.generate(text, **kw)
    return _resample(wav.squeeze().cpu().numpy(), m.sr)


def say_vosk(text, speaker=2):
    try:
        from vosk_tts import Model, Synth
    except ImportError:
        _pip('vosk-tts'); from vosk_tts import Model, Synth
    if 'vosk' not in _M:
        _M['vosk'] = Synth(Model(model_name='vosk-model-tts-ru-0.9-multi'))
    out = tempfile.mktemp(suffix='.wav')
    _M['vosk'].synth(text, out, speaker_id=int(speaker))
    return _read_any(out)


def say(text, spec=None):
    """«движок:голос» → float32 моно SR."""
    eng, _, arg = (spec or DEFAULT).partition(':')
    if eng == 'edge':
        return say_edge(text, arg or 'ru-RU-DmitryNeural')
    if eng == 'qwen':
        return say_qwen(text, arg or QWEN_INSTRUCT)
    if eng == 'chat':
        return say_chat(text, arg or None)
    if eng == 'vosk':
        return say_vosk(text, arg or 2)
    raise ValueError('неизвестный движок озвучки: %s' % eng)
