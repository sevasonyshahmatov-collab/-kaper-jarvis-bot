/* JARVIS v3a — работа без интернета (идеи 37–38). Регистрирует assets/footer.js, область — папка сайта.
   Страницы, стили, скрипты и данные: сначала сеть (всегда свежее), нет сети — последняя сохранённая копия.
   Картинки и шрифты своего сайта: сначала копия (они не меняются), сеть — если копии нет.
   Чужие адреса (шрифты Google, фото лиг, живой счёт) не трогаем. Никаких личных данных не храним.
   VER меняет ежедневная сборка (seo/build_seo.py, stamp_sw: отпечаток страниц и данных из CORE) — браузер видит новый sw.js,
   ставит его и удаляет старые копии страниц. Копии картинок — в отдельном кэше IMG, при смене VER не пропадают.
   Данные и страницы запрашиваются с cache:'no-cache' — сверка с сервером, мимо 10-минутного кэша браузера. */
const VER='jv-758a804b50',ROOT=new URL('./',self.location).href,CACHE=VER+'|'+ROOT,IMG='jv-img|'+ROOT;
const CORE=['index.html','hockey/index.html','football/index.html','matches.html','results.html','offline.html',
 'assets/v3a.css','assets/nav.css','assets/home.css','assets/footer.css','assets/nav.js','assets/footer.js','assets/v3a.js',
 'data/today.js','data/lines.js','data/model.js','data/results-lite.js','favicon.svg','icon-192.png'];
self.addEventListener('install',e=>{self.skipWaiting();
 e.waitUntil(caches.open(CACHE).then(c=>Promise.all(CORE.map(u=>c.add(new Request(ROOT+u,{cache:'reload'})).catch(()=>{})))))});
self.addEventListener('activate',e=>e.waitUntil(caches.keys()
 .then(ks=>Promise.all(ks.filter(k=>k.startsWith('jv-')&&k!==CACHE&&k!==IMG).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
const put=(req,res,to)=>{if(res&&res.ok&&res.type==='basic'){const cp=res.clone();caches.open(to||CACHE).then(c=>c.put(req,cp)).catch(()=>{})}return res};
/* сверка с сервером (ETag): свежий файл, если он поменялся; навигацию заново не собрать с другими настройками — её как есть */
const net=req=>req.mode==='navigate'?fetch(req):fetch(req,{cache:'no-cache'});
const STATIC=/\.(?:webp|png|jpe?g|svg|gif|avif|ico|woff2?)$/i;
self.addEventListener('fetch',e=>{
 const req=e.request;if(req.method!=='GET')return;
 const u=new URL(req.url);if(u.origin!==self.location.origin||!u.href.startsWith(ROOT)||req.headers.has('range'))return;
 if(STATIC.test(u.pathname)){e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(r=>put(req,r,IMG))));return}
 e.respondWith(net(req).then(r=>put(req,r)).catch(()=>caches.match(req).then(hit=>hit||caches.match(req,{ignoreSearch:true}))
  .then(hit=>hit||(req.mode==='navigate'?caches.match(ROOT+'offline.html'):undefined)).then(hit=>hit||Response.error())))});
