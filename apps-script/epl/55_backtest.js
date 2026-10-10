/* ==========================================================================
 * ПРОВЕРКА МОДЕЛИ НА ПРОШЛЫХ СЕЗОНАХ (честно, «вслепую»)
 * --------------------------------------------------------------------------
 * Берём два последних завершённых сезона из «Архив_сезонов». Перед каждой игровой неделей модель
 * строится только по матчам, сыгранным ДО неё, и даёт прогноз на матчи недели. Потом сравниваем
 * с исходами и с закрывающей линией букмекера (Pinnacle без маржи):
 *  • Brier и логлосс по П1/Х/П2 — меньше лучше;
 *  • какая доля линии в «лучшем прогнозе» даёт самый точный результат;
 *  • тотал 2,5 — модель против линии.
 * Перебираются настройки модели (период полураспада, доля xG/ударов, поправка на ничьи, новички).
 * Лучший вариант пишется на лист «Проверка модели» и применяется кнопкой (при первой настройке — сам).
 * Длинный перебор не помещается в 6 минут Google — продолжается сам следующими запусками.
 * ========================================================================== */

var SHEET_BT = 'Проверка модели';
var BT_SEASONS = 2;
var BT_MAX_MS = 270000;
var BT_BLENDS = [0, 0.25, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1];
var BLEND_W_MAX = 0.9;            // модель в «лучшем прогнозе» всегда остаётся хотя бы на 10%: линия есть не у всех матчей и бывает недоступна

function btGrid_(best) {
  if (!best) {
    var g = [];
    [120, 180, 270, 365, 540].forEach(function (h) { [0, 0.35, 0.6, 0.8].forEach(function (p) { g.push({ half: h, proc: p }); }); });
    return g;
  }
  var b = { half: best.half, proc: best.proc };
  var out = [];
  [-0.13, -0.04, 0].forEach(function (r) { out.push(Object.assign({}, b, { rho: r })); });
  [0.08, 0.3].forEach(function (x) { out.push(Object.assign({}, b, { promo: x })); });
  [2, 8].forEach(function (x) { out.push(Object.assign({}, b, { prior: x })); });
  return out;
}

/** Данные для проверки: матчи архива, сезоны для оценки и новички каждого сезона. */
function btData_(ss) {
  var arch = archiveRead_(ss), cur = seasonLabel_(seasonStartYear_());
  arch = arch.filter(function (m) { return m.season !== cur; });
  if (arch.length < 800) throw new Error('в архиве мало матчей (' + arch.length + ') — сначала «Загрузить архив сезонов»');
  var seasons = []; arch.forEach(function (m) { if (seasons.indexOf(m.season) < 0) seasons.push(m.season); });
  seasons.sort();
  var evalS = seasons.slice(-BT_SEASONS), rate = sotRate_(arch);
  var teamsBy = {}; arch.forEach(function (m) { (teamsBy[m.season] = teamsBy[m.season] || {})[m.home] = true; teamsBy[m.season][m.away] = true; });
  var newBy = {};
  seasons.forEach(function (s, i) { newBy[s] = {}; if (!i) return; Object.keys(teamsBy[s]).forEach(function (t) { if (!teamsBy[seasons[i - 1]][t]) newBy[s][t] = true; }); });
  var games = modelGames_(arch, rate);
  arch.forEach(function (m, i) { games[i].season = m.season; games[i].odds = [m.o1, m.ox, m.o2]; games[i].ou = [m.oOver, m.oUnder]; });
  return { games: games, evalS: evalS, newBy: newBy };
}
function weekStart_(t) { var d = new Date(t); var wd = (d.getUTCDay() + 6) % 7; return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - wd); }

/** Один прогон проверки с параметрами P. */
function btRun_(D, P) {
  var acc = { n: 0, b: 0, l: 0, nm: 0, bm: 0, lm: 0, bMod: 0, blend: {}, tn: 0, tb: 0, tbm: 0 };
  BT_BLENDS.forEach(function (w) { acc.blend[w] = { b: 0, l: 0 }; });
  var warm = null, wk = null, fit = null;
  D.games.forEach(function (g) {
    if (D.evalS.indexOf(g.season) < 0) return;
    var w0 = weekStart_(g.t);
    if (w0 !== wk) { fit = modelFit_(D.games, w0, P, D.newBy[g.season], warm); warm = fit; wk = w0; }
    var p = modelPredict_(fit, g.home, g.away), pm = [p.p1, p.px, p.p2];
    var act = g.hg > g.ag ? 0 : g.hg === g.ag ? 1 : 2;
    acc.n++; acc.b += brier3_(pm, act); acc.l += ll3_(pm, act);
    var f = fairProbs_(g.odds);
    if (f) {
      acc.nm++; acc.bm += brier3_(f, act); acc.lm += ll3_(f, act); acc.bMod += brier3_(pm, act);
      BT_BLENDS.forEach(function (w) { var pb = [0, 1, 2].map(function (i) { return w * f[i] + (1 - w) * pm[i]; }); acc.blend[w].b += brier3_(pb, act); acc.blend[w].l += ll3_(pb, act); });
    }
    var fo = fairProbs_(g.ou);
    if (fo) { var o = g.hg + g.ag > 2.5 ? 1 : 0; acc.tn++; acc.tb += Math.pow(p.o25 - o, 2); acc.tbm += Math.pow(fo[0] - o, 2); }
  });
  var bestW = null;
  BT_BLENDS.forEach(function (w) { if (acc.nm && (bestW === null || acc.blend[w].l < acc.blend[bestW].l)) bestW = w; });
  return { P: P, n: acc.n, brier: acc.b / acc.n, ll: acc.l / acc.n, nm: acc.nm, brierMkt: acc.nm ? acc.bm / acc.nm : null, llMkt: acc.nm ? acc.lm / acc.nm : null,
    bestW: bestW, llBlend: bestW !== null ? acc.blend[bestW].l / acc.nm : null, brierBlend: bestW !== null ? acc.blend[bestW].b / acc.nm : null,
    blend: BT_BLENDS.map(function (w) { return [w, acc.nm ? acc.blend[w].l / acc.nm : null]; }),
    tot: acc.tn ? [acc.tb / acc.tn, acc.tbm / acc.tn, acc.tn] : null };
}

/** Перебор настроек с продолжением. auto=true — без окон; apply=true — применить лучший вариант в конце. */
function backtestRun_(auto, apply) {
  var ss = SpreadsheetApp.getActive(), t0 = Date.now();
  var st = propJson_('BT_STATE', null);
  if (!st || st.done) st = { stage: 'A', i: 0, res: [], apply: !!apply, started: mskNow_() };
  var D = btData_(ss);
  while (true) {
    var bestA = st.stage === 'B' ? btBest_(st.res.filter(function (r) { return r.stage === 'A'; })) : null;
    var grid = btGrid_(bestA ? bestA.P : null);
    if (st.i >= grid.length) {
      if (st.stage === 'A') { st.stage = 'B'; st.i = 0; continue; }
      st.done = true; break;
    }
    var P = Object.assign({}, MODEL_DEFAULT, grid[st.i]);
    var r = btRun_(D, P); r.stage = st.stage;
    st.res.push(r); st.i++;
    propSetJson_('BT_STATE', st);
    if (Date.now() - t0 > BT_MAX_MS) break;
  }
  propSetJson_('BT_STATE', st);
  btRender_(ss, st);
  if (!st.done) {
    btScheduleContinue_();
    if (!auto) uiAlert_('Проверка идёт: готово ' + st.res.length + ' вариантов. Продолжу сам через минуту, итог — на листе «' + SHEET_BT + '».');
    return { done: false, runs: st.res.length };
  }
  btUnschedule_();
  var best = btBest_(st.res);
  if (st.apply && best) btApply_(best);
  if (!auto) { sheetOpen_(SHEET_BT); uiAlert_(btSummary_(best) + (st.apply ? '\n\nЛучший вариант применён.' : '\n\nПрименить: меню «⚽ АПЛ» → Модель → «Применить лучший вариант проверки».')); }
  return { done: true, runs: st.res.length, best: best };
}
/** Лучшие настройки — по точности самой модели (логлосс); доля линии в «лучшем прогнозе» — отдельно, при этих настройках. */
function btBest_(res) {
  var b = null;
  res.forEach(function (r) { if (!b || r.ll < b.ll) b = r; });
  return b;
}
function btApply_(best) {
  var P = {}; ['half', 'proc', 'rho', 'prior', 'promo'].forEach(function (k) { P[k] = best.P[k]; });
  propSetJson_('MODEL_PARAMS', P);
  if (best.bestW !== null) props_().setProperty('BLEND_W', String(Math.min(BLEND_W_MAX, best.bestW)));
  props_().setProperty('MODEL_PARAMS_TS', mskNow_());
  FIT_CACHE_ = null;
}
function btApplyBest_() {
  var st = propJson_('BT_STATE', null);
  if (!st || !st.done) { uiAlert_('Проверка ещё не закончена — сначала «Проверить модель на прошлых сезонах».'); return; }
  var best = btBest_(st.res); btApply_(best);
  try { refreshModelSheets_(SpreadsheetApp.getActive()); } catch (e) {}
  uiAlert_('Применено: ' + btParamsText_(best.P) + (best.bestW !== null ? ', доля линии в «лучшем прогнозе» ' + Math.round(best.bestW * 100) + '%' : '') + '.');
}
function btParamsText_(P) {
  return 'полураспад ' + P.half + ' дн., доля «игры» (xG/удары) ' + Math.round(P.proc * 100) + '%, поправка на ничьи ' + P.rho + ', новичок слабее на ' + P.promo + ', приор ' + P.prior + ' матча';
}
function btSummary_(b) {
  if (!b) return 'Нет результатов.';
  return 'Лучший вариант (' + b.n + ' матчей двух сезонов, прогноз строился только по прошлым матчам):\n' + btParamsText_(b.P) + '.\n\n' +
    'Brier модели ' + b.brier.toFixed(4) + (b.brierMkt !== null ? ', букмекера ' + b.brierMkt.toFixed(4) : '') +
    (b.bestW !== null ? '; точнее всего смесь ' + Math.round(b.bestW * 100) + '% линии + ' + Math.round((1 - b.bestW) * 100) + '% модели (Brier ' + b.brierBlend.toFixed(4) + ')' + (b.bestW > BLEND_W_MAX ? ', в «лучший прогноз» берётся не больше ' + Math.round(BLEND_W_MAX * 100) + '% линии' : '') : '') + '.';
}
function btRender_(ss, st) {
  var sh = sheet_(ss, SHEET_BT), rows = st.res.map(function (r) {
    return [r.stage, r.P.half, Math.round(r.P.proc * 100) + '%', r.P.rho, r.P.promo, r.P.prior, r.n, r.brier.toFixed(4), r.ll.toFixed(4),
      r.brierMkt !== null ? r.brierMkt.toFixed(4) : '', r.llMkt !== null ? r.llMkt.toFixed(4) : '',
      r.bestW !== null ? Math.round(r.bestW * 100) + '%' : '', r.brierBlend !== null ? r.brierBlend.toFixed(4) : '', r.llBlend !== null ? r.llBlend.toFixed(4) : '',
      r.tot ? r.tot[0].toFixed(4) + ' / ' + r.tot[1].toFixed(4) : ''];
  });
  sh.clear();
  sh.getRange(1, 1).setValue('ПРОВЕРКА МОДЕЛИ на прошлых сезонах · ' + (st.done ? 'готово' : 'идёт') + ' · начата ' + st.started).setFontWeight('bold').setFontSize(12);
  var best = btBest_(st.res);
  sh.getRange(2, 1).setValue(best ? btSummary_(best).replace(/\n+/g, ' ') : '').setFontColor('#666666');
  writeTable_(sh, ['Этап', 'Полураспад, дн.', 'Доля xG/ударов', 'Ничьи (rho)', 'Новичок слабее', 'Приор, матчей', 'Матчей', 'Brier модели', 'Логлосс модели',
    'Brier букмекера', 'Логлосс букмекера', 'Лучшая доля линии', 'Brier «лучшего»', 'Логлосс «лучшего»', 'Тотал 2,5: Brier модель / линия'], rows, { top: 4, clear: false });
  if (best) {
    var bi = st.res.indexOf(best);
    try { sh.getRange(5 + bi, 1, 1, 15).setBackground('#d9f2e3').setFontWeight('bold'); } catch (e) {}
    var bl = best.blend.filter(function (x) { return x[1] !== null; }).map(function (x) { return [Math.round(x[0] * 100) + '% линия', x[1].toFixed(4)]; });
    if (bl.length) writeTable_(sh, ['«Лучший прогноз» при лучших настройках', 'Логлосс'], bl, { top: 7 + rows.length, clear: false });
  }
}
function btScheduleContinue_() {
  btUnschedule_();
  try { ScriptApp.newTrigger('btContinue_').timeBased().after(60 * 1000).create(); } catch (e) {}
}
function btUnschedule_() { try { ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'btContinue_') ScriptApp.deleteTrigger(t); }); } catch (e) {} }
function btContinue_() {
  btUnschedule_();
  runAuto_('btContinue_', function () {
    var r = backtestRun_(true, (propJson_('BT_STATE', {}) || {}).apply);
    if (r.done) { try { refreshModelSheets_(SpreadsheetApp.getActive()); } catch (e) {} return 'проверка модели завершена: вариантов ' + r.runs + (r.best ? '; ' + btParamsText_(r.best.P) : ''); }
    return 'проверка модели: готово вариантов ' + r.runs + ', продолжу';
  });
}
function backtestNow_() { props_().deleteProperty('BT_STATE'); backtestRun_(false, false); }
