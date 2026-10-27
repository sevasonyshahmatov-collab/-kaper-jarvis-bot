# Выгрузка таблицы владельца пометками ::notice:: (логи Actions из облака не читаются).
import csv, io, re, sys, urllib.parse, requests
ID = '1irgDnokNe9RMTrb_7Pu2tH9XpVHu5tFpdgInFj9IJIs'
h = requests.get('https://docs.google.com/spreadsheets/d/%s/htmlview' % ID, timeout=60)
print('htmlview', h.status_code, len(h.text))
names = re.findall(r'name: "((?:[^"\\]|\\.)*)", pageUrl: "[^"]*gid=(\d+)', h.text) or \
        re.findall(r'<li[^>]*id="sheet-button-(\d+)"[^>]*><a[^>]*>([^<]+)</a>', h.text)
names = [(n, g) if not n.isdigit() else (g, n) for n, g in names]
print('::notice title=SHEETS::' + ' | '.join('%s=%s' % (n, g) for n, g in names)[:3900] or 'none; status %d' % h.status_code)
budget = 9
for n, g in names:
    if budget == 0:
        break
    r = requests.get('https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=%s' % (ID, g), timeout=60)
    if r.status_code != 200:
        continue
    rows = [[c.strip()[:18] for c in row[:12]] for row in csv.reader(io.StringIO(r.content.decode('utf-8', 'replace')))]
    rows = [row for row in rows if any(row)][:30]
    txt = '\n'.join(';'.join(row) for row in rows).replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    print('::notice title=S %s::%s' % (n[:40], txt[:3800]))
    budget -= 1
