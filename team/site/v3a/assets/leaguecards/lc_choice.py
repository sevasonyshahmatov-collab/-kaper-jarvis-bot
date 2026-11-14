# -*- coding: utf-8 -*-
"""Страница выбора фото для карточек лиг (черновик 14.11): vote/leaguecards.html (noindex) + коллаж cand/choice-collage.jpg.
Варианты — choice.json [{code, lg, cut, player, club, note}], автор и лицензия — из cand/hqmeta.json (lc_hq.py).
Вырезка копируется в assets/leaguecards/var/<cut>.webp (то, что увидит сайт)."""
import json, os, shutil, html
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
meta = json.load(open(os.path.join(H, 'cand', 'hqmeta.json'), encoding='utf-8'))
ch = json.load(open(os.path.join(H, 'choice.json'), encoding='utf-8'))
os.makedirs(os.path.join(H, 'var'), exist_ok=True)
e = html.escape
cards, notes = [], []
for v in ch['variants']:
    m = meta.get(v['cut']) if v.get('cut') else None
    photo = None
    if m:
        shutil.copyfile(os.path.join(H, 'cand', 'cut-%s.webp' % v['cut']), os.path.join(H, 'var', '%s.webp' % v['cut']))
        photo = '../assets/leaguecards/var/%s.webp' % v['cut']
    cards.append({'code': v['code'], 'lg': v['lg'], 'photo': photo, 'cls': v.get('cls', ''), 'club': v['club'], 'player': v['player'],
                  'credit': ('%s, %s' % (m['author'], m['license'])) if m else v.get('credit', ''), 'page': m['page'] if m else '',
                  'src': m['src'] if m else '', 'cutsz': m['cut'] if m else '', 'note': v.get('note', '')})
js = json.dumps(cards, ensure_ascii=False)
page = '''<!doctype html>
<html lang="ru" data-sport="hockey"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><title>Выбор фото для карточек лиг — черновик</title>
<link rel="stylesheet" href="../assets/v3a.css"><link rel="stylesheet" href="../assets/leaguecards/lc.css">
<style>
body{background:var(--paper);color:var(--ink)}
.wrap{max-width:1180px;margin:0 auto;padding:24px 16px 80px}
h1{font:800 clamp(26px,4vw,40px)/1.1 var(--display);text-transform:none;margin:0 0 12px}
.lead{font:500 16px/1.5 var(--display);color:var(--ink-2);max-width:70ch;margin:0 0 8px}
h2{font:800 clamp(22px,3vw,30px)/1.1 var(--display);margin:48px 0 16px;text-transform:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:72px 28px;padding-top:56px}
.v{display:grid;gap:14px;align-content:start}
.v .lc-deck{display:block}
.cap{text-align:center;font:600 14px/1.45 var(--display);color:var(--ink-2)}
.cap b{display:block;font:900 22px/1.1 var(--display);color:var(--ink);margin-bottom:4px}
.cap a{color:inherit}
.cap i{display:block;font-style:normal;color:var(--ink-3);font-size:13px}
.ask{margin:32px 0 0;padding:18px 20px;border-radius:12px;background:var(--card);border:1px solid var(--rule-2);font:600 16px/1.5 var(--display)}
</style></head><body>
<main class="wrap">
<h1>Карточки лиг в «Хоккее»: какого игрока ставим</h1>
<p class="lead">Все фото — со свободной лицензией (Wikimedia Commons), автор подписан под карточкой, как на сайте. Ответьте в боте одним словом,
например: <b>КХЛ-2, НХЛ-1</b>. Пока выбора нет, на странице «Хоккей» в черновике стоит вариант, отмеченный «сейчас в черновике».</p>
%NOTE%
<div id="out"></div>
<p class="ask">Ответ: «КХЛ-…, НХЛ-…» (и «Главная-…» для карточки «Хоккей» на главной, если меняем фото Макдэвида).</p>
</main>
<script src="../assets/leaguecards/lc.js"></script>
<script>
const V=%JS%,SEC=%SEC%;
const out=document.getElementById('out');
for(const [lg,title] of SEC){
 const vs=V.filter(v=>v.lg===lg);if(!vs.length)continue;
 const h=document.createElement('h2');h.textContent=title;out.appendChild(h);
 const g=document.createElement('div');g.className='grid';out.appendChild(g);
 vs.forEach(v=>{const w=document.createElement('div');w.className='v';const d=document.createElement('div');d.className='lc-deck';w.appendChild(d);
  const id=lg==='home'?'nhl':lg;
  LeagueCards.mount(d,[{id,name:id==='khl'?'КХЛ':'НХЛ',cnt:'Вариант '+v.code,href:'#',logo:'../assets/lg/'+id+'.webp',club:v.club,photo:v.photo,photoCls:v.cls,cols:8,pl:()=>'клубов',clubs:[]}]);
  const c=document.createElement('p');c.className='cap';
  c.innerHTML=`<b>${v.code}</b>${v.player}<br>${v.page?`Фото: <a href="${v.page}" target="_blank" rel="noopener">${v.credit}</a>`:v.credit}${v.src?`<i>исходник ${v.src} px · вырезка ${v.cutsz} px</i>`:''}${v.note?`<i>${v.note}</i>`:''}`;
  w.appendChild(c);g.appendChild(w)})}
</script>
</body></html>'''
page = page.replace('%JS%', js).replace('%SEC%', json.dumps(ch['sections'], ensure_ascii=False)).replace('%NOTE%', ch.get('note_html', ''))
os.makedirs(os.path.join(ROOT, 'vote'), exist_ok=True)
open(os.path.join(ROOT, 'vote', 'leaguecards.html'), 'w', encoding='utf-8').write(page)
print('ok', len(cards))
