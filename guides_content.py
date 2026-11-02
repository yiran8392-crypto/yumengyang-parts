# -*- coding: utf-8 -*-
"""
采购指南正文（英文）· 三篇
=========================
sitegen.py 生成 guides/*.html 时读这个文件。

正文用「块」表示，别直接写一大坨 HTML：

    ("h2", "小标题")
    ("p",  "段落，可以带内链 token")
    ("ul", ["要点 1", "要点 2"])
    ("ol", ["步骤 1", "步骤 2"])
    ("table", ["表头1", "表头2"], [["行1列1", "行1列2"], ...])
    ("tip",  "浅色提示框里的文字")

内链 token（由 sitegen 解析成相对链接，找不到目标就自动降级，不会产生死链）：

    [[L:cat/coil|点火线圈目录]]              品类页（key 见 CAT_META）
    [[L:part/0221503465|Bosch 0221503465]]   型号页（按 OE 号找，找不到退回首页搜索）
    [[L:home|站内查询]]                       首页
    [[L:guides/index.html|全部指南]]          指南目录
    [[L:guides/vin-to-parts-guide.html|VIN 指南]]

正文英文；页面框架（导航、页脚、按钮）照旧走 assets/i18n.js 四语切换。
"""

GUIDES = [
    # ================================================================= 1
    {
        "slug": "how-to-find-ignition-coil-by-oe-number",
        "nav": "Find a coil by OE number",
        "title": "How to Find the Right Ignition Coil by OE Number and Cross-Reference",
        "h1": "How to find the right ignition coil by OE number",
        "desc": ("A practical guide for mechanics and parts buyers: how to read an ignition coil OE number, "
                 "how to turn it into a cross-reference list, and the five mistakes that cause wrong shipments."),
        "lead": ("Engine code, not car model, decides which coil fits. This guide shows how to start from the "
                 "number stamped on the old coil, read it correctly, and convert it into a list of numbers you "
                 "can actually order against."),
        "date": "2026-11-02",
        "minutes": 6,
        "body": [
            ("h2", "Why the OE number beats the car model"),
            ("p", ("Two cars can share a badge and take different coils. A Volkswagen Golf with a 1.6 petrol "
                   "engine and a Golf with a 1.4 TSI use different coil families, and within one engine there "
                   "are often two revisions that are not interchangeable. The workshop that orders \"a coil for "
                   "a 2012 Golf\" has maybe a 70% chance of getting the right part the first time. The workshop "
                   "that orders against the number on the old coil has close to 100%.")),
            ("p", ("The OE number is the manufacturer's own identifier for that exact assembly: housing height, "
                   "connector keyway, pin count, built-in igniter or not, and the length of the boot. Those are "
                   "the things that stop a coil from seating, not the engine size.")),
            ("h2", "How an ignition coil OE number is built"),
            ("p", ("Every major brand encodes the same information in a different shape. Learn the shape and you "
                   "can read an unfamiliar number in a few seconds.")),
            ("table", ["Number family", "Typical shape", "Example", "How to read it"], [
                ["Bosch", "10 digits, printed in groups", "0 221 504 465",
                 "Spaces are cosmetic — the number is 0221504465. The 0221 block is the ignition-coil family."],
                ["VW / Audi / Skoda / Seat", "9 characters, letter last", "06A 905 115 D",
                 "Digits are the base part, the final letter is the revision. Later letters replace earlier ones."],
                ["Denso (Toyota, Lexus)", "5 digits, dash, 5 digits", "90919-02248",
                 "90919 is Toyota's ignition group; the second block identifies the coil itself."],
                ["Delphi / Delco style", "8 digits, no letters", "19005252",
                 "Short and easy to mistype — check the last two digits twice."],
                ["Chinese OE (Chery, Geely, Great Wall)", "block-letterblock", "A11-3705110DA",
                 "3705 is the ignition-coil group in the Chinese industry numbering; the tail letter is the variant."],
            ]),
            ("p", ("Two habits save time here. First, strip the spaces and dashes before you search: "
                   "\"0 221 504 465\", \"0221504465\" and \"0221-504-465\" are one number. Second, keep the "
                   "trailing letter — 06A905115 and 06A905115D are different parts even though the first eight "
                   "characters match.")),
            ("h2", "Where to read the number on the car"),
            ("ul", [
                "Laser marking on the coil body — usually on the flat top or the side of the housing, small and "
                "often covered by dust. Wipe it and use a torch at an angle.",
                "Moulded label or sticker on the connector housing; on older coils this is the only place the "
                "revision letter appears.",
                "The rubber boot or the metal bracket, where some makers stamp a short code instead of the full "
                "number.",
                "The workshop parts catalogue (ETKA, EPC, Microcat) opened by VIN — this gives the number the "
                "factory fitted, which is what you want for a car that has never been repaired.",
                "The old invoice or the box, if the coil has already been replaced once. Beware: the box may hold "
                "a cheaper substitute, not the original.",
            ]),
            ("p", ("If the marking is unreadable, photograph the connector and the boot next to a ruler and send "
                   "the pictures with the VIN. A coil is identified visually faster than it is guessed from a "
                   "model name.")),
            ("h2", "From one number to a cross-reference list"),
            ("p", ("A single OE number usually has three or four equivalents. Suppliers renumber, and the car "
                   "maker supersedes a part without changing the casting. Work the chain in this order:")),
            ("ol", [
                "Write down the number from the old part exactly, including the revision letter.",
                "Look up the supersession: 06A905115 became 06A905115D, and later D was replaced again. Later "
                "letters are normally backward compatible; earlier letters are not always forward compatible.",
                "Collect the equivalent numbers from two or three other brands for the same engine — that is what "
                "a cross-reference list is.",
                "Confirm the physical details against the listing: pin count, connector shape, boot length, and "
                "whether the coil has an integrated igniter.",
                "Only then compare price. Price without the cross-reference check is how wrong parts get shipped.",
            ]),
            ("p", ("On our site every coil page carries an OE number and, where we have it, a cross-reference row — "
                   "for example [[L:part/0221503465|Bosch 0221503465]] lists the vehicles it fits, and the "
                   "[[L:cat/coil|full ignition coil catalogue]] can be filtered by OE number, our SKU or vehicle "
                   "name.")),
            ("h2", "Five mistakes that cause wrong shipments"),
            ("ul", [
                "<b>Cylinder-specific coils.</b> Some engines use the same electrical coil in two housing lengths. "
                "The number differs by one letter and the long one will not seat under the cover.",
                "<b>Pin count and keyway.</b> Three-pin and four-pin coils look identical in a photo. Count the "
                "pins and check the keyway before ordering.",
                "<b>Igniter inside or outside.</b> A coil with a built-in igniter cannot replace one that uses an "
                "external module, even if the connector fits.",
                "<b>Marketplace \"OE numbers\".</b> A listing ID is not an OE number. If the number does not "
                "appear on the part, treat it as a description, not an identifier.",
                "<b>Look-alike characters.</b> Zero and letter O, one and letter I, and the letters B and 8 are "
                "the usual culprits on laser marking. When a search returns nothing, re-read the number "
                "character by character.",
            ]),
            ("h2", "The 60-second check before you order"),
            ("ol", [
                "Scan or read the fault code and confirm which cylinder is misfiring — do not replace all four "
                "coils because of one code.",
                "Read the number off the failed coil and write it down with the revision letter.",
                "Search that number on our [[L:home|OE and cross-reference lookup]] and open the matching part "
                "page.",
                "Check fitment, pin count and boot length against the old part photo; compare the cross-reference "
                "row.",
                "Send the OE number and the quantity on WhatsApp for price, MOQ and packing.",
            ]),
            ("p", ("If the number you have returns nothing, send it anyway with the VIN and a photo of the "
                   "connector. Numbers that are not in a catalogue are usually superseded numbers or a "
                   "dealer-only revision, and both can be matched by hand. To place the car from its VIN first, "
                   "see [[L:guides/vin-to-parts-guide.html|VIN to parts]].")),
        ],
    },

    # ================================================================= 2
    {
        "slug": "vin-to-parts-guide",
        "nav": "VIN to parts",
        "title": "VIN to Parts: How to Read a VIN and Find the Exact Part",
        "h1": "VIN to parts: how to read a VIN and find the exact part",
        "desc": ("What the 17 characters of a VIN mean, how to read the WMI and the model-year digit, what a VIN "
                 "cannot tell you, and the five-step workflow from VIN to a confirmed part number."),
        "lead": ("A VIN identifies one vehicle, not one part. Read the four blocks correctly and the VIN removes "
                 "most of the guesswork — then confirm the last step with an OE number."),
        "date": "2026-11-02",
        "minutes": 7,
        "body": [
            ("h2", "What a VIN actually is"),
            ("p", ("Since 1981 every road vehicle sold in the United States carries a 17-character Vehicle "
                   "Identification Number, and the format is now used worldwide under ISO 3779. It is fixed "
                   "length, contains no spaces, and never uses the letters I, O or Q — they are excluded so they "
                   "cannot be confused with 1 and 0.")),
            ("p", ("That last detail matters in practice. If a customer sends a \"VIN\" containing the letter O, "
                   "it is either a typing error or not a VIN at all.")),
            ("h2", "The four blocks"),
            ("table", ["Characters", "Name", "What it gives you"], [
                ["1–3", "WMI — World Manufacturer Identifier",
                 "Who built the vehicle and in which country. This is the block that tells you the brand."],
                ["4–8", "VDS — Vehicle Descriptor Section",
                 "Maker-defined: body style, series, engine family, restraint system. Meaning changes completely "
                 "between brands."],
                ["9", "Check digit", "A calculated character. Used to catch typos before anyone orders a part."],
                ["10", "Model year", "One letter or digit for the model year — not the registration year."],
                ["11", "Plant code", "Which factory assembled the vehicle. Useful when the same model was built in "
                                     "two countries with different suppliers."],
                ["12–17", "Serial number", "The sequence number. Unique within the plant and year."],
            ]),
            ("h2", "The first three characters: who built it"),
            ("p", ("The WMI is the fastest way to stop a mis-identified inquiry. Ten that come up constantly in "
                   "aftermarket work:")),
            ("table", ["WMI", "Manufacturer", "Country"], [
                ["WBA", "BMW", "Germany"],
                ["WDD / WDB", "Mercedes-Benz", "Germany"],
                ["WVW", "Volkswagen", "Germany"],
                ["WAU", "Audi", "Germany"],
                ["1HG", "Honda", "United States"],
                ["JTD", "Toyota", "Japan"],
                ["KMH", "Hyundai", "Korea"],
                ["LSV", "SAIC Volkswagen", "China"],
                ["LVS", "Changan Ford", "China"],
                ["9BW", "Volkswagen do Brasil", "Brazil"],
            ]),
            ("p", ("Note the Chinese and Brazilian WMIs. A \"German\" model assembled in China or Brazil often "
                   "uses locally sourced sensors and ignition parts, so the WMI is not trivia — it decides which "
                   "parts list applies. Used imports from the Gulf, Africa and Latin America frequently fall into "
                   "this group.")),
            ("h2", "Character 10: the model year code"),
            ("p", ("Position 10 is a single letter or digit. The letters I, O, Q, U and Z are skipped, and the "
                   "cycle repeats every 30 years — which is why a 1990 car and a 2020 car can both read \"L\".")),
            ("table", ["Code", "Model year", "Code", "Model year", "Code", "Model year"], [
                ["A", "2010", "F", "2015", "L", "2020"],
                ["B", "2011", "G", "2016", "M", "2021"],
                ["C", "2012", "H", "2017", "N", "2022"],
                ["D", "2013", "J", "2018", "P", "2023"],
                ["E", "2014", "K", "2019", "R", "2024"],
                ["—", "—", "—", "—", "S", "2025"],
            ]),
            ("p", ("The model year is not the registration year. A car first registered in March 2011 is very "
                   "often a 2010 model year, and facelift parts change on the model-year boundary, not on the "
                   "calendar.")),
            ("h2", "What a VIN does not tell you"),
            ("ul", [
                "The engine code. Two cars with the same VIN prefix can carry different engines, and the coil, "
                "sensor or pump changes with the engine.",
                "Brake and suspension package. Bigger brakes mean a different ABS sensor bracket and cable length.",
                "Whether the car has been re-engined, converted or rebuilt after an accident — common on used "
                "imports.",
                "Left- or right-hand drive on models built in both configurations; the ABS sensor position is "
                "mirrored and the part numbers differ.",
            ]),
            ("p", ("So the VIN narrows the search; the OE number closes it. Treat the VIN as the first filter and "
                   "the part number as the confirmation.")),
            ("h2", "The workflow we use"),
            ("ol", [
                "Paste the 17 characters into the VIN box on our [[L:home|lookup home page]]. It reports the "
                "brand from the WMI, the model year from position 10, and whether the check digit is valid.",
                "Match the vehicle to the engine: ask for the engine code, or the displacement and fuel type from "
                "the registration document.",
                "Open the category page — for example [[L:cat/abs|ABS sensors]] or [[L:cat/coil|ignition coils]] — "
                "and filter by vehicle name.",
                "Confirm the OE number against the old part, then use the cross-reference row on the part page to "
                "see equivalent numbers.",
                "Send the OE number, quantity and destination port on WhatsApp for the quotation.",
            ]),
            ("h2", "A worked example"),
            ("p", ("VIN <code>WVWZZZ1K9AW123456</code> reads as: WVW = Volkswagen Germany, ZZZ = filler used when "
                   "the VDS is not needed, 1K = the Golf Mk6 platform, check digit 9 valid, A = model year 2010. "
                   "The car is a 2010 Golf, but the engine is still unknown — and that is the point.")),
            ("p", ("If the job is a front-left ABS sensor on that car, the OE number is WHT003857 (cross-referenced "
                   "to 7H0927803 on many listings). Our catalogue carries it as "
                   "[[L:part/wht003857-7h0927803|WHT003857 / 7H0927803]], with the front-right counterpart listed "
                   "separately. Same VIN, same axle, different side, different number — that is the whole lesson "
                   "of this guide.")),
            ("p", ("For a full walkthrough of reading the number off the old coil, see "
                   "[[L:guides/how-to-find-ignition-coil-by-oe-number.html|how to find an ignition coil by OE "
                   "number]]. More guides are listed on the [[L:guides/index.html|guides index]].")),
        ],
    },

    # ================================================================= 3
    {
        "slug": "abs-sensor-symptoms-and-replacement",
        "nav": "ABS sensor symptoms",
        "title": "ABS Sensor Symptoms, Fault Codes and How to Match the Right Part Number",
        "h1": "ABS sensor symptoms, fault codes and part matching",
        "desc": ("How to recognise a failing ABS wheel-speed sensor, what the common fault codes mean, how to "
                 "test before replacing, and how to match front/rear and left/right part numbers."),
        "lead": ("Most \"ABS sensor\" jobs start with a warning light and end with a wrong-side part. This guide "
                 "covers the symptoms, the scan data, and the four details that decide the part number."),
        "date": "2026-11-02",
        "minutes": 7,
        "body": [
            ("h2", "What the sensor does, and the two types"),
            ("p", ("An ABS wheel-speed sensor reports how fast each wheel is turning. The control unit compares the "
                   "four signals and releases brake pressure on a wheel that is locking. When one signal drops out, "
                   "ABS switches off and the light stays on — the brakes still work, but without anti-lock "
                   "assistance and usually without traction control or stability control.")),
            ("table", ["", "Passive (inductive)", "Active (Hall / magneto-resistive)"], [
                ["Wires", "2", "2 or 3"],
                ["Signal", "AC voltage generated by the spinning tone ring", "Square wave, needs a supply voltage"],
                ["Reads down to", "About 5–10 km/h, then the signal fades", "Close to zero — used for hill-hold and "
                                                                              "low-speed functions"],
                ["Test with a multimeter", "Resistance and AC output while spinning the wheel",
                 "Supply voltage and signal switching; a resistance reading means nothing"],
                ["Typical failure", "Cracked cable at the hub, chafed harness, corroded tone ring",
                 "Water ingress at the connector, failed Hall element"],
            ]),
            ("h2", "Symptoms you will actually notice"),
            ("ul", [
                "ABS warning lamp on after start-up, sometimes only after the first few metres of driving.",
                "Traction control or ESP lamp on at the same time — one dead sensor usually disables both.",
                "ABS pulsing or a grinding pedal at low speed when no wheel is slipping, caused by a false "
                "signal.",
                "Speedometer needle dropping to zero or jumping, on cars that take the speed signal from a wheel "
                "sensor.",
                "Cruise control refusing to engage, and on some models a gearbox that holds gears longer.",
                "Intermittent faults that appear in rain, after a bump, or when the steering is on full lock — "
                "classic chafed-cable behaviour.",
            ]),
            ("h2", "What the scan tool usually shows"),
            ("p", ("Read the codes from the ABS module, not from the engine module. The table below shows the "
                   "families you will meet most often — always confirm the exact meaning in the manufacturer's "
                   "code list, because the same number means different things on different platforms.")),
            ("table", ["Platform family", "Typical codes", "What it points at"], [
                ["VW / Audi / Skoda / Seat", "00283, 00285, 00287, 00290",
                 "Wheel-speed sensor, front left / front right / rear right / rear left — the order is fixed and "
                 "worth memorising."],
                ["GM / Opel / Chevrolet", "C0035 – C0050",
                 "The four wheel-speed sensor circuits and their performance tests."],
                ["Toyota / Lexus", "C0200 – C0215",
                 "Wheel-speed sensor circuits by corner, plus signal-erratics codes."],
                ["Generic OBD-II", "P0500 and relatives",
                 "Vehicle speed signal. On many cars this is the gearbox output sensor, not an ABS sensor — check "
                 "before ordering."],
            ]),
            ("p", ("Live data is more useful than the code. Drive slowly and watch the four wheel-speed values: a "
                   "sensor that reads 0 km/h while the others read 12 km/h has told you everything.")),
            ("h2", "Test before you replace"),
            ("ol", [
                "Read and record the codes, then clear them and reproduce the fault — a code that returns "
                "immediately is a hard fault.",
                "Inspect the harness at the hub: look for cracks where the cable flexes on steering movement, and "
                "for corrosion inside the connector.",
                "On a passive sensor, measure resistance across the two pins and compare with the workshop "
                "figure; then spin the wheel by hand and watch for AC voltage.",
                "On an active sensor, check the supply with the ignition on, then watch the signal on a scope or "
                "in live data while turning the wheel.",
                "Inspect the tone ring or magnetic encoder on the hub — a cracked or rusty ring produces the same "
                "symptoms as a dead sensor and costs less to fix.",
            ]),
            ("h2", "The four details that decide the part number"),
            ("ul", [
                "<b>Corner.</b> Front left, front right, rear left, rear right are four different numbers on most "
                "platforms, even when the sensors look identical. Right-hand-drive cars mirror them.",
                "<b>Cable length and grommet.</b> The same sensor with a longer cable is a different OE number, and "
                "the short one will not reach the body clip.",
                "<b>Connector keyway and pin count.</b> Two-pin and three-pin housings are not interchangeable, and "
                "some families use the same shell with a different key.",
                "<b>Driven axle.</b> An AWD version may use a different rear sensor or a different mounting "
                "bracket from the FWD version of the same model.",
            ]),
            ("h2", "Why \"same model, same year\" still fails"),
            ("p", ("Facelifts, brake packages and market-specific assembly plants change sensors on cars that look "
                   "identical. A 2010 Golf built in Wolfsburg and one built in China can carry different front "
                   "sensor numbers. The VIN helps you place the car; only the OE number confirms the part — see "
                   "[[L:guides/vin-to-parts-guide.html|the VIN guide]] for how to read the first eleven "
                   "characters.")),
            ("p", ("Our [[L:cat/abs|ABS sensor catalogue]] lists every model by OE number and cross-reference. "
                   "Typical entries: [[L:part/4e0927804|4E0927804]] for the front-right position on Audi A4 to A8, "
                   "and [[L:part/wht003857-7h0927803|WHT003857 / 7H0927803]] for the front-left position on Golf "
                   "Mk6, A3 and TT.")),
            ("h2", "Before you order"),
            ("ul", [
                "Photograph the old sensor, the connector and the mounting point — one picture answers three "
                "questions.",
                "Note the corner and the cable length, not just the model name.",
                "Check whether the fault is the sensor, the harness or the tone ring; two out of three do not need "
                "a new sensor.",
                "Send the OE number and quantity on WhatsApp for price, MOQ and packing.",
            ]),
        ],
    },
]
