/* JARVIS v3a — цвета свитеров клубов НХЛ и КХЛ для страниц игроков (владелец 06.11: «разукрасим игроков в цвета клубов»).
   JERSEY[ключ эмблемы] = [основной тёмный/насыщенный, второй цвет (рукав, акцент), кромка (тонкая полоса)].
   Ключи как у assets/em/<ключ>.webp: КХЛ — dinamo_msk…, НХЛ — nhl_edm, minnesota, dallas.
   JV_JERSEY.vars(ключ) -> строка CSS-переменных для карточки/шапки: --kb основной, --kbm конец градиента, --ks второй, --kt кромка,
   --ko цвет текста (белый или тёмный — что контрастнее на фоне, ≥4.5), --ko2 приглушённый текст (≥4.5), --kx акцент для заливок и контуров (≥3 к фону),
   --kp подложка портрета, --kpo текст на ней. JV_JERSEY.key(лига, аббревиатура) — ключ по аббревиатуре НХЛ (EDM → nhl_edm). */
window.JV_JERSEY=(()=>{
const J={
 /* КХЛ */
 dinamo_msk:['#0a3a8f','#6f9bf0','#ffffff'],
 avangard:['#c8102e','#161616','#ffffff'],
 amur:['#f26522','#1b2a4a','#ffffff'],
 cska:['#b5121b','#1b3a8c','#ffffff'],
 spartak:['#c8141a','#f4f1ea','#7a0c10'],
 torpedo:['#1e3a93','#e30613','#ffffff'],
 sibir:['#1b325a','#8fb0e0','#ffffff'],
 lokomotiv:['#c4101f','#1b4da1','#ffffff'],
 traktor:['#1c1c1c','#d9d9d9','#ffffff'],
 metallurg:['#1b2a5a','#f5a623','#ffffff'],
 salavat:['#1f2a8a','#d4af37','#ffffff'],
 neftekhimik:['#1c3f6e','#c82832','#ffffff'],
 dinamo_minsk:['#1768ae','#9fd3f5','#ffffff'],
 akbars:['#00663c','#e30613','#ffffff'],
 severstal:['#2f2f2f','#ffcc00','#ffffff'],
 ska:['#c8161d','#1f4e9e','#ffffff'],
 barys:['#0f3a6b','#2aa7b8','#ffffff'],
 avtomobilist:['#c4101a','#141414','#ffffff'],
 admiral:['#14203f','#c8a96a','#ffffff'],
 lada:['#0f4c81','#c8d2e1','#ffffff'],
 sochi:['#142850','#f5b400','#ffffff'],
 shanghai:['#ff5a00','#161616','#ffd36a'],
 /* НХЛ */
 nhl_ana:['#15110e','#f47a38','#b9975b'],
 nhl_bos:['#171717','#ffb81c','#ffffff'],
 nhl_buf:['#002654','#fcb514','#ffffff'],
 nhl_cgy:['#b20e24','#f1be48','#ffffff'],
 nhl_car:['#c00000','#111111','#ffffff'],
 nhl_chi:['#cf0a2c','#111111','#ffffff'],
 nhl_col:['#6f263d','#236192','#c5ccd1'],
 nhl_cbj:['#002654','#ce1126','#a4a9ad'],
 dallas:['#006847','#8f8f8c','#ffffff'],
 nhl_det:['#ce1126','#f1f1f1','#7a0c18'],
 nhl_edm:['#ff4c00','#041e42','#ffffff'],
 nhl_fla:['#c8102e','#041e42','#b9975b'],
 nhl_lak:['#111111','#a2aaad','#ffffff'],
 minnesota:['#154734','#a6192e','#f3ead2'],
 nhl_mtl:['#af1e2d','#192168','#ffffff'],
 nhl_nsh:['#041e42','#ffb81c','#ffffff'],
 nhl_njd:['#ce1126','#111111','#ffffff'],
 nhl_nyi:['#00539b','#f47d30','#ffffff'],
 nhl_nyr:['#0038a8','#ce1126','#ffffff'],
 nhl_ott:['#c52032','#111111','#c2912c'],
 nhl_phi:['#f74902','#111111','#ffffff'],
 nhl_pit:['#101010','#fcb514','#ffffff'],
 nhl_sjs:['#006d75','#111111','#ea7200'],
 nhl_sea:['#001628','#99d9d9','#e9072b'],
 nhl_stl:['#002f87','#fcb514','#ffffff'],
 nhl_tbl:['#002868','#ffffff','#8e9aa5'],
 nhl_tor:['#00205b','#e8edf5','#6aa0ff'],
 nhl_uta:['#0e0e12','#6cace4','#ffffff'],
 nhl_van:['#00205b','#00843d','#ffffff'],
 nhl_vgk:['#333f42','#b4975a','#c8102e'],
 nhl_wsh:['#c8102e','#041e42','#ffffff'],
 nhl_wpg:['#041e42','#4f81c7','#a2aaad']
};
const rgb=h=>{const n=parseInt(h.slice(1),16);return[n>>16,n>>8&255,n&255]};
const hex=a=>'#'+a.map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('');
const mix=(a,b,t)=>{const x=rgb(a),y=rgb(b);return hex(x.map((v,i)=>v+(y[i]-v)*t))};
const lum=h=>{const[r,g,b]=rgb(h).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*r+.7152*g+.0722*b};
const cr=(a,b)=>{const x=lum(a),y=lum(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
const DK='#0b1222',WH='#ffffff';
/* ключ по аббревиатуре НХЛ */
const key=(lg,ab)=>{ab=String(ab||'').replace(/[^\w-]/g,'');return lg==='khl'?ab:ab==='MIN'?'minnesota':ab==='DAL'?'dallas':'nhl_'+ab.toLowerCase()};
function calc(k){
 const c=J[k];if(!c)return null;
 const b=c[0],s=c[1],t=c[2],lt0=cr(DK,b)>cr(WH,b),bm=lt0?mix(b,WH,.14):mix(b,s,.15);
 /* текст: белый или тёмный — что контрастнее на самом худшем из двух фонов градиента */
 const worst=x=>Math.min(cr(x,b),cr(x,bm)),ko=worst(WH)>=worst(DK)?WH:DK;
 /* приглушённый: смешиваем с фоном, пока контраст не опустится до 5 */
 let ko2=ko;for(let i=1;i<=8;i++){const m=mix(ko,b,i*.05);if(worst(m)>=5)ko2=m;else break}
 /* акцент: второй цвет, если читается на основном; иначе кромка; иначе текст */
 const kx=cr(s,b)>=3?s:cr(t,b)>=3?t:ko;
 /* подложка портрета: второй цвет, а если он сливается с карточкой — кромка */
 const kp=cr(s,b)>=1.1?s:t;
 return{b,bm,s,t,ko,ko2,kx,kp,kpo:cr(WH,kp)>=cr(DK,kp)?WH:DK,lt:ko===DK};
}
const vars=k=>{const v=calc(k);if(!v)return'';
 return`--kb:${v.b};--kbm:${v.bm};--ks:${v.s};--kt:${v.t};--ko:${v.ko};--ko2:${v.ko2};--kx:${v.kx};--kp:${v.kp};--kpo:${v.kpo}`};
/* акцент для страницы на фоне bg (#rrggbb): самый «цветной» из основного/второго/кромки, что читается на фоне (≥3.2); иначе осветляем */
const pick=(k,bg)=>{const c=J[k];if(!c)return null;const chroma=h=>{const a=rgb(h);return Math.max(...a)-Math.min(...a)};
 for(const t of[0,.15,.3,.45,.6]){const ok=c.map(x=>mix(x,WH,t)).filter(x=>cr(x,bg)>=3.2&&chroma(x)>45);
  if(ok.length){const g=ok.sort((a,b)=>chroma(b)-chroma(a))[0];return{g,go:cr(WH,g)>=cr(DK,g)?WH:DK}}}
 return{g:WH,go:DK}};
return{J,calc,vars,key,pick,cr,mix,lum}
})();
