// Проверка шапки ?hh=8 без браузера и без WebGPU: node tools/test_hero8.mjs
// 1) описание слоёв (JVSh.preset) сверяется с определениями компонентов из vendor/shaders.min.js: имена, ключи пропсов, типы значений;
// 2) mount() при navigator.gpu без адаптера и createShader с пустым адаптером не падают и отдают причину (уходим в CSS-фолбэк).
import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import {fileURLToPath, pathToFileURL} from 'node:url'

const dir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../team/site/v3a/assets/hero2/')
const heroPath = path.join(dir, 'hero8.js')
const vendorUrl = pathToFileURL(path.join(dir, 'vendor/shaders.min.js')).href
let fails = 0
const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fails++ }

// ── окружение для hero8.js ──
const classes = new Set()
const host = {classList: {add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c)}, style: {setProperty() {}}, getBoundingClientRect: () => ({width: 1440, height: 710})}
const cv = {style: {}}
const win = {URL, JSON, Math, Date, Promise, Object, Array, Set, Map, String, Number, ResizeObserver: undefined, setInterval, clearInterval, setTimeout, clearTimeout, performance, navigator: {}, matchMedia: () => ({matches: false}), document: {currentScript: {src: pathToFileURL(heroPath).href}, addEventListener() {}, hidden: false}, addEventListener() {}, console}
win.window = win
vm.createContext(win)
// dynamic import внутри vm недоступен — отдаём hero8.js как обычный модуль-обёртку
const src = fs.readFileSync(heroPath, 'utf8').replace(/await import\(/g, 'await __imp(')
win.__imp = u => import(u)
win.document.createElement = () => ({getContext: () => null, toBlob() {}, width: 0, height: 0})
vm.runInContext(src, win)
const SH = win.JVSh
ok(SH && typeof SH.mount === 'function' && typeof SH.preset === 'function', 'hero8.js экспортирует JVSh.mount / JVSh.preset')

// ── 1. слои против определений ──
const lib = await import(vendorUrl)
const defs = Object.fromEntries(lib.DEFS.map(d => [d.name, d]))
const BLEND = ['normal', 'multiply', 'screen', 'overlay', 'softLight', 'hardLight', 'linearDodge', 'linearBurn', 'colorDodge', 'colorBurn', 'darken', 'lighten', 'difference', 'exclusion', 'hue', 'saturation', 'color', 'luminosity']
const MASK = ['alpha', 'alphaInverted', 'luminance', 'luminanceInverted']
const META = new Set(['opacity', 'blendMode', 'visible', 'maskSource', 'maskType', 'boundingBox', 'transform', 'flow', 'absolute'])
for (const kind of ['ice', 'pitch']) {
  const p = SH.preset(kind, 1440, 710), ids = new Set(p.components.map(c => c.id))
  ok(p.components.length > 3, `${kind}: слоёв ${p.components.length}: ${p.components.map(c => c.type).join(' > ')}`)
  for (const c of p.components) {
    const d = defs[c.type]
    ok(!!d, `${kind}/${c.id}: компонент ${c.type} есть в сборке`)
    if (!d) continue
    for (const [k, v] of Object.entries(c.props || {})) {
      if (META.has(k)) {
        if (k === 'blendMode') ok(BLEND.includes(v), `${kind}/${c.id}.blendMode=${v}`)
        if (k === 'maskType') ok(MASK.includes(v), `${kind}/${c.id}.maskType=${v}`)
        if (k === 'maskSource') ok(ids.has(v), `${kind}/${c.id}.maskSource=${v} — такой слой есть`)
        if (k === 'opacity') ok(typeof v === 'number' && v >= 0 && v <= 1, `${kind}/${c.id}.opacity=${v}`)
        continue
      }
      const def = d.props[k]
      ok(!!def, `${kind}/${c.id}.${k} — пропс существует у ${c.type}`)
      if (!def) continue
      const a = typeof def.default, b = typeof v
      const same = a === b || (def.default && typeof def.default === 'object' && b === 'object')
      ok(same, `${kind}/${c.id}.${k}: тип ${b} (по умолчанию ${a})`)
      if (typeof v === 'number' && def.ui && typeof def.ui.min === 'number') ok(v >= def.ui.min && v <= def.ui.max, `${kind}/${c.id}.${k}=${v} в диапазоне ${def.ui.min}…${def.ui.max}`)
    }
  }
  const fn = p.components.find(c => c.type === 'Fog')
  ok(fn && fn.props.mouseInfluence === 0, `${kind}: Fog не следует за курсором (mouseInfluence=0)`)
  ok(!p.components.some(c => /Cursor|Glass|Fluted|Ripples|Trail/.test(c.type)), `${kind}: нет запрещённых слоёв (курсор/стекло)`)
}
const g = SH.frostGeom(1440, 710), s = JSON.parse(g.shape)
ok(g.scale >= 1440 / 710 && s.type === 'roundedRectSDF' && Math.abs(s.radius * 2 * g.scale * 710 - 1440) < 12 && Math.abs(s.height * 2 * g.scale * 710 - 710) < 8, `иней: форма совпадает с холстом (scale ${g.scale.toFixed(3)}, radius ${s.radius}, height ${s.height})`)

// ── 2. поведение без WebGPU ──
let r = await SH.mount(host, cv, 'ice')
ok(r === false, 'navigator.gpu нет → mount вернул false (CSS-фолбэк)')
win.navigator.gpu = {requestAdapter: async () => null}
Object.defineProperty(globalThis, 'navigator', {value: win.navigator, configurable: true})
classes.clear(); r = await SH.mount(host, cv, 'ice')
ok(r === false && classes.has('gl-off'), 'navigator.gpu есть, адаптера нет → mount вернул false, на блоке gl-off')
// createShader сам: пустой адаптер → onError + getFailureReason, без исключений
const errs = []; let inst = null, threw = null
try { inst = await lib.createShader({style: {width: '100%', height: '100%'}, getBoundingClientRect: () => ({width: 1440, height: 710}), width: 1440, height: 710, getContext: () => null, addEventListener() {}}, SH.preset('ice', 1440, 710), {disableTelemetry: true, onError: e => errs.push(e)}) } catch (e) { threw = e }
ok(!threw || /./.test(String(threw)), `createShader без адаптера: ${threw ? 'исключение поймано (' + String(threw.message || threw).slice(0, 60) + ')' : 'без исключения, причина ' + JSON.stringify(errs)}`)
ok(threw || errs.length > 0 || (inst && inst.getFailureReason()), 'причина отказа доступна (onError / getFailureReason) — mount уйдёт в фолбэк')
console.log(fails ? `\nПровалено: ${fails}` : '\nВсе проверки пройдены')
process.exit(fails ? 1 : 0)
