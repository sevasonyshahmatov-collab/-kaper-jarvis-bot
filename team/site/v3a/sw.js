/* JARVIS v3a — работа без интернета (идеи 37–38). Регистрирует assets/footer.js, область — папка сайта.
   Страницы, стили, скрипты и данные: сначала сеть (всегда свежее), нет сети — последняя сохранённая копия.
   Картинки и шрифты своего сайта: сначала копия (они не меняются), сеть — если копии нет.
   Чужие адреса (шрифты Google, фото лиг, живой счёт) не трогаем. Никаких личных данных не храним.
   VER меняет ежедневная сборка (seo/build_seo.py, stamp_sw: отпечаток страниц и данных из CORE) — браузер видит новый sw.js,
   ставит его и удаляет старые копии страниц СВОЕЙ папки (у / и /draft/ кэши раздельные, аудит 19.11). Копии картинок — в отдельном кэше IMG,
   при смене VER не пропадают: показываем копию сразу и тихо сверяем с сервером (если картинку заменили — в следующий раз будет новая);
   в кэше картинок не больше IMG_MAX штук, лишние старые удаляются.
   Данные и страницы запрашиваются с cache:'no-cache' — сверка с сервером, мимо 10-минутного кэша браузера. */
const VER='jv-6262998009',ROOT=new URL('./',self.location).href,CACHE=VER+'|'+ROOT,IMG='jv-img|'+ROOT;
const CORE=['index.html','hockey/index.html','football/index.html','matches.html','results.html','offline.html',
 'assets/v3a.css','assets/nav.css','assets/home.css','assets/footer.css','assets/nav.js','assets/footer.js','assets/v3a.js',
 'data/today.js','data/lines.js','data/model.js','data/results-lite.js','favicon.svg?v=3','icon-192.png?v=3'];
self.addEventListener('install',e=>{self.skipWaiting();
 e.waitUntil(caches.open(CACHE).then(c=>Promise.all(CORE.map(u=>c.add(new Request(ROOT+u,{cache:'reload'})).catch(()=>{})))))});
self.addEventListener('activate',e=>e.waitUntil(caches.keys()
 .then(ks=>Promise.all(ks.filter(k=>k.startsWith('jv-')&&(!k.includes('|')||k.endsWith('|'+ROOT))&&k!==CACHE&&k!==IMG).map(k=>caches.delete(k)))).then(trim).then(()=>self.clients.claim())));
const IMG_MAX=800,trim=()=>caches.open(IMG).then(c=>c.keys().then(ks=>Promise.all(ks.slice(0,Math.max(0,ks.length-IMG_MAX)).map(k=>c.delete(k))))).catch(()=>{});
const put=(req,res,to)=>{if(res&&res.ok&&res.type==='basic'){const cp=res.clone();caches.open(to||CACHE).then(c=>c.put(req,cp)).catch(()=>{})}return res};
/* сверка с сервером (ETag): свежий файл, если он поменялся; навигацию заново не собрать с другими настройками — её как есть */
const net=req=>req.mode==='navigate'?fetch(req):fetch(req,{cache:'no-cache'});
const STATIC=/\.(?:webp|png|jpe?g|svg|gif|avif|ico|woff2?)$/i;
self.addEventListener('fetch',e=>{
 const req=e.request;if(req.method!=='GET')return;
 const u=new URL(req.url);if(u.origin!==self.location.origin||!u.href.startsWith(ROOT)||req.headers.has('range'))return;
 if(STATIC.test(u.pathname)){const fresh=fetch(req).then(r=>put(req,r,IMG));e.waitUntil(fresh.catch(()=>{}));
  e.respondWith(caches.open(IMG).then(c=>c.match(req)).then(hit=>hit||fresh));return}
 /* переходы с параметрами в адресе в копию не кладём: иначе ссылками со случайными ?… можно раздувать кэш посетителя (16.11) */
 e.respondWith(net(req).then(r=>req.mode==='navigate'&&u.search?r:put(req,r)).catch(()=>caches.open(CACHE).then(c=>c.match(req).then(hit=>hit||(req.mode==='navigate'?c.match(req,{ignoreSearch:true}):undefined)))
  .then(hit=>hit||(req.mode==='navigate'?caches.open(CACHE).then(c=>c.match(ROOT+'offline.html')):undefined)).then(hit=>hit||Response.error())))});
