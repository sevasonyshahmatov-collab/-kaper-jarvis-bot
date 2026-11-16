/* JARVIS v3a — «Лучше, чем у N % игроков того же амплуа» (владелец 16.11, по образцу Opta Analyst / FBref).
   Данные: P.pc = [[ключ, значение, %]] в hockey/data/pp/<лига>/<id>.json (daily/split.py pct_ranks): доля нападающих
   (защитников) своей лиги с худшей цифрой; в выборке — от 5 матчей. Здесь — подписи, формат и отрисовка.
   JV_PCT.block(P)            — раздел профиля игрока (полосы по группам)
   JV_PCT.duel(PA,PB,na,nb)   — раздел «Сравнения»: два игрока, полосы навстречу друг другу */
(function(){
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mmss=s=>{s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const n1=d=>v=>(+v).toFixed(d).replace('.',',');
const K={ /* ключ: [подпись, формат, меньше — лучше] */
 ppg:['Очки за матч',n1(2)],gpg:['Голы за матч',n1(2)],apg:['Передачи за матч',n1(2)],p60:['Очки за 60 минут',n1(2)],
 spg:['Броски за матч',n1(1)],shp:['Реализация бросков',v=>n1(1)(v)+' %'],
 toi:['Время на льду за матч',mmss],pm:['Плюс-минус',v=>(v>0?'+':v<0?'−':'')+Math.abs(v)],pim:['Штраф за матч, мин',n1(1),1],
 hit:['Силовые приёмы за матч',n1(1)],blk:['Блоки бросков за матч',n1(1)],tk:['Отборы за матч',n1(2)],gv:['Потери за матч',n1(2),1],
 fo:['Вбрасывания',v=>n1(1)(v)+' %'],spd:['Макс. скорость',v=>n1(1)(v)+' км/ч'],shot:['Самый сильный бросок',v=>Math.round(v)+' км/ч'],
 dist:['Пробег за матч',v=>n1(1)(v)+' км']};
const GR=[['Атака',['ppg','gpg','apg','p60','spg','shp']],['Роль и дисциплина',['toi','pm','pim']],
 ['Без шайбы',['hit','blk','tk','gv','fo']],['Скорость и сила',['spd','shot','dist']]];
const tier=p=>p>=90?'t4':p>=70?'t3':p>=30?'t2':'t1';
const amp=pos=>pos==='D'?['защитников','защитник']:['нападающих','нападающий'];
const map=P=>{const m={};(P&&P.pc||[]).forEach(r=>m[r[0]]=r);return m};
const LGN={khl:'КХЛ',nhl:'НХЛ'};

function block(P,lg){const m=map(P);if(!Object.keys(m).length)return'';const[am]=amp(P.pos);
 const top=Object.values(m).filter(r=>r[2]>=70).sort((a,b)=>b[2]-a[2]).slice(0,3);
 const gr=GR.map(([h,ks])=>{const rs=ks.filter(k=>m[k]);if(!rs.length)return'';
  return `<div class="pc-g"><h3>${h}</h3><ul>${rs.map(k=>{const[,v,p]=m[k],[l,f]=K[k];
   return `<li class="${tier(p)}"><span class="pc-l">${esc(l)}</span><b class="pc-v">${esc(f(v))}</b><span class="pc-bar" aria-hidden="true"><i style="--p:${p}%"></i></span><b class="pc-p" aria-label="лучше, чем у ${p} процентов ${am}">${p}</b></li>`}).join('')}</ul></div>`}).join('');
 return `<section class="pp-sec pc-sec" id="s-pc" aria-labelledby="h-pc"><h2 id="h-pc">Против ${am} ${LGN[lg]||''}</h2>
  <p class="hint">Число справа — у скольких процентов ${am} лиги эта цифра хуже. 99 — лучший в лиге, 50 — середина. Считаем всех, кто сыграл от 5 матчей.</p>
  ${top.length?`<p class="pc-best">Сильнее всего: ${top.map(r=>`<span class="${tier(r[2])}">${esc(K[r[0]][0].toLowerCase())} <b>${r[2]}</b></span>`).join('')}</p>`:''}
  <div class="pc-gs">${gr}</div>
  <ul class="pc-key" aria-hidden="true"><li class="t4">90+ элита</li><li class="t3">70–89 выше среднего</li><li class="t2">30–69 средне</li><li class="t1">до 30 слабо</li></ul></section>`}

function duel(PA,PB,na,nb,cross){const a=map(PA),b=map(PB);
 const same=(PA.pos==='D')===(PB.pos==='D');
 const gr=GR.map(([h,ks])=>{const rs=ks.filter(k=>a[k]&&b[k]);if(!rs.length)return'';
  return `<div class="pd-g"><h3>${h}</h3>${rs.map(k=>{const[,va,pa]=a[k],[,vb,pb]=b[k],[l,f]=K[k],w=pa>pb?'a':pb>pa?'b':'';
   return `<div class="pd-r${w?' w-'+w:''}"><b class="pd-v a">${esc(f(va))}</b><span class="pd-bar a ${tier(pa)}"><em>${pa}</em><span><i style="--p:${pa}%"></i></span></span><span class="pd-l">${esc(l)}</span><span class="pd-bar b ${tier(pb)}"><span><i style="--p:${pb}%"></i></span><em>${pb}</em></span><b class="pd-v b">${esc(f(vb))}</b></div>`}).join('')}</div>`}).join('');
 if(!gr)return'';
 const[aa]=amp(PA.pos),[ab]=amp(PB.pos);
 return `<section class="cmp-g pd-sec"><h2><span>Против своего амплуа</span></h2>
  <p class="cmp-note">Полоса и число — у скольких процентов ${same?aa:'игроков своего амплуа'} ${cross?'своей лиги':'лиги'} цифра хуже: 99 — лучший, 50 — середина.${same?'':' Нападающий и защитник: каждый сравнивается со своими.'}</p>
  <div class="pd-hd"><span class="a">${na}</span><span class="b">${nb}</span></div>${gr}</section>`}

window.JV_PCT={block,duel};
})();
