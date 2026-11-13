/* JARVIS v3a — соцсети: ЕДИНСТВЕННОЕ место, где хранятся адреса (задание 14.11, п. 7).
   Владелец даёт ссылку — вписать её в url ниже, больше ничего менять не нужно: плитки сами появятся
   в блоке «Мы в сети» на главной, в подвале всех страниц и в листе «Ещё» нижней панели телефона.
   Плитка без адреса не показывается вообще (никаких пустых ссылок и «#»).
   Предпросмотр для владельца: ?social=demo в адресе любой страницы — видны все три (пробные адреса, помечены «пример»).
   Места на странице: <div data-social="big|row|sheet"></div> — заполняются сами (JV_SOCIAL.fill). */
(()=>{
const LINKS=[
  {id:'tg',name:'Telegram',url:'https://t.me/jarvibet',note:'Прогнозы до матча и итоги дня'},
  {id:'yt',name:'YouTube',url:'',note:'Разборы и ролики о матчах'},
  {id:'ig',name:'Instagram',url:'',note:'Короткие ролики и итоги'}
];
const DEMO={yt:'https://www.youtube.com/',ig:'https://www.instagram.com/'};
const ICON={
 tg:'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 3.2 2.9 10.4c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.4-1.5ZM8.3 13.2l9.6-6c.5-.3.9-.1.5.2l-8.2 7.4-.3 3.4-1.6-5Z"/></svg>',
 yt:'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 .5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1c.4-1.6.5-3.2.5-4.8s-.1-3.2-.5-4.8ZM9.7 15.1V8.9l5.8 3.1-5.8 3.1Z"/></svg>',
 ig:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4.2"/><circle cx="17.4" cy="6.6" r="1.1" fill="currentColor" stroke="none"/></svg>'
};
let demo=false;try{demo=new URLSearchParams(location.search).get('social')==='demo'}catch(e){}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const list=()=>LINKS.map(l=>({...l,url:l.url||(demo&&DEMO[l.id])||'',demo:!l.url&&demo&&!!DEMO[l.id]})).filter(l=>/^https:\/\//.test(l.url));
const tile=(l,cls)=>`<a class="soc-t soc-${l.id}${cls||''}" href="${esc(l.url)}" target="_blank" rel="noopener"><span class="soc-i">${ICON[l.id]||''}</span><span class="soc-x"><b>${esc(l.name)}</b><small>${esc(l.note)}${l.demo?' · пример':''}</small></span></a>`;
function fill(root){(root||document).querySelectorAll('[data-social]').forEach(box=>{const L=list();
  if(!L.length){box.hidden=true;box.innerHTML='';return}
  const v=box.dataset.social||'row';box.className='soc soc-'+v;box.hidden=false;
  box.innerHTML=L.map((l,i)=>tile(l,v==='big'&&i===0&&l.id==='tg'?' soc-main':'')).join('');
  /* подпись-заголовок у места, если она есть рядом (data-social-head) — прячется вместе с пустым блоком */
  const h=box.previousElementSibling;if(h&&h.hasAttribute('data-social-head'))h.hidden=false})}
window.JV_SOCIAL={links:list,fill};
/* стили — рядом, подключаются сами */
try{const s=(document.currentScript&&document.currentScript.src)||'';if(s&&!document.querySelector('link[data-soc]')){const l=document.createElement('link');l.rel='stylesheet';l.dataset.soc=1;l.href=new URL('social.css',s).href;document.head.appendChild(l)}}catch(e){}
fill();if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>fill());
})();
