/* VIN 车架号查询（纯离线）：WMI→品牌、第9位校验位、第10位年款、VDS 只做结构提示；也认 6/8 位前缀。
   识别出品牌后到 data.js 的适配车型里模糊匹配，匹配不到给照片 / WhatsApp 兜底。 */
(function () {
  "use strict";
  if (typeof window === "undefined") return;
  var W = {
    JHM:"Honda",JHL:"Honda",JTD:"Toyota",JT2:"Toyota",JT3:"Toyota",JTE:"Toyota",JTF:"Toyota",JTN:"Toyota",JTJ:"Lexus",
    JTH:"Lexus",JN1:"Nissan",JN3:"Nissan",JN8:"Nissan",JNK:"Infiniti",JNR:"Infiniti",JS1:"Suzuki",JS2:"Suzuki",
    JA3:"Mitsubishi",JA4:"Mitsubishi",JM1:"Mazda",JM3:"Mazda",JF1:"Subaru",JF2:"Subaru",JD1:"Daihatsu",JDA:"Daihatsu",
    KMH:"Hyundai",KM8:"Hyundai",KNA:"Kia",KNB:"Kia",KNC:"Kia",KND:"Kia",KNE:"Kia",KL1:"Daewoo",KLA:"Daewoo",KPT:"SsangYong",
    WBA:"BMW",WBS:"BMW",WBX:"BMW",WDB:"Mercedes-Benz",WDC:"Mercedes-Benz",WDD:"Mercedes-Benz",WDF:"Mercedes-Benz",
    WVW:"Volkswagen",WV1:"Volkswagen",WV2:"Volkswagen",WVG:"Volkswagen",WAU:"Audi",WA1:"Audi",WUA:"Audi",
    WP0:"Porsche",WP1:"Porsche",W0L:"Opel",WOL:"Opel",WMW:"Mini",
    VF1:"Renault",VF2:"Renault",VF6:"Renault",VF3:"Peugeot",VF7:"Citroen",SAJ:"Jaguar",SAL:"Land Rover",SCF:"Aston Martin",
    YV1:"Volvo",YV4:"Volvo",YS3:"Saab",ZFA:"Fiat",ZAR:"Alfa Romeo",ZAM:"Maserati",ZLA:"Lancia",ZFF:"Ferrari",XTA:"Lada",
    LSG:"Buick/Chevrolet/Cadillac",LSV:"Volkswagen/Skoda",LFV:"Volkswagen/Audi",LSJ:"Roewe/MG/Maxus",
    LZW:"Wuling/Baojun",LVT:"Chery",LVV:"Chery",LGW:"Great Wall/Haval/Wey",L6T:"Geely/Lynk",LGX:"BYD",LC0:"BYD",
    LS5:"Changan",LVS:"Ford",LGB:"Nissan/Venucia",LDN:"Kia",LBE:"Hyundai",LDC:"Peugeot/Citroen",LBV:"BMW",
    LJD:"Dongfeng",LJ1:"JAC",LFP:"FAW",
    "1G1":"Chevrolet","1GC":"Chevrolet","1G4":"Buick","1G6":"Cadillac","1FA":"Ford","1FB":"Ford","1FC":"Ford",
    "1FD":"Ford","1FM":"Ford","1FT":"Ford","1HG":"Honda","1HJ":"Honda","1J4":"Jeep","1J8":"Jeep","1C3":"Chrysler",
    "1B3":"Dodge","1B4":"Dodge","1B7":"Dodge","1N4":"Nissan","1N6":"Nissan","1LN":"Lincoln","1ME":"Mercury",
    "1M8":"Mercury","1YV":"Mazda","1VW":"Volkswagen","2G1":"Chevrolet","2HG":"Honda","2T1":"Toyota","2FZ":"Ford",
    "3N1":"Nissan","3G1":"Chevrolet","3FA":"Ford","3VW":"Volkswagen","3HG":"Honda","4T1":"Toyota","4T3":"Toyota",
    "5TF":"Toyota","5FN":"Honda","5J6":"Honda"
  };
  var EXAMPLE = "JTDBE46K940123456", YSEQ = "ABCDEFGHJKLMNPRSTVWXY", NOW = new Date().getFullYear() + 1;
  var MODE = "auto", LASTN = 0;

  function years(c) {
    var i = YSEQ.indexOf(c), a, b, d;
    if (i >= 0) { a = 1980 + i; b = a + 30; }
    else { d = "123456789".indexOf(c); if (d < 0) return null; a = 2001 + d; b = a + 30; }
    return b <= NOW ? [b, a] : [a, b > NOW ? null : b];
  }
  var TR = { A:1,B:2,C:3,D:4,E:5,F:6,G:7,H:8,J:1,K:2,L:3,M:4,N:5,P:7,R:9,S:2,T:3,U:4,V:5,W:6,X:7,Y:8,Z:9 };
  var WT = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2];
  function checkOf(v) {
    var s = 0, i, c, n;
    for (i = 0; i < 17; i++) {
      c = v.charAt(i);
      n = TR[c] != null ? TR[c] : (/[0-9]/.test(c) ? +c : NaN);
      if (isNaN(n)) return null;
      s += n * WT[i];
    }
    var r = s % 11, ch = r === 10 ? "X" : String(r);
    return { ok: v.charAt(8) === ch, ch: ch };
  }
  function clean(t) { return String(t == null ? "" : t).toUpperCase().replace(/[^0-9A-Z]+/g, ""); }
  function nrm(t) { return String(t == null ? "" : t).toUpperCase().replace(/[^0-9A-Z\u4e00-\u9fa5]+/g, ""); }
  function prefixBrands(wmi) {
    var pre = wmi.slice(0, 2), out = [], k, s, i;
    for (k in W) {
      if (k.slice(0, 2) !== pre) continue;
      s = W[k].split("/");
      for (i = 0; i < s.length; i++) if (out.indexOf(s[i]) < 0) out.push(s[i]);
    }
    return out;
  }
  function parse(raw) {
    var v = clean(raw), full = /^[A-HJ-NPR-Z0-9]{17}$/.test(v);
    if (v.length < 3) return null;
    var wmi = v.slice(0, 3), hit = W[wmi], yr = full ? years(v.charAt(9)) : null;
    return {
      raw: v, wmi: wmi, full: full, brands: hit ? hit.split("/") : prefixBrands(wmi), exact: !!hit,
      vds: full ? v.slice(3, 8) : v.slice(3), year: yr ? yr[0] : null, yearAlt: yr ? yr[1] : null,
      check: full ? checkOf(v) : null, plant: full ? v.charAt(10) : "", serial: full ? v.slice(11) : ""
    };
  }
  function isVin(q) {
    var v = clean(q);
    if (!v) return false;
    if (MODE === "oe" || MODE === "sku" || MODE === "model") return false;
    if (MODE === "vin") return v.length === 17 || v.length === 8 || v.length === 6;
    if (v.length === 17) return /^[A-HJ-NPR-Z0-9]{17}$/.test(v);
    return (v.length === 6 || v.length === 8) && !!W[v.slice(0, 3)];
  }
  function results(q) {
    var p = parse(q), out = [], all = (window.SITE_DATA && window.SITE_DATA.items) || [], i, j, it, bs = [], b;
    if (!p) return [];
    for (i = 0; i < p.brands.length; i++) { b = nrm(p.brands[i]); if (b) bs.push(b); }
    if (!bs.length) return [];
    for (j = 0; j < all.length; j++) {
      it = all[j];
      var hq = it._q || nrm([it.m, it.oe, (it.x || []).join(" "), it.a, it.b, it.n].join(" "));
      var ha = nrm(it.a || "");
      for (i = 0; i < bs.length; i++) {
        if (hq.indexOf(bs[i]) >= 0) {
          it._vs = (ha.indexOf(bs[i]) >= 0 ? 2 : 1) + (nrm(it.b) === bs[i] ? 1 : 0);
          out.push(it);
          break;
        }
      }
    }
    out.sort(function (x, y) { return (y._vs - x._vs) || (x.i - y.i); });
    return out;
  }
  function T(k, fb) { return (window.I18N && window.I18N.t) ? window.I18N.t(k, fb) : fb; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function L(s) { return '<bdi dir="ltr">' + esc(s) + "</bdi>"; }
  function waHref(txt) {
    var a = document.querySelector(".fab"), base = "https://wa.me/8615915859048";
    if (a && a.href) base = a.href.split("?")[0];
    return base + "?text=" + encodeURIComponent(txt);
  }
  function panelHTML(q) {
    var p = parse(q);
    if (!p) return "";
    var check = "";
    if (p.full && p.check) check = p.check.ok
      ? '<span class="vinok">&#10003; ' + esc(T("vin_check_ok", "check digit OK")) + "</span>"
      : '<span class="vinbad">! ' + esc(T("vin_check_bad", "check digit mismatch")) + "</span>";
    var yr = p.year ? String(p.year) + (p.yearAlt ? " / " + p.yearAlt : "") : "—";
    var rows = [[T("vin_brand", "Brand"), "<b>" + esc(p.brands.length ? p.brands.join(" / ") : T("vin_none", "not recognised")) + "</b>" +
      (p.exact ? "" : ' <span class="vinwarn">' + esc(T("vin_guess", "prefix guess")) + "</span>")],
      [T("vin_wmi", "WMI 1-3"), L(p.wmi)], [T("vin_year", "Year (10)"), esc(yr)]];
    if (p.full) {
      rows.push([T("vin_vds", "VDS 4-8"), L(p.vds) + ' <span class="vsub">' + esc(T("vin_vds_note", "maker-defined: body / series / engine")) + "</span>"]);
      rows.push([T("vin_plant", "Plant (11) / serial"), L(p.plant) + " · " + L(p.serial)]);
    } else {
      rows.push([T("vin_prefix", "Prefix"), L(p.raw) + ' <span class="vsub">' + esc(T("vin_prefix_note", "brand inferred from WMI")) + "</span>"]);
    }
    var h = '<div class="vinbox"><div class="vinhd"><span class="vinbadge">VIN</span><bdi dir="ltr" class="vinraw">' +
      esc(p.raw) + "</bdi>" + check + "</div><dl>";
    for (var i = 0; i < rows.length; i++) h += "<dt>" + esc(rows[i][0]) + "</dt><dd>" + rows[i][1] + "</dd>";
    h += '</dl><p class="vinnote">' + esc(p.brands.length
      ? T("vin_note", "Matched against each model's fitment field. The VIN alone is not a 100% guarantee - send a part photo or the licence if you need certainty.")
      : T("vin_unknown_wmi", "This WMI is not in our offline table - the VIN alone cannot tell the brand."));
    return h + "</p></div>";
  }
  function sync(q, total) {
    var box = document.getElementById("vinpanel");
    if (!box) return;
    if (!isVin(q)) { box.hidden = true; box.innerHTML = ""; return; }
    if (total != null) LASTN = total;
    box.hidden = false;
    box.innerHTML = panelHTML(q);
  }
  function fallbackHTML(q) {
    var p = parse(q), sug = (p && p.brands.length) ? p.brands.slice(0, 3) : ["Toyota", "Changan", "Honda"];
    var btns = sug.map(function (b) { return '<button data-t="' + esc(b) + '">' + esc(b) + "</button>"; }).join("");
    return '<div class="empty vinempty"><div class="big">&#128663;</div><h3>' + esc(T("vin_nf_t", "No parts matched this VIN yet")) +
      "</h3><p>" + esc(T("vin_nf_p", "We could not identify the car from this VIN. Send a photo of the car, the part or the vehicle licence and we will check by hand.")) +
      "</p><p>" + esc(T("vin_nf_p2", "You can also search by model name, OE number, or the first 6 / 8 digits of the VIN.")) + "</p>" +
      '<div class="tips">' + btns + "</div>" +
      '<p><a class="vinwa" href="' + esc(waHref("Hi, my VIN is " + ((p && p.raw) || "") + ". Which part fits my car?")) +
      '" target="_blank" rel="noopener">' + esc(T("vin_ask", "Send this VIN on WhatsApp")) + "</a></p></div>";
  }
  window.VIN = {
    parse: parse, results: results, match: isVin, sync: sync, panelHTML: panelHTML,
    fallbackHTML: fallbackHTML, norm: nrm, example: EXAMPLE,
    get mode() { return MODE; },
    setMode: function (m) { MODE = m || "auto"; }
  };
  function fire(q) {
    var ev;
    try { ev = new Event("input"); } catch (e) { ev = document.createEvent("Event"); ev.initEvent("input", true, false); }
    q.dispatchEvent(ev);
  }
  function init() {
    var bar = document.getElementById("vintabs");
    if (bar) bar.addEventListener("click", function (e) {
      var t = e.target, b = t && t.closest ? t.closest(".vtab") : null;
      if (!b) return;
      MODE = b.getAttribute("data-mode") || "auto";
      var kids = bar.querySelectorAll(".vtab"), i;
      for (i = 0; i < kids.length; i++) kids[i].className = "vtab" + (kids[i] === b ? " on" : "");
      var q = document.getElementById("q");
      if (!q) return;
      q.setAttribute("data-i18n-ph", MODE === "vin" ? "vin_ph" : "home_ph");
      if (window.I18N && window.I18N.apply) window.I18N.apply();
      if (MODE === "vin" && !clean(q.value)) q.value = EXAMPLE;
      fire(q);
    });
    document.addEventListener("click", function (e) {
      var t = e.target, b = t && t.closest ? t.closest("[data-vin-ex]") : null;
      if (!b) return;
      var q = document.getElementById("q");
      if (!q) return;
      e.preventDefault();
      q.value = b.getAttribute("data-vin-ex");
      MODE = "vin";
      fire(q);
    });
    document.addEventListener("i18n:change", function () {
      var q = document.getElementById("q");
      if (q) sync(q.value, LASTN);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
