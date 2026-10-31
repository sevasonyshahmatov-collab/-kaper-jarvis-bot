/* JARVIS v3a — анимация крупных заголовков (31.10): буквы выезжают снизу из-под невидимой черты, по очереди,
   с лёгкой пружинкой. GSAP 3.13 + SplitText (бесплатны с 2025 г., «GSAP Standard License»), грузятся с jsdelivr.
   Первый экран — при загрузке, остальные — когда заголовок появляется в экране, один раз.
   Не загрузился GSAP за 1,2 с — заголовки просто видны (первый экран придерживаем невидимым максимум 1,2 с, без мигания).
   prefers-reduced-motion — без анимации. Скринридер читает заголовок целиком: SplitText (aria:'auto') ставит
   aria-label на заголовок и aria-hidden на буквы. Подключать после скриптов, которые рисуют заголовки. */
(()=>{
'use strict';
const doc=document.documentElement;
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
const FIRST=[...document.querySelectorAll('.hero h1, .tmname h1')];
const REST=[...document.querySelectorAll('.sec-head h2, .sub h2, .faq h2')].filter(h=>!FIRST.includes(h));
if(!FIRST.length&&!REST.length)return;
const CDN='https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/';
const st=document.createElement('style');
st.textContent=`.tw-hold{visibility:hidden}
.tw-on .tw .ln>span{transform:none!important;transition:none!important}
.tw-on [data-rv]>.tw{opacity:1!important;transform:none!important;transition:none!important}
.tw-w-mask{padding:.14em .02em .08em;margin:-.14em -.02em -.08em;vertical-align:top}
.tw-c{will-change:transform}`;
document.head.appendChild(st);
FIRST.forEach(h=>h.classList.add('tw-hold'));
let done=false;
const release=()=>FIRST.forEach(h=>h.classList.remove('tw-hold'));
const timer=setTimeout(()=>{done=true;release()},1200);
function load(src){return new Promise((ok,no)=>{const s=document.createElement('script');s.src=src;s.async=true;s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
load(CDN+'gsap.min.js').then(()=>load(CDN+'SplitText.min.js')).then(start).catch(()=>{clearTimeout(timer);done=true;release()});

function split(h){
 h.classList.add('tw');
 const s=SplitText.create(h,{type:'words,chars',mask:'words',wordsClass:'tw-w',charsClass:'tw-c',aria:'auto'});
 gsap.set(s.chars,{yPercent:118});
 return s;
}
const play=(s,delay=0)=>gsap.to(s.chars,{yPercent:0,duration:.82,ease:'back.out(1.5)',stagger:.032,delay,
 onComplete:()=>gsap.set(s.chars,{clearProps:'willChange'})});
function start(){
 if(!window.gsap||!window.SplitText){if(!done){clearTimeout(timer);done=true;release()}return}
 gsap.registerPlugin(SplitText);
 const late=done;clearTimeout(timer);done=true;
 doc.classList.add('tw-on');
 const go=()=>{
  // первый экран: если GSAP опоздал и заголовок уже показан — не трогаем, иначе — выезд при загрузке
  if(!late)FIRST.forEach((h,i)=>{const s=split(h);h.classList.remove('tw-hold');play(s,.12+i*.1)});
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;io.unobserve(e.target);play(e.target._tw)}),{rootMargin:'0px 0px -12% 0px'});
  REST.forEach(h=>{h._tw=split(h);io.observe(h)});
 };
 // шрифты подгружаются отдельно — делим на буквы после них, чтобы ширины слов не поехали
 (document.fonts&&document.fonts.ready?Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,600))]):Promise.resolve()).then(go);
}
})();
