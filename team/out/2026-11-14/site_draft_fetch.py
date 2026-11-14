# Достать снимки черновика сайта из ветки-черновика (картинки в team/out не храним) -> out/site_1411/
import os, subprocess
os.makedirs('out/site_1411', exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'claude/site-v3a-draft-1411'], check=True)
for n in ('lc_variants.jpg', 'profiles_before_after.jpg'):
    data = subprocess.run(['git', 'show', 'FETCH_HEAD:docs/handoff/site_1411/' + n], check=True, capture_output=True).stdout
    open('out/site_1411/' + n, 'wb').write(data)
    print('ok', n, len(data))
