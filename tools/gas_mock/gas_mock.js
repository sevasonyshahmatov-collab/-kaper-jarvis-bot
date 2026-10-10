/* Макет Google Таблиц и сервисов Apps Script для проверки кода таблиц без Google.
 *
 *   const gm = require('./gas_mock');
 *   const env = gm.makeEnv({ now: '2026-10-04T13:00:00Z' });
 *   gm.load(env, ['apps-script/epl/00_core.js', ...]);     // код исполняется как в Apps Script
 *   env.ctx.renderBrief_(env.ss);
 *   fs.writeFileSync('book.html', gm.renderHtml(env.ss));    // листы с оформлением — для снимка
 *
 * Ведёт себя строго, как Таблица: запись за край листа (1000×26 у нового) — ошибка; строка «2:1» или «2026-10-17»
 * в нетекстовой ячейке превращается в дату. Сеть закрыта: UrlFetchApp бросает ошибку.
 */
const fs = require('fs');
const vm = require('vm');

function a1Col(n) { let s = ''; while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); } return s; }

class Range {
  constructor(sheet, r, c, nr, nc) { Object.assign(this, { sheet, r, c, nr: nr || 1, nc: nc || 1 }); sheet._check(this.r + this.nr - 1, this.c + this.nc - 1); }
  _each(fn) { for (let i = 0; i < this.nr; i++) for (let j = 0; j < this.nc; j++) fn(this.sheet._cell(this.r + i, this.c + j, true), i, j); return this; }
  _grid(v, name) {
    if (!Array.isArray(v) || v.length !== this.nr || v.some(row => !Array.isArray(row) || row.length !== this.nc))
      throw new Error(name + ': размер данных не совпадает с диапазоном ' + this.nr + '×' + this.nc);
    return v;
  }
  getSheet() { return this.sheet; } getRow() { return this.r; } getColumn() { return this.c; } getNumRows() { return this.nr; } getNumColumns() { return this.nc; }
  getA1Notation() { return a1Col(this.c) + this.r + (this.nr > 1 || this.nc > 1 ? ':' + a1Col(this.c + this.nc - 1) + (this.r + this.nr - 1) : ''); }
  setValue(v) { return this._each(c => { c.v = this.sheet._coerce(v, c.nf); }); }
  setValues(v) { this._grid(v, 'setValues'); return this._each((c, i, j) => { c.v = this.sheet._coerce(v[i][j], c.nf); }); }
  getValue() { const c = this.sheet._cell(this.r, this.c); return c && c.v !== undefined ? c.v : ''; }
  getValues() { const out = []; for (let i = 0; i < this.nr; i++) { const row = []; for (let j = 0; j < this.nc; j++) { const c = this.sheet._cell(this.r + i, this.c + j); row.push(c && c.v !== undefined ? c.v : ''); } out.push(row); } return out; }
  getDisplayValues() { return this.getValues().map(r => r.map(v => display(v, ''))); }
  _set(k, v) { return this._each(c => { c[k] = v; }); }
  _setGrid(k, v, name) { this._grid(v, name); return this._each((c, i, j) => { c[k] = v[i][j]; }); }
  setBackground(v) { return this._set('bg', v); } setBackgrounds(v) { return this._setGrid('bg', v, 'setBackgrounds'); }
  setFontColor(v) { return this._set('fc', v); } setFontColors(v) { return this._setGrid('fc', v, 'setFontColors'); }
  setFontWeight(v) { return this._set('fw', v); } setFontWeights(v) { return this._setGrid('fw', v, 'setFontWeights'); }
  setFontSize(v) { return this._set('fs', v); } setFontSizes(v) { return this._setGrid('fs', v, 'setFontSizes'); } setFontStyle(v) { return this._set('fi', v); } setFontLine(v) { return this._set('fl', v); }
  setFontFamily(v) { return this._set('ff', v); }
  setNumberFormat(v) { return this._set('nf', v); } setNumberFormats(v) { return this._setGrid('nf', v, 'setNumberFormats'); }
  setHorizontalAlignment(v) { return this._set('ha', v); } setHorizontalAlignments(v) { return this._setGrid('ha', v, 'setHorizontalAlignments'); }
  setVerticalAlignment(v) { return this._set('va', v); } setWrap(v) { return this._set('wrap', v); } setWrapStrategy() { return this; }
  setNote(v) { return this._set('note', v); } setDataValidation() { return this; } clearDataValidations() { return this; }
  setBorder(top, left, bottom, right, vert, horiz, color, style) {
    const w = style && /THICK/.test(style) ? 3 : style && /MEDIUM/.test(style) ? 2 : 1, b = { color: color || '#000', w };
    return this._each((c, i, j) => {
      if (top !== null && i === 0) c.bt = top ? b : null;
      if (bottom !== null && i === this.nr - 1) c.bb = bottom ? b : null;
      if (left !== null && j === 0) c.bl = left ? b : null;
      if (right !== null && j === this.nc - 1) c.br = right ? b : null;
    });
  }
  merge() { const c = this.sheet._cell(this.r, this.c, true); c.merge = { rows: this.nr, cols: this.nc }; return this; }
  breakApart() { const c = this.sheet._cell(this.r, this.c, true); delete c.merge; return this; }
  clear() { return this._each(c => { for (const k of Object.keys(c)) delete c[k]; }); }
  clearContent() { return this._each(c => { delete c.v; }); }
  clearFormat() { return this._each(c => { const v = c.v; for (const k of Object.keys(c)) delete c[k]; if (v !== undefined) c.v = v; }); }
  activate() { return this; }
  // формулы макет не считает: хранит текст; copyTo размножает значения/формулы первой строки источника на весь диапазон
  getFormula() { const c = this.sheet._cell(this.r, this.c); return c && c.f ? c.f : ''; }
  setFormula(f) { return this._set('f', f); }
  copyTo(dst) { const src = []; for (let j = 0; j < this.nc; j++) src.push(Object.assign({}, this.sheet._cell(this.r, this.c + j) || {}));
    return dst._each((c, i, j) => { const s = src[j % src.length]; if (s.v !== undefined) c.v = s.v; else delete c.v; if (s.f) c.f = s.f; }); }
}

class Sheet {
  constructor(ss, name) { Object.assign(this, { ss, name, cells: new Map(), maxRows: 1000, maxCols: 26, widths: {}, heights: {}, frozenRows: 0, frozenCols: 0, hidden: false, tab: null, grid: true }); }
  _cell(r, c, make) { const k = r + ',' + c; let x = this.cells.get(k); if (!x && make) { x = {}; this.cells.set(k, x); } return x; }
  _check(r, c) { if (r > this.maxRows || c > this.maxCols) throw new Error('Координаты диапазона находятся за пределами листа «' + this.name + '» (' + r + ',' + c + ' при ' + this.maxRows + '×' + this.maxCols + ')'); }
  _coerce(v, nf) {
    if (typeof v !== 'string' || nf === '@') return v;
    let m;
    const D = this.ss.DateCtor || Date;                                  // даты — из контекста кода, иначе instanceof Date там не сработает
    if ((m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/))) return new D(+m[1], +m[2] - 1, +m[3]);
    if ((m = v.match(/^(\d{1,2}):(\d{2})$/)) && +m[2] < 60) return new D(1899, 11, 30, +m[1], +m[2]);
    if (/^-?\d+(\.\d+)?$/.test(v.trim()) && v.trim() !== '') return Number(v);
    return v;
  }
  getName() { return this.name; } setName(n) { this.name = n; return this; } getSheetId() { return this.ss.sheets.indexOf(this); }
  getParent() { return this.ss; }
  getRange(r, c, nr, nc) {
    if (typeof r === 'string') {
      const m = r.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/); if (!m) throw new Error('A1 не разобран: ' + r);
      const col = s => s.split('').reduce((a, ch) => a * 26 + ch.charCodeAt(0) - 64, 0);
      const r1 = +m[2], c1 = col(m[1]), r2 = m[4] ? +m[4] : r1, c2 = m[3] ? col(m[3]) : c1;
      return new Range(this, r1, c1, r2 - r1 + 1, c2 - c1 + 1);
    }
    if (nr === 0 || nc === 0) throw new Error('Количество строк/столбцов в диапазоне должно быть не меньше 1');
    return new Range(this, r, c, nr, nc);
  }
  getDataRange() { return new Range(this, 1, 1, Math.max(1, this.getLastRow()), Math.max(1, this.getLastColumn())); }
  getLastRow() { let m = 0; for (const [k, x] of this.cells) if (x.v !== undefined && x.v !== '') m = Math.max(m, +k.split(',')[0]); return m; }
  getLastColumn() { let m = 0; for (const [k, x] of this.cells) if (x.v !== undefined && x.v !== '') m = Math.max(m, +k.split(',')[1]); return m; }
  getMaxRows() { return this.maxRows; } getMaxColumns() { return this.maxCols; }
  insertRowsAfter(r, n) { this.maxRows += n; return this; } insertColumnsAfter(c, n) { this.maxCols += n; return this; }
  insertRowsBefore(r, n) {                                             // строки r… сдвигаются вниз, как в Таблице
    const moved = new Map();
    for (const [k, x] of this.cells) { const [rr, cc] = k.split(',').map(Number); moved.set((rr >= r ? rr + n : rr) + ',' + cc, x); }
    this.cells = moved; this.maxRows += n; return this;
  }
  deleteRows(r, n) {
    const moved = new Map();
    for (const [k, x] of this.cells) { const [rr, cc] = k.split(',').map(Number); if (rr < r) moved.set(k, x); else if (rr >= r + n) moved.set((rr - n) + ',' + cc, x); }
    this.cells = moved; return this;
  }
  appendRow(row) { const r = this.getLastRow() + 1; this._check(r, row.length); this.getRange(r, 1, 1, row.length).setValues([row]); return this; }
  clear() { this.cells = new Map(); return this; } clearContents() { for (const x of this.cells.values()) delete x.v; return this; }
  clearFormats() { for (const x of this.cells.values()) { const v = x.v; for (const k of Object.keys(x)) delete x[k]; if (v !== undefined) x.v = v; } return this; }
  setColumnWidth(c, w) { this.widths[c] = w; return this; } setColumnWidths(c, n, w) { for (let i = 0; i < n; i++) this.widths[c + i] = w; return this; }
  setRowHeight(r, h) { this.heights[r] = h; return this; } setRowHeights(r, n, h) { for (let i = 0; i < n; i++) this.heights[r + i] = h; return this; }
  autoResizeColumns() { return this; } autoResizeColumn() { return this; }
  setFrozenRows(n) { this.frozenRows = n; return this; } setFrozenColumns(n) { this.frozenCols = n; return this; }
  getFrozenRows() { return this.frozenRows; } getFrozenColumns() { return this.frozenCols; }
  hideSheet() { this.hidden = true; return this; } showSheet() { this.hidden = false; return this; } isSheetHidden() { return this.hidden; }
  setTabColor(c) { this.tab = c; return this; } getTabColor() { return this.tab; }
  setHiddenGridlines(h) { this.grid = !h; return this; }
  activate() { this.ss.active = this; return this; }
  setConditionalFormatRules() { return this; } getConditionalFormatRules() { return []; }
  protect() { return { setWarningOnly() { return this; }, setDescription() { return this; } }; }
}

class Spreadsheet {
  constructor() { this.sheets = []; this.active = null; this.toasts = []; this.tz = 'Europe/Moscow'; }
  getSheetByName(n) { return this.sheets.find(s => s.name === n) || null; }
  insertSheet(n) { if (this.getSheetByName(n)) throw new Error('Лист «' + n + '» уже есть'); const s = new Sheet(this, n || ('Лист' + (this.sheets.length + 1))); this.sheets.push(s); this.active = s; return s; }
  getSheets() { return this.sheets.slice(); }
  deleteSheet(s) { this.sheets = this.sheets.filter(x => x !== s); }
  setActiveSheet(s) { if (!s) throw new Error('setActiveSheet: нет листа'); this.active = s; return s; }
  getActiveSheet() { return this.active; }
  moveActiveSheet(pos) { const s = this.active; this.sheets = this.sheets.filter(x => x !== s); this.sheets.splice(pos - 1, 0, s); }
  toast(msg) { this.toasts.push(String(msg)); } setSpreadsheetTimeZone(t) { this.tz = t; } getSpreadsheetTimeZone() { return this.tz; }
  getId() { return 'mock-spreadsheet'; } getName() { return 'макет'; } getUrl() { return 'https://docs.google.com/spreadsheets/d/mock'; }
}

/** Utilities.formatDate для Europe/Moscow (UTC+3 круглый год) и UTC. */
function formatDate(d, tz, f) {
  const off = /Moscow/.test(tz) ? 3 : 0, x = new Date(d.getTime() + off * 3600000), p = n => String(n).padStart(2, '0');
  const map = { yyyy: x.getUTCFullYear(), MM: p(x.getUTCMonth() + 1), dd: p(x.getUTCDate()), HH: p(x.getUTCHours()), mm: p(x.getUTCMinutes()), ss: p(x.getUTCSeconds()),
    M: x.getUTCMonth() + 1, d: x.getUTCDate(), H: x.getUTCHours(), E: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][x.getUTCDay()] };
  return f.replace(/yyyy|MM|dd|HH|mm|ss|M|d|H|E/g, k => map[k]);
}

function makeEnv(opt) {
  opt = opt || {};
  const ss = new Spreadsheet(), props = {}, alerts = [], log = [], others = {}, cacheMap = new Map();
  const RealDate = Date, nowMs = opt.now ? new RealDate(opt.now).getTime() : RealDate.now();
  class MockDate extends RealDate { constructor(...a) { if (a.length === 0) super(nowMs); else super(...a); } static now() { return nowMs; } }
  ss.DateCtor = MockDate;
  const store = {
    getProperty: k => (k in props ? props[k] : null), setProperty: (k, v) => { props[k] = String(v); return store; },
    deleteProperty: k => { delete props[k]; return store; }, getKeys: () => Object.keys(props), getProperties: () => Object.assign({}, props),
    setProperties: o => { Object.assign(props, o); return store; },
  };
  const ui = {
    alert: (...a) => { alerts.push(a.filter(x => typeof x === 'string').join(' | ')); return 'YES'; }, prompt: () => ({ getSelectedButton: () => 'CANCEL', getResponseText: () => '' }),
    createMenu: () => { const m = { addItem: () => m, addSeparator: () => m, addSubMenu: () => m, addToUi: () => m }; return m; },
    Button: { YES: 'YES', NO: 'NO', OK: 'OK', CANCEL: 'CANCEL' }, ButtonSet: { YES_NO: 1, OK_CANCEL: 2, OK: 3 },
  };
  const builder = () => { const b = new Proxy({}, { get: (t, k) => k === 'build' ? () => ({}) : () => b }); return b; };
  const ctx = {
    console: { log: (...a) => log.push(a.join(' ')), error: (...a) => log.push('ERR ' + a.join(' ')) },
    Date: MockDate, Math, JSON, Number, String, Object, Array, RegExp, Error, isFinite, isNaN, parseInt, parseFloat, encodeURIComponent, decodeURIComponent, Map, Set,
    SpreadsheetApp: { getActive: () => ss, getActiveSpreadsheet: () => ss, getUi: () => ui, flush() {},
      openById: id => { if (others[id]) { others[id].opened = (others[id].opened || 0) + 1; return others[id]; } throw new Error('макет: нет доступа к таблице ' + id); }, BorderStyle: { SOLID: 'SOLID', SOLID_MEDIUM: 'SOLID_MEDIUM', SOLID_THICK: 'SOLID_THICK', DASHED: 'DASHED', DOTTED: 'DOTTED' },
      newDataValidation: builder, newConditionalFormatRule: builder, newRichTextValue: builder },
    PropertiesService: { getScriptProperties: () => store, getDocumentProperties: () => store, getUserProperties: () => store },
    Utilities: { formatDate,
      // только 'yyyy-MM-dd' и 'yyyy-MM-dd HH:mm'; Москва — UTC+3, остальное — как UTC
      parseDate: (t, tz, f) => new MockDate(String(t).replace(' ', 'T') + (String(t).length <= 10 ? 'T00:00:00' : ':00') + (tz === 'Europe/Moscow' ? '+03:00' : 'Z')), sleep() {}, base64Encode: s => Buffer.from(String(s)).toString('base64'), newBlob: s => ({ getDataAsString: () => String(s) }),
      computeDigest: () => [], DigestAlgorithm: {}, Charset: {} },
    UrlFetchApp: { fetch: u => { throw new Error('макет: сеть закрыта (' + String(u).slice(0, 60) + ')'); }, fetchAll: () => { throw new Error('макет: сеть закрыта'); } },
    ScriptApp: { getProjectTriggers: () => [], deleteTrigger() {}, newTrigger: () => builder(), getOAuthToken: () => 'mock', WeekDay: { MONDAY: 'MONDAY' } },
    CacheService: { getScriptCache: () => (opt.cache ? { get: k => (cacheMap.has(k) ? cacheMap.get(k) : null), put: (k, v) => { cacheMap.set(k, String(v)); },
      remove: k => { cacheMap.delete(k); } } : { get: () => null, put() {}, remove() {} }) },   // opt.cache — память между вызовами, иначе всегда пусто
    LockService: { getScriptLock: () => ({ tryLock: () => true, waitLock() {}, releaseLock() {} }) },
    Session: { getScriptTimeZone: () => 'Europe/Moscow', getActiveUser: () => ({ getEmail: () => '' }) },
    MailApp: { sendEmail() {} }, DriveApp: {},
    Logger: { log: (...a) => { log.push('LOG ' + a.join(' ')); } },
  };
  vm.createContext(ctx);
  // вторая таблица для SpreadsheetApp.openById(id): env.addSpreadsheet(id)
  const addSpreadsheet = id => { const o = new Spreadsheet(); o.DateCtor = MockDate; others[id] = o; return o; };
  return { ctx, ss, props, alerts, log, addSpreadsheet, cache: cacheMap };
}

/** Загрузить файлы проекта в контекст — как Apps Script: общий глобальный объём, по порядку. */
function load(env, files) { files.forEach(f => vm.runInContext(fs.readFileSync(f, 'utf8'), env.ctx, { filename: f })); return env; }

/* ---------------- HTML-снимок книги ---------------- */
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function display(v, nf) {
  if (v === undefined || v === null || v === '') return '';
  if (v instanceof Date) { const p = n => String(n).padStart(2, '0'); return v.getFullYear() < 1900 ? p(v.getHours()) + ':' + p(v.getMinutes()) : p(v.getDate()) + '.' + p(v.getMonth() + 1) + '.' + v.getFullYear(); }
  if (typeof v === 'number') {
    let m;
    if (nf && (m = nf.match(/^0(?:\.(0+))?(%?)$/))) { const d = m[1] ? m[1].length : 0; return (m[2] ? (v * 100).toFixed(d) + '%' : v.toFixed(d)).replace('.', ','); }
    return String(Math.round(v * 1e6) / 1e6).replace('.', ',');
  }
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
  return String(v);
}
function sheetHtml(sh) {
  const R = Math.max(sh.getLastRow(), 4) + 1, C = Math.max(sh.getLastColumn(), 1);
  const cover = new Set();
  let total = 36; for (let c = 1; c <= C; c++) total += sh.widths[c] || 100;
  let html = '<table class="g' + (sh.grid ? '' : ' nogrid') + '" style="width:' + total + 'px"><colgroup><col style="width:36px">';
  for (let c = 1; c <= C; c++) html += '<col style="width:' + (sh.widths[c] || 100) + 'px">';
  html += '</colgroup><tr class="hdr"><th></th>';
  for (let c = 1; c <= C; c++) html += '<th class="' + (c === sh.frozenCols ? 'fz-c' : '') + '">' + a1Col(c) + '</th>';
  html += '</tr>';
  for (let r = 1; r <= R; r++) {
    html += '<tr style="height:' + (sh.heights[r] || 21) + 'px"' + (r === sh.frozenRows ? ' class="fz-r"' : '') + '><th>' + r + '</th>';
    for (let c = 1; c <= C; c++) {
      if (cover.has(r + ',' + c)) continue;
      const x = sh._cell(r, c) || {}, st = [];
      if (x.bg) st.push('background:' + x.bg);
      if (x.fc) st.push('color:' + x.fc);
      if (x.fw === 'bold') st.push('font-weight:700');
      if (x.fi === 'italic') st.push('font-style:italic');
      if (x.fs) st.push('font-size:' + (x.fs * 1.333).toFixed(1) + 'px');
      const num = typeof x.v === 'number';
      st.push('text-align:' + (x.ha || (num ? 'right' : 'left')));
      st.push('vertical-align:' + (x.va === 'middle' ? 'middle' : x.va === 'top' ? 'top' : 'bottom'));
      st.push(x.wrap ? 'white-space:normal' : 'white-space:nowrap');
      if (x.bt) st.push('border-top:' + x.bt.w + 'px solid ' + x.bt.color);
      if (x.bb) st.push('border-bottom:' + x.bb.w + 'px solid ' + x.bb.color);
      if (c === sh.frozenCols) st.push('border-right:2px solid #bdc1c6');
      let span = '';
      if (x.merge) {
        span = ' colspan="' + x.merge.cols + '" rowspan="' + x.merge.rows + '"';
        for (let i = 0; i < x.merge.rows; i++) for (let j = 0; j < x.merge.cols; j++) if (i || j) cover.add((r + i) + ',' + (c + j));
      }
      html += '<td' + span + ' style="' + st.join(';') + '">' + esc(display(x.v, x.nf)) + '</td>';
    }
    html += '</tr>';
  }
  return html + '</table>';
}
/** Вся книга: вкладки (скрытые — отдельно) и выбранные листы. */
function renderHtml(ss, names) {
  const vis = ss.sheets.filter(s => !s.hidden), hid = ss.sheets.filter(s => s.hidden);
  const tabs = vis.map(s => '<span class="tab" style="border-bottom:4px solid ' + (s.tab || 'transparent') + '">' + esc(s.name) + '</span>').join('') +
    (hid.length ? '<span class="hid">скрыты: ' + hid.map(s => esc(s.name)).join(', ') + '</span>' : '');
  const pick = (names || vis.map(s => s.name)).map(n => ss.getSheetByName(n)).filter(Boolean);
  return '<!doctype html><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;font-size:13.3px;margin:0;background:#fff;color:#202124}' +
    '.tabs{padding:8px 10px;background:#f1f3f4;border-bottom:1px solid #dadce0;position:sticky;top:0}.tab{display:inline-block;margin-right:6px;padding:4px 10px;background:#fff;border-radius:4px 4px 0 0;font-size:12px}' +
    '.hid{color:#80868b;font-size:12px;margin-left:12px}h2{font:600 14px Arial;margin:18px 10px 6px;color:#5f6368}' +
    'table.g{border-collapse:collapse;table-layout:fixed;margin:0 10px 20px}table.g td,table.g th{border:1px solid #e2e3e3;padding:2px 4px;overflow:visible;line-height:1.2}' +
    'table.g.nogrid td{border-color:transparent}table.g th{background:#f8f9fa;color:#80868b;font-weight:400;font-size:11px;text-align:center}' +
    'tr.fz-r td,tr.fz-r th{border-bottom:2px solid #bdc1c6 !important}</style>' +
    '<div class="tabs">' + tabs + '</div>' + pick.map(s => '<h2 id="' + esc(s.name) + '">' + esc(s.name) + '</h2>' + sheetHtml(s)).join('');
}

module.exports = { makeEnv, load, renderHtml, sheetHtml, display };
