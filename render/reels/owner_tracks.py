# -*- coding: utf-8 -*-
"""Треки владельца для роликов: wav по ключу из render/reels/run.py TRACKS (slx, kizaru, vace, quantum, north, depto, jefe,
kilo, rotten).

Источник — по порядку:
  1) TRACKS_DIR — папка с <ключ>.wav (локальная сборка);
  2) ветка claude/team-dev-tracks-v2: tracks/<ключ>.mp3.enc, AES-256 (openssl enc -aes-256-cbc -pbkdf2),
     ключ — переменная окружения TRACKS_KEY (секрет репозитория, в itogi.yml). Ключ в коде, payload и логах не бывает.
Сами треки в рабочую ветку не кладём.
"""
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRANCH = 'claude/team-dev-tracks-v2'
_fetched = False


def available():
    return bool(os.environ.get('TRACKS_DIR') or os.environ.get('TRACKS_KEY'))


def wav(key):
    """Путь к wav 44,1 кГц стерео трека key. Нет источника — RuntimeError."""
    global _fetched
    d = os.environ.get('TRACKS_DIR')
    if d:
        p = os.path.join(d, key + '.wav')
        if os.path.exists(p):
            return p
    if not os.environ.get('TRACKS_KEY'):
        raise RuntimeError('нет треков: задайте TRACKS_DIR или секрет TRACKS_KEY')
    if not _fetched:
        subprocess.run(['git', 'fetch', '-q', '--depth', '1', 'origin', '%s:refs/remotes/origin/%s' % (BRANCH, BRANCH)],
                       cwd=ROOT, check=True)
        _fetched = True
    tmp = tempfile.mkdtemp()
    enc, mp3, out = (os.path.join(tmp, key + e) for e in ('.mp3.enc', '.mp3', '.wav'))
    with open(enc, 'wb') as f:
        f.write(subprocess.run(['git', 'show', 'origin/%s:tracks/%s.mp3.enc' % (BRANCH, key)], cwd=ROOT, check=True,
                               capture_output=True).stdout)
    key_env = dict(os.environ, TRACKS_KEY=''.join(os.environ['TRACKS_KEY'].split()))   # без пробелов и переносов из вставки
    subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-pass', 'env:TRACKS_KEY', '-in', enc, '-out', mp3],
                   check=True, env=key_env)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '2', '-ar', '44100', out], check=True)
    return out
