/* 型号查询站 · 界面多语言（en 默认，另有 zh / ar / ru / fr）
   只翻界面文案和品类名；产品数据（型号 / 车型 / 备注）永远是英文。
   <title> / meta description / canonical 都不动，SEO 保持英文。
   页面里用 data-i18n="key" 标文案，data-v-n 之类给占位符传值；
   data-cat="coil" 标品类名。切换器是 <select class="langsel">。
   语言选择存 localStorage（键 ymy_lang），也支持 ?lang=zh 临时预览。
   加新语种要动三处：这里（LANGS / IDX / T / C / norm）、sitegen.py 的
   LANG_OPTIONS + LANG_BOOT、assets/share.js，然后跑 rerender.py 重出页面。 */
(function () {
  var DEF = "en";
  var KEY = "ymy_lang";
  var LANGS = [["en", "English"], ["zh", "简体中文"], ["ar", "العربية"], ["ru", "Русский"], ["fr", "Français"]];
  var IDX = { zh: 0, ar: 1, ru: 2, fr: 3 };

  /* 文案字典：en 走页面里的英文原文（fallback），这里只放 zh/ar/ru/fr */
  var T = {
    zh: {
      nav_all: "全部 {n} 个品类", wa: "WhatsApp 询价", home: "首页", sitemap: "网站地图",
      guides_link: "采购指南", guides_h: "采购指南", guides_more: "更多指南", guides_use: "接下来",
      guides_lead: "来自我们车间和外贸部的实操笔记：怎么读料号、怎么用车架号定位车型、怎么先诊断再下单。产品数据保持英文，界面跟随你的语言。",
      lookup: "OE / 交叉号查询", lang_label: "语言",
      our_sku: "我方料号", spec_oe: "OE 号", spec_xref: "交叉号", spec_brand: "品牌",
      spec_fit: "适配车型", spec_fit_brands: "适配品牌", spec_notes: "备注", btn_wa: "WhatsApp 问价与起订量",
      spec_years: "年份", spec_displ: "排量", spec_engine: "发动机号",
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
      empty_filters: "当前筛选", empty_drop: "去掉", empty_reset: "重置全部筛选",
      empty_wa: "WhatsApp 问一句，可能目录里没上架",
      empty_note: "站点已有 {n} 个型号，每周还在上新。把 OE 号或零件照片发给我们，人工帮你查。",
      hint_relax: "试着放宽一个条件，或换个写法",
      scanning: "正在搜索…", scanning_h: "正在扫描全部 {n} 个型号…",
      scanning_p: "目录被拆成小文件，首页才能秒开；剩下的正在加载。", scanning_n: "已加载 {n}%",
      load_more_rest: "继续加载", loading_more: "加载中…", chunk_fail: "部分数据没加载成功",
      hint_click: "点击卡片看大图与适配车型", hint_search: "搜索：{q}",
      empty_p: "可以试试型号后 6 位、去掉连字符（9091902248），或者用英文车型名（Camry / Golf / Audi A4）。",
      btn_copy: "复制型号", btn_copied: "已复制 ✓", btn_fullsize: "看大图",
      btn_inquiry: "WhatsApp 询价", btn_page: "独立页面", modal_oe: "OE 号",
      modal_xref: "交叉号", modal_fit: "适配车型", modal_notes: "备注", modal_cat: "品类",
      no_photo: "这个型号暂时没有图片", no_photo_sub: "可 WhatsApp 索取实拍",
      cat_h2: "按品类浏览全部型号",
      cat_home_lead: "每个品类下面列出前 100 个型号（点「查看全部」看整类），区块可折叠、可单独滚动。",
      brand_h2: "按车辆品牌浏览配件",
      brand_home_lead: "按适配的车辆品牌分组：丰田、现代、起亚、宝马、福特、大众等等。每个品牌页列出该品牌的全部型号，带 OE 号和交叉号。",
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
      vin_hist_t: "该车架号历史查过的配件", vin_hist_note: "历史查询参考，请核实实车。", vin_sku_hist: "历史编号",
      /* ---------- 官网化区块 ---------- */
      trust_warranty: "全系质保", trust_v_warranty: "12–24 个月", trust_v_moq: "小批量", trust_return: "退货率", trust_cover: "电喷件覆盖", trust_moq: "支持小批量",
      why_h: "25+ 个国家的买家为什么从我们这里下单", why_lead: "我们是工厂，不是中间商：同样的型号、一样的检验，价格只有原厂的一小部分。",
      why_q_t: "OE 级品质", why_q_v: "自有品牌 WEILI，按 OE 规格生产我们做的电器件与传感器。",
      why_p_t: "约 1/3 原厂价", why_p_v: "工厂直供，中间没有进口商、没有分销商。",
      why_r_t: "24 小时报价", why_r_v: "发 OE 号或照片 + 数量，一个工作日内回带价报价。",
      why_s_t: "全球发货", why_s_v: "广州港直达你的门，包装按件型配，路上不磕坏。",
      hot_h: "热门型号", hot_all: "全部品类", hot_sub: "本季卖得最多的型号 —— 点开卡片看适配车型、实拍图和 WhatsApp 询价按钮。",
      faq_h: "常见问题", faq_lead: "买家下第一单前最常问的六件事。还有别的 —— 发 WhatsApp，一个工作日内回。",
      faq_q1: "起订量（MOQ）是多少？", faq_a1: "MOQ 取决于型号和包装。把你要的型号和数量发过来，我们按行逐条确认。",
      faq_q2: "交期多久？", faq_a2: "现货几天内从广州仓发出；生产单看数量 —— 具体发货日期写进报价里确认。",
      faq_q3: "质保多久？", faq_a3: "按品类 12–24 个月。具体年限写在报价单和发票上，你我看到的是一样的。",
      faq_q4: "可以退货换货吗？", faq_a4: "可以。把问题件的照片发过来，我们换货或冲抵货款。我们的退货率是 0.03%，很少见。",
      faq_q5: "可以先拿样品测试吗？", faq_a5: "可以。大货前可按要求提供样品，运费由买家承担。",
      faq_q6: "怎么付款？", faq_a6: "标准方式是电汇（T/T）。付款条件在你付款前会写在发票上。",
      foot_addr: "{cn}", foot_contact: "联系方式", foot_email: "邮箱",
      foot_hours: "工作时间", foot_links: "找配件", foot_parts: "型号 · 实拍图 · 适配数据",
      foot_legal: "政策", foot_privacy: "隐私政策", foot_returns: "退换货政策",
      doc_ref: "以英文版本为准", foot_contact_via: "对这份说明有疑问？WhatsApp 或邮件联系，一个工作日内回复。",
      block_terms: "质保 · 交期 · 起订量 · 样品",
      t_warranty: "质保", t_warranty_v: "按品类 12–24 个月。具体年限写在报价单和发票上。",
      t_lead: "交期", t_lead_v: "现货几天内从广州仓发出；生产单看数量，发货日期按单确认。",
      t_moq: "起订量", t_moq_v: "按型号和包装定。把清单发来，我们逐条确认；首个订单小批量也可以。",
      t_sample: "样品", t_sample_v: "大货前可按要求提供测试样品，运费由买家承担。",
      rel_more_h: "更多", rel_note: "同品类的相近型号 —— 下单前请核对 OE 号。",
      cta_h: "这个型号要报价？", cta_p: "把型号和 OE 号发到 WhatsApp —— 一个工作日内回价格、起订量和包装。",
      cta_btn: "WhatsApp 询价（{n}）",
      lk_oe_t: "同 OE / 同交叉号的其他型号", lk_veh_t: "同车型的热门件",
      lk_rel_t: "同品类的其他型号",
      /* ---------- 品牌页 / 车型页 ---------- */
      brands_crumb: "品牌", vehicles_crumb: "车型",
      brand_idx_h1: "按车辆品牌浏览",
      brand_idx_lead: "配件按适配的车辆品牌分组。共 {b} 个品牌、{n} 个型号 —— 每个型号都能看 OE 号、交叉号、实拍图和 WhatsApp 询价按钮。",
      browse_vehicle: "按车型浏览", browse_brand: "按品牌浏览", search_oe_btn: "按 OE 号搜索",
      brand_parts_h1: "{b} 配件", parts_n_paren: "（{n} 个型号）",
      brand_lead: "点火线圈、传感器、燃油泵等 {b} 配件。每个型号都带 OE 号、交叉号、适配信息和实拍图；把 OE 号发到 WhatsApp，我们回价格、起订量与包装。",
      brand_search_oe: "按 OE 号搜索 {b} 配件", brand_models_h2: "{b} 车型", brand_xfit_h2: "也适用于这些车型", brand_others_h2: "其他品牌",
      see_all_cat: "查看全部 {n} 个{cat}",
      veh_idx_lead: "车型名取自我们的适配数据。共 {v} 个车型、{n} 个型号。选一个车型，看全部适配配件和它们的 OE 号。",
      all_veh_h2: "全部车型（{n}）",
      veh_lead: "适配 {v} 的配件。每个型号都带 OE 号、交叉号、适配信息和实拍图；把 OE 号发到 WhatsApp，我们回价格、起订量与包装。",
      veh_brands_h2: "适配品牌", veh_others_h2: "其他车型",
    },
    ar: {
      nav_all: "كل الفئات ({n})", wa: "راسلنا على واتساب", home: "الرئيسية", sitemap: "خريطة الموقع",
      guides_link: "أدلة الشراء", guides_h: "أدلة الشراء", guides_more: "أدلة أخرى", guides_use: "الخطوة التالية",
      guides_lead: "ملاحظات عملية من ورشتنا وقسم التصدير: كيف تقرأ رقم القطعة، وكيف تحدد السيارة من رقم الهيكل، وكيف تشخّص قبل الطلب. بيانات المنتج بالإنجليزية، والواجهة بلغتك.",
      lookup: "بحث OE والمراجع", lang_label: "اللغة",
      our_sku: "رمزنا", spec_oe: "رقم OE", spec_xref: "المراجع البديلة",
      spec_brand: "العلامة التجارية", spec_fit: "التوافق مع المركبات", spec_fit_brands: "علامات التوافق", spec_notes: "ملاحظات",
      spec_years: "سنوات الصنع", spec_displ: "سعة المحرك", spec_engine: "رقم المحرك",
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
      empty_filters: "الفلاتر الحالية", empty_drop: "إزالة", empty_reset: "إعادة تعيين كل الفلاتر",
      empty_wa: "اسألنا على واتساب — قد تكون القطعة خارج الكتالوج",
      empty_note: "لدينا {n} قطعة على الموقع ونضيف الجديد أسبوعياً. أرسل رقم OE أو صورة القطعة وسنتحقق.",
      hint_relax: "جرّب إزالة أحد الفلاتر أو صيغة أخرى للرقم",
      scanning: "جارٍ البحث…", scanning_h: "جارٍ فحص كل القطع ({n})…",
      scanning_p: "الكتالوج مقسّم إلى ملفات صغيرة كي تفتح الصفحة بسرعة، والباقي يُحمّل الآن.", scanning_n: "تم تحميل {n}%",
      load_more_rest: "تحميل المزيد", loading_more: "جارٍ التحميل…", chunk_fail: "تعذّر تحميل بعض الملفات",
      hint_click: "اضغط على البطاقة لعرض الصورة والتوافق", hint_search: "بحث: {q}",
      empty_p: "جرّب آخر 6 أرقام من الرقم، أو احذف الشرطات (9091902248)، أو ابحث باسم الطراز بالإنجليزية (Camry / Golf / Audi A4).",
      btn_copy: "نسخ", btn_copied: "تم النسخ ✓", btn_fullsize: "الصورة الكاملة",
      btn_inquiry: "استفسار واتساب", btn_page: "صفحة التفاصيل", modal_oe: "رقم OE",
      modal_xref: "مراجع", modal_fit: "التوافق", modal_notes: "ملاحظات", modal_cat: "الفئة",
      no_photo: "لا توجد صورة لهذه القطعة بعد", no_photo_sub: "اطلب صورة على واتساب",
      cat_h2: "تصفح كل القطع حسب الفئة",
      cat_home_lead: "كل فئة تعرض أول 100 قطعة — اضغط «عرض الكل» للقائمة الكاملة.",
      brand_h2: "تصفح القطع حسب ماركة المركبة",
      brand_home_lead: "القطع مجمّعة حسب ماركة المركبة التي تناسبها — تويوتا وهيونداي وكيا وبي إم دبليو وفورد وفولكس فاجن وغيرها. كل صفحة ماركة تعرض كل أرقام قطعها مع رقم OE والمراجع.",
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
      vin_hist_t: "قطع سبق البحث عنها بهذا رقم الهيكل", vin_hist_note: "مرجع من سجل البحث فقط — تحقق من المركبة الفعلية.", vin_sku_hist: "رمز محفوظ",
      /* ---------- 官网化区块 ---------- */
      trust_warranty: "ضمان على كل قطعة", trust_v_warranty: "12–24 شهراً", trust_v_moq: "طلبيات صغيرة", trust_return: "نسبة الإرجاع", trust_cover: "تغطية قطع الحقن الإلكتروني", trust_moq: "طلبات صغيرة مقبولة",
      why_h: "لماذا يشتري منّا تجّار من أكثر من 25 دولة", why_lead: "نحن المصنع ولسنا وسيطاً: نفس أرقام القطع، مفحوصة، بجزء بسيط من سعر الوكيل.",
      why_q_t: "جودة بمستوى OE", why_q_v: "تُصنع قطعنا الكهربائية والحسّاسات حسب مواصفات OE تحت علامتنا WEILI.",
      why_p_t: "حوالي ثلث سعر الوكيل", why_p_v: "سعر مباشر من المصنع، دون مستورد أو موزّع في المنتصف.",
      why_r_t: "عرض سعر خلال 24 ساعة", why_r_v: "أرسل رقم OE أو صورة مع الكمية — يصلك عرض مسعّر خلال يوم عمل.",
      why_s_t: "شحن إلى كل العالم", why_s_v: "من ميناء قوانغتشو إلى بابك، والتغليف يناسب نوع القطعة فلا تصل متضررة.",
      hot_h: "أرقام القطع الأكثر طلباً", hot_all: "كل الفئات", hot_sub: "القطع الأكثر بيعاً هذا الموسم — كل بطاقة تفتح قائمة التوافق والصور وزر عرض السعر على واتساب.",
      faq_h: "الأسئلة الشائعة", faq_lead: "ستة أسئلة يسألها المشترون قبل أول طلب. وأي سؤال آخر — أرسله على واتساب ونرد خلال يوم عمل.",
      faq_q1: "ما هو الحد الأدنى للطلب؟", faq_a1: "الحد الأدنى يعتمد على القطعة والتغليف. أرسل الأرقام والكميات المطلوبة ونؤكدها بنداً بنداً.",
      faq_q2: "كم تستغرق مدة التسليم؟", faq_a2: "القطع المتوفرة تخرج من مستودعنا في قوانغتشو خلال أيام. طلبات الإنتاج تعتمد على الكمية — ونؤكد تاريخ الشحن في عرض السعر.",
      faq_q3: "ما مدة الضمان؟", faq_a3: "من 12 إلى 24 شهراً حسب نوع القطعة. المدة الدقيقة مكتوبة في عرض السعر والفاتورة، فتكون واحدة لك ولنا.",
      faq_q4: "هل يمكن الإرجاع أو التبديل؟", faq_a4: "نعم. أرسل صوراً للمشكلة ونستبدل القطع المعطوبة أو نخصم قيمتها. نسبة الإرجاع لدينا 0.03% فهي حالة نادرة.",
      faq_q5: "هل أحصل على عيّنات للاختبار؟", faq_a5: "نعم. العيّنات متاحة عند الطلب قبل الشراء بالكمية، ويتحمّل المشتري تكلفة الشحن.",
      faq_q6: "كيف أدفع؟", faq_a6: "التحويل البنكي (T/T) هو طريقتنا القياسية. تُثبَّت شروط الدفع في الفاتورة قبل أن تدفع.",
      foot_addr: "{en}", foot_contact: "التواصل", foot_email: "البريد الإلكتروني",
      foot_hours: "ساعات العمل", foot_links: "ابحث عن قطعة", foot_parts: "أرقام القطع · صور حقيقية · بيانات التوافق",
      foot_legal: "السياسات", foot_privacy: "سياسة الخصوصية", foot_returns: "سياسة الإرجاع والاستبدال",
      doc_ref: "النسخة الإنجليزية هي المرجع", foot_contact_via: "لديك سؤال عن هذه الصفحة؟ راسلنا على واتساب أو البريد ونرد خلال يوم عمل.",
      block_terms: "الضمان · مدة التسليم · الحد الأدنى · العيّنات",
      t_warranty: "الضمان", t_warranty_v: "من 12 إلى 24 شهراً حسب نوع القطعة. المدة الدقيقة مكتوبة في عرض السعر والفاتورة.",
      t_lead: "مدة التسليم", t_lead_v: "القطع المتوفرة تخرج خلال أيام من مستودع قوانغتشو؛ طلبات الإنتاج حسب الكمية ويُؤكَّد التاريخ لكل طلب.",
      t_moq: "الحد الأدنى للطلب", t_moq_v: "يُحدَّد حسب القطعة والتغليف. أرسل قائمتك ونؤكد كل بند؛ والطلبات الأولى الصغيرة مقبولة.",
      t_sample: "العيّنات", t_sample_v: "متاحة عند الطلب للاختبار قبل الشراء بالكمية، ويتحمّل المشتري تكلفة الشحن.",
      rel_more_h: "المزيد من", rel_note: "قطع من نفس الفئة — تحقّق من رقم OE قبل الطلب.",
      cta_h: "تريد سعراً لهذه القطعة؟", cta_p: "أرسل الرمز ورقم OE على واتساب — نرد بالسعر والحد الأدنى والتغليف خلال يوم عمل.",
      cta_btn: "واتساب: {n}",
      lk_oe_t: "قطع أخرى بنفس رقم OE / المراجع", lk_veh_t: "قطع شائعة لنفس المركبة",
      lk_rel_t: "قطع أخرى من نفس الفئة",
      /* ---------- 品牌页 / 车型页 ---------- */
      brands_crumb: "العلامات", vehicles_crumb: "الطرازات",
      brand_idx_h1: "تصفح حسب ماركة المركبة",
      brand_idx_lead: "القطع مجمّعة حسب ماركة المركبة التي تناسبها. {b} ماركة و {n} قطعة — كل قطعة تربطك برقم OE والمراجع والصور وزر طلب السعر على واتساب.",
      browse_vehicle: "تصفح حسب الطراز", browse_brand: "تصفح حسب العلامة", search_oe_btn: "ابحث برقم OE",
      brand_parts_h1: "قطع {b}", parts_n_paren: "({n} قطعة)",
      brand_lead: "ملفات إشعال وحسّاسات ومضخات وقود وغيرها من قطع {b}. كل قطعة مربوطة برقم OE والمراجع والتوافق والصور. أرسل رقم OE على واتساب للسعر والحد الأدنى والتغليف.",
      brand_search_oe: "ابحث عن قطع {b} برقم OE", brand_models_h2: "طرازات {b}", brand_xfit_h2: "يناسب أيضًا هذه الطرازات", brand_others_h2: "ماركات أخرى",
      see_all_cat: "عرض كل {n} {cat}",
      veh_idx_lead: "أسماء الطرازات مأخوذة من بيانات التوافق. {v} طرازاً و {n} قطعة. اختر طرازاً لعرض كل القطع المتوافقة بأرقام OE.",
      all_veh_h2: "كل الطرازات ({n})",
      veh_lead: "قطع تناسب {v}. كل قطعة تعرض رقم OE والمراجع والتوافق والصور. أرسل رقم OE على واتساب للسعر والحد الأدنى والتغليف.",
      veh_brands_h2: "ماركات متوافقة", veh_others_h2: "طرازات أخرى",
    },
    ru: {
      nav_all: "Все категории ({n})", wa: "Написать в WhatsApp", home: "Главная",
      sitemap: "Карта сайта", lookup: "Поиск по OE и кросс-номерам", lang_label: "Язык",
      guides_link: "Руководства", guides_h: "Руководства по подбору", guides_more: "Другие материалы",
      guides_use: "Что дальше",
      guides_lead: "Короткие практические заметки нашего цеха и отдела экспорта: как читать номер детали, как определить автомобиль по VIN и как проверить неисправность до заказа. Данные товаров на английском, интерфейс на вашем языке.",
      our_sku: "Наш артикул", spec_oe: "Номер OE", spec_xref: "Кросс-номера",
      spec_brand: "Бренд", spec_fit: "Применимость", spec_fit_brands: "Совместимые марки", spec_notes: "Примечания",
      spec_years: "Годы выпуска", spec_displ: "Объём двигателя", spec_engine: "Код двигателя",
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
      empty_filters: "Активные фильтры", empty_drop: "Убрать", empty_reset: "Сбросить все фильтры",
      empty_wa: "Спросите в WhatsApp — возможно, детали нет в каталоге",
      empty_note: "На сайте {n} артикулов, список пополняется каждую неделю. Пришлите номер OE или фото детали — проверим.",
      hint_relax: "Снимите один фильтр или попробуйте другой формат номера",
      scanning: "Идёт поиск…", scanning_h: "Проверяем все {n} деталей…",
      scanning_p: "Каталог разбит на небольшие файлы, чтобы страница открывалась быстро; остальное загружается.", scanning_n: "загружено {n}%",
      load_more_rest: "Загрузить ещё", loading_more: "Загрузка…", chunk_fail: "часть файлов не загрузилась",
      hint_click: "Нажмите на карточку: фото и применимость", hint_search: "Поиск: {q}",
      empty_p: "Попробуйте последние 6 цифр, без дефисов (9091902248), или название модели на английском (Camry / Golf / Audi A4).",
      btn_copy: "Копировать", btn_copied: "Скопировано ✓", btn_fullsize: "Открыть фото",
      btn_inquiry: "Запрос в WhatsApp", btn_page: "Страница детали", modal_oe: "Номер OE",
      modal_xref: "Кросс-номер", modal_fit: "Применимость", modal_notes: "Примечания",
      modal_cat: "Категория", no_photo: "Фото для этой детали пока нет",
      no_photo_sub: "Запросите фото в WhatsApp", cat_h2: "Все модели по категориям",
      cat_home_lead: "В каждой категории — первые 100 моделей, «Смотреть все» откроет полный список.",
      brand_h2: "Подбор деталей по марке автомобиля",
      brand_home_lead: "Детали сгруппированы по марке автомобиля, на который они подходят — Toyota, Hyundai, Kia, BMW, Ford, Volkswagen и другие. На странице каждой марки — все её артикулы с номерами OE и кросс-номерами.",
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
      vin_hist_t: "Детали, которые уже искали по этому VIN", vin_hist_note: "Исторический справочник — проверьте по факту.", vin_sku_hist: "архивный код",
      /* ---------- 官网化区块 ---------- */
      trust_warranty: "Гарантия на каждую деталь", trust_v_warranty: "12–24 мес.", trust_v_moq: "Малые партии", trust_return: "Доля возвратов", trust_cover: "Покрытие деталей впрыска", trust_moq: "Малые партии",
      why_h: "Почему покупатели из 25+ стран заказывают у нас", why_lead: "Мы завод, а не посредник: те же номера, проверенные детали, за часть цены оригинала.",
      why_q_t: "Качество уровня OE", why_q_v: "Электрика и датчики выпускаются по спецификации OE под нашим брендом WEILI.",
      why_p_t: "Около 1/3 цены OEM", why_p_v: "Цена напрямую с завода — без импортёра и дистрибьютора посередине.",
      why_r_t: "Предложение за 24 часа", why_r_v: "Пришлите номер OE или фото с количеством — ценовое предложение будет в течение рабочего дня.",
      why_s_t: "Доставка по всему миру", why_s_v: "Из порта Гуанчжоу до вашей двери; упаковка подбирается под деталь, чтобы ничего не пострадало в пути.",
      hot_h: "Популярные артикулы", hot_all: "Все категории", hot_sub: "Самые продаваемые модели сезона — карточка открывает применяемость, фото и кнопку запроса цены в WhatsApp.",
      faq_h: "Частые вопросы", faq_lead: "Шесть вопросов, которые задают перед первым заказом. Остальное — напишите в WhatsApp, ответим в течение рабочего дня.",
      faq_q1: "Каков минимальный заказ?", faq_a1: "MOQ зависит от детали и упаковки. Пришлите модели и количества — подтвердим MOQ по каждой позиции.",
      faq_q2: "Сколько идёт доставка?", faq_a2: "Складские позиции уходят с нашего склада в Гуанчжоу в течение нескольких дней. Срок производства зависит от количества — точную дату фиксируем в предложении.",
      faq_q3: "Какая гарантия?", faq_a3: "От 12 до 24 месяцев в зависимости от типа детали. Точный срок указан в предложении и счёте — он одинаков для вас и для нас.",
      faq_q4: "Можно вернуть или обменять деталь?", faq_a4: "Да. Пришлите фото проблемы — заменим или зачтём бракованные детали. Доля возвратов у нас 0.03%, это редкость.",
      faq_q5: "Можно получить образцы для теста?", faq_a5: "Да. Образцы предоставляются по запросу до серийного заказа; доставку оплачивает покупатель.",
      faq_q6: "Как оплатить?", faq_a6: "Стандартно — банковский перевод (T/T). Условия оплаты фиксируются в счёте до оплаты.",
      foot_addr: "{en}", foot_contact: "Контакты", foot_email: "E-mail",
      foot_hours: "Часы работы", foot_links: "Найти деталь", foot_parts: "Артикулы · реальные фото · применяемость",
      foot_legal: "Документы", foot_privacy: "Политика конфиденциальности", foot_returns: "Возврат и обмен",
      doc_ref: "Справочной является английская версия", foot_contact_via: "Вопрос по этой странице? Напишите в WhatsApp или на e-mail — ответим в течение рабочего дня.",
      block_terms: "Гарантия · сроки · MOQ · образцы",
      t_warranty: "Гарантия", t_warranty_v: "12–24 месяца в зависимости от типа детали. Точный срок указан в предложении и счёте.",
      t_lead: "Сроки", t_lead_v: "Складские позиции уходят из Гуанчжоу в течение дней; производство зависит от количества, дату подтверждаем по заказу.",
      t_moq: "MOQ", t_moq_v: "Определяется деталью и упаковкой. Пришлите список — подтвердим по позициям; небольшие первые заказы возможны.",
      t_sample: "Образцы", t_sample_v: "Доступны по запросу для теста до серийного заказа; доставку оплачивает покупатель.",
      rel_more_h: "Ещё", rel_note: "Похожие позиции той же категории — сверьте номер OE перед заказом.",
      cta_h: "Нужна цена на эту деталь?", cta_p: "Отправьте артикул и номер OE в WhatsApp — ответим ценой, MOQ и упаковкой в течение рабочего дня.",
      cta_btn: "WhatsApp: {n}",
      lk_oe_t: "Другие артикулы с тем же OE / кросс-номером", lk_veh_t: "Популярные детали для того же авто",
      lk_rel_t: "Другие артикулы этой категории",
      /* ---------- 品牌页 / 车型页 ---------- */
      brands_crumb: "Марки", vehicles_crumb: "Модели",
      brand_idx_h1: "Подбор по марке автомобиля",
      brand_idx_lead: "Детали сгруппированы по марке автомобиля. {b} марок, {n} артикулов — у каждой детали номер OE, кросс-номера, фото и кнопка запроса цены в WhatsApp.",
      browse_vehicle: "Подбор по модели", browse_brand: "Подбор по марке", search_oe_btn: "Поиск по номеру OE",
      brand_parts_h1: "Детали {b}", parts_n_paren: "({n} артикулов)",
      brand_lead: "Катушки зажигания, датчики, топливные насосы и другие детали для {b}. У каждой детали — номер OE, кросс-номера, применимость и фото. Пришлите номер OE в WhatsApp: цена, MOQ и упаковка.",
      brand_search_oe: "Искать детали {b} по номеру OE", brand_models_h2: "Модели {b}", brand_xfit_h2: "Также подходит для моделей", brand_others_h2: "Другие марки",
      see_all_cat: "Все {n} {cat}",
      veh_idx_lead: "Названия моделей взяты из наших данных о применимости. {v} моделей, {n} артикулов. Выберите модель, чтобы увидеть все совместимые детали с номерами OE.",
      all_veh_h2: "Все модели ({n})",
      veh_lead: "Детали для {v}. У каждой — номер OE, кросс-номера, применимость и фото. Пришлите номер OE в WhatsApp: цена, MOQ и упаковка.",
      veh_brands_h2: "Совместимые марки", veh_others_h2: "Другие модели",
    },
    fr: {
      nav_all: "Toutes les catégories ({n})", wa: "Devis WhatsApp", home: "Accueil", sitemap: "Plan du site",
      guides_link: "Guides d'achat", guides_h: "Guides d'achat", guides_more: "Autres guides", guides_use: "Et ensuite",
      guides_lead: "Notes pratiques de notre atelier et de notre service export : comment lire une référence, comment identifier un véhicule par son numéro de série (VIN) et comment diagnostiquer avant de commander. Les données produit restent en anglais, l'interface suit votre langue.",
      lookup: "Recherche OE / références croisées", lang_label: "Langue",
      our_sku: "Notre référence", spec_oe: "Référence OE", spec_xref: "Références croisées", spec_brand: "Marque",
      spec_fit: "Compatibilité véhicule", spec_fit_brands: "Marques compatibles", spec_notes: "Remarques", btn_wa: "WhatsApp : prix et MOQ",
      spec_years: "Années", spec_displ: "Cylindrée", spec_engine: "Code moteur",
      btn_search_all: "Chercher parmi {n} références", block_app: "Application véhicule", block_buy: "Commander cette pièce",
      buy_text: "{company} fournit ces pièces sous notre propre marque {brand}. Envoyez la référence OE sur WhatsApp : nous confirmons la disponibilité, le prix, le MOQ et l'emballage. Échantillons d'essai disponibles sur demande.",
      rel_more: "Plus de {cat}", more: "Plus", nopic: "Pas encore de photo pour cette référence", nopic_sub: "Demandez une photo réelle sur WhatsApp",
      langnote: "Les données produit sont affichées en anglais", app_fallback: "Envoyez-nous le modèle du véhicule, nous confirmerons la compatibilité.",
      cat_lead: "Chaque référence en stock est livrée avec sa référence OE et ses références croisées. Cliquez sur une référence pour voir la compatibilité, les photos et le bouton de devis.",
      models_n: "{n} références", search_oe: "rechercher par référence OE", filter_search: "filtrer sur la page de recherche",
      all_models: "Toutes les références ({n})", models_range: "Références {a}–{b} sur {n}",
      page_of: "Page {p} / {t}", all_cat_h1: "Toutes les catégories",
      all_cat_lead: "{c} catégories, {n} références. Choisissez une catégorie pour voir toutes les références avec leur référence OE, leurs références croisées et la compatibilité.",
      cat_arrow: "{n} références →", home_h1: "Recherche de références auto",
      home_sub: "Saisissez une référence OE, une référence croisée, notre référence ou un modèle de véhicule : la pièce apparaît en quelques secondes.",
      top_h2: "Catégories les plus demandées", top_sub: "Les six catégories que nos clients demandent le plus — cliquez sur une carte pour voir toutes les références.",
      home_ph: "Réf. OE / réf. croisée / notre réf. / véhicule — ex. 90919-02248, WL18-AD001, Camry",
      clear: "Effacer", chip_all: "Tout", found: "{n} références trouvées", shown: "{n} affichées",
      of_total: "sur {n}", load_more: "Charger la suite ({n})", no_match: "Aucune référence correspondante",
      empty_filters: "Filtres actifs", empty_drop: "retirer", empty_reset: "Réinitialiser tous les filtres",
      empty_wa: "Posez la question sur WhatsApp — la pièce n'est peut-être pas encore au catalogue",
      empty_note: "Le site compte {n} références et s'enrichit chaque semaine. Envoyez la référence OE ou une photo de la pièce : nous vérifions manuellement.",
      hint_relax: "Retirez un filtre ou essayez une autre forme de référence",
      scanning: "Recherche en cours…", scanning_h: "Analyse des {n} références…",
      scanning_p: "Le catalogue est découpé en petits fichiers pour que la page s'ouvre vite ; le reste se charge en arrière-plan.", scanning_n: "{n}% chargé",
      load_more_rest: "Charger la suite", loading_more: "Chargement…", chunk_fail: "certains fichiers ne se sont pas chargés",
      hint_click: "Cliquez sur une carte pour la grande photo et la compatibilité", hint_search: "Recherche : {q}",
      empty_p: "Essayez les 6 derniers chiffres, sans tirets (9091902248), ou le nom du modèle en anglais (Camry / Golf / Audi A4).",
      btn_copy: "Copier la référence", btn_copied: "Copié ✓", btn_fullsize: "Voir en grand",
      btn_inquiry: "Demander le prix sur WhatsApp", btn_page: "Page dédiée",
      modal_oe: "Référence OE", modal_xref: "Références croisées", modal_fit: "Compatibilité", modal_notes: "Remarques",
      modal_cat: "Catégorie", no_photo: "Pas encore de photo pour cette pièce", no_photo_sub: "Demandez une photo sur WhatsApp",
      cat_h2: "Toutes les références par catégorie",
      cat_home_lead: "Chaque catégorie affiche ses 100 premières références — « Tout voir » ouvre la liste complète.",
      brand_h2: "Parcourir les pièces par marque de véhicule",
      brand_home_lead: "Pièces regroupées par marque de véhicule compatible — Toyota, Hyundai, Kia, BMW, Ford, Volkswagen et bien d'autres. Chaque page de marque liste toutes ses références avec les numéros OE et les références croisées.",
      catbox_open: "Ouvrir / fermer : {c} catégories · {n} références", view_all: "Tout voir",
      updated: "Mis à jour le {d}", parts_n: "{n} références",
      herostat: "{n} références · {m} photos réelles",
      nf_h1: "Page introuvable", nf_p: "Le lien de cette pièce a peut-être changé. Recherchez la référence OE depuis l'accueil ou écrivez-nous sur WhatsApp.",
      nf_back: "Retour à la recherche",
      /* VIN 车架号查询 */
      vin_tab_auto: "Auto", vin_tab_oe: "OE", vin_tab_sku: "Réf.", vin_tab_model: "Modèle", vin_tab_vin: "VIN",
      vin_ph: "VIN de 17 caractères — ex. JTDBE46K940123456",
      vin_brand: "Marque", vin_wmi: "WMI (1-3)", vin_year: "Année-modèle (10)", vin_or: "ou",
      vin_vds: "VDS (4-8)", vin_vds_note: "défini par le constructeur : carrosserie / série / moteur",
      vin_plant: "Usine (11) / numéro de série", vin_prefix: "Préfixe", vin_prefix_note: "déduit du WMI",
      vin_check_ok: "chiffre de contrôle valide", vin_check_bad: "chiffre de contrôle erroné",
      vin_guess: "déduit", vin_none: "non identifié",
      vin_note: "Rapproché des compatibilités connues. Pour une certitude à 100 %, envoyez une photo de la pièce ou de la carte grise.",
      vin_unknown_wmi: "Ce WMI n'est pas dans notre table — la marque ne peut pas être déduite du VIN.",
      vin_nf_t: "Aucune pièce trouvée pour ce VIN",
      vin_nf_p: "Le véhicule n'a pas été identifié. Envoyez-nous une photo de la voiture, de la pièce ou de la carte grise : nous vérifions à la main.",
      vin_nf_p2: "Vous pouvez aussi chercher par modèle, référence OE ou les 6 / 8 premiers caractères du VIN.",
      vin_ask: "Envoyer ce VIN sur WhatsApp",
      f_title: "Filtrer par véhicule", f_brand_any: "Toutes les marques", f_model_any: "Tous les modèles", f_year_any: "Toutes les années", f_disp_any: "Toutes les cylindrées", f_clear: "Réinitialiser",
      vin_hist_t: "Pièces déjà recherchées avec ce VIN", vin_hist_note: "Référence historique — vérifiez sur le véhicule réel.", vin_sku_hist: "référence archivée",
      /* ---------- 官网化区块 ---------- */
      trust_warranty: "Garantie sur chaque pièce", trust_v_warranty: "12–24 mois", trust_v_moq: "Petites séries", trust_return: "Taux de retour", trust_cover: "Couverture injection", trust_moq: "Petites séries acceptées",
      why_h: "Pourquoi des acheteurs de plus de 25 pays commandent chez nous", why_lead: "Nous sommes l'usine, pas un intermédiaire : les mêmes références, contrôlées, pour une fraction du prix d'origine.",
      why_q_t: "Qualité niveau OE", why_q_v: "Nos pièces électriques et nos capteurs sont fabriqués selon les spécifications OE sous notre marque WEILI.",
      why_p_t: "Environ 1/3 du prix d'origine", why_p_v: "Prix direct usine, sans importateur ni distributeur au milieu.",
      why_r_t: "Devis en 24 heures", why_r_v: "Envoyez la référence OE ou une photo avec la quantité : devis chiffré sous un jour ouvré.",
      why_s_t: "Expédition mondiale", why_s_v: "Du port de Guangzhou jusqu'à votre porte ; l'emballage est adapté au type de pièce, rien n'arrive abîmé.",
      hot_h: "Références les plus demandées", hot_all: "Toutes les catégories", hot_sub: "Les pièces les plus vendues de la saison — chaque carte ouvre la compatibilité véhicule, les photos réelles et le bouton de devis WhatsApp.",
      faq_h: "Questions fréquentes", faq_lead: "Six questions que les acheteurs posent avant la première commande. Autre chose ? Écrivez sur WhatsApp, réponse sous un jour ouvré.",
      faq_q1: "Quel est le MOQ (quantité minimale) ?", faq_a1: "Le MOQ dépend de la pièce et de l'emballage. Envoyez vos références et vos quantités : nous confirmons ligne par ligne.",
      faq_q2: "Quels sont les délais ?", faq_a2: "Les articles en stock partent de notre entrepôt de Guangzhou en quelques jours. La production dépend des quantités — la date exacte est écrite sur le devis.",
      faq_q3: "Quelle est la durée de garantie ?", faq_a3: "De 12 à 24 mois selon le type de pièce. La durée exacte figure sur le devis et la facture : la même pour vous et pour nous.",
      faq_q4: "Peut-on retourner ou échanger une pièce ?", faq_a4: "Oui. Envoyez les photos de la pièce défectueuse : nous échangeons ou déduisons sa valeur. Notre taux de retour est de 0,03 %, c'est rare.",
      faq_q5: "Peut-on recevoir des échantillons pour test ?", faq_a5: "Oui. Des échantillons sont disponibles sur demande avant la commande en série ; les frais de transport sont à la charge de l'acheteur.",
      faq_q6: "Comment payer ?", faq_a6: "Le virement bancaire (T/T) est notre méthode standard. Les conditions de paiement sont écrites sur la facture avant votre paiement.",
      foot_addr: "{en}", foot_contact: "Contact", foot_email: "E-mail",
      foot_hours: "Horaires", foot_links: "Trouver une pièce", foot_parts: "Références · photos réelles · compatibilité",
      foot_legal: "Informations", foot_privacy: "Politique de confidentialité", foot_returns: "Retours et remboursements",
      doc_ref: "La version anglaise fait foi", foot_contact_via: "Une question sur cette page ? Écrivez sur WhatsApp ou par e-mail : réponse sous un jour ouvré.",
      block_terms: "Garantie · délais · MOQ · échantillons",
      t_warranty: "Garantie", t_warranty_v: "12 à 24 mois selon le type de pièce. La durée exacte figure sur le devis et la facture.",
      t_lead: "Délais", t_lead_v: "Les articles en stock partent de Guangzhou en quelques jours ; la production dépend des quantités et la date est confirmée par commande.",
      t_moq: "MOQ", t_moq_v: "Défini par la pièce et l'emballage. Envoyez votre liste : nous confirmons position par position ; les petites premières commandes sont possibles.",
      t_sample: "Échantillons", t_sample_v: "Disponibles sur demande pour test avant commande en série ; transport à la charge de l'acheteur.",
      rel_more_h: "Plus", rel_note: "Références proches de la même catégorie — vérifiez la référence OE avant de commander.",
      cta_h: "Besoin d'un prix pour cette pièce ?", cta_p: "Envoyez la référence et la référence OE sur WhatsApp : prix, MOQ et emballage sous un jour ouvré.",
      cta_btn: "WhatsApp : {n}",
      lk_oe_t: "Autres références avec le même OE / la même référence croisée", lk_veh_t: "Pièces courantes pour le même véhicule",
      lk_rel_t: "Autres références de la même catégorie",
      /* ---------- 品牌页 / 车型页 ---------- */
      brands_crumb: "Marques", vehicles_crumb: "Véhicules",
      brand_idx_h1: "Parcourir par marque de véhicule",
      brand_idx_lead: "Les pièces sont regroupées par marque de véhicule compatible. {b} marques, {n} références — chaque pièce donne son numéro OE, ses références croisées, ses photos et un bouton de devis WhatsApp.",
      browse_vehicle: "Parcourir par véhicule", browse_brand: "Parcourir par marque", search_oe_btn: "Rechercher par référence OE",
      brand_parts_h1: "Pièces {b}", parts_n_paren: "({n} références)",
      brand_lead: "Bobines d'allumage, capteurs, pompes à carburant et autres pièces pour {b}. Chaque pièce donne son numéro OE, ses références croisées, sa compatibilité et ses photos. Envoyez le numéro OE sur WhatsApp pour le prix, le MOQ et l'emballage.",
      brand_search_oe: "Chercher les pièces {b} par numéro OE", brand_models_h2: "Modèles {b}", brand_xfit_h2: "Compatible aussi avec ces modèles", brand_others_h2: "Autres marques",
      see_all_cat: "Voir les {n} {cat}",
      veh_idx_lead: "Noms de modèles issus de nos données de compatibilité. {v} véhicules, {n} références. Choisissez un véhicule pour voir toutes les pièces compatibles avec leur numéro OE.",
      all_veh_h2: "Tous les véhicules ({n})",
      veh_lead: "Pièces compatibles avec {v}. Chaque pièce indique son numéro OE, ses références croisées, sa compatibilité et ses photos. Envoyez le numéro OE sur WhatsApp pour le prix, le MOQ et l'emballage.",
      veh_brands_h2: "Marques compatibles", veh_others_h2: "Autres véhicules",
    }
  };

  /* 品类名：key -> [zh, ar, ru, fr]（英文名在原页面里，en 时用原文） */
  var C = {
    coil: ["点火线圈", "ملفات الإشعال", "Катушки зажигания", "Bobines d'allumage"],
    fuelpump: ["燃油泵", "مضخات الوقود", "Топливные насосы", "Pompes à carburant"],
    o2: ["氧传感器", "حساسات الأكسجين", "Датчики кислорода", "Sondes lambda"],
    plug: ["火花塞", "شمعات الإشعال", "Свечи зажигания", "Bougies d'allumage"],
    abs: ["ABS 传感器", "حساسات ABS", "Датчики ABS", "Capteurs ABS"],
    wire: ["火花塞线", "أسلاك شمعات الإشعال", "Провода свечей", "Faisceaux d'allumage"],
    thermo: ["节温器", "منظمات الحرارة", "Термостаты", "Thermostats"],
    ckp: ["曲轴位置传感器", "حساسات موضع العمود المرفقي", "Датчики положения коленвала", "Capteurs de position vilebrequin"],
    cmp: ["凸轮轴位置传感器", "حساسات موضع عمود الكامات", "Датчики положения распредвала", "Capteurs d'arbre à cames"],
    dpfe: ["压差传感器", "حساسات الضغط التفاضلي", "Датчики перепада давления", "Capteurs de pression différentielle"],
    fuelpress: ["油压调节器", "منظمات ضغط الوقود", "Регуляторы давления топлива", "Régulateurs de pression carburant"],
    injector: ["喷油嘴", "حاقنات الوقود", "Форсунки", "Injecteurs"],
    maf: ["空气流量计", "حساسات تدفق الهواء", "Датчики массового расхода воздуха", "Débitmètres d'air"],
    map: ["进气压力传感器", "حساسات ضغط المشعب", "Датчики давления во впуске", "Capteurs de pression d'admission"],
    njkspark: ["NJK 火花塞", "شمعات NJK", "Свечи NJK", "Bougies NJK"],
    ocv: ["机油控制阀", "صمامات التحكم في الزيت", "Клапаны управления маслом", "Électrovannes de commande d'huile"],
    purge: ["碳罐电磁阀", "صمامات تطهير العلبة", "Клапаны продувки адсорбера", "Électrovannes de purge canister"],
    stepper: ["怠速马达", "محركات الخطوة", "Шаговые моторы", "Moteurs pas-à-pas de ralenti"],
    temp: ["温度传感器", "حساسات الحرارة", "Датчики температуры", "Sondes de température"],
    throttle: ["节气门阀体", "جسم الخانق", "Дроссельные узлы", "Boîtiers papillon"],
    tpms: ["胎压传感器", "حساسات ضغط الإطارات", "Датчики давления в шинах", "Capteurs de pression des pneus"],
    tps: ["节气门位置传感器", "حساسات موضع الخانق", "Датчики положения дросселя", "Capteurs de position papillon"],
    vsv: ["真空电磁阀", "صمامات التفريغ", "Вакуумные клапаны", "Électrovannes de dépression"]
  };

  var lang = DEF;

  function norm(v) {
    v = String(v || "").toLowerCase();
    if (v.indexOf("zh") === 0) return "zh";
    if (v.indexOf("ar") === 0) return "ar";
    if (v.indexOf("ru") === 0) return "ru";
    if (v.indexOf("fr") === 0) return "fr";
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
    /* data-v-cat="coil" → {cat} 换成当前语种的品类名（英文页用 data-v-cat-en 里的英文名） */
    if (el.hasAttribute("data-v-cat")) {
      v.cat = catName(el.getAttribute("data-v-cat"), el.getAttribute("data-v-cat-en") || "");
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
