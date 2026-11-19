/* JARVIS v3a — блок «Где закончат сезон» на странице хоккейной лиги (hockey/league.html?lg=<khl|nhl>, #odds; владелец 19.11).
   Данные: hockey/data/odds_<лига>.json (hockey/odds_build.py — 10 000 розыгрышей оставшихся матчей регулярки). Эмблемы и названия —
   assets/data/teams-lite.js. Это расчёт по шайбам сезона, без кэфов и ставок. */
(()=>{
'use strict';
const box=document.getElementById('oddsBox');if(!box)return;
const LG=(new URLSearchParams(location.search).get('lg')||'').toLowerCase();
const sec=document.getElementById('odds');
if(!/^(khl|nhl)$/.test(LG)){if(sec){sec.hidden=true;sec.removeAttribute('data-zone')}return}
const T=(window.JV_TEAMS||{teams:{}}).teams;
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const plural=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
const theme=(new URLSearchParams(location.search).get('theme')||'');
const tq=/^(arena|a|b|c)$/.test(theme)?`&theme=${theme}`:'';
const thref=s=>`../team/index.html?id=${encodeURIComponent(s)}${tq}`;
const em=s=>`<img class="em" src="../assets/em/s/${esc(s)}.webp" alt="" loading="lazy" width="64" height="64">`;
/* проценты: целые; почти наверняка — «>99», почти никогда — «<1», ни разу — «—» */
const pc=v=>v>=99.5?(v>=100?'100':'>99'):v>=0.5?String(Math.round(v)):v>0?'<1':'—';
const fx=v=>(+v).toFixed(0);
const MON=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const when=s=>{const m=/^(\d{4})-(\d\d)-(\d\d) (\d\d:\d\d)/.exec(s||'');return m?`${+m[3]} ${MON[+m[2]-1]} в ${m[4]} МСК`:''};

function draw(D){
 const confs=D.confs||[];let conf=confs[0],view='main';
 const KHL=LG==='khl';
 box.innerHTML=`
  <div class="sec-head" data-rv><h2>Где закончат сезон</h2></div>
  <p class="odlead" data-rv>Шансы каждого клуба на плей-офф и на каждое место в конференции. Мы ${D.sims.toLocaleString('ru-RU')} раз разыграли
   оставшиеся ${D.left_games} ${plural(D.left_games,'матч','матча','матчей')} регулярки и посчитали, как часто клуб оказывался на каждом месте.</p>
  <div class="odbar" data-rv>
   <div class="lgsw tabs" role="tablist" id="odConf" aria-label="Конференция">${confs.map(c=>`<button class="tab" role="tab" type="button" data-c="${esc(c)}" aria-selected="${c===conf}">${esc(c)}</button>`).join('')}</div>
   <div class="lgsw tabs" role="tablist" id="odView" aria-label="Вид"><button class="tab" role="tab" type="button" data-v="main" aria-selected="true">Главное</button><button class="tab" role="tab" type="button" data-v="pl" aria-selected="false">По местам</button></div>
  </div>
  <div id="odBody"></div>
  <ul class="lkey odkey" id="odKey"></ul>
  <details class="odhow"><summary>Как считали</summary>
   <p>Сила атаки и обороны клуба — шайбы за игру в этом сезоне. Пока игр мало, цифры подтягиваем к среднему по лиге, чтобы одна
    крупная победа не делала из клуба фаворита. Учитываем, что дома играют чуть лучше. Сила клуба в каждом розыгрыше немного
    «плавает» — мы не знаем её точно. Ничья превращается в овертайм или буллиты: победителю 2 очка, проигравшему 1.</p>
   <p>В плей-офф выходят ${esc(D.po_rule)}. При равенстве очков выше клуб с бо́льшим числом побед.
    «Очки к концу» — среднее по всем розыгрышам; в скобках — коридор, в который клуб попадал в 8 случаях из 10.</p>
   ${D.full_schedule?'':'<p>Полного календаря КХЛ до конца регулярки у нас пока нет: матчи после ближайших трёх недель разыграны против случайных соперников из лиги.</p>'}
   <p>Это расчёт по цифрам, а не прогноз и не гарантия. Обновлено ${esc(when(D.built))}.</p></details>`;
 const body=document.getElementById('odBody'),key=document.getElementById('odKey');
 const rows=()=>D.teams.filter(t=>t.conf===conf);
 const club=t=>`<a href="${thref(t.id)}">${em(t.id)}<span>${esc((T[t.id]||{}).name||t.name)}</span></a>`;
 const bar=v=>`<span class="odp"><b>${pc(v)}${v>0&&v<99.5&&v>=0.5?'<small>%</small>':''}</b><i aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,v))}%"></i></i></span>`;
 const main=()=>{const R=rows();
  body.innerHTML=`<div class="tabscroll odtbl"><table class="ltab odmain"><thead><tr><th>#</th><th>Клуб</th><th title="Очки сейчас">О</th><th>Очки к&nbsp;концу</th><th>Плей-офф</th><th class="hm">1-е место</th></tr></thead><tbody>${R.map((t,i)=>
   `<tr class="${t.po>=50?'z1':''}"><td>${i+1}</td><td>${club(t)}</td><td class="pt">${t.pts}</td><td class="xp"><b>${fx(t.xp)}</b><small>${t.lo}–${t.hi}</small></td><td>${bar(t.po)}</td><td class="hm c1">${pc(t.c1)}${t.c1>=0.5&&t.c1<99.5?'<small>%</small>':''}</td></tr>`).join('')}</tbody></table></div>`;
  key.innerHTML=`<li><i style="background:#0d7a48"></i>Скорее в плей-офф, чем нет</li><li>О — очки сейчас; % — доля розыгрышей</li>`};
 const places=()=>{const R=rows(),n=R.length?R[0].pl.length:0,cut=KHL?8:0;
  const cell=(v,i)=>{const a=Math.round(Math.min(1,v/60)*100);return `<td class="h${v>=40?' hi':''}${cut&&i===cut-1?' cut':''}" style="--a:${a}%">${v>=0.5?Math.round(v):v>0?'·':''}</td>`};
  body.innerHTML=`<div class="tabscroll odtbl odpl"><table class="ltab odplace" style="--n:${n}"><thead><tr><th>Клуб</th>${Array.from({length:n},(_,i)=>`<th class="${cut&&i===cut-1?'cut':''}">${i+1}</th>`).join('')}</tr></thead><tbody>${R.map(t=>
   `<tr><td>${club(t)}</td>${t.pl.map(cell).join('')}</tr>`).join('')}</tbody></table></div>`;
  key.innerHTML=`<li>Цифра — шанс занять это место в конференции, %. Чем ярче клетка, тем выше шанс</li>${cut?'<li><i style="background:#0d7a48"></i>Черта — граница плей-офф (8 мест)</li>':'<li>В НХЛ путёвки дают и по дивизионам, поэтому граница плей-офф по местам в конференции не сплошная</li>'}`};
 const render=()=>view==='main'?main():places();
 const sw=(id,attr,set)=>document.getElementById(id).addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b||b.getAttribute('aria-selected')==='true')return;
  document.getElementById(id).querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected',x===b));set(b.getAttribute(attr));render()});
 sw('odConf','data-c',v=>conf=v);sw('odView','data-v',v=>view=v);
 render();
 if(window.JV&&JV.reveal)JV.reveal();
 if(location.hash==='#odds')setTimeout(()=>sec&&sec.scrollIntoView(),80);
}
/* без JVD: в черновике файл лежит в draft/hockey/data/ (на живом сайте его ещё нет) */
fetch('data/odds_'+LG+'.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(draw)
 .catch(e=>{console.error(e);if(sec){sec.hidden=true;sec.removeAttribute('data-zone')}});
})();
