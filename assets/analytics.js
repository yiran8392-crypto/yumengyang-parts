/* ============================================================================
   驭盟扬 · 全站访问统计（2026-11-10）
   ----------------------------------------------------------------------------
   设计原则（改这个文件之前先读这四行）：
     1. 只加"能回答业务问题"的事件：有人搜了但没搜到、点了 WhatsApp、切了语言；
     2. 不碰数据、不碰 DOM 结构 —— 全部走"事件委托"，页面模板改了这里照样能用；
     3. 不写死提供方 —— 下面 PROVIDERS 里加一个对象就多一种后端，改 站点设置.txt 一行就切换；
     4. 无 cookie、无指纹、不跨站 —— 默认 GoatCounter（连 cookie 都不用，不用弹同意框）。

   配置来源（优先级从高到低）：
     <meta name="ymy-analytics" content="goatcounter:yumengyang">
     window.YMY_ANALYTICS_CFG = "goatcounter:yumengyang"
     地址栏 ?ymy_analytics=off|local|goatcounter:xxx   （调试用，不落文件）

   页面里可以直接调：
     YMY.track('anything', {a: 1});        // 自定义事件
     YMY.page('/c/0221503465.html');        // 手动补一个 pageview
     YMY.off('用户不想被统计');              // 写 localStorage，永久关闭
   ============================================================================ */
(function () {
  "use strict";
  if (typeof window === "undefined" || window.YMY_ANALYTICS) return;

  var VERSION = "2026-11-10a";
  var LS_OFF = "ymy_analytics_off";

  /* ---------------------------------------------------------------- 配置解析 */
  function rawConfig() {
    var q = "";
    try { q = new URLSearchParams(location.search).get("ymy_analytics") || ""; } catch (e) { }
    if (q) return q;
    if (window.YMY_ANALYTICS_CFG) return String(window.YMY_ANALYTICS_CFG);
    var m = document.querySelector('meta[name="ymy-analytics"]');
    return m ? (m.getAttribute("content") || "") : "";
  }

  function parse(cfg) {
    cfg = String(cfg || "").trim();
    if (!cfg) return { provider: "off" };
    var i = cfg.indexOf(":");
    var p = (i < 0 ? cfg : cfg.slice(0, i)).toLowerCase().trim();
    var arg = i < 0 ? "" : cfg.slice(i + 1).trim();
    return { provider: p, arg: arg, raw: cfg };
  }

  /* ------------------------------------------------------ 环境判断 / 开关 */
  var host = location.hostname || "";
  var isLocal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(host) || location.protocol === "file:";
  var forced = /ymy_analytics=/.test(location.search);
  var optedOut = false;
  try { optedOut = localStorage.getItem(LS_OFF) === "1"; } catch (e) { }
  var dnt = !forced && navigator.doNotTrack === "1";

  var conf = parse(rawConfig());
  var debug = /local|debug/.test(conf.raw) || /ymy_analytics=(local|debug)/.test(location.search);
  // 要不要把买家搜的词一起记下来（站点设置.txt 的「统计查询词=1」，默认不记）
  var Q_ON = !!document.querySelector('meta[name="ymy-analytics-q"]');

  /* --------------------------------------------------------- 本地调试缓冲 */
  // ?ymy_analytics=local 时：不发网络请求，事件进 window.__YMY_AEV，方便在控制台看
  var LOCAL = conf.provider === "local" || conf.provider === "debug";
  window.__YMY_AEV = window.__YMY_AEV || [];

  /* ------------------------------------------------------------ 工具函数 */
  function cut(s, n) { s = String(s == null ? "" : s); return s.length > n ? s.slice(0, n) : s; }
  function slug(s) {
    return cut(String(s == null ? "" : s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""), 28);
  }
  function pagePath() {
    var p = location.pathname.replace(/\/index\.html$/, "/");
    return p || "/";
  }
  function lang() {
    return document.documentElement.getAttribute("data-lang") || "en";
  }
  function fitmentSku(el) {
    // 最近的、带链接的卡片 / 弹窗，用 href 的文件名当 SKU
    var a = el && el.closest ? el.closest('a[href*="/c/"], a[href*="?sku="]') : null;
    if (!a) return "";
    var m = /\/c\/([^/?#]+)\.html/.exec(a.getAttribute("href") || "");
    return m ? m[1] : "";
  }
  function eventPath(name, props) {
    // GoatCounter 只有"路径"这个概念，所以把事件折叠成 /ev/名称/关键值
    var parts = ["/ev", slug(name)];
    var keys = ["q", "where", "mode", "lang", "sku", "n"];
    for (var i = 0; i < keys.length; i++) {
      if (props && props[keys[i]] !== undefined && props[keys[i]] !== "") {
        parts.push(slug(keys[i] + "-" + props[keys[i]]));
        if (parts.length >= 4) break;
      }
    }
    return cut(parts.join("/"), 140);
  }

  /* ------------------------------------------------------------- 提供方适配 */
  // 加一个新后端：在 PROVIDERS 里加一项 {init: fn, send: fn(detail)}
  //   detail = { kind: 'page'|'event', name, path, props }
  var PROVIDERS = {
    off: { send: function () { } },

    local: {
      send: function (d) {
        window.__YMY_AEV.push(d);
        if (window.console && console.log) {
          console.log("[ymy-analytics]", d.kind, d.name || d.path, d.props || "");
        }
      }
    },

    /* GoatCounter：免费、无 cookie、自带事件支持。
       注册地址 https://www.goatcounter.com/ ，Site code 就是配置里的那个词。 */
    goatcounter: {
      init: function (arg) {
        if (!arg || isLocal) return false;
        window.goatcounter = window.goatcounter || {};
        window.goatcounter.path = function (p) { return String(p || "").split("?")[0].replace(/index\.html$/, ""); };
        if (window.goatcounter.count) return true;           // count.js 已就绪
        var s = document.createElement("script");
        s.async = true;
        s.src = "https://gc.zgo.at/count.js";
        s.setAttribute("data-goatcounter", "https://" + arg + ".goatcounter.com/count");
        document.head.appendChild(s);
        return true;
      },
      send: function (d) {
        var gc = window.goatcounter;
        if (!gc || !gc.count) return false;
        if (d.kind === "event") gc.count({ path: d.path, title: d.name, event: true });
        return true;
      }
    },

    /* Google Analytics 4：要 cookie，欧盟访问按 GDPR 会需要同意框，慎用。 */
    ga4: {
      init: function (arg) {
        if (!arg || isLocal) return false;
        window.dataLayer = window.dataLayer || [];
        window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
        if (!document.querySelector('script[data-ymy="ga4"]')) {
          var s = document.createElement("script");
          s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(arg);
          s.setAttribute("data-ymy", "ga4"); document.head.appendChild(s);
        }
        window.gtag("js", new Date());
        window.gtag("config", arg, { send_page_view: false });
        return true;
      },
      send: function (d) {
        if (!window.gtag) return false;
        var params = {};
        Object.keys(d.props || {}).forEach(function (k) { params[k] = d.props[k]; });
        params.page_path = d.path || pagePath();
        params.page_language = lang();
        window.gtag("event", d.kind === "page" ? "page_view" : d.name, params);
        return true;
      }
    },

    /* Umami：自托管或 cloud.umami.is，配置写  umami:站点ID|https://host */
    umami: {
      init: function (arg) {
        if (!arg || isLocal) return false;
        var bits = arg.split("|");
        var id = bits[0], host = bits[1] || "https://cloud.umami.is";
        if (!document.querySelector('script[data-ymy="umami"]')) {
          var s = document.createElement("script");
          s.async = true; s.defer = true;
          s.src = host.replace(/\/$/, "") + "/script.js";
          s.setAttribute("data-website-id", id);
          s.setAttribute("data-ymy", "umami");
          document.head.appendChild(s);
        }
        return true;
      },
      send: function (d) {
        if (!window.umami || !window.umami.track) return false;
        if (d.kind === "page") return false;                  // umami 自己记 pageview
        window.umami.track(d.name, d.props || {});
        return true;
      }
    },

    /* Plausible：配置写  plausible:parts.yumengyang.com */
    plausible: {
      init: function (arg) {
        if (!arg || isLocal) return false;
        if (!document.querySelector('script[data-ymy="plausible"]')) {
          var s = document.createElement("script");
          s.async = true;
          s.src = "https://plausible.io/js/script.js";
          s.setAttribute("data-domain", arg);
          s.setAttribute("data-ymy", "plausible");
          document.head.appendChild(s);
        }
        return true;
      },
      send: function (d) {
        if (!window.plausible) return false;
        if (d.kind === "page") return false;
        window.plausible(d.name, { props: d.props || {} });
        return true;
      }
    },

    /* 自建收集口：POST JSON 到自己的地址（Cloudflare Worker / 飞书 Webhook 都行） */
    custom: {
      init: function (arg) { return !!arg && !isLocal; },
      send: function (d) {
        try {
          var body = JSON.stringify({ v: VERSION, kind: d.kind, name: d.name, path: d.path,
            props: d.props || {}, lang: lang(), t: new Date().toISOString() });
          if (navigator.sendBeacon) navigator.sendBeacon(conf.arg, body);
          else fetch(conf.arg, { method: "POST", body: body, keepalive: true, mode: "no-cors" });
        } catch (e) { }
        return true;
      }
    }
  };

  var backend = PROVIDERS[conf.provider] || PROVIDERS.off;

  /* ----------------------------------------------------------------- 发送 */
  function emit(kind, name, props, path) {
    if (optedOut || dnt) return;
    var d = { kind: kind, name: name, props: props || {}, path: path || "" };
    if (backend.send(d) === false && !LOCAL) {
      // 后端脚本还没就绪（count.js 异步），排一次队重试
      pending.push(d);
    }
  }
  var pending = [];
  function flush() {
    if (!pending.length) return;
    var left = [];
    pending.forEach(function (d) { if (backend.send(d) === false) left.push(d); });
    if (debug && left.length !== pending.length) {
      try { console.info("[ymy-analytics] 补发成功 " + (pending.length - left.length) + " 条，剩 " + left.length); } catch (e) { }
    }
    pending = left;
  }

  /* ----------------------------------------------------------------- 对外 */
  var YMY = {
    version: VERSION,
    enabled: function () { return !optedOut && !dnt && backend !== PROVIDERS.off; },
    track: function (name, props) {
      emit("event", String(name), props || {});
    },
    page: function (path) { emit("page", "pageview", {}, path || pagePath()); },
    off: function (why) {
      optedOut = true;
      try { localStorage.setItem(LS_OFF, "1"); } catch (e) { }
      if (window.console && debug) console.log("[ymy-analytics] off:", why || "");
    }
  };
  window.YMY = window.YMY || YMY;
  window.YMY_ANALYTICS = YMY;

  /* ------------------------------------------------------------- 自动埋点 */
  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  function autoTrack() {
    // 1) 页面浏览（GoatCounter 的 count.js 自己会发一次；这里只对 local / ga4 / custom 补发）
    if (conf.provider === "ga4" || conf.provider === "custom" || LOCAL) {
      emit("page", "pageview", {});
    }

    // 2) WhatsApp / 邮件：任何页面、任何位置的按钮都算（事件委托，模板不用改）
    document.addEventListener("click", function (e) {
      var t = e.target && e.target.closest ? e.target : null;
      if (!t) return;
      var a = t.closest('a[href*="wa.me"], a[href^="mailto:"]');
      if (a) {
        var href = a.getAttribute("href") || "";
        var isWa = href.indexOf("wa.me") > -1;
        var zone = a.closest(".fab") ? "fab" : a.closest("#modal") ? "modal" :
                   a.closest(".empty") ? "noresult" : a.closest("main") ? "main" : "nav";
        emit("event", isWa ? "wa_click" : "mail_click",
             { where: zone, sku: fitmentSku(a), path: pagePath() });
        return;
      }
      // 3) 复制链接 / 分享
      if (t.closest("#d-copy")) emit("event", "copy_link", { where: "modal" });
      // 4) 展开品类 / 折叠列表
      if (t.closest(".catbox > summary")) emit("event", "catbox_toggle", {});
    }, true);

    // 5) 语言切换
    document.addEventListener("change", function (e) {
      if (e.target && e.target.id === "langsel") emit("event", "lang_switch", { lang: e.target.value });
    }, true);

    // 6) 询价表单（contact.html）
    var rfq = document.getElementById("rfq");
    if (rfq) {
      rfq.addEventListener("submit", function () { emit("event", "rfq_submit", { mode: "email" }); });
      var wa = document.getElementById("rfq-wa");
      if (wa) wa.addEventListener("click", function () { emit("event", "rfq_submit", { mode: "wa" }); });
    }

    // 7) 首页搜索：输入停止 900ms 或按回车，读 #count 里的命中数
    var q = document.getElementById("q"), grid = document.getElementById("grid");
    if (q) {
      var timer = null, last = "";
      var report = function () {
        var term = (q.value || "").trim();
        if (term === last) return;
        last = term;
        var hits = 0;
        if (grid) hits = grid.querySelectorAll("a.card").length;
        if (!term) { emit("event", "search_clear", {}); return; }
        var p = { n: hits, len: Math.min(term.length, 40), mode: document.querySelector('.vtab[aria-selected="true"]') ?
                 (document.querySelector('.vtab[aria-selected="true"]').textContent || "").trim().toLowerCase() : "auto" };
        if (Q_ON) p.q = cut(term.replace(/\s+/g, "").toLowerCase(), 24);
        emit("event", hits > 0 ? "search_hit" : "search_miss", p);
      };
      q.addEventListener("input", function () {
        clearTimeout(timer); timer = setTimeout(report, 900);
      });
      q.addEventListener("keydown", function (e) { if (e.key === "Enter") { clearTimeout(timer); report(); } });
      var more = document.getElementById("more");
      if (more) more.addEventListener("click", function () {
        emit("event", "search_more", { n: grid ? grid.querySelectorAll("a.card").length : 0 });
      });
    }

    // 8) 车型级联筛选
    ["f-b", "f-m", "f-y", "f-d"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("change", function () {
        emit("event", "vehicle_filter", { mode: id.replace("f-", ""), n: el.value ? 1 : 0 });
      });
    });

    // 9) VIN 面板
    var vt = document.getElementById("vintabs");
    if (vt) vt.addEventListener("click", function (e) {
      var b = e.target && e.target.closest ? e.target.closest(".vtab") : null;
      if (b && /vin/i.test(b.textContent || "")) emit("event", "vin_open", {});
    });

    // 10) 批量查价页
    var bulkGo = document.getElementById("bulk-go");
    if (bulkGo) bulkGo.addEventListener("click", function () {
      var ta = document.getElementById("bulk-in");
      var lines = ta ? (ta.value || "").split(/\r?\n/).filter(function (x) { return x.trim(); }).length : 0;
      emit("event", "bulk_check", { n: Math.min(lines, 500) });
    });

    // 11) 补发排队
    setTimeout(flush, 1500);
    setTimeout(flush, 5000);
    window.addEventListener("load", function () { setTimeout(flush, 1200); });
  }

  /* ------------------------------------------------------------------ 启动 */
  function start() {
    if (optedOut) return;
    if (dnt) return;
    if (backend === PROVIDERS.off) return;
    if (isLocal && !LOCAL && !forced) return;      // 本机预览不污染线上数据
    try { if (backend.init) backend.init(conf.arg); } catch (e) { }
    autoTrack();
    // ?ymy_analytics=debug 时，控制台会自己报接线状态——统计不进数先看这里
    if (debug) {
      try {
        console.info("[ymy-analytics] provider=" + conf.provider + " endpoint=" + (conf.arg || "-") +
                     " local=" + isLocal + " dnt=" + dnt + " q=" + Q_ON);
        setTimeout(function () {
          var gc = window.goatcounter || {};
          console.info("[ymy-analytics] 脚本已加载=" + (typeof gc.count === "function") +
                       " 队列未发=" + pending.length);
        }, 2500);
      } catch (e) { }
    }
  }

  ready(start);
})();
