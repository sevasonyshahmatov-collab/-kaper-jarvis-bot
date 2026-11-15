# Достать снимки и видео черновика сайта из ветки-черновика (файлы в team/out не храним) -> out/site_1511/
import os, subprocess
os.makedirs('out/site_1511', exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'claude/site-v3a-draft-1411'], check=True)
for n in ('ba_1_liga_khl_390.jpg', 'ba_2_profil_grafik_390.jpg', 'ba_3_rynki_futbolist_390.jpg', 'ba_4_klub_match_390.jpg',
          'ba_5_glavnaya_390.jpg', 'profile_anim_390.mp4'):
    data = subprocess.run(['git', 'show', 'FETCH_HEAD:docs/handoff/site_1511/' + n], check=True, capture_output=True).stdout
    open('out/site_1511/' + n, 'wb').write(data)
    print('ok', n, len(data))
