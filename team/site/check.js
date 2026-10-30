// Автопроверка собранного сайта на Playwright (владелец 30.10): открывает сайт из папки, без сервера и сети,
// на ширинах 390, 768, 1440 проходит главную, «Прогноз дня» (табло с отсчётом), карточки матчей дня
// («через N ч M мин»), кнопку Telegram и ссылки, страницы прогнозов, тренды и мини-приложение.
// Ловит ошибки консоли и скриптов, пустые блоки, горизонтальную прокрутку, битые картинки и ссылки; делает снимки.
//
//   node team/site/check.js <папка сайта> [папка снимков]        (по умолчанию снимки — <сайт>/../site_check)
//
// Адрес сайта — переменная SITE_URL (иначе берётся из canonical главной). Запросы к нему отдаются из папки,
// остальные (шрифты, счётчики) отклоняются: проверяем только своё. Итог — строки CHECK OK / CHECK FAIL,
// отчёт report.json и report.txt рядом со снимками; код выхода 1, если есть ошибки (предупреждения не валят).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SITE = path.resolve(process.argv[2] || 'site');
const OUT = path.resolve(process.argv[3] || path.join(SITE, '..', 'site_check'));
const WIDTHS = [390, 768, 1440];
const HEIGHT = { 390: 844, 768: 1024, 1440: 900 };
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.gif': 'image/gif', '.mp4': 'video/mp4', '.webm': 'video/webm', '.woff2': 'font/woff2', '.txt': 'text/plain', '.xml': 'application/xml' };

function baseUrl() {
  let b = process.env.SITE_URL;
  if (!b) {
    const m = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8').match(/<link rel="canonical" href="([^"]+)"/);
    b = m ? m[1] : 'https://jarvis.local/';
  }
  return b.replace(/\/?$/, '/');
}
const BASE = baseUrl();
// файлы, без которых сайт работает (приложение берёт нарисованные фоны, если нет картинок Gemini)
const OPTIONAL = /^app\/bg\/photos\.json$/;

// адрес сайта → файл в папке (папка → index.html); null — файла нет
function fileOf(url) {
  const u = new URL(url);
  let rel = decodeURIComponent(u.pathname.slice(new URL(BASE).pathname.length));
  if (rel === '' || rel.endsWith('/')) rel += 'index.html';
  const f = path.join(SITE, rel);
  if (!f.startsWith(SITE)) return null;
  if (fs.existsSync(f) && fs.statSync(f).isFile()) return f;
  if (fs.existsSync(f + '.html')) return f + '.html';
  if (fs.existsSync(path.join(f, 'index.html'))) return path.join(f, 'index.html');
  return null;
}

const errors = [];
const warns = [];
const shots = [];
const fail = (where, msg) => errors.push(`${where}: ${msg}`);
const warn = (where, msg) => warns.push(`${where}: ${msg}`);

// страницы: главная, все прогнозы, один прогноз (самый свежий), тренды, мини-приложение
function pages() {
  const P = [['главная', ''], ['прогнозы', 'prognozy/']];
  const dir = path.join(SITE, 'prognozy');
  const one = fs.existsSync(dir) ? fs.readdirSync(dir).filter(f => /^20.*\.html$/.test(f)).sort().pop() : null;
  if (one) P.push(['прогноз', 'prognozy/' + one]);
  else warn('прогноз', 'нет ни одной страницы прогноза (prognozy/20*.html)');
  if (fileOf(BASE + 'trendy/')) P.push(['тренды', 'trendy/']);
  if (fileOf(BASE + 'app/')) P.push(['приложение', 'app/']);
  return P;
}

async function newPage(browser, w, tag) {
  const ctx = await browser.newContext({ viewport: { width: w, height: HEIGHT[w] }, deviceScaleFactor: 1,
    isMobile: w < 500, hasTouch: w < 500, locale: 'ru-RU', timezoneId: 'Europe/Moscow' });
  const page = await ctx.newPage();
  const bad = [];
  await page.route('**/*', route => {
    const url = route.request().url();
    if (!url.startsWith(BASE)) return route.abort();
    const f = fileOf(url);
    if (!f) { bad.push(url.slice(BASE.length)); return route.fulfill({ status: 404, body: 'not found' }); }
    route.fulfill({ status: 200, body: fs.readFileSync(f), contentType: TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream' });
  });
  page.on('console', m => { if (m.type() === 'error' && !/net::ERR_FAILED|Failed to load resource/.test(m.text())) fail(tag, 'консоль: ' + m.text().slice(0, 200)); });
  page.on('pageerror', e => fail(tag, 'ошибка скрипта: ' + String(e.message || e).slice(0, 200)));
  return { ctx, page, bad };
}

// прокрутить до низа, чтобы сработали ленивые картинки и появления
async function scrollAll(page) {
  await page.evaluate(async () => {
    const step = innerHeight * 0.8;
    for (let y = 0; y < document.documentElement.scrollHeight; y += step) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
    scrollTo(0, 0); await new Promise(r => setTimeout(r, 200));
  });
}

async function common(page, tag, bad, app) {
  const r = await page.evaluate(() => {
    const doc = document.documentElement;
    const wide = [...document.querySelectorAll('body *')].filter(e => {
      const b = e.getBoundingClientRect(), s = getComputedStyle(e);
      return b.width > 0 && b.right > innerWidth + 1 && s.position !== 'fixed' && !e.closest('[aria-hidden="true"]') && getComputedStyle(e.parentElement).overflowX === 'visible';
    }).slice(0, 3).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : ''));
    const imgs = [...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0 && getComputedStyle(i).display !== 'none')
      .map(i => i.getAttribute('src'));
    const links = [...document.querySelectorAll('a[href]')].map(a => a.href);
    const tg = [...document.querySelectorAll('a[href*="t.me/jarvibet"]')].filter(a => a.offsetParent !== null).length;
    return { sw: doc.scrollWidth, w: innerWidth, wide, imgs, links, tg, h1: (document.querySelector('h1') || {}).textContent || '' };
  });
  if (r.sw > r.w + 1) fail(tag, `горизонтальная прокрутка: ширина ${r.sw} > ${r.w}` + (r.wide.length ? ' (вылезают: ' + r.wide.join(', ') + ')' : ''));
  for (const s of new Set(r.imgs)) fail(tag, 'битая картинка: ' + s);
  for (const s of new Set(bad)) if (!/favicon/.test(s)) (OPTIONAL.test(s) ? warn : fail)(tag, 'нет файла на сайте: ' + s);
  if (app) return r.links;                 // мини-приложение открывается внутри Telegram: без кнопки канала и h1
  if (!r.tg) fail(tag, 'не видно кнопки/ссылки Telegram @jarvibet');
  if (!r.h1.trim()) warn(tag, 'нет заголовка h1');
  return r.links;
}

// пустые блоки главной и табло «Прогноз дня» с отсчётом
async function landingChecks(page, tag) {
  const r = await page.evaluate(() => {
    const txt = s => { const e = document.querySelector(s); return e ? e.innerText.trim() : null; };
    const T = window.__TODAY || {};
    return { mlist: document.querySelectorAll('#mlist .card').length, khl: (T.khl || []).length, nhl: (T.nhl || []).length,
      tick: txt('#tick'), honest: txt('#honest'), months: txt('#monthlist'), pv: txt('#pv'), board: !!document.querySelector('.board'),
      tabs: [...document.querySelectorAll('.tab')].map(t => t.dataset.l) };
  });
  if (!r.board) fail(tag, 'нет табло «Прогноз дня» (.board)');
  if (!r.mlist) fail(tag, 'пустой блок «Матчи дня» (#mlist без карточек)');
  if (!r.khl && !r.nhl) warn(tag, 'нет настоящих матчей дня (__TODAY пуст) — показаны примеры');
  if (r.tick !== null && !r.tick) warn(tag, 'пустая бегущая строка итогов (#tick)');
  if (r.honest !== null && !r.honest) fail(tag, 'пустой блок «Показываю всё» (#honest)');
  // вкладка НХЛ переключает карточки
  if (r.tabs.includes('nhl')) {
    await page.click('#t-nhl');
    const n = await page.locator('#mlist .card').count();
    if (!n) (r.nhl ? fail : warn)(tag, 'вкладка НХЛ: нет карточек');
    await page.click('#t-khl');
  }
}

// отсчёт: время ставим за 2 ч до «Прогноза дня» — на табло ЧЧ:ММ:СС, в карточках «через N ч M мин»
async function countdown(browser, w) {
  const tag = `отсчёт ${w}`;
  const { ctx, page } = await newPage(browser, w, tag);
  await page.goto(BASE, { waitUntil: 'load' });
  const T = await page.evaluate(() => {
    const T = window.__TODAY; if (!T) return null;
    const all = [...(T.khl || []), ...(T.nhl || [])];
    const first = [...all].sort((a, b) => b.pr - a.pr)[0];
    return { first: first && first.t, n: all.filter(m => m.t).length };
  });
  if (!T || !T.first) { warn(tag, 'нет времени матчей в __TODAY — отсчёт не проверен'); await ctx.close(); return; }
  const at = Date.parse(T.first.replace(' ', 'T') + ':00+03:00');
  await page.clock.setFixedTime(new Date(at - (2 * 3600 + 5 * 60) * 1000));
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => ({
    clock: !document.getElementById('clock') || document.getElementById('clock').hidden ? null : document.getElementById('cd').textContent,
    cds: [...document.querySelectorAll('.card .cd')].map(e => e.textContent.trim()) }));
  if (r.clock === null) fail(tag, 'табло «Прогноз дня»: отсчёт до вбрасывания не показан');
  else if (!/^\d\d:\d\d:\d\d$/.test(r.clock)) fail(tag, 'табло: отсчёт в странном виде «' + r.clock + '»');
  if (!r.cds.some(s => /^через (\d+ ч )?\d+ мин$/.test(s))) fail(tag, 'карточки матчей: нет «через N ч M мин» (' + r.cds.slice(0, 3).join(' | ') + ')');
  const f = path.join(OUT, `countdown-${w}.png`);
  await page.locator('.hero').screenshot({ path: f }).catch(() => page.screenshot({ path: f }));
  shots.push(f);
  await ctx.close();
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const links = new Set();
  for (const w of WIDTHS) {
    for (const [name, rel] of pages()) {
      const tag = `${name} ${w}`;
      const { ctx, page, bad } = await newPage(browser, w, tag);
      try {
        const resp = await page.goto(BASE + rel, { waitUntil: 'load', timeout: 30000 });
        if (!resp || resp.status() !== 200) { fail(tag, 'страница не открылась'); continue; }
        await page.waitForTimeout(800);
        await scrollAll(page);
        (await common(page, tag, bad, rel.startsWith('app/'))).forEach(l => links.add(l));
        if (rel === '') await landingChecks(page, tag);
        const f = path.join(OUT, `${(rel.replace(/\/$/, '').replace(/[\/.]/g, '_') || 'index').replace(/_html$/, '')}-${w}.png`);
        await page.screenshot({ path: f, fullPage: true });
        shots.push(f);
      } catch (e) {
        fail(tag, 'проверка оборвалась: ' + String(e.message || e).split('\n')[0]);
      } finally { await ctx.close(); }
    }
    await countdown(browser, w);
  }
  await browser.close();
  // ссылки: свои — должен быть файл, чужие — только список
  const ext = new Set();
  for (const l of links) {
    const u = l.split('#')[0];
    if (!/^https?:/.test(u)) continue;
    if (u.startsWith(BASE)) { if (!fileOf(u)) fail('ссылки', 'ведёт в никуда: ' + u.slice(BASE.length)); }
    else ext.add(new URL(u).host);
  }
  const rep = { site: SITE, base: BASE, ok: !errors.length, errors: [...new Set(errors)], warns: [...new Set(warns)],
    external_hosts: [...ext].sort(), shots: shots.map(f => path.relative(OUT, f)) };
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(rep, null, 1));
  const txt = [(rep.ok ? 'CHECK OK' : 'CHECK FAIL') + ` — ошибок ${rep.errors.length}, предупреждений ${rep.warns.length}, снимков ${shots.length}`,
    ...rep.errors.map(e => '  ✗ ' + e), ...rep.warns.map(e => '  · ' + e), '  внешние ссылки: ' + rep.external_hosts.join(', ')].join('\n');
  fs.writeFileSync(path.join(OUT, 'report.txt'), txt + '\n');
  console.log(txt);
  process.exit(rep.ok ? 0 : 1);
})();
