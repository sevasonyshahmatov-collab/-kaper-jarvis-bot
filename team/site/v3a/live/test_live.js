/* Проверка assets/live.js в Playwright с подменой ответов источников (page.route). Запуск: node test_live.js <папка для снимков> */
const {chromium} = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const OUT = process.argv[2] || '/tmp/shots';
fs.mkdirSync(OUT, {recursive: true});
const MIME = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.png': 'image/png'};
const srv = http.createServer((q, r) => {
  let p = decodeURIComponent(q.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, p);
  if (!f.startsWith(ROOT) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, {'content-type': MIME[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f));
});
const ok = (c, m) => { if (!c) { console.log('FAIL', m); process.exitCode = 1; } else console.log('ok  ', m); };
const cors = {'access-control-allow-origin': '*', 'content-type': 'application/json'};

(async () => {
  await new Promise(r => srv.listen(0, r));
  const base = 'http://127.0.0.1:' + srv.address().port;
  const br = await chromium.launch();
  for (const [w, h] of [[390, 844], [1440, 900]]) {
    const ctx = await br.newContext({viewport: {width: w, height: h}});
    const page = await ctx.newPage();
    page.on('pageerror', e => console.log('PAGEERR', e.message));
    await page.clock.install({time: new Date('2026-11-05T14:00:00Z')});
    const start = '2026-11-05T13:30:00.000Z';              /* начало 30 минут назад */
    let khl = {k: 'live', score: '1:0', period: 2}, esp = {state: 'in', h: 1, a: 0, per: 2, clock: '12:34', det: '12:34 - 2nd Period'}, calls = {khl: 0, espn: 0};
    await page.route('**/*', async route => {
      const u = route.request().url();
      if (u.includes('khl.api.webcaster.pro')) {
        calls.khl++;
        if (khl.fail) return route.abort();
        const e = {id: 1, start_at: Date.parse(start), game_state_key: khl.k === 'final' ? 'finished' : 'live', score: khl.score, period: khl.k === 'final' ? -1 : khl.period,
          team_a: {id: 10}, team_b: {id: 16}};
        return route.fulfill({status: 200, headers: cors, body: JSON.stringify([{event: e}])});
      }
      if (u.includes('site.api.espn.com')) {
        calls.espn++;
        const soccer = u.includes('/soccer/');
        const t = soccer ? [{abbreviation: 'EVE', displayName: 'Everton', shortDisplayName: 'Everton', location: 'Everton', name: 'Everton'}, {abbreviation: 'COV', displayName: 'Coventry City', shortDisplayName: 'Coventry', location: 'Coventry City', name: 'Coventry City'}]
          : [{abbreviation: 'LA', displayName: 'Los Angeles Kings', shortDisplayName: 'Kings', location: 'Los Angeles', name: 'Kings'}, {abbreviation: 'SJ', displayName: 'San Jose Sharks', shortDisplayName: 'Sharks', location: 'San Jose', name: 'Sharks'}];
        const ev = {id: '9', date: start.replace('.000', ''), status: {period: esp.per, displayClock: esp.clock, type: {state: esp.state, completed: esp.state === 'post', shortDetail: esp.det, detail: esp.det}},
          competitions: [{competitors: [{homeAway: 'home', score: String(esp.h), team: t[0]}, {homeAway: 'away', score: String(esp.a), team: t[1]}]}]};
        return route.fulfill({status: 200, headers: cors, body: JSON.stringify({events: [ev]})});
      }
      if (u.startsWith(base) && (u.endsWith('/') || u.endsWith('.html'))) {   /* страницы: начало матча подменяем на «30 минут назад» */
        const res = await route.fetch(); let b = await res.text();
        b = b.replace(/data-lv-t="[^"]+"/g, 'data-lv-t="' + start + '"');
        return route.fulfill({response: res, body: b});
      }
      route.continue();
    });
    const tag = w + '_';
    /* 1. страница матча КХЛ */
    await page.goto(base + '/khl/2026-11-05-avangard-cska/');
    await page.waitForSelector('.lv-box .lv:not([hidden])');
    ok((await page.textContent('.lv-box .lv-tag')) === 'LIVE', w + ' КХЛ: LIVE');
    ok((await page.textContent('.lv-box .lv-sc')) === '1:0', w + ' КХЛ: счёт 1:0');
    ok((await page.textContent('.lv-box .lv-st')) === '2-й период', w + ' КХЛ: период');
    ok(await page.$eval('.mt-odds-wrap', e => getComputedStyle(e).display === 'none'), w + ' КХЛ: кэфы скрыты в лайве');
    await page.screenshot({path: OUT + '/' + tag + 'khl_live.png'});
    khl.score = '2:0'; await page.clock.fastForward(31000);
    await page.waitForFunction(() => document.querySelector('.lv-box .lv-sc').textContent === '2:0');
    ok(await page.$eval('.lv-box .lv', e => e.classList.contains('lv-goal')), w + ' КХЛ: подсветка гола');
    await page.screenshot({path: OUT + '/' + tag + 'khl_goal.png'});
    khl.k = 'final'; khl.score = '3:1'; await page.clock.fastForward(31000);
    await page.waitForFunction(() => document.querySelector('.lv-box .lv-tag').textContent === 'Финал');
    ok((await page.textContent('.lv-box .lv-sc')) === '3:1', w + ' КХЛ: финал 3:1');
    await page.screenshot({path: OUT + '/' + tag + 'khl_final.png'});
    const n = calls.khl; await page.clock.fastForward(95000);
    ok(calls.khl === n, w + ' КХЛ: после финала опроса нет');
    /* 2. вкладка скрыта — опроса нет */
    /* 3. НХЛ, страница матча */
    await page.goto(base + '/nhl/2026-11-05-los-angeles-san-jose/'); await page.waitForTimeout(1500);
    await page.waitForSelector('.lv-box .lv:not([hidden])');
    ok((await page.textContent('.lv-box .lv-sc')) === '1:0', w + ' НХЛ: счёт');
    ok((await page.textContent('.lv-box .lv-st')) === '2-й период, 12:34', w + ' НХЛ: период и время');
    await page.screenshot({path: OUT + '/' + tag + 'nhl_live.png'});
    esp.h = 1; esp.a = 1; await page.clock.fastForward(31000);
    await page.waitForFunction(() => document.querySelector('.lv-box .lv-sc').textContent === '1:1');
    ok(true, w + ' НХЛ: смена счёта');
    /* 4. футбол: прогноз на сегодня (список) */
    esp = {state: 'in', h: 0, a: 1, per: 2, clock: "67'", det: "67'"};
    await page.goto(base + '/football/forecast-epl.html');
    await page.waitForSelector('.fc-m > .lv:not([hidden])');
    const ft = await page.$eval('.fc-m > .lv', e => e.textContent);
    ok(/LIVE/.test(ft) && /0:1/.test(ft.replace(/\s/g, '')) && /67/.test(ft), w + ' футбол список: ' + ft);
    await page.locator('.fc-m').first().scrollIntoViewIfNeeded(); await page.locator('.fc-m').first().screenshot({path: OUT + '/' + tag + 'epl_list.png'});
    /* 4б. «Мои матчи»: избранные клубы в localStorage */
    await page.addInitScript(() => { try { localStorage.setItem('jv_fav_v1', JSON.stringify(['h:avangard', 'h:cska'])); } catch (e) {} });
    khl = {k: 'live', score: '2:1', period: 3};
    await page.goto(base + '/me/');
    const mm = await page.waitForSelector('.me-m[data-lv] > .lv:not([hidden])', {timeout: 8000}).catch(() => null);
    ok(!!mm, w + ' Мои матчи: LIVE в строке');
    if (mm) await page.locator('.me-m[data-lv]').first().screenshot({path: OUT + '/' + tag + 'me_row.png'});
    /* 5. ошибка источника — тихо */
    khl = {k: 'live', score: '1:0', period: 1, fail: true};
    await page.goto(base + '/khl/2026-11-05-avangard-cska/');
    await page.waitForTimeout(300);
    ok(await page.$eval('.lv-box', e => !e.querySelector('.lv') || e.querySelector('.lv').hidden), w + ' ошибка: ничего не показано');
    /* 6. вне окна: матч в будущем — запросов нет */
    await ctx.close();
  }
  /* 7. не опрашивать вне окна и при скрытой вкладке */
  const ctx = await br.newContext({viewport: {width: 1440, height: 900}}); const page = await ctx.newPage();
  await page.clock.install({time: new Date('2026-11-05T10:00:00Z')}); let hits = 0;
  await page.route(/espn|webcaster/, r => { hits++; r.abort(); });
  await page.goto(base + '/nhl/2026-11-05-los-angeles-san-jose/'); await page.clock.fastForward(65000);
  ok(hits === 0, 'вне окна матча запросов нет (' + hits + ')');
  await br.close(); srv.close();
})();
