# снимок «отступы было/стало» из ветки-черновика -> out/site_1411/
import os, subprocess
os.makedirs('out/site_1411', exist_ok=True)
subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'claude/site-v3a-draft-1411'], check=True)
d = subprocess.run(['git', 'show', 'FETCH_HEAD:docs/handoff/site_1411/padding_before_after.jpg'], check=True, capture_output=True).stdout
open('out/site_1411/padding_before_after.jpg', 'wb').write(d); print('ok', len(d))
