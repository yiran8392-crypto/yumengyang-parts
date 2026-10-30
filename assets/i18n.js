/* 型号查询站 · 界面多语言（en 默认，另有 zh / ar / ru）
   只翻界面文案和品类名；产品数据（型号 / 车型 / 备注）永远是英文。
   <title> / meta description / canonical 都不动，SEO 保持英文。
   页面里用 data-i18n="key" 标文案，data-v-n 之类给占位符传值；
   data-cat="coil" 标品类名。切换器是 <select class="langsel">。
   语言选择存 localStorage（键 ymy_lang），也支持 ?lang=zh 临时预览。 */
(function () {
  var DEF = "en";
  var KEY = "ymy_lang";
  var LANGS = [["en", "English"], ["zh", "简体中文"], ["ar", "العربية"], ["ru", "Русский"]];
  var IDX = { zh: 0, ar: 1, ru: 2 };

  /* 文案字典：en 走页面里的英文原文（fallback），这里只放 zh/ar/ru */
  var T = {
    zh: {
      nav_all: "全部 {n} 个品类", wa: "WhatsApp 询价", home: "首页", sitemap: "网站地图",
      lookup: "OE / 交叉号查询", lang_label: "语言",
      our_sku: "我方料号", spec_oe: "OE 号", spec_xref: "交叉号", spec_brand: "品牌",
      spec_fit: "适配车型", spec_notes: "备注", btn_wa: "WhatsApp 问价与起订量",
      btn_search_all: "搜索全部 {n} 个型号", block_app: "适配车型", block_buy: "采购说明",
      buy_text: "{company} 以自有品牌 {brand} 供应这些产品。把 OE 号发到 WhatsApp，我们确认现货、价格、起订量与包装；可按要求提供测试样品。",
      rel_more: "更多{cat}", more: "更多", nopic: "这个型号暂无实拍图", nopic_sub: "可以 WhatsApp 索取实拍图",
      langnote: "产品数据以英文显示", app_fallback: "请把车型发给我们，我们确认适配。",
      cat_lead: "我们现货的每个型号都带 OE 号和交叉号。点型号可以看适配、实拍图和询价按钮。",
      models_n: "{n} 个型号", search_oe: "按 OE 号搜索", filter_search: "在搜索页筛选",
      all_models: "全部型号（{n}）", models_range: "第 {a}–{b} 个，共 {n} 个",
      page_of: "第 {p} / {t} 页", all_cat_h1: "全部品类",
      all_cat_lead: "共 {c} 个品类、{n} 个型号。选一个品类，看全部型号的 OE 号、交叉号和适配。",
      cat_arrow: "{n} 个型号 →", home_h1: "汽配型号查询",
      home_sub: "输入 OE 号、交叉号、我方料号或车型，几秒钟找到对应产品。",
      top_h2: "热销品类", top_sub: "客户问得最多的六个品类，点卡片看全部型号。",
      home_ph: "OE 号 / 交叉号 / 料号 / 车型 —— 例如 90919-02248、WL18-AD001、Camry",
      clear: "清空", chip_all: "全部", found: "找到 {n} 个型号", shown: "已显示 {n}",
      of_total: "共 {n}", load_more: "加载更多（{n}）", no_match: "没有匹配的型号",
      hint_click: "点击卡片看大图与适配车型", hint_search: "搜索：{q}",
      empty_p: "可以试试型号后 6 位、去掉连字符（9091902248），或者用英文车型名（Camry / Golf / Audi A4）。",
      btn_copy: "复制型号", btn_copied: "已复制 ✓", btn_fullsize: "看大图",
      btn_inquiry: "WhatsApp 询价", btn_page: "独立页面", modal_oe: "OE 号",
      modal_xref: "交叉号", modal_fit: "适配车型", modal_notes: "备注", modal_cat: "品类",
      no_photo: "这个型号暂时没有图片", no_photo_sub: "可 WhatsApp 索取实拍",
      cat_h2: "按品类浏览全部型号",
      cat_home_lead: "每个品类下面列出前 100 个型号（点「查看全部」看整类），区块可折叠、可单独滚动。",
      catbox_open: "展开 / 收起：{c} 个品类 · {n} 个型号", view_all: "查看全部",
      updated: "更新时间 {d}", parts_n: "{n} 个型号",
      herostat: "{n} 个型号 · {m} 张实拍图",
      nf_h1: "页面走丢了", nf_p: "型号页可能换过链接。回首页按 OE 号搜一下，或者直接发 WhatsApp 问我们。",
      nf_back: "回到查询首页",
      /* VIN 车架号查询 */
      vin_tab_auto: "自动", vin_tab_oe: "OE 号", vin_tab_sku: "料号", vin_tab_model: "车型", vin_tab_vin: "VIN 车架号",
      vin_ph: "17 位 VIN 车架号 —— 例如 JTDBE46K940123456",
      vin_brand: "品牌", vin_wmi: "WMI（1-3 位）", vin_year: "年款（第 10 位）", vin_or: "或",
      vin_vds: "VDS（4-8 位）", vin_vds_note: "厂家自定义：车身 / 系列 / 发动机",
      vin_plant: "工厂（11）/ 序号", vin_prefix: "前缀", vin_prefix_note: "品牌按 WMI 推",
      vin_check_ok: "校验位有效", vin_check_bad: "校验位对不上，可能输错",
      vin_guess: "推测", vin_none: "未识别",
      vin_note: "已按品牌匹配适配车型。要 100% 确认请发零件照片或行驶证。",
      vin_unknown_wmi: "这个 WMI 不在离线表里，认不出品牌。",
      vin_nf_t: "这个 VIN 暂时没匹配到零件",
      vin_nf_p: "没从 VIN 认出车型。把车/零件/行驶证拍张照发我们，人工给你核。",
      vin_nf_p2: "也可以按车型名、OE 号或 VIN 前 6/8 位搜。",
      vin_ask: "把这个 VIN 发到 WhatsApp",
      f_title: "按车型选件", f_brand_any: "全部品牌", f_model_any: "全部车型", f_year_any: "全部年款", f_disp_any: "全部排量", f_clear: "重置",
      vin_hist_t: "该车架号历史查过的配件", vin_hist_note: "历史查询参考，请核实实车。",
    },
    ar: {
      nav_all: "كل الفئات ({n})", wa: "راسلنا على واتساب", home: "الرئيسية", sitemap: "خريطة الموقع",
      lookup: "بحث OE والمراجع", lang_label: "اللغة",
      our_sku: "رمزنا", spec_oe: "رقم OE", spec_xref: "المراجع البديلة",
      spec_brand: "العلامة التجارية", spec_fit: "التوافق مع المركبات", spec_notes: "ملاحظات",
      btn_wa: "واتساب للسعر والحد الأدنى", btn_search_all: "ابحث في {n} قطعة",
      block_app: "تطبيق المركبة", block_buy: "شراء هذه القطعة",
      buy_text: "{company} تورّد هذه القطع تحت علامتنا {brand}. أرسل رقم OE على واتساب وسنؤكد التوفر والسعر والحد الأدنى والتغليف. تتوفر عينات للاختبار عند الطلب.",
      rel_more: "المزيد من {cat}", more: "المزيد من", nopic: "لا توجد صورة لهذه القطعة",
      nopic_sub: "اطلب صورة حقيقية على واتساب", langnote: "بيانات المنتج معروضة بالإنجليزية",
      app_fallback: "أرسل لنا طراز مركبتك وسنؤكد التوافق.",
      cat_lead: "كل قطعة متوفرة لدينا مع رقم OE والمراجع. اضغط على رقم القطعة لعرض التوافق والصور وطلب عرض السعر.",
      models_n: "{n} قطعة", search_oe: "ابحث برقم OE", filter_search: "تصفية في صفحة البحث",
      all_models: "كل القطع ({n})", models_range: "القطع {a}–{b} من {n}",
      page_of: "صفحة {p} / {t}", all_cat_h1: "كل فئات المنتجات",
      all_cat_lead: "{c} فئة و {n} قطعة. اختر فئة لعرض كل قطعة برقم OE والمراجع والتوافق.",
      cat_arrow: "{n} قطعة ←", home_h1: "بحث أرقام OE والمراجع",
      home_sub: "ابحث برقم OE أو المرجع أو رمزنا أو المركبة — اعثر على القطعة في ثوانٍ.",
      top_h2: "الفئات الأكثر طلباً", top_sub: "ست فئات يطلبها عملاؤنا أكثر — اضغط على البطاقة لعرض كل القطع.",
      home_ph: "رقم OE / مرجع / رمز / مركبة — مثال 90919-02248 أو WL18-AD001 أو Camry",
      clear: "مسح", chip_all: "الكل", found: "تم إيجاد {n} قطعة", shown: "معروض {n}",
      of_total: "من {n}", load_more: "تحميل المزيد ({n})", no_match: "لا نتائج",
      hint_click: "اضغط على البطاقة لعرض الصورة والتوافق", hint_search: "بحث: {q}",
      empty_p: "جرّب آخر 6 أرقام من الرقم، أو احذف الشرطات (9091902248)، أو ابحث باسم الطراز بالإنجليزية (Camry / Golf / Audi A4).",
      btn_copy: "نسخ", btn_copied: "تم النسخ ✓", btn_fullsize: "الصورة الكاملة",
      btn_inquiry: "استفسار واتساب", btn_page: "صفحة التفاصيل", modal_oe: "رقم OE",
      modal_xref: "مراجع", modal_fit: "التوافق", modal_notes: "ملاحظات", modal_cat: "الفئة",
      no_photo: "لا توجد صورة لهذه القطعة بعد", no_photo_sub: "اطلب صورة على واتساب",
      cat_h2: "تصفح كل القطع حسب الفئة",
      cat_home_lead: "كل فئة تعرض أول 100 قطعة — اضغط «عرض الكل» للقائمة الكاملة.",
      catbox_open: "توسيع / طي: {c} فئة · {n} قطعة", view_all: "عرض الكل",
      updated: "آخر تحديث {d}", parts_n: "{n} قطعة",
      herostat: "{n} رقم قطعة · {m} صورة حقيقية",
      nf_h1: "الصفحة غير موجودة", nf_p: "ربما تغيّر رابط القطعة. ابحث برقم OE في الصفحة الرئيسية أو راسلنا على واتساب.",
      nf_back: "العودة للرئيسية",
      vin_tab_auto: "تلقائي", vin_tab_oe: "رقم OE", vin_tab_sku: "رمزنا", vin_tab_model: "الطراز", vin_tab_vin: "رقم الهيكل",
      vin_ph: "رقم هيكل 17 خانة — مثال JTDBE46K940123456",
      vin_brand: "العلامة", vin_wmi: "WMI (1-3)", vin_year: "سنة الطراز (10)", vin_or: "أو",
      vin_vds: "VDS (4-8)", vin_vds_note: "تحدده الشركة: الهيكل / السلسلة / المحرك",
      vin_plant: "المصنع (11) / التسلسل", vin_prefix: "البادئة", vin_prefix_note: "من WMI",
      vin_check_ok: "رقم التحقق صحيح", vin_check_bad: "رقم التحقق غير مطابق",
      vin_guess: "استنتاج", vin_none: "غير معروف",
      vin_note: "تمت المطابقة مع التوافق. للتأكيد التام أرسل صورة القطعة أو الرخصة.",
      vin_unknown_wmi: "WMI غير موجود في جدولنا — لا يمكن تحديد العلامة من رقم الهيكل.",
      vin_nf_t: "لم نجد قطعاً لهذا رقم الهيكل",
      vin_nf_p: "لم نتعرف على المركبة. أرسل صورة السيارة أو القطعة أو الرخصة وسنتحقق يدوياً.",
      vin_nf_p2: "أو ابحث باسم الطراز أو رقم OE أو أول 6 / 8 خانات.",
      vin_ask: "أرسل رقم الهيكل على واتساب",
      f_title: "التصفية حسب المركبة", f_brand_any: "كل العلامات", f_model_any: "كل الطرازات", f_year_any: "كل السنوات", f_disp_any: "كل السعات", f_clear: "إعادة تعيين",
      vin_hist_t: "قطع سبق البحث عنها بهذا رقم الهيكل", vin_hist_note: "مرجع من سجل البحث فقط — تحقق من المركبة الفعلية.",
    },
    ru: {
      nav_all: "Все категории ({n})", wa: "Написать в WhatsApp", home: "Главная",
      sitemap: "Карта сайта", lookup: "Поиск по OE и кросс-номерам", lang_label: "Язык",
      our_sku: "Наш артикул", spec_oe: "Номер OE", spec_xref: "Кросс-номера",
      spec_brand: "Бренд", spec_fit: "Применимость", spec_notes: "Примечания",
      btn_wa: "WhatsApp: цена и MOQ", btn_search_all: "Искать среди {n} деталей",
      block_app: "Применение", block_buy: "О закупке",
      buy_text: "{company} поставляет эти детали под нашим брендом {brand}. Пришлите номер OE в WhatsApp — подтвердим наличие, цену, MOQ и упаковку. Образцы для теста — по запросу.",
      rel_more: "Ещё {cat}", more: "Ещё", nopic: "Нет фото этой детали",
      nopic_sub: "Запросите настоящее фото в WhatsApp", langnote: "Данные о продукте приведены на английском",
      app_fallback: "Пришлите модель автомобиля — подтвердим применимость.",
      cat_lead: "Каждая деталь в наличии: номер OE и кросс-номера. Нажмите на номер детали, чтобы увидеть применимость, фото и кнопку запроса цены.",
      models_n: "{n} моделей", search_oe: "поиск по номеру OE", filter_search: "фильтр на странице поиска",
      all_models: "Все модели ({n})", models_range: "Модели {a}–{b} из {n}",
      page_of: "Стр. {p} / {t}", all_cat_h1: "Все категории",
      all_cat_lead: "{c} категорий, {n} артикулов. Выберите категорию, чтобы увидеть все модели с номерами OE, кросс-номерами и применимостью.",
      cat_arrow: "{n} моделей →", home_h1: "Поиск по OE и кросс-номерам",
      home_sub: "Поиск по номеру OE, кросс-номеру, нашему артикулу или модели авто — за секунды.",
      top_h2: "Хиты продаж", top_sub: "Шесть категорий, которые спрашивают чаще всего — нажмите на карточку, чтобы увидеть все модели.",
      home_ph: "Номер OE / кросс-номер / артикул / авто — напр. 90919-02248, WL18-AD001, Camry",
      clear: "Очистить", chip_all: "Все", found: "Найдено {n} деталей", shown: "показано {n}",
      of_total: "из {n}", load_more: "Ещё ({n})", no_match: "Ничего не найдено",
      hint_click: "Нажмите на карточку: фото и применимость", hint_search: "Поиск: {q}",
      empty_p: "Попробуйте последние 6 цифр, без дефисов (9091902248), или название модели на английском (Camry / Golf / Audi A4).",
      btn_copy: "Копировать", btn_copied: "Скопировано ✓", btn_fullsize: "Открыть фото",
      btn_inquiry: "Запрос в WhatsApp", btn_page: "Страница детали", modal_oe: "Номер OE",
      modal_xref: "Кросс-номер", modal_fit: "Применимость", modal_notes: "Примечания",
      modal_cat: "Категория", no_photo: "Фото для этой детали пока нет",
      no_photo_sub: "Запросите фото в WhatsApp", cat_h2: "Все модели по категориям",
      cat_home_lead: "В каждой категории — первые 100 моделей, «Смотреть все» откроет полный список.",
      catbox_open: "Развернуть / свернуть: {c} категорий · {n} моделей", view_all: "Смотреть все",
      updated: "Обновлено {d}", parts_n: "{n} деталей",
      herostat: "{n} артикулов · {m} реальных фото",
      nf_h1: "Страница не найдена", nf_p: "Возможно, ссылка на деталь изменилась. Найдите по номеру OE на главной или напишите нам в WhatsApp.",
      nf_back: "На главную",
      vin_tab_auto: "Авто", vin_tab_oe: "OE", vin_tab_sku: "Артикул", vin_tab_model: "Модель", vin_tab_vin: "VIN",
      vin_ph: "VIN из 17 знаков — напр. JTDBE46K940123456",
      vin_brand: "Бренд", vin_wmi: "WMI (1-3)", vin_year: "Год (10)", vin_or: "или",
      vin_vds: "VDS (4-8)", vin_vds_note: "задаёт завод: кузов / серия / двигатель",
      vin_plant: "Завод (11) / номер", vin_prefix: "Префикс", vin_prefix_note: "по WMI",
      vin_check_ok: "контрольная цифра верна", vin_check_bad: "контрольная цифра не совпала",
      vin_guess: "по префиксу", vin_none: "не распознан",
      vin_note: "Сверено с применимостью. Для 100% гарантии пришлите фото детали или техпаспорт.",
      vin_unknown_wmi: "Этого WMI нет в таблице — по VIN бренд не определить.",
      vin_nf_t: "По этому VIN детали не найдены",
      vin_nf_p: "Автомобиль по VIN не распознан. Пришлите фото машины, детали или техпаспорта — проверим вручную.",
      vin_nf_p2: "Или ищите по модели, номеру OE или первым 6 / 8 знакам.",
      vin_ask: "Отправить VIN в WhatsApp",
      f_title: "Подбор по авто", f_brand_any: "Все бренды", f_model_any: "Все модели", f_year_any: "Все годы", f_disp_any: "Все объёмы", f_clear: "Сброс",
      vin_hist_t: "Детали, которые уже искали по этому VIN", vin_hist_note: "Исторический справочник — проверьте по факту.",
    }
  };

  /* 品类名：key -> [zh, ar, ru]（英文名在原页面里，en 时用原文） */
  var C = {
    coil: ["点火线圈", "ملفات الإشعال", "Катушки зажигания"],
    fuelpump: ["燃油泵", "مضخات الوقود", "Топливные насосы"],
    o2: ["氧传感器", "حساسات الأكسجين", "Датчики кислорода"],
    plug: ["火花塞", "شمعات الإشعال", "Свечи зажигания"],
    abs: ["ABS 传感器", "حساسات ABS", "Датчики ABS"],
    wire: ["火花塞线", "أسلاك شمعات الإشعال", "Провода свечей"],
    thermo: ["节温器", "منظمات الحرارة", "Термостаты"],
    ckp: ["曲轴位置传感器", "حساسات موضع العمود المرفقي", "Датчики положения коленвала"],
    cmp: ["凸轮轴位置传感器", "حساسات موضع عمود الكامات", "Датчики положения распредвала"],
    dpfe: ["压差传感器", "حساسات الضغط التفاضلي", "Датчики перепада давления"],
    fuelpress: ["油压调节器", "منظمات ضغط الوقود", "Регуляторы давления топлива"],
    injector: ["喷油嘴", "حاقنات الوقود", "Форсунки"],
    maf: ["空气流量计", "حساسات تدفق الهواء", "Датчики массового расхода воздуха"],
    map: ["进气压力传感器", "حساسات ضغط المشعب", "Датчики давления во впуске"],
    njkspark: ["NJK 火花塞", "شمعات NJK", "Свечи NJK"],
    ocv: ["机油控制阀", "صمامات التحكم في الزيت", "Клапаны управления маслом"],
    purge: ["碳罐电磁阀", "صمامات تطهير العلبة", "Клапаны продувки адсорбера"],
    stepper: ["怠速马达", "محركات الخطوة", "Шаговые моторы"],
    temp: ["温度传感器", "حساسات الحرارة", "Датчики температуры"],
    throttle: ["节气门阀体", "جسم الخانق", "Дроссельные узлы"],
    tpms: ["胎压传感器", "حساسات ضغط الإطارات", "Датчики давления в шинах"],
    tps: ["节气门位置传感器", "حساسات موضع الخانق", "Датчики положения дросселя"],
    vsv: ["真空电磁阀", "صمامات التفريغ", "Вакуумные клапаны"]
  };

  var lang = DEF;

  function norm(v) {
    v = String(v || "").toLowerCase();
    if (v.indexOf("zh") === 0) return "zh";
    if (v.indexOf("ar") === 0) return "ar";
    if (v.indexOf("ru") === 0) return "ru";
    return "en";
  }
  function fill(s, vars) {
    return String(s).replace(/\{(\w+)\}/g, function (m, n) {
      return vars && vars[n] != null ? vars[n] : m;
    });
  }
  function t(key, fb, vars) {
    var d = T[lang];
    var s = d && d[key] != null ? d[key] : null;
    if (s == null) s = fb == null ? "" : fb;
    return fill(s, vars);
  }
  function catName(key, fb) {
    var arr = C[key];
    if (!arr || lang === "en") return fb || "";
    return arr[IDX[lang]] || fb || "";
  }
  function domVars(el) {
    var v = {}, a;
    for (var i = 0; i < el.attributes.length; i++) {
      a = el.attributes[i];
      if (a.name.indexOf("data-v-") === 0) v[a.name.slice(7)] = a.value;
    }
    return v;
  }
  function apply() {
    var root = document.documentElement;
    root.setAttribute("lang", lang === "zh" ? "zh-CN" : lang);
    root.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    root.setAttribute("data-lang", lang);

    var i, el, s, list = document.querySelectorAll("[data-i18n]");
    for (i = 0; i < list.length; i++) {
      el = list[i];
      if (!el.hasAttribute("data-i18n-src")) el.setAttribute("data-i18n-src", el.textContent);
      s = T[lang] && T[lang][el.getAttribute("data-i18n")];
      el.textContent = s == null ? el.getAttribute("data-i18n-src") : fill(s, domVars(el));
    }
    list = document.querySelectorAll("[data-i18n-ph]");
    for (i = 0; i < list.length; i++) {
      el = list[i];
      if (!el.hasAttribute("data-i18n-ph-src")) el.setAttribute("data-i18n-ph-src", el.getAttribute("placeholder") || "");
      s = T[lang] && T[lang][el.getAttribute("data-i18n-ph")];
      el.setAttribute("placeholder", s == null ? el.getAttribute("data-i18n-ph-src") : fill(s, domVars(el)));
    }
    list = document.querySelectorAll("[data-cat]");
    for (i = 0; i < list.length; i++) {
      el = list[i];
      if (!el.hasAttribute("data-cat-src")) el.setAttribute("data-cat-src", el.textContent);
      el.textContent = catName(el.getAttribute("data-cat"), el.getAttribute("data-cat-src"));
    }
    list = document.querySelectorAll("select.langsel");
    for (i = 0; i < list.length; i++) list[i].value = lang;

    try {
      document.dispatchEvent(new CustomEvent("i18n:change", { detail: { lang: lang } }));
    } catch (e) {}
  }
  function set(v, save) {
    lang = norm(v);
    if (save) { try { localStorage.setItem(KEY, lang); } catch (e) {} }
    apply();
  }
  function read() {
    var q = "";
    try { q = new URLSearchParams(location.search).get("lang") || ""; } catch (e) {}
    if (!q) { try { q = localStorage.getItem(KEY) || ""; } catch (e) {} }
    return norm(q);
  }

  document.addEventListener("change", function (e) {
    var el = e.target;
    if (el && el.classList && el.classList.contains("langsel")) set(el.value, true);
  });

  window.I18N = {
    t: t, cat: catName, set: set, apply: apply, read: read,
    get lang() { return lang; },
    langs: LANGS
  };

  lang = read();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
