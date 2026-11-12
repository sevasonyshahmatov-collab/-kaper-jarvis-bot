/* Проба шрифтовых пар на настоящих страницах (владелец 12.11: «чтобы не выглядело как шаблон нейросети»).
   Включается из nav.js по ?font=…; ничего не меняет, пока пара не выбрана. Файлы — assets/vendor/fonts/lab/ (все OFL, с кириллицей).
   arena  — Roboto Flex: широкое начертание в заголовках (как у nhl.com), обычное в цифрах и меню; текст — Golos Text
   afisha — Sofia Sans Extra Condensed: узкий плакатный набор; текст — Onest
   tablo  — Tektur: рубленый «табло»; текст — Geologica */
(()=>{
const me=document.currentScript,f=me.dataset.font,dir=new URL('vendor/fonts/lab/',me.src).href;
const CY='U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116',LA='U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD';
const face=(fam,file,w,extra)=>[['cyrillic',CY],['latin',LA]].map(([s,u])=>`@font-face{font-family:"${fam}";font-style:normal;font-weight:${w};font-display:swap;src:url(${dir}${file}-${s}.woff2) format("woff2");unicode-range:${u};${extra||''}}`).join('');
const P={
 arena:{n:'Арена · Roboto Flex + Golos',css:face('Lab D','robotoflex','100 1000','font-stretch:100%')+face('Lab W','robotoflex','100 1000','font-stretch:132%')+face('Lab T','golos','400 900')
  +`:root{--display:"Lab D","JV Display",Arial,sans-serif;--text:"Lab T",Arial,sans-serif}
    h1,h2,.pp h1 b,.pp-wm,.pp-stick .wm,.logo{font-family:"Lab W","Lab D",sans-serif!important;font-stretch:132%;letter-spacing:-.01em}
    h1,h2{font-weight:800!important}`},
 afisha:{n:'Афиша · Sofia Sans XCond + Onest',css:face('Lab D','sofiaxc','1 1000','size-adjust:128%')+face('Lab T','onest','100 900')
  +`:root{--display:"Lab D","JV Display",Arial,sans-serif;--text:"Lab T",Arial,sans-serif}
    h1,h2,.pp h1 b{letter-spacing:.005em!important}`},
 tablo:{n:'Табло · Tektur + Geologica',css:face('Lab D','tektur','400 900','size-adjust:104%')+face('Lab T','geologica','100 900')
  +`:root{--display:"Lab D","JV Display",Arial,sans-serif;--text:"Lab T",Arial,sans-serif}`}};
const p=P[f];if(!p)return;
const st=document.createElement('style');st.textContent=p.css;document.head.appendChild(st);
document.documentElement.dataset.font=f;
/* плашка выбора — только пока идёт проба */
const add=()=>{const d=document.createElement('div');d.style.cssText='position:fixed;left:10px;bottom:10px;z-index:200;display:flex;gap:2px;background:#0b0c0e;color:#fff;padding:4px;font:600 12px/1 Arial,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.4)';
 const u=k=>{const q=new URLSearchParams(location.search);q.set('font',k);return location.pathname+'?'+q+location.hash};
 d.innerHTML=[['arena','Арена'],['afisha','Афиша'],['tablo','Табло'],['off','Как сейчас']].map(([k,n])=>`<a href="${u(k)}" style="padding:7px 9px;color:${k===f?'#0b0c0e':'#fff'};background:${k===f?'#ffc21a':'transparent'};text-decoration:none">${n}</a>`).join('');
 document.body.appendChild(d)};
document.body?add():addEventListener('DOMContentLoaded',add);
})();
