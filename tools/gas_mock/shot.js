/* Снимки HTML-листов макета: node tools/gas_mock/shot.js <папка с *.html> [ширина окна] → рядом *.png */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require(path.join(process.execPath, '../../lib/node_modules/playwright'))); }

(async () => {
  const dir = process.argv[2], width = Number(process.argv[3] || 1600);
  const browser = await chromium.launch({ executablePath: fs.existsSync('/opt/pw-browsers/chromium') ? undefined : undefined });
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
  for (const f of fs.readdirSync(dir).filter(x => /^\d+\.html$/.test(x)).sort()) {
    await page.goto('file://' + path.resolve(dir, f));
    const w = await page.evaluate(() => Math.max(...[...document.querySelectorAll('table')].map(t => t.getBoundingClientRect().right)) + 20);
    await page.setViewportSize({ width: Math.max(800, Math.ceil(w)), height: 900 });
    await page.screenshot({ path: path.join(dir, f.replace('.html', '.png')), fullPage: true });
    console.log(f.replace('.html', '.png'));
  }
  await browser.close();
})();
