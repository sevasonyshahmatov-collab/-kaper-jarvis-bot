/* JARVIS v3a — «Избранное» (этап B личного кабинета, без сервера). Общий скрипт: window.JVFav + звёздочка на страницах клубов.
   Хранение: localStorage, ключ jv_fav_v1 = ["h:cska","f:arsenal"] (h — хоккей, f — футбол; id как в data/search.json).
   Любое обращение к хранилищу в try/catch: без него звёздочка работает до закрытия страницы, а страница не ломается.
   Подключение: <script src="…/assets/fav.js" defer></script>. Любая кнопка <button class="favbtn" data-fav="h:cska"> оживает сама. */
(()=>{
if(window.JVFav)return;
const SRC=(document.currentScript&&document.currentScript.src)||new URL('assets/fav.js',location.href).href;
const KEY='jv_fav_v1',RX=/^[hf]:[a-z0-9_]{1,60}$/;
let mem=[];
const load=()=>{try{const a=JSON.parse(localStorage.getItem(KEY)||'[]');if(Array.isArray(a))mem=a.filter(x=>typeof x==='string'&&RX.test(x)).slice(0,60)}catch(e){}return mem};
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(mem))}catch(e){}};
const subs=[];
const emit=()=>{sync();subs.forEach(f=>{try{f(mem.slice())}catch(e){}})};
const key=(s,id)=>s+':'+id;
const F=window.JVFav={
  list:()=>load().map(k=>({s:k[0],id:k.slice(2)})),
  has:(s,id)=>load().includes(key(s,id)),
  toggle(s,id){const k=key(s,id);if(!RX.test(k))return false;load();const i=mem.indexOf(k);if(i<0){mem.unshift(k);mem=mem.slice(0,60)}else mem.splice(i,1);save();emit();return i<0},
  add(s,id){const k=key(s,id);if(!RX.test(k))return;load();if(!mem.includes(k)){mem.unshift(k);mem=mem.slice(0,60);save();emit()}},
  remove(s,id){load();const i=mem.indexOf(key(s,id));if(i>=0){mem.splice(i,1);save();emit()}},
  /* стереть всё, что сайт хранит у посетителя в этом браузере */
  clear(){mem=[];try{localStorage.clear()}catch(e){}try{sessionStorage.clear()}catch(e){}emit()},
  onchange(f){subs.push(f)},
  sync:()=>sync(),
  btn:(s,id,cls)=>`<button type="button" class="favbtn${cls?' '+cls:''}" data-fav="${s}:${id}" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.8l2.7 5.9 6.4.7-4.8 4.3 1.4 6.3L12 16.7l-5.7 3.3 1.4-6.3L2.9 9.4l6.4-.7z"/></svg><span></span></button>`
};
/* состояние всех кнопок страницы */
function sync(){
  document.querySelectorAll('.favbtn[data-fav]').forEach(b=>{
    const on=mem.includes(b.dataset.fav),t=b.querySelector('span'),nm=b.dataset.name||'клуб';
    b.setAttribute('aria-pressed',on?'true':'false');
    b.title=on?'Убрать из «Мой JARVIS»':'Добавить в «Мой JARVIS» — избранные клубы';
    b.setAttribute('aria-label',(on?'Убрать из избранного: ':'Добавить в избранное: ')+nm);
    if(t&&!b.classList.contains('favbtn-ico'))t.textContent=on?'В избранном':'В избранное';
  });
}
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('.favbtn[data-fav]');if(!b)return;e.preventDefault();e.stopPropagation();
  const k=b.dataset.fav;F.toggle(k[0],k.slice(2))});
addEventListener('storage',e=>{if(e.key===KEY||e.key===null){load();emit()}});
try{const l=document.createElement('link');l.rel='stylesheet';l.href=new URL('fav.css',SRC).href;document.head.appendChild(l)}catch(e){}

/* страницы клубов: хоккей team/index.html?id=…, футбол football/team.html?id=… — звёздочку ставим рядом с кнопкой «Получать прогнозы» */
(()=>{
  const p=location.pathname,m=/[?&]id=([a-z0-9_]+)/i.exec(location.search);if(!m)return;
  const s=/\/team\/(index\.html)?$/.test(p)?'h':/\/football\/team\.html$/.test(p)?'f':'';if(!s)return;
  const id=m[1].toLowerCase();
  const put=()=>{
    const top=document.querySelector('.tmtop');if(!top)return false;
    if(top.querySelector('.favbtn'))return true;
    const h1=document.querySelector('h1'),name=h1?h1.textContent.trim():id;
    const g=document.createElement('div');g.className='favgrp';
    g.innerHTML=F.btn(s,id,'favbtn-hero');g.firstChild.dataset.name=name;
    const fo=top.querySelector('.follow');if(fo){fo.before(g);g.appendChild(fo)}else top.appendChild(g);
    load();sync();return true;
  };
  const go=()=>{load();if(put())return;
    if(!('MutationObserver' in window))return;
    const mo=new MutationObserver(()=>{if(put())mo.disconnect()});mo.observe(document.body,{childList:true,subtree:true});setTimeout(()=>mo.disconnect(),15000)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',go);else go();
})();
load();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sync);else sync();
})();
