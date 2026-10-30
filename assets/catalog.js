/* 型号数据分片加载器（首页只引第 0 片，其余按需 <script> 注入）
   —— 用 <script> 而不是 fetch：file:// 双击打开也能跑
   —— 片文件由 data_prep.py 生成：data/chunk-00.js … data/chunk-28.js
   挂到 window.CATALOG。 */
(function () {
  "use strict";
  if (typeof window === "undefined") return;

  var META = window.YMY_META || { chunks: 1, size: 240, total: 0, cats: [], photos: 0, generated: "" };
  var RAW = (window.YMY_CHUNKS = window.YMY_CHUNKS || {});
  var ITEMS = [], DONE = {}, BUSY = {}, FAILED = {}, SUBS = [];
  var MAXPAR = 4, wantAll = false;

  function sortItems() {
    ITEMS.sort(function (a, b) { return (a.i || 0) - (b.i || 0); });
  }

  function ingest(k, fromHtml) {
    if (DONE[k]) return 0;
    DONE[k] = 1;
    var add = RAW[k] || [], i;
    for (i = 0; i < add.length; i++) ITEMS.push(add[i]);
    if (add.length) sortItems();
    for (i = 0; i < SUBS.length; i++) {
      try { SUBS[i](k); } catch (e) { }
    }
    return add.length;
  }

  function load(k) {
    if (k == null || k < 0) return Promise.resolve(0);
    if (DONE[k] || FAILED[k]) return Promise.resolve(0);
    if (BUSY[k]) return BUSY[k];
    BUSY[k] = new Promise(function (res) {
      var s = document.createElement("script");
      s.src = "data/chunk-" + (k < 10 ? "0" + k : k) + ".js";
      s.async = true;
      s.onload = function () {
        delete BUSY[k];
        var n = ingest(k);
        try { s.parentNode.removeChild(s); } catch (e) { }
        pump();
        res(n);
      };
      s.onerror = function () {
        delete BUSY[k];
        FAILED[k] = 1;
        try { s.parentNode.removeChild(s); } catch (e) { }
        for (var i = 0; i < SUBS.length; i++) { try { SUBS[i](-1); } catch (e) { } }
        pump();
        res(0);
      };
      document.head.appendChild(s);
    });
    return BUSY[k];
  }

  function next() {
    for (var i = 0; i < META.chunks; i++) {
      if (!DONE[i] && !BUSY[i] && !FAILED[i]) return i;
    }
    return -1;
  }

  function pump() {
    var guard = 0;
    while (Object.keys(BUSY).length < MAXPAR && guard++ < 64) {
      var k = next();
      if (k < 0) break;
      load(k);
    }
  }

  function allLoaded() {
    for (var i = 0; i < META.chunks; i++) if (!DONE[i]) return false;
    return true;
  }

  function failedCount() { return Object.keys(FAILED).length; }

  function retry() {
    FAILED = {};
    pump();
  }

  window.CATALOG = {
    meta: function () { return META; },
    items: function () { return ITEMS; },
    load: load,
    next: next,
    loadAll: function () { wantAll = true; pump(); },
    loadMore: function () { var k = next(); return k < 0 ? Promise.resolve(0) : load(k); },
    allLoaded: allLoaded,
    failed: failedCount,
    retry: retry,
    loaded: function () { return ITEMS.length; },
    on: function (fn) { SUBS.push(fn); },
    ingest: ingest
  };

  /* 页面里已经 <script> 引了第 0 片 */
  if (RAW[0]) ingest(0, true);
})();
