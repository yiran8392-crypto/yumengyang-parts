/* 级联筛选（品牌 → 车型 → 年款 → 排量）：全部从 data.js 的适配车型字段现解析，
   解析不出来的字段就不出选项，不硬凑。挂到 window.FACETS。 */
(function () {
  "use strict";
  if (typeof window === "undefined") return;

  var B = ("Toyota,Honda,Nissan,Mazda,Suzuki,Subaru,Mitsubishi,Isuzu,Lexus,Daihatsu,Hyundai,Kia,Daewoo,SsangYong," +
    "Ford,Chevrolet,Buick,Cadillac,Chrysler,Dodge,Jeep,Volkswagen,Audi,Skoda,SEAT,Opel,Vauxhall,BMW,Mercedes-Benz," +
    "Renault,Peugeot,Citroen,Fiat,Lancia,Alfa Romeo,Volvo,Saab,Rover,Land Rover,Jaguar,Mini,Porsche," +
    "Changan,Chery,Geely,BYD,JAC,Dongfeng,FAW,Wuling,Baojun,Great Wall,Haval,Jinbei,Brilliance,Foton,MG,Roewe," +
    "Maxus,Venucia,Lifan,Soueast,Haima,Zotye,Landwind,Changhe,Hafei,Xiali,Cowin,Riich,Karry,Bisu,Exeed,Lynk,Wey," +
    "Huanghai,Borgward,Luxgen,Neta,Seres,Leapmotor,Zhonghua").split(",");

  var STOP = /^(single|multi|point|pickup|van|truck|bus|sedan|wagon|hatchback|suv|mpv|diesel|petrol|gas|series|new|old|with|and|for|all|type|model|version|front|rear|left|right|4wd|2wd)$/i;
  var YEARP = /\b((?:19|20)\d{2})\s*[-–~至]\s*((?:19|20)\d{2}|现在|今|present|\+)?|\b(\d{2})\s*-\s*(\d{2})\b|\b((?:19|20)\d{2})\b/g;
  var DISP = /\b(\d\.\d)\s*(?:L|T|升)?/gi;
  var brandRe = new Map();
  for (var i = 0; i < B.length; i++) {
    brandRe.set(B[i], new RegExp("\\b" + B[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i"));
  }

  function parseItem(it) {
    var a = it.a || "";
    var brands = [], models = [], disps = [], ymin = 0, ymax = 0, m, y1, y2;
    brandRe.forEach(function (re, name) {
      var mm = re.exec(a);
      if (!mm) return;
      brands.push(name);
      // 品牌后面 1-3 个词当车型候选
      var tail = a.slice(mm.index + mm[0].length, mm.index + mm[0].length + 40);
      var words = tail.split(/[\s,;、]+/).filter(Boolean);
      var got = 0;
      for (var k = 0; k < words.length && got < 2; k++) {
        var w = words[k].replace(/[^A-Za-z0-9\-]/g, "");
        if (!w || STOP.test(w) || /^\d/.test(w) || w.length < 2) break;
        if (models.indexOf(w) < 0) models.push(w);
        got++;
      }
    });
    YEARP.lastIndex = 0;
    while ((m = YEARP.exec(a))) {
      if (m[1]) { y1 = +m[1]; y2 = m[2] && /^\d{4}$/.test(m[2]) ? +m[2] : (m[2] ? 2030 : y1); }
      else if (m[3]) { y1 = 2000 + +m[3]; y2 = 2000 + +m[4]; if (y1 > y2) { var t = y1; y1 = y2; y2 = t; } }
      else if (m[5]) { y1 = +m[5]; y2 = y1; }
      if (y1 >= 1970 && y1 <= 2035) {
        ymin = ymin ? Math.min(ymin, y1) : y1;
        ymax = ymax ? Math.max(ymax, y2) : y2;
      }
    }
    DISP.lastIndex = 0;
    while ((m = DISP.exec(a))) {
      var d = m[1];
      if (d >= 0.5 && d <= 8.0 && disps.indexOf(d) < 0) disps.push(d);
    }
    it._fb = brands; it._fm = models;
    it._fy = ymin ? [ymin, ymax] : null; it._fd = disps;
  }

  function build(items) {
    for (var i = 0; i < items.length; i++) parseItem(items[i]);
  }

  function uniqSorted(arr) {
    var seen = {}, out = [];
    for (var i = 0; i < arr.length; i++) if (!seen[arr[i]]) { seen[arr[i]] = 1; out.push(arr[i]); }
    return out;
  }

  function pool(items, sel) {
    var out = [];
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (sel.b && it._fb.indexOf(sel.b) < 0) continue;
      if (sel.m && it._fm.indexOf(sel.m) < 0) continue;
      out.push(it);
    }
    return out;
  }

  function opts(items, sel, cat) {
    var base = [];
    for (var i = 0; i < items.length; i++) if (cat === "all" || items[i].c === cat) base.push(items[i]);
    var forBrand = pool(base, {});
    var bc = {}, mc = {}, yc = {}, dc = {};
    for (var j = 0; j < forBrand.length; j++) {
      var it = forBrand[j];
      it._fb.forEach(function (b) { bc[b] = (bc[b] || 0) + 1; });
    }
    var pb = pool(base, { b: sel.b });
    for (j = 0; j < pb.length; j++) {
      var it2 = pb[j];
      it2._fm.forEach(function (m) { mc[m] = (mc[m] || 0) + 1; });
      if (it2._fy) for (var y = it2._fy[0]; y <= it2._fy[1]; y += 1) yc[y] = (yc[y] || 0) + 1;
      it2._fd.forEach(function (d) { dc[d] = (dc[d] || 0) + 1; });
    }
    function top(obj, n, numeric) {
      var arr = Object.keys(obj).map(function (k) { return [k, obj[k]]; });
      arr.sort(function (a, b) { return numeric ? (+a[0] - +b[0]) : (b[1] - a[1]); });
      return arr.slice(0, n).map(function (x) { return numeric ? +x[0] : x[0]; });
    }
    return {
      brands: top(bc, 300, false),
      models: top(mc, 300, false),
      years: top(yc, 40, true),
      disps: top(dc, 30, true)
    };
  }

  function match(it, sel) {
    if (sel.b && (it._fb || []).indexOf(sel.b) < 0) return false;
    if (sel.m && (it._fm || []).indexOf(sel.m) < 0) return false;
    if (sel.y) { if (!it._fy || it._fy[0] > sel.y || it._fy[1] < sel.y) return false; }
    if (sel.d && (it._fd || []).indexOf(sel.d) < 0) return false;
    return true;
  }

  window.FACETS = { build: build, opts: opts, match: match, brands: B };
})();
