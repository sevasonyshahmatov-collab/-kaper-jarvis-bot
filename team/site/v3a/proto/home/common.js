/* Общий помощник трёх шаблонов главной: берёт те же данные, что index.html (window.JVL из assets/lines.js), и отдаёт готовый список матчей. */
(()=>{
'use strict';
const J=window.JVL,R=window.JV_ROOT??'../../../';
const LG={khl:'КХЛ',nhl:'НХЛ',epl:'АПЛ',laliga:'Ла Лига',seriea:'Серия А',bundesliga:'Бундеслига',ligue1:'Лига 1',rpl:'РПЛ',ucl:'Лига чемпионов',uel:'Лига Европы'};
const isH=m=>m.lg==='khl'||m.lg==='nhl';
/* страница матча, как в seo/build_match.py: <лига>/<дата>-<хозяева>-<гости>/index.html (НХЛ — английские названия городов) */
const NHL_EN={"nhl_car":"carolina","nhl_edm":"edmonton","minnesota":"minnesota","nhl_bos":"boston","nhl_vgk":"vegas","nhl_mtl":"montreal","nhl_tbl":"tampa-bay","nhl_njd":"new-jersey","nhl_uta":"utah","dallas":"dallas","nhl_col":"colorado","nhl_ott":"ottawa","nhl_fla":"florida","nhl_tor":"toronto","nhl_sea":"seattle","nhl_buf":"buffalo","nhl_nsh":"nashville","nhl_nyr":"rangers","nhl_det":"detroit","nhl_wsh":"washington","nhl_nyi":"islanders","nhl_stl":"st-louis","nhl_ana":"anaheim","nhl_sjs":"san-jose","nhl_cgy":"calgary","nhl_wpg":"winnipeg","nhl_cbj":"columbus","nhl_pit":"pittsburgh","nhl_phi":"philadelphia","nhl_lak":"los-angeles","nhl_chi":"chicago","nhl_van":"vancouver"};
const slug=(m,id)=>m.lg==='nhl'?(NHL_EN[id]||id.replace(/^nhl_/,'').replace(/_/g,'-')):id.replace(/_/g,'-');
const pageOf=m=>`${R}${m.lg}/${m.t.slice(0,10)}-${slug(m,m.h)}-${slug(m,m.a)}/index.html`;
const atMs=t=>Date.parse(String(t).replace(' ','T')+':00+03:00');
const ymd=d=>d.toISOString().slice(0,10);
const msk=()=>new Date(Date.now()+3*3600e3);
const pl=(n,a,b,c)=>{const k=n%100,j=n%10;return k>10&&k<20?c:j===1?a:j>1&&j<5?b:c};
function all(){
 if(!J)return [];
 const raw=((J.TD&&J.TD.matches)||[]).filter(m=>m.t&&m.h&&m.a);
 const now=Date.now(),fresh=raw.filter(m=>atMs(m.t)>now-2*3600e3),src=fresh.length?fresh:raw;
 const today=ymd(msk()),tm=ymd(new Date(Date.parse(today+'T00:00:00Z')+864e5));
 return src.map(m=>{
  const ln=J.L[m.key],md=J.M[m.key],hockey=isH(m);
  const pr=md?[md.p1,md.x,md.p2]:null;
  let bi=-1;if(pr)pr.forEach((p,i)=>{if(p!=null&&(bi<0||p>pr[bi]))bi=i});
  const d=m.t.slice(0,10);
  return Object.assign({},m,{hockey,ln,md,pr,bi,
   best:pr?pr[bi]:0,
   who:bi===0?m.hn:bi===2?m.an:'ничья',
   hm:m.t.slice(11,16),
   day:d===today?'сегодня':d===tm?'завтра':J.ddmm(m.t),
   lgn:LG[m.lg]||m.lg,
   hc:`${R}assets/${hockey?'em':'fc'}/${encodeURIComponent(m.h)}.webp`,
   ac:`${R}assets/${hockey?'em':'fc'}/${encodeURIComponent(m.a)}.webp`,
   page:pageOf(m),
   href:`${R}${hockey?'hockey':'football'}/index.html#matches`});
 }).sort((a,b)=>atMs(a.t)-atMs(b.t));
}
/* матч дня: ближайшие сутки, есть расчёт модели и линия; берём самый уверенный */
function hero(list){
 const pool=list.filter(m=>m.md&&m.ln);const base=pool.length?pool:list.filter(m=>m.md);
 if(!base.length)return list[0]||null;
 const t0=atMs(base[0].t),near=base.filter(m=>atMs(m.t)-t0<30*3600e3);
 return near.reduce((a,b)=>b.best>a.best?b:a);
}
const dateStr=()=>msk().toLocaleDateString('ru-RU',{weekday:'long',day:'numeric',month:'long',timeZone:'UTC'}).replace(/^./,c=>c.toUpperCase());
window.HOME={J,R,all,hero,dateStr,pl,isH,esc:J?J.esc:String,pct:v=>J.p0(v),f2:v=>J.f2(v),
 upd:()=>{const b=J&&J.TD&&J.TD.built;return b?`данные от ${J.ddmm(b)}, ${b.slice(11,16)} МСК`:''}};
})();
