# -*- coding: utf-8 -*-
"""Треки владельца роликов 12.10 (slx, kizaru, vace — «Состав»; rotten — «Сравнение»; north — «Терминал»; jefe — «Карточка»)
владельцу в личку бота: расшифровать mp3 из ветки claude/team-dev-tracks-v2 (секрет TRACKS_KEY) в out/tracks/. Только владельцу."""
import os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BRANCH = 'claude/team-dev-tracks-v2'
OUT = os.path.join(ROOT, 'out', 'tracks')
os.makedirs(OUT, exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth', '1', 'origin', '%s:refs/remotes/origin/%s' % (BRANCH, BRANCH)], cwd=ROOT, check=True)
env = dict(os.environ, TRACKS_KEY=''.join(os.environ.get('TRACKS_KEY', '').split()))
for key in ('slx', 'kizaru', 'vace', 'rotten', 'north', 'jefe'):
    enc = os.path.join(OUT, key + '.mp3.enc')
    with open(enc, 'wb') as f:
        f.write(subprocess.run(['git', 'show', 'origin/%s:tracks/%s.mp3.enc' % (BRANCH, key)], cwd=ROOT, check=True, capture_output=True).stdout)
    subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-pass', 'env:TRACKS_KEY', '-in', enc,
                    '-out', os.path.join(OUT, key + '.mp3')], check=True, env=env)
    os.remove(enc)
    print('трек готов:', key, flush=True)
