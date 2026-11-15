# Снимки живого сайта из ветки-черновика (картинки в team/out не храним) -> out/site_now/
import os, subprocess
os.makedirs('out/site_now', exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'claude/site-v3a-draft-1411'], check=True)
ls = subprocess.run(['git', 'ls-tree', '--name-only', 'FETCH_HEAD', 'docs/handoff/site_now/'], check=True, capture_output=True, text=True).stdout.split()
for p in ls:
    data = subprocess.run(['git', 'show', 'FETCH_HEAD:' + p], check=True, capture_output=True).stdout
    open('out/site_now/' + os.path.basename(p), 'wb').write(data)
    print('ok', p, len(data))
