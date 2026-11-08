/* Образец единого стиля: строка матча, таблица, показатели, лиги, палитра — на настоящих данных (today/lines/model, teams-lite). */
(()=>{
'use strict';
const H=window.HOME,$=id=>document.getElementById(id),R='../../';
const e=H?H.esc:String,pc=v=>H.pct(v),f2=v=>H.f2(v);

/* строка матча */
const all=H&&H.J?H.all():[];
let L=all.filter(m=>m.hockey).slice(0,3).concat(all.filter(m=>!m.hockey).slice(0,3)).sort((a,b)=>a.t<b.t?-1:1);
const OUT=['П1','Х','П2'];
function row(m){
 const ln=m.ln,pr=m.pr,k=ln?[ln.p1,ln.x,ln.p2]:null,fav=k?k.indexOf(Math.min(...k.filter(Boolean))):-1;
 const bar=pr?`<div class="pbar"><div class="b">${pr.map((p,i)=>`<i class="${i===m.bi?'on':''}" style="flex:${Math.max(p||0,.05)}"></i>`).join('')}</div>
   <div class="t">${pr.map((p,i)=>i===m.bi?`<b>${OUT[i]} ${pc(p)}%</b>`:`<span>${OUT[i]} ${pc(p)}%</span>`).join('')}</div></div>`:'<div class="pbar"><span class="small">расчёт скоро</span></div>';
 const kq=k?`<div class="kq">${k.map((v,i)=>v?`<i class="${i===fav?'fav':''}"><small>${OUT[i]}</small>${f2(v)}</i>`:'').join('')}</div>`:'<div></div>';
 return `<li><a class="mrow ${m.hockey?'hk':'fb'}" href="${m.page||m.href}" data-sp="${m.hockey?'hk':'fb'}">
  <time>${m.hm}<small>${e(m.lgn)}</small></time>
  <div class="tms"><span class="tm"><img src="${m.hc}" alt="" loading="lazy">${'<span>'+e(m.hn)+'</span>'}</span><span class="tm"><img src="${m.ac}" alt="" loading="lazy"><span>${e(m.an)}</span></span></div>
  ${bar}${kq}</a></li>`;
}
const rows=$('rows');
function draw(f){const list=f==='all'?L:L.filter(m=>(m.hockey?'hk':'fb')===f);rows.innerHTML=list.length?list.map(row).join(''):'<li class="small" style="padding:16px">Матчей нет</li>'}
draw('all');
$('rchips').addEventListener('click',ev=>{const b=ev.target.closest('.chip');if(!b)return;$('rchips').querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x===b));draw(b.dataset.f)});

/* таблица и показатели: лидер конференции КХЛ «Восток» */
const T=(window.JV_TEAMS||{}).teams||{};
const conf=Object.entries(T).filter(([,t])=>t.lg==='khl'&&t.conf==='Восток').sort((a,b)=>a[1].place-b[1].place).slice(0,6);
if(conf.length){
 $('tblh').textContent='КХЛ · Восток';
 $('tbl').innerHTML=`<thead><tr><th>#</th><th>Клуб</th><th class="r">И</th><th class="hs">Форма</th><th class="r">О</th></tr></thead><tbody>${conf.map(([id,t],i)=>`<tr class="${i<1?'top':''}">
  <td class="pl">${t.place}</td><td><span class="cl"><img src="${R}assets/em/${id}.webp" alt="" loading="lazy">${e(t.name)}</span></td><td class="r num">${t.gp}</td>
  <td class="hs"><span class="form">${(t.form||'').split('').slice(-5).map(c=>`<i class="${c==='В'?'w':'l'}">${c}</i>`).join('')}</span></td><td class="r p num">${t.pts}</td></tr>`).join('')}</tbody>`;
 const [id,t]=conf[0],ax=(window.JV_TEAMS.axes||[]),f1=v=>v.toFixed(2).replace('.',',');
 $('sth').textContent=t.name;
 const tile=(l,v,u,a,s)=>`<div class="st"><span class="l">${l}</span><b class="v num">${v}<small>${u}</small></b>${a!=null?`<div class="bar"><i style="width:${a}%"></i></div><div class="s">${s} — <b>${a}</b> из 100 в КХЛ</div>`:''}</div>`;
 $('stats').innerHTML=tile('Забивает за игру',f1(t.gf/t.gp),'',t.axes[0],ax[0]||'Атака')+tile('Пропускает за игру',f1(t.ga/t.gp),'',t.axes[1],ax[1]||'Защита')
  +tile('Вратари: отражённые',(t.raw[2]*100).toFixed(1).replace('.',','),'%',t.axes[2],ax[2]||'Вратари')+tile('Голы в большинстве за игру',f1(t.raw[3]),'',t.axes[3],ax[3]||'Большинство');
}

/* лиги */
const LG=[['khl','КХЛ','hk'],['nhl','НХЛ','hk'],['epl','АПЛ','fb'],['laliga','Ла Лига','fb'],['seriea','Серия А','fb'],['bundesliga','Бундеслига','fb'],['ligue1','Лига 1','fb'],['rpl','РПЛ','fb'],['ucl','Лига чемпионов','fb']];
const cnt=lg=>((H&&H.J&&H.J.TD.matches)||[]).filter(m=>m.lg===lg&&m.t.slice(0,10)===new Date(Date.now()+3*3600e3).toISOString().slice(0,10)).length;
$('lgs').innerHTML=LG.map(([k,n,s])=>{const c=cnt(k);return `<a class="lg ${s}" href="#"><img src="${R}assets/lg/${k}.webp" alt="" loading="lazy"><b>${n}</b><span>${c?c+' '+H.pl(c,'матч','матча','матчей')+' сегодня':'сегодня матчей нет'}</span></a>`}).join('');

/* палитра */
const SW=[['--bg','Фон','основа всех страниц'],['--surface','Карточка','блоки и строки'],['--line-2','Линия','рамки, пустые полосы'],['--ink','Текст','заголовки и цифры'],['--ink-3','Подпись','второстепенное'],
 ['--signal','Жёлтый','только кнопки и выбранный кэф'],['--hk','Хоккей','полоса, разметка «лёд»'],['--fb','Футбол','полоса, разметка «газон»'],['--win','Победа','форма, итоги'],['--loss','Поражение','форма, итоги']];
$('sw').innerHTML=SW.map(([v,n,d])=>`<div><i style="background:var(${v})"></i><b>${n}</b><span>${d}</span></div>`).join('');
})();
