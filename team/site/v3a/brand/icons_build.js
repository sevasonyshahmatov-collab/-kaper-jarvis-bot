// Иконки сайта из favicon.svg: node team/site/v3a/brand/icons_build.js  (Playwright + chromium)
const {chromium}=require('playwright'),fs=require('fs'),path=require('path');
const V=path.resolve(__dirname,'..');
const svg=fs.readFileSync(path.join(V,'favicon.svg'),'utf8');
const full=svg.replace(' rx="14"','');                       // без скругления: iOS и Android скругляют сами
const mask=s=>s.replace(/<path/,'<g transform="translate(32 32) scale(.8) translate(-32 -32)"><path').replace('</svg>','</g></svg>');
const jobs=[['favicon-32.png',32,svg],['apple-touch-icon.png',180,full],['icon-192.png',192,svg],['icon-512.png',512,svg],['icon-maskable-512.png',512,mask(full)]];
(async()=>{const b=await chromium.launch();
 for(const [f,n,s] of jobs){const p=await b.newPage({viewport:{width:n,height:n}});
  await p.setContent(`<body style="margin:0;background:transparent">${s.replace('<svg ',`<svg width="${n}" height="${n}" style="display:block" `)}</body>`);
  await p.screenshot({path:path.join(V,f),omitBackground:true,clip:{x:0,y:0,width:n,height:n}});await p.close()}
 await b.close()})();
