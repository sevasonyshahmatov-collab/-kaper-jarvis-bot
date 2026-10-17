# -*- coding: utf-8 -*-
"""Архив роликов (решение владельца 17.10: «все ролики нужно сохранять, хоть в каком виде»).

Каждый готовый ролик сжимается до 720×1280 (H.264, ~1 МБ) и кладётся в videos/архив/<папка>/<имя>.mp4 —
эта папка коммитится в репозиторий, поэтому ролики не теряются вместе с временной рабочей средой.

    python tools/video_archive.py <папка в архиве> <ролик.mp4> [<ролик.mp4> …] [--name <имя>]
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, 'videos', 'архив')


def archive(src, folder, name=None):
    name = name or os.path.splitext(os.path.basename(src))[0]
    for suf in ('_preview', '_с_музыкой'):
        if name.endswith(suf):
            name = name[:-len(suf)]
    dst = os.path.join(ARCH, folder, name + '.mp4')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-vf', 'scale=720:-2', '-c:v', 'libx264',
                    '-preset', 'slow', '-crf', '30', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', dst],
                   check=True)
    return dst


if __name__ == '__main__':
    args = sys.argv[1:]
    name = None
    if '--name' in args:
        i = args.index('--name')
        name = args[i + 1]
        del args[i:i + 2]
    folder, files = args[0], args[1:]
    for f in files:
        print(archive(f, folder, name if len(files) == 1 else None))
