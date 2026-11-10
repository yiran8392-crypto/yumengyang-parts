/* 级联筛选（品牌 → 车型 → 年款 → 排量）
   数据来源：data/facets.js（facets_build.py 生成，含品牌/车系词典与统计）
   逻辑：车型/品牌在浏览器里按同一套词典解析并缓存到 item._fb / item._fm，
        选项列表直接用 facets 里的统计（首屏就有全量，不用等 29 个分片）。
   挂到 window.FACETS。 */
(function () {
  "use strict";
  if (typeof window === "undefined") return;

  var CAT = window.YMY_FACETS || null;
  var ALIAS = (CAT && CAT.aliases) || {};
  var MODELS = (CAT && CAT.models) || {};
  var STOP = {};
  if (CAT && CAT.stop) for (var s = 0; s < CAT.stop.length; s++) STOP[CAT.stop[s]] = 1;

  var ALIAS_KEYS = Object.keys(ALIAS).sort(function (a, b) { return b.length - a.length; });
  var ALIAS_NORM = {};
  for (var ak in ALIAS) ALIAS_NORM[ak.replace(/[^A-Z0-9]/g, "")] = ALIAS[ak];

  var TOK = /[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*/g;
  var CODEY = /^(?:[A-Za-z]{1,3}\d|\d)/;
  var NOW = new Date().getFullYear();

  function norm(v) { return String(v || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase(); }
  function tidy(a) {
    return " " + String(a || "").toUpperCase().replace(/[^A-Z ]+/g, " ").replace(/\s+/g, " ").trim() + " ";
  }

  function brandsOf(a) {
    var t = tidy(a), out = [];
    for (var i = 0; i < ALIAS_KEYS.length; i++) {
      var k = ALIAS_KEYS[i];
      if (t.indexOf(" " + k + " ") < 0) continue;
      var canon = ALIAS[k];
      if (out.indexOf(canon) < 0) out.push(canon);
    }
    return out;
  }

  function okModel(key, brand, seen) {
    if (key.length < 3 || key.length > 14 || seen[key]) return false;
    if (STOP[key] || ALIAS_NORM[key]) return false;
    if (CODEY.test(key)) return false;
    var owner = MODELS[key];
    if (owner && owner !== brand) return false;
    return true;
  }

  function modelsOf(a, bs) {
    var toks = String(a || "").match(TOK) || [], keys = [], out = [], seen = {}, i, j;
    for (i = 0; i < toks.length; i++) keys.push(norm(toks[i]));
    // 1) 词典登记过的车系
    for (i = 0; i < keys.length; i++) {
      var k = keys[i], owner = MODELS[k];
      if (owner && bs.indexOf(owner) >= 0 && !seen[k]) { seen[k] = 1; out.push(k); }
    }
    // 2) 品牌名后面 1–2 个词
    for (i = 0; i < keys.length; i++) {
      var brand = ALIAS_NORM[keys[i]];
      if (!brand || bs.indexOf(brand) < 0) continue;
      for (j = i + 1; j <= i + 2 && j < keys.length; j++) {
        var m = keys[j];
        if (!okModel(m, brand, seen)) continue;
        seen[m] = 1; out.push(m);
      }
    }
    return out;
  }

  function parseItem(it) {
    if (it._fb) return;
    var a = it.a || "";
    var bs = brandsOf(a);
    var ms = bs.length ? modelsOf(a, bs) : [];
    it._fb = bs;
    it._fm = ms;
    // 年款区间（文本兜底只在没有 y 时才用）
    var ymin = 0, ymax = 0;
    if (it.y && it.y.length) {
      for (var q = 0; q < it.y.length; q++) {
        var ys = String(it.y[q] || "").trim();
        var my = /^((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2})?)?$/.exec(ys);
        if (!my) continue;
        var y1 = +my[1], y2 = my[2] ? +my[2] : y1;
        if (ys.charAt(ys.length - 1) === "-") y2 = NOW;
        y2 = Math.min(y2, NOW);
        if (y1 < 1970 || y1 > NOW) continue;
        ymin = ymin ? Math.min(ymin, y1) : y1;
        ymax = ymax ? Math.max(ymax, y2) : y2;
      }
    }
    it._fy = ymin ? [ymin, ymax] : null;
    var ds = [];
    if (it.d && it.d.length) {
      for (var w = 0; w < it.d.length; w++) {
        var dv = parseFloat(String(it.d[w] || ""));
        if (dv >= 0.5 && dv <= 8.0 && ds.indexOf(dv) < 0) ds.push(dv);
      }
    }
    it._fd = ds;
  }

  function build(items) {
    for (var i = 0; i < items.length; i++) parseItem(items[i]);
  }

  function catalogBrand(name) {
    if (!CAT) return null;
    for (var i = 0; i < CAT.brands.length; i++) if (CAT.brands[i][0] === name) return CAT.brands[i];
    return null;
  }

  function catalogModel(brand, key) {
    var b = catalogBrand(brand);
    if (!b) return null;
    for (var i = 0; i < b[2].length; i++) if (b[2][i][0] === key) return b[2][i];
    return null;
  }

  function counts(items, sel, cat) {
    var bc = {}, mc = {}, yc = {}, dc = {}, i, it;
    for (i = 0; i < items.length; i++) {
      it = items[i];
      if (cat !== "all" && it.c !== cat) continue;
      parseItem(it);
      for (var b = 0; b < it._fb.length; b++) if (!sel.b || it._fb[b] === sel.b) bc[it._fb[b]] = (bc[it._fb[b]] || 0) + 1;
      if (sel.b && it._fb.indexOf(sel.b) < 0) continue;
      for (var m = 0; m < it._fm.length; m++) mc[it._fm[m]] = (mc[it._fm[m]] || 0) + 1;
      if (sel.m && it._fm.indexOf(sel.m) < 0) continue;
      if (it._fy) for (var y = it._fy[0]; y <= it._fy[1]; y++) yc[y] = (yc[y] || 0) + 1;
      for (var d = 0; d < it._fd.length; d++) dc[it._fd[d]] = (dc[it._fd[d]] || 0) + 1;
    }
    return { bc: bc, mc: mc, yc: yc, dc: dc };
  }

  function opts(items, sel, cat) {
    var c = counts(items, sel, cat), i;
    var brands = [], models = [], years = [], disps = [];

    if (CAT && cat === "all") {
      for (i = 0; i < CAT.brands.length; i++) brands.push({ v: CAT.brands[i][0], n: CAT.brands[i][1] });
    } else {
      for (var b in c.bc) brands.push({ v: b, n: c.bc[b] });
      brands.sort(function (x, y) { return y.n - x.n; });
    }

    if (sel.b) {
      var cb = CAT && cat === "all" ? catalogBrand(sel.b) : null;
      if (cb) {
        for (i = 0; i < cb[2].length; i++) models.push({ v: cb[2][i][0], label: cb[2][i][1], n: cb[2][i][2] });
      } else {
        for (var mk in c.mc) models.push({ v: mk, label: mk, n: c.mc[mk] });
        models.sort(function (x, y) { return y.n - x.n; });
      }
    }

    if (sel.m) {
      var cm = CAT && cat === "all" ? catalogModel(sel.b, sel.m) : null;
      var y0 = cm ? cm[3] : 0, y1 = cm ? cm[4] : 0;
      if (!y0) for (var k in c.yc) { if (!y0 || +k < y0) y0 = +k; if (+k > y1) y1 = +k; }
      for (var y = y1; y >= y0; y--) years.push({ v: y, label: y, n: c.yc[y] || 0 });
      var dm = cm ? cm[5] : null;
      if (dm && dm.length) for (i = 0; i < dm.length; i++) disps.push({ v: dm[i], label: dm[i] + " L", n: c.dc[dm[i]] || 0 });
      else {
        var dk = Object.keys(c.dc).map(Number).sort(function (a, b) { return a - b; });
        for (i = 0; i < dk.length; i++) disps.push({ v: dk[i], label: dk[i] + " L", n: c.dc[dk[i]] });
      }
    }

    return { brands: brands, models: models, years: years, disps: disps };
  }

  function match(it, sel) {
    parseItem(it);
    if (sel.b && it._fb.indexOf(sel.b) < 0) return false;
    if (sel.m && it._fm.indexOf(sel.m) < 0) return false;
    if (sel.y && (!it._fy || it._fy[0] > sel.y || it._fy[1] < sel.y)) return false;
    if (sel.d && (it._fd || []).indexOf(sel.d) < 0) return false;
    return true;
  }

  window.FACETS = { build: build, opts: opts, match: match, modelOf: function (k) { return MODELS[k] || ""; }, catalog: CAT };
})();
