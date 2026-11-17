/* ==========================================================================
   型号查询站 · 故障码识别（2026-11-17 第一期）
   ==========================================================================

   要解决的问题：搜索框原来只认 OE / 交叉号 / 料号 / 车型，客户输 P0301 会得到
   「查无此件」的空结果页 —— 而我们明明有 P0301 的诊断页。

   这一层只做「分流」，不做诊断：
     · 命中的码有诊断页（47 个）→ 直接跳到 codes/<code>.html
     · 码型合法但没收录        → 跳到 codes/index.html?q=<CODE>，由下面
                                renderPanel() 按「码段 → 常见指向哪几类件」给方向
     · 认不出是码              → 原样返回 null，调用方照旧走型号搜索

   为什么码段兜底写在前端而不是生成页面：P 码有几千个，替每个码生成一页就是
   thin content，会被判垃圾页；按码段给「一般指向哪几类件」既不增加页面，也不至于
   让客户看到「没有这个东西」。

   口径纪律（重要）：这里给的永远是「最常见原因排序」，不是诊断结论。
   页面文案必须保持 check first / most likely 的语气，不能写「换这个就好」。

   维护：SYSTEMS/兜底表改这里；47 个码变化时同步 KNOWN（脚本 _selftest/verify_dtc.mjs 会查）。
   品类 slug → 品类页文件名（CAT）是从 codes/*.html 的实际链接里提取的，
   品类页改名时要一起改。
   ========================================================================== */
(function () {
  "use strict";

  /* ---------------------------------------------------------------- 已知码 */
  /* 有诊断页的码（codes_content.CODES 的镜像，小写） */
  var KNOWN = (
    "p0300 p0301 p0302 p0303 p0304 p0351 p0352 p0353 p0354 p0335 p0336 p0340 p0341 " +
    "p0011 p0016 p0100 p0101 p0102 p0105 p0106 p0171 p0172 p0174 p0201 p0202 p0230 " +
    "p0087 p0089 p0130 p0133 p0134 p0135 p0420 p0442 p0455 p0115 p0117 p0120 p0122 " +
    "p0128 p0505 p0500 c0035 c0036 c0040 c0045 c0050"
  ).split(" ");

  /* ------------------------------------------------- 品类 slug → [品类页, 英文名] */
  /* 英文名是 data-cat 的兜底文本（英文界面直接用它），其它语种由 i18n.js
     按 data-cat 换成对应译名。这份是 2026-11-17 从 codes/*.html 的 parts 链接里
     提取的，品类页改名/改称呼时一起改（_selftest 有一致性检查）。 */
  var CAT = {
    coil: ["ignition-coils", "Ignition Coils"],
    plug: ["spark-plugs", "Spark Plugs"],
    wire: ["spark-plug-wires", "Spark Plug Wire Sets"],
    injector: ["fuel-injectors", "Fuel Injectors"],
    fuelpump: ["fuel-pumps", "Fuel Pumps"],
    fuelpress: ["fuel-pressure-regulators", "Fuel pressure regulators"],
    maf: ["mass-air-flow-sensors", "Mass air flow sensors"],
    map: ["intake-pressure-sensors", "Intake Pressure Sensors (MAP)"],
    o2: ["oxygen-sensors", "Oxygen Sensors"],
    ckp: ["crankshaft-position-sensors", "Crankshaft Position Sensors"],
    cmp: ["camshaft-position-sensors", "Camshaft position sensors"],
    ocv: ["oil-control-valves", "Oil control valves"],
    temp: ["temperature-sensors", "Temperature sensors"],
    thermo: ["thermostats", "Thermostats"],
    tps: ["throttle-position-sensors", "Throttle position sensors"],
    throttle: ["throttle-bodies", "Throttle bodies"],
    stepper: ["idle-stepper-motors", "Idle Stepper Motors"],
    purge: ["canister-purge-valves", "Canister purge valves"],
    vsv: ["vacuum-solenoid-valves", "Vacuum Solenoid Valves"],
    abs: ["abs-sensors", "ABS Sensors"]
  };

  /* ------------------------------------------------------ 码段 → 常见件方向 */
  /* 顺序有意义：先匹配到的赢。
     ★ 位置类必须排在泛 P03 前面：P0335/P0340 是曲轴/凸轮位置，不是失火。
     ★ P024x 是涡轮码，别被「燃油泵电路」捞进来，所以泵电路只收 P023x。 */
  var FAM = [
    [/^P033[56]$|^P034[0-5]$/, ["ckp", "cmp"], "pos"],
    [/^P03[0-2]\d$|^P03[5-9]\d$/, ["coil", "plug", "injector"], "ign"],
    [/^P02[0-2]\d$/, ["injector", "wire"], "inj"],
    [/^P023\d$/, ["fuelpump", "fuelpress"], "pump"],
    [/^P001[1-6]$/, ["ocv", "cmp", "ckp"], "vvt"],
    [/^P010\d$/, ["maf", "map"], "air"],
    [/^P011\d$/, ["temp", "thermo"], "temp"],
    [/^P012\d$/, ["tps", "throttle", "stepper"], "thr"],
    [/^P01[345]\d$/, ["o2"], "o2"],
    [/^P01[67]\d$/, ["maf", "o2", "injector", "fuelpump", "purge"], "mix"],
    [/^P01[89]\d$/, ["fuelpress", "fuelpump"], "fuelp"],
    [/^P04[23]\d$/, ["o2", "coil"], "cat"],
    [/^P04[45]\d$/, ["purge", "vsv"], "evap"],
    [/^P05[0-3]\d$/, ["abs"], "speed"],
    [/^C0[01]\d\d$/, ["abs"], "abs"]
  ];

  /* -------------------------------------------------------------- 界面文案 */
  /* 只翻这几句；品类名走 data-cat，由 assets/i18n.js 自动翻译，不重复维护。 */
  var STR = {
    en: {
      hint: "Fault code?",
      all: "All fault codes",
      nf: "No page for {c} yet",
      lead: "We write up {n} OBD-II codes in detail; {c} is not one of them yet. The code family still tells you where to start.",
      cats: "Parts to check first",
      cta: "Send us the code plus the car (year and engine) and a photo of the scanner — we tell you which of our numbers fits before you order.",
      browse: "All fault codes we cover",
      u: "This is a body or network code. We supply engine-management and ABS parts, so do the wiring / scan-tool check first, then tell us which part actually failed.",
      manu: "{c} is a manufacturer-specific code: the same number means different things on different brands. Send us the car model and we check it against our catalogue.",
      other: "This code points at a system we do not stock parts for (EGR, transmission, hybrid). We supply ignition, fuel delivery, air metering, sensors and ABS parts.",
      first: "check first",
      then: "then"
    },
    zh: {
      hint: "故障码也能查",
      all: "全部故障码",
      nf: "暂时没有 {c} 的诊断页",
      lead: "我们写细的有 {n} 个 OBD-II 码，{c} 还没轮到。但这个码所属的码段还是能告诉你先查哪几类件。",
      cats: "先查这几类件",
      cta: "把码、车型（年份 + 发动机）和一张扫描仪照片发给我们，报价前先确认哪个料号装得上。",
      browse: "我们收录的全部故障码",
      u: "这是车身或网络类故障码。我们只做电喷和 ABS 件的供应，建议先查线路或做扫描仪检测，确定具体是哪个件坏了再找我们。",
      manu: "{c} 是厂家自定义码，同一个号码在不同品牌上含义不一样。把车型发给我们，我们帮你比对。",
      other: "这个码指向的系统我们没有配件（EGR、变速箱、混动等）。我们做点火、供油、进气计量、传感器和 ABS。",
      first: "优先查",
      then: "其次"
    },
    ar: {
      hint: "رمز العطل؟",
      all: "كل رموز الأعطال",
      nf: "لا توجد صفحة للرمز {c} حتى الآن",
      lead: "لدينا {n} رمز OBD-II مشروحًا بالتفصيل، و{c} ليس منها بعد. لكن عائلة الرمز تدلّك على القطع التي تُفحص أولًا.",
      cats: "القطع التي تُفحص أولًا",
      cta: "أرسل لنا الرمز والسيارة (السنة والمحرك) وصورة من جهاز الفحص — نحدد لك رقم القطعة المناسب قبل الطلب.",
      browse: "كل رموز الأعطال التي نغطيها",
      u: "هذا رمز في نظام الهيكل أو الشبكة. نحن نورّد قطع حقن الوقود و ABS، لذلك افحص الأسلاك أو استخدم جهاز الفحص أولًا ثم أخبرنا بالقطعة التالفة.",
      manu: "{c} رمز خاص بالمصنّع: الرقم نفسه يعني أمورًا مختلفة على علامات مختلفة. أرسل لنا الطراز ونقارنه بكتالوجنا.",
      other: "هذا الرمز يخص نظامًا لا نوفّر له قطعًا (EGR أو ناقل الحركة أو الهجين). نحن نوفّر الإشعال والوقود وقياس الهواء والحساسات وABS.",
      first: "افحص أولًا",
      then: "ثم"
    },
    ru: {
      hint: "Код ошибки?",
      all: "Все коды",
      nf: "Страницы для кода {c} пока нет",
      lead: "Подробно разобрано {n} кодов OBD-II, {c} пока не входит. Но семейство кода подсказывает, какие детали проверять первыми.",
      cats: "Что проверять первым",
      cta: "Пришлите код, автомобиль (год и двигатель) и фото сканера — до заказа подтвердим, какой наш номер подходит.",
      browse: "Все коды, которые мы разбираем",
      u: "Это код кузова или сети. Мы поставляем детали впрыска и ABS, поэтому сначала проверьте проводку или сканером, а затем скажите, какая деталь вышла из строя.",
      manu: "{c} — код производителя: один и тот же номер значит разное у разных марок. Пришлите модель, и мы сверим с каталогом.",
      other: "Этот код относится к системе, по которой у нас нет деталей (EGR, трансмиссия, гибрид). Мы поставляем зажигание, топливоподачу, измерение воздуха, датчики и ABS.",
      first: "сначала",
      then: "затем"
    },
    fr: {
      hint: "Code défaut ?",
      all: "Tous les codes",
      nf: "Pas encore de page pour le code {c}",
      lead: "Nous détaillons {n} codes OBD-II ; {c} n'en fait pas encore partie. La famille du code indique toutefois par quelles pièces commencer.",
      cats: "Pièces à vérifier en premier",
      cta: "Envoyez-nous le code, le véhicule (année et moteur) et une photo du scanner — nous confirmons la référence compatible avant la commande.",
      browse: "Tous les codes que nous traitons",
      u: "C'est un code de carrosserie ou de réseau. Nous fournissons des pièces d'injection et d'ABS : commencez par un contrôle du faisceau ou du scanner, puis dites-nous quelle pièce a lâché.",
      manu: "{c} est un code constructeur : le même numéro signifie autre chose selon la marque. Envoyez-nous le modèle, nous vérifions dans notre catalogue.",
      other: "Ce code relève d'un système dont nous ne fournissons pas les pièces (EGR, boîte de vitesses, hybride). Nous fournissons allumage, alimentation carburant, mesure d'air, capteurs et ABS.",
      first: "en premier",
      then: "ensuite"
    },
    es: {
      hint: "¿Código de avería?",
      all: "Todos los códigos",
      nf: "Todavía no hay página para el código {c}",
      lead: "Detallamos {n} códigos OBD-II; {c} aún no está entre ellos. La familia del código sí indica por qué piezas empezar.",
      cats: "Piezas que revisar primero",
      cta: "Envíanos el código, el coche (año y motor) y una foto del escáner — confirmamos qué referencia nuestra encaja antes de pedir.",
      browse: "Todos los códigos que cubrimos",
      u: "Es un código de carrocería o de red. Suministramos piezas de inyección y ABS: revisa primero el cableado o con el escáner y luego dinos qué pieza falló.",
      manu: "{c} es un código del fabricante: el mismo número significa cosas distintas según la marca. Envíanos el modelo y lo comprobamos con nuestro catálogo.",
      other: "Este código pertenece a un sistema del que no suministramos piezas (EGR, cambio, híbrido). Suministramos encendido, alimentación, medición de aire, sensores y ABS.",
      first: "primero",
      then: "después"
    },
    pt: {
      hint: "Código de falha?",
      all: "Todos os códigos",
      nf: "Ainda não há página para o código {c}",
      lead: "Detalhamos {n} códigos OBD-II; {c} ainda não está entre eles. A família do código indica por quais peças começar.",
      cats: "Peças a verificar primeiro",
      cta: "Envie o código, o carro (ano e motor) e uma foto do scanner — confirmamos qual referência nossa serve antes do pedido.",
      browse: "Todos os códigos que cobrimos",
      u: "É um código de carroceria ou de rede. Fornecemos peças de injeção e ABS: verifique primeiro a fiação ou com o scanner e depois diga qual peça falhou.",
      manu: "{c} é um código de fabricante: o mesmo número significa coisas diferentes em cada marca. Envie o modelo e comparamos com o nosso catálogo.",
      other: "Este código pertence a um sistema do qual não fornecemos peças (EGR, câmbio, híbrido). Fornecemos ignição, alimentação, medição de ar, sensores e ABS.",
      first: "primeiro",
      then: "depois"
    },
    id: {
      hint: "Kode gangguan?",
      all: "Semua kode",
      nf: "Belum ada halaman untuk kode {c}",
      lead: "Kami membahas {n} kode OBD-II secara rinci; {c} belum termasuk. Namun keluarga kode tetap menunjukkan komponen mana yang diperiksa lebih dulu.",
      cats: "Komponen yang diperiksa lebih dulu",
      cta: "Kirim kode, mobil (tahun dan mesin) serta foto scanner — kami pastikan nomor kami yang cocok sebelum Anda memesan.",
      browse: "Semua kode yang kami bahas",
      u: "Ini kode bodi atau jaringan. Kami memasok komponen injeksi dan ABS, jadi periksa kabel atau scanner dulu, lalu beri tahu komponen mana yang rusak.",
      manu: "{c} adalah kode khusus pabrikan: nomor yang sama bisa berarti lain di merek berbeda. Kirim model mobilnya, kami cocokkan dengan katalog kami.",
      other: "Kode ini ada di sistem yang tidak kami sediakan komponennya (EGR, transmisi, hibrida). Kami memasok pengapian, bahan bakar, pengukuran udara, sensor dan ABS.",
      first: "lebih dulu",
      then: "lalu"
    },
    fa: {
      hint: "کد عیب؟",
      all: "همهٔ کدها",
      nf: "هنوز صفحه‌ای برای کد {c} نداریم",
      lead: "ما {n} کد OBD-II را با جزئیات توضیح داده‌ایم و {c} هنوز در میان آن‌ها نیست. اما خانوادهٔ کد نشان می‌دهد اول کدام قطعات را بررسی کنید.",
      cats: "قطعاتی که اول بررسی می‌شوند",
      cta: "کد، خودرو (سال و موتور) و عکس دستگاه عیب‌یاب را بفرستید — پیش از سفارش می‌گوییم کدام شمارهٔ ما می‌خورد.",
      browse: "همهٔ کدهایی که پوشش می‌دهیم",
      u: "این کد مربوط به بدنه یا شبکه است. ما قطعات انژکتوری و ABS تأمین می‌کنیم؛ اول سیم‌کشی یا دستگاه عیب‌یاب را بررسی کنید و بعد بگویید کدام قطعه خراب شده.",
      manu: "{c} کد اختصاصی سازنده است: همین شماره در برندهای مختلف معانی متفاوتی دارد. مدل خودرو را بفرستید تا با کاتالوگ ما تطبیق دهیم.",
      other: "این کد مربوط به سیستمی است که ما قطعهٔ آن را نداریم (EGR، گیربکس یا هیبریدی). ما قطعات جرقه، سوخت‌رسانی، اندازه‌گیری هوا، سنسور و ABS را تأمین می‌کنیم.",
      first: "اول",
      then: "سپس"
    }
  };

  /* ------------------------------------------------------------------ 工具 */

  /* 输入 → 规范码（大写、去掉空格/连字符）；认不出返回 null。
     纯 4 位数字只在「是我们收录的码」时才当码，否则当成 OE/料号去搜型号——
     因为 0301 这种也可能本来就是料号片段，误判会把人带离型号搜索。 */
  function detect(raw) {
    var s = String(raw == null ? "" : raw).toUpperCase().replace(/[^0-9A-Z]+/g, "");
    var m = /^([PBCU])?(\d{4})$/.exec(s);
    if (!m) return null;
    if (m[1]) return m[1] + m[2];
    var guess = "P" + m[2];
    return isKnown(guess) ? guess : null;
  }

  function isKnown(code) {
    return KNOWN.indexOf(String(code || "").toLowerCase()) >= 0;
  }

  function family(code) {
    var c = String(code || "").toUpperCase();
    for (var i = 0; i < FAM.length; i++) {
      if (FAM[i][0].test(c)) return { cats: FAM[i][1], key: FAM[i][2] };
    }
    return null;
  }

  /* 目标地址。base = "" 给根目录页面，base = "../" 给 codes/ 里的页面。 */
  function href(code, base) {
    var c = String(code || "").toLowerCase();
    base = base || "";
    if (isKnown(c)) return base + "codes/" + c + ".html";
    return base + "codes/index.html?q=" + encodeURIComponent(String(code).toUpperCase());
  }

  function lang() {
    var l = (document.documentElement.getAttribute("data-lang") || "en").toLowerCase();
    l = l.slice(0, 2);
    return STR[l] ? l : "en";
  }

  /* ------------------------------------------------------ codes/index 面板 */

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m];
    });
  }

  function waHref(message) {
    var a = document.querySelector('a[href^="https://wa.me/"]');
    var num = a && /wa\.me\/(\d+)/.exec(a.href);
    if (!num) return "";
    return "https://wa.me/" + num[1] + "?text=" + encodeURIComponent(message);
  }

  /* 从地址栏的 ?q= 渲染提示面板；只在 codes/index.html 上有 #dtc-panel 时才动。 */
  function renderPanel() {
    var host = document.getElementById("dtc-panel");
    if (!host) return;
    var raw = "";
    try { raw = new URLSearchParams(location.search).get("q") || ""; } catch (e) { raw = ""; }
    var code = detect(raw);
    if (!code) return;

    /* 收录过的码：直接进诊断页，别让客户多点一次 */
    if (isKnown(code)) {
      location.replace("./" + code.toLowerCase() + ".html");
      return;
    }

    var L = STR[lang()];
    var n = KNOWN.length;
    var fam = family(code);
    var lead = L.lead.replace("{n}", n).replace("{c}", code);
    var body = [];

    /* 内联样式：不碰 assets/style.css（那个文件常有别人在改），面板自己也够用 */
    body.push("<section class=\"dsec\" style=\"border-top:1px solid #e2e8ee;margin-top:20px;padding-top:20px\">");
    body.push("<h2>" + esc(L.nf.replace("{c}", code)) + "</h2>");
    body.push("<p class=\"gp\">" + esc(lead) + "</p>");

    if (/^[BU]/.test(code)) {
      /* 车身 / 网络码：不装懂，直接说清我们不覆盖 */
      body.push("<p class=\"gp\">" + esc(L.u) + "</p>");
    } else if (fam) {
      body.push("<p class=\"gp\"><b>" + esc(L.cats) + ":</b></p>");
      body.push("<div class=\"guidecards\">");
      for (var i = 0; i < fam.cats.length; i++) {
        var slug = fam.cats[i];
        var meta = CAT[slug];
        if (!meta) continue;
        var order = i === 0 ? L.first : (i === 1 ? L.then : "");
        body.push(
          "<a class=\"guidecard\" href=\"../category/" + meta[0] + ".html\">" +
          "<b data-cat=\"" + slug + "\">" + esc(meta[1]) + "</b>" +
          (order ? "<span>" + esc(order) + "</span>" : "") +
          "</a>"
        );
      }
      body.push("</div>");
    } else if (/^[PBCU][1-3]/.test(code)) {
      /* P1xxx / P2xxx / P3xxx 这类厂家自定义码：同一个号在不同品牌含义不同，不能按码段套品类 */
      body.push("<p class=\"gp\">" + esc(L.manu.replace("{c}", code)) + "</p>");
    } else {
      /* 码段认得出（P0xxx / C0xxx）但没有对应件：EGR、变速箱这类我们不做的系统 */
      body.push("<p class=\"gp\">" + esc(L.other) + "</p>");
    }

    body.push("<p class=\"gp\">" + esc(L.cta) + "</p>");
    body.push("<p>");
    var wa = waHref("Hi, my " + (/[0-9]/.test(code) ? "car" : "car") +
                    " shows fault code " + code + ". Year/engine: ");
    if (wa) {
      body.push("<a class=\"btn-wa\" href=\"" + esc(wa) + "\" target=\"_blank\" rel=\"noopener\">" +
                "WhatsApp " + esc(code) + "</a> ");
    }
    body.push("<a class=\"btn-ghost\" href=\"./index.html\">" + esc(L.browse) + "</a>");
    body.push("</p>");
    body.push("</section>");

    host.innerHTML = body.join("");
    host.hidden = false;
    /* 品类名靠站里的 i18n 字典翻；插入后要再 apply 一次才会生效 */
    if (window.I18N && typeof window.I18N.apply === "function") {
      try { window.I18N.apply(); } catch (e) { /* 翻不动就保留英文，不影响功能 */ }
    }
  }

  /* --------------------------------------------- 首页搜索框下：「故障码也能查」 */
  /* 只在首页插（有 #homesearch + #q）。样式用内联：
     首页那块底色被配色改成了浅底，style.css 里的 .vtab 是给深底用的（半透明白字），
     直接套上去会看不见，所以这里自带一套白底深字的 pill。 */
  var HINT_CSS = {
    wrap: "display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:8px 0 0;font-size:13px;color:#41627d",
    chip: "border:1px solid #cfdae4;background:#fff;color:#16324a;border-radius:999px;" +
          "font-family:inherit;font-size:12.5px;line-height:1;padding:6px 11px;cursor:pointer",
    all: "color:#0f334d;text-decoration:none;border-bottom:1px solid rgba(15,51,77,.35)"
  };
  var HINT_CODES = ["P0301", "P0171", "C0035"];
  var PH_EXTRA = " · P0301";

  function submitForm(form) {
    try { if (form.requestSubmit) { form.requestSubmit(); return; } } catch (e) { /* 旧浏览器走下面 */ }
    var ev;
    try { ev = new Event("submit", { bubbles: true, cancelable: true }); }
    catch (e) { ev = document.createEvent("Event"); ev.initEvent("submit", true, true); }
    form.dispatchEvent(ev);
  }

  /* placeholder 里追加一个故障码示例。不改 i18n.js（那要升 I18N_V 全站重渲染），
     只在运行时追加；切语言后 I18N 会重设 placeholder，所以 i18n:change 时再补一次。 */
  function extendPlaceholder() {
    var q = document.getElementById("q");
    if (!q || q.getAttribute("data-i18n-ph") !== "home_ph") return;
    var ph = q.getAttribute("placeholder") || "";
    if (!ph || ph.indexOf("P0301") >= 0) return;
    q.setAttribute("placeholder", ph + PH_EXTRA);
  }

  function renderHintBar() {
    var q = document.getElementById("q");
    var form = document.getElementById("homesearch");
    if (!q || !form) return;
    extendPlaceholder();
    var L = STR[lang()];
    var bar = document.getElementById("dtc-hint");
    if (!bar) {
      bar = document.createElement("p");
      bar.id = "dtc-hint";
      bar.style.cssText = HINT_CSS.wrap;
      form.parentNode.insertBefore(bar, form.nextSibling);
      bar.addEventListener("click", function (e) {
        var b = e.target && e.target.closest ? e.target.closest("[data-dtc-ex]") : null;
        if (!b) return;
        e.preventDefault();
        q.value = b.getAttribute("data-dtc-ex");
        q.focus();
        submitForm(form);      /* 点了示例就直接查：示例码就该一路走到底 */
      });
    }
    var html = "<span>" + esc(L.hint) + "</span>";
    for (var i = 0; i < HINT_CODES.length; i++) {
      html += "<button type=\"button\" data-dtc-ex=\"" + HINT_CODES[i] + "\" style=\"" + HINT_CSS.chip + "\">" +
              HINT_CODES[i] + "</button>";
    }
    html += "<a href=\"codes/index.html\" style=\"" + HINT_CSS.all + "\">" + esc(L.all) + " &rarr;</a>";
    bar.innerHTML = html;
  }

  function boot() {
    renderPanel();      /* codes/index.html 的「未收录」面板 */
    renderHintBar();    /* 首页搜索框下的提示条 */
  }

  window.DTC = {
    detect: detect,
    isKnown: isKnown,
    family: family,
    href: href,
    render: renderPanel,
    hint: renderHintBar,
    known: KNOWN,
    cats: CAT,
    strings: STR
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  document.addEventListener("i18n:change", function () {
    renderHintBar();
    renderPanel();
  });
})();
