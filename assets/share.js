/* 型号页：WhatsApp 分享 + 复制链接
   ---------------------------------------------------------------
   服务端先把英文版的 wa.me 链接写进 href（没 JS 也能分享）；
   这个脚本只做三件事：
     1. 按当前界面语言重写分享文案（en / zh / ar / ru / fr）
     2. 复制链接按钮（clipboard API，失败退回 execCommand）
     3. 跟着 <select class="langsel"> 的 i18n:change 事件重跑一遍

   页面里需要的数据全在 data-* 上，脚本不猜任何东西：
     data-sharebar 容器
     a.js-share    data-url / data-sku / data-oe / data-fit
     button.js-copy data-url
*/
(function () {
  "use strict";

  var T = {
    en: {
      share: "Share on WhatsApp", copy: "Copy link", copied: "Copied!",
      a: "Check this part: ", b: ". ", fits: "Fits ",
      c: "OE-grade replacement - price and MOQ on WhatsApp: "
    },
    zh: {
      share: "分享到 WhatsApp", copy: "复制链接", copied: "已复制！",
      a: "看这个件：", b: "。", fits: "适配 ",
      c: "OE 品质替代件，价格和起订量 WhatsApp 问我："
    },
    ar: {
      share: "مشاركة على واتساب", copy: "نسخ الرابط", copied: "تم النسخ!",
      a: "تحقق من هذه القطعة: ", b: ". ", fits: "تناسب ",
      c: "بديل بجودة OE - السعر والحد الأدنى للطلب على واتساب: "
    },
    ru: {
      share: "Поделиться в WhatsApp", copy: "Копировать ссылку", copied: "Скопировано!",
      a: "Проверьте эту деталь: ", b: ". ", fits: "Подходит на ",
      c: "Замена уровня OE - цена и минимальный заказ в WhatsApp: "
    },
    fr: {
      share: "Partager sur WhatsApp", copy: "Copier le lien", copied: "Copié !",
      a: "Voir cette pièce : ", b: ". ", fits: "Compatible avec ",
      c: "Remplacement qualité OE — prix et MOQ sur WhatsApp : "
    }
  };

  function lang() {
    var l = "";
    try { l = (document.documentElement.getAttribute("data-lang") || "").toLowerCase(); } catch (e) {}
    return T[l] ? l : "en";
  }

  /* 从 data-* 拼分享文案：料号 + OE + 一句适配 + 页面地址 */
  function shareText(el, dict) {
    var url = el.getAttribute("data-url") || "";
    var sku = el.getAttribute("data-sku") || "";
    var oe = el.getAttribute("data-oe") || "";
    var fit = el.getAttribute("data-fit") || "";
    var s = dict.a + sku + (oe ? " (OE " + oe + ")" : "") + dict.b;
    if (fit) s += dict.fits + fit + dict.b;
    return s + dict.c + url;
  }

  /* 复制：HTTPS 走 clipboard API，file:// 或老浏览器退回 textarea + execCommand */
  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    var ok = false;
    try {
      ta.select();
      ta.setSelectionRange(0, ta.value.length);
      ok = document.execCommand("copy");
    } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; },
        function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }

  function markCopied(btn, dict) {
    var label = btn.querySelector(".sbt");
    if (!label) return;
    if (!btn.getAttribute("data-label")) btn.setAttribute("data-label", label.textContent);
    btn.classList.add("ok");
    label.textContent = dict.copied;
    btn.setAttribute("aria-live", "polite");
    clearTimeout(btn._t);
    btn._t = setTimeout(function () {
      btn.classList.remove("ok");
      label.textContent = (T[lang()] || T.en).copy;
    }, 1800);
  }

  function apply() {
    var dict = T[lang()];
    var bars = document.querySelectorAll("[data-sharebar]");
    for (var i = 0; i < bars.length; i++) {
      var bar = bars[i];
      var a = bar.querySelector(".js-share");
      if (a) {
        a.setAttribute("href", "https://wa.me/?text=" + encodeURIComponent(shareText(a, dict)));
        a.setAttribute("title", dict.share);
        a.setAttribute("aria-label", dict.share);
        var sl = a.querySelector(".sbt");
        if (sl) sl.textContent = dict.share;
      }
      var c = bar.querySelector(".js-copy");
      if (c) {
        c.setAttribute("title", dict.copy);
        c.setAttribute("aria-label", dict.copy);
        var cl = c.querySelector(".sbt");
        if (cl && !c.classList.contains("ok")) cl.textContent = dict.copy;
      }
    }
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    var btn = t && t.closest ? t.closest(".js-copy") : null;
    if (!btn) return;
    var url = btn.getAttribute("data-url") || "";
    try { if (!url) url = location.href.split("#")[0].split("?")[0]; } catch (err) {}
    copyText(url).then(function (ok) {
      if (ok) markCopied(btn, T[lang()]);
    });
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
  document.addEventListener("i18n:change", apply);
})();
