/* 级联筛选（品牌 / 车型 / 年款 / 排量 —— 谁先选都行）
   数据来源：data/facets.js（facets_build.py 生成，每个车系带「年段 → 排量」）
   选项怎么来：
     · 品类 = 全部时，直接按 facets 的统计算（秒出、全量，不用等 29 个分片）
     · 选中某个品类时，退回按已加载的型号现算（品类不在 facets 的统计维度里）
   规则：车型要先有品牌（同一个车系名会跨品牌）；品牌 / 年款 / 排量随时可选。
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
    for (i = 0; i < keys.length; i++) {
      var k = keys[i], owner = MODELS[k];
      if (owner && bs.indexOf(owner) >= 0 && !seen[k]) { seen[k] = 1; out.push(k); }
    }
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

  /* 排量 token：和 facets_build.py 同一套规则（一位小数 + L/T，「1.4T」不会被当成 1.4L） */
  function dispTok(raw) {
    var m = /^(\d(?:\.\d+)?)\s*([LT])?$/i.exec(String(raw || "").trim());
    if (!m) return "";
    var v = parseFloat(m[1]);
    if (!(v >= 0.5 && v <= 8.0)) return "";
    return v.toFixed(1) + (m[2] ? m[2].toUpperCase() : "L");
  }

  function dispCmp(a, b) {
    var ma = /^([\d.]+)([LT])$/.exec(a) || [0, "99", "Z"];
    var mb = /^([\d.]+)([LT])$/.exec(b) || [0, "99", "Z"];
    return (+ma[1] - +mb[1]) || ((ma[2] === "L" ? 0 : 1) - (mb[2] === "L" ? 0 : 1));
  }

  function parseItem(it) {
    if (it._fb) return;
    var a = it.a || "";
    var bs = brandsOf(a);
    var ms = bs.length ? modelsOf(a, bs) : [];
    it._fb = bs;
    it._fm = ms;
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
        var t = dispTok(it.d[w]);
        if (t && ds.indexOf(t) < 0) ds.push(t);
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

  /* ---------- 车系上的「年段 → 排量」（facets 统计里最后一个字段） ---------- */
  function spansOf(m) { return (m && m[6]) || []; }

  function fits(m, y, d) {
    if (!y && !d) return true;
    var sp = spansOf(m);
    for (var i = 0; i < sp.length; i++) {
      var s = sp[i];
      if (y && (y < s[0] || y > s[1])) continue;
      if (d && ("," + s[2] + ",").indexOf("," + d + ",") < 0) continue;
      return true;
    }
    return false;
  }

  /* ---------- 方案 A：选项直接按 facets 统计算（品类 = 全部时用） ---------- */
  function optsFromCatalog(sel) {
    var bs = (CAT && CAT.brands) || [];
    var brands = [], models = [], years = [], disps = [], yset = {}, dset = {}, i, j, y;
    var showN = !sel.y && !sel.d;
    var scopeModels = [];      /* 品牌/车型已经定下来的车系 */

    for (i = 0; i < bs.length; i++) {
      var okBrand = false, bm = bs[i][2];
      for (j = 0; j < bm.length; j++) {
        if (!fits(bm[j], sel.y, sel.d)) continue;
        okBrand = true;
        if ((!sel.b || bs[i][0] === sel.b) && (!sel.m || bm[j][0] === sel.m)) scopeModels.push(bm[j]);
      }
      if (okBrand) brands.push({ v: bs[i][0], n: showN ? bs[i][1] : null });
    }

    if (sel.b) {
      var cb = catalogBrand(sel.b);
      var cbModels = cb ? cb[2] : [];
      for (i = 0; i < cbModels.length; i++) {
        var m = cbModels[i];
        if (!fits(m, sel.y, sel.d)) continue;
        models.push({ v: m[0], label: m[1], n: showN ? m[2] : null });
      }
    }

    for (i = 0; i < scopeModels.length; i++) {
      var sp = spansOf(scopeModels[i]);
      for (j = 0; j < sp.length; j++) {
        var s = sp[j], toks = s[2] ? s[2].split(",") : [];
        if (!sel.d) {
          for (y = s[0]; y <= s[1]; y++) yset[y] = 1;
        } else if (toks.indexOf(sel.d) >= 0) {
          for (y = s[0]; y <= s[1]; y++) yset[y] = 1;
        }
        if (sel.y && (sel.y < s[0] || sel.y > s[1])) continue;
        for (var t = 0; t < toks.length; t++) dset[toks[t]] = 1;
      }
    }

    var yk = Object.keys(yset).map(Number).sort(function (a, b) { return b - a; });
    for (i = 0; i < yk.length; i++) years.push({ v: yk[i], label: yk[i], n: null });
    var dk = Object.keys(dset).sort(dispCmp);
    for (i = 0; i < dk.length; i++) disps.push({ v: dk[i], label: dk[i], n: null });

    return { brands: brands, models: models, years: years, disps: disps };
  }

  /* ---------- 方案 B：按已加载的型号现算（选了具体品类时用，带条数） ---------- */
  function yearOk(it, y) { return !y || (!!it._fy && it._fy[0] <= y && y <= it._fy[1]); }
  function dispOk(it, d) { return !d || (it._fd || []).indexOf(d) >= 0; }

  function optsFromItems(items, sel, cat) {
    var bc = {}, mc = {}, yc = {}, dc = {}, i, it, k;
    for (i = 0; i < items.length; i++) {
      it = items[i];
      if (cat !== "all" && it.c !== cat) continue;
      parseItem(it);
      var yOK = yearOk(it, sel.y), dOK = dispOk(it, sel.d),
          bOK = !sel.b || it._fb.indexOf(sel.b) >= 0,
          mOK = !sel.m || it._fm.indexOf(sel.m) >= 0;
      if (mOK && yOK && dOK) for (k = 0; k < it._fb.length; k++) bc[it._fb[k]] = (bc[it._fb[k]] || 0) + 1;
      if (sel.b && bOK && yOK && dOK) for (k = 0; k < it._fm.length; k++) mc[it._fm[k]] = (mc[it._fm[k]] || 0) + 1;
      if (bOK && mOK && dOK && it._fy) for (var y = it._fy[0]; y <= it._fy[1]; y++) yc[y] = (yc[y] || 0) + 1;
      if (bOK && mOK && yOK) for (k = 0; k < it._fd.length; k++) dc[it._fd[k]] = (dc[it._fd[k]] || 0) + 1;
    }

    var brands = [], models = [], years = [], disps = [], b;
    for (b in bc) brands.push({ v: b, n: bc[b] });
    brands.sort(function (x, y) { return y.n - x.n; });

    if (sel.b) {
      var cb = catalogBrand(sel.b), added = {};
      if (cb) {
        for (i = 0; i < cb[2].length; i++) {
          var cm = cb[2][i];
          if ((sel.y || sel.d) && mc[cm[0]] == null) continue;
          models.push({ v: cm[0], label: cm[1], n: (sel.y || sel.d) ? mc[cm[0]] : cm[2] });
          added[cm[0]] = 1;
        }
      }
      for (var mk in mc) if (!added[mk]) models.push({ v: mk, label: mk, n: mc[mk] });
    }

    var yk = Object.keys(yc).map(Number).sort(function (a, b2) { return b2 - a; });
    for (i = 0; i < yk.length; i++) years.push({ v: yk[i], label: yk[i], n: yc[yk[i]] });
    var dk = Object.keys(dc).sort(dispCmp);
    for (i = 0; i < dk.length; i++) disps.push({ v: dk[i], label: dk[i], n: dc[dk[i]] });

    return { brands: brands, models: models, years: years, disps: disps };
  }

  function opts(items, sel, cat) {
    if (CAT && cat === "all") return optsFromCatalog(sel);
    return optsFromItems(items, sel, cat);
  }

  function match(it, sel) {
    parseItem(it);
    if (sel.b && it._fb.indexOf(sel.b) < 0) return false;
    if (sel.m && it._fm.indexOf(sel.m) < 0) return false;
    if (!yearOk(it, sel.y)) return false;
    if (!dispOk(it, sel.d)) return false;
    return true;
  }

  window.FACETS = {
    build: build, opts: opts, match: match, catalog: CAT,
    dispTok: dispTok,
    modelOf: function (k) { return MODELS[k] || ""; }
  };
})();
