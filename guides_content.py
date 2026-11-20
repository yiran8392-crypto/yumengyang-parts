# -*- coding: utf-8 -*-
"""
采购指南正文（英文）· 八篇
=========================
sitegen.py 生成 guides/*.html 时读这个文件。

2026-11-20 从三篇扩到八篇：新增燃油泵、氧传感器、节气门、曲轴/凸轮轴传感器、火花塞五篇
（GEO 那版说明里排的内容层第一步；AI 搜索引用最多的是「讲清楚一件事」的长文，不是型号页）。

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

    # ================================================================= 4
    {
        "slug": "fuel-pump-symptoms-and-part-matching",
        "nav": "Fuel pump symptoms",
        "title": "Fuel Pump Symptoms, P0230 and How to Match a Pump, Hanger or Assembly",
        "h1": "Fuel pump symptoms and how to match a pump, hanger or assembly",
        "desc": ("How a tired in-tank fuel pump behaves, what P0087 and P0230 really mean, when an assembly beats a "
                 "bare pump, and the details that decide the part number."),
        "lead": ("Roughly half of the jobs quoted as \"fuel pump\" turn out to be a relay, a clogged filter or a "
                 "pressure sensor. This guide separates the diagnosis from the purchase, then covers what actually "
                 "decides the part number: pump only, hanger only, or the complete module."),
        "date": "2026-11-20",
        "minutes": 7,
        "body": [
            ("h2", "What the pump actually does"),
            ("p", ("Almost every petrol car built since the 1990s uses an electric pump inside the tank. It pushes "
                   "fuel forward at low pressure — typically 3 to 4 bar on port injection — and the pressure "
                   "regulator or the returnless system keeps it there. On a direct-injection engine the in-tank "
                   "pump only feeds a mechanical high-pressure pump on the engine, so a weak low-pressure pump "
                   "shows up as a high-pressure fault code, not as a missing one.")),
            ("p", ("Because the pump is cooled and lubricated by the fuel around it, the two things that kill it "
                   "are running the tank near empty and a blocked filter. Both are cheaper to prevent than the "
                   "pump is to replace.")),
            ("h2", "Symptoms, from early to terminal"),
            ("ul", [
                "Longer cranking before the engine fires, worst after the car has stood overnight.",
                "Loss of power under load — a hill or a full-throttle overtake — that disappears when you lift off.",
                "Hesitation or a single lean misfire at high rpm, often with no fault code at all.",
                "Whining or buzzing from under the rear seat that changes pitch with load; a healthy pump is "
                "audible at key-on but quiet once running.",
                "Sudden no-start with the engine cranking normally, sometimes restored by a sharp knock on the "
                "tank — the classic worn-brush symptom.",
                "Intermittent stall in hot weather or after a long drive, then a normal restart after twenty "
                "minutes: a pump that is failing hot.",
            ]),
            ("h2", "What the codes tell you — and what they do not"),
            ("table", ["Code", "Reads as", "What it usually means"], [
                ["P0230", "Fuel pump primary circuit malfunction",
                 "The control side: relay, fuse, wiring or the pump driver in the control unit. Rarely the pump "
                 "itself."],
                ["P0231 / P0232", "Fuel pump secondary circuit low / high",
                 "The monitored feed or ground side. Check voltage at the pump connector under load."],
                ["P0087", "Fuel rail / system pressure too low",
                 "A real pressure shortfall: pump, filter, regulator or a leaking injector. Also the code you get "
                 "from a GDI high-pressure pump."],
                ["P0089", "Fuel pressure regulator performance",
                 "The regulator or its control, not necessarily the pump."],
                ["P0627", "Fuel pump A control circuit open",
                 "The module is not seeing the pump circuit at all — check the connector before ordering."],
            ]),
            ("p", ("No code is common. A pump that is merely tired stays inside the monitoring window and simply "
                   "under-delivers. Pressure and volume testing finds it; a code reader does not.")),
            ("h2", "Test before you buy"),
            ("ol", [
                "Measure rail pressure at key-on and again with the engine running under load; compare with the "
                "workshop figure for that engine.",
                "Check the pump's current draw with a clamp meter. A pump pulling well above spec is worn; one "
                "pulling almost nothing is dead or unpowered.",
                "Listen and feel the relay, then swap it with an identical one from the fuse box — a two-minute "
                "test that saves a tank removal.",
                "Measure voltage at the pump connector while cranking. Anything below battery voltage minus a volt "
                "points at wiring or the module, not the pump.",
                "Replace the fuel filter before condemning the pump if the car has covered high mileage on the "
                "original filter.",
            ]),
            ("tip", "A pump that runs but delivers nothing is usually a split hose inside the tank or a failed "
                    "in-tank regulator — the pump itself is fine. Look inside the module before ordering."),
            ("h2", "Pump, hanger or complete assembly?"),
            ("p", ("The same car can be sold three ways, and the price difference is large. Knowing which one you "
                   "are quoting stops the classic argument at the counter.")),
            ("table", ["What you buy", "When it makes sense", "Watch out for"], [
                ["Bare pump (motor only)", "The hanger, sender and regulator are healthy and only the motor is "
                                           "tired.", "You must transfer the strainer, the hose and often the "
                                                     "connector — and match the flow rating exactly."],
                ["Pump + hanger", "The plastic housing or the sender is cracked, or the original is not serviceable.",
                 "Sender resistance and tank depth must match, or the gauge will read wrong."],
                ["Complete module", "Fastest and safest for a workshop: everything new, nothing to transfer.",
                 "Higher price and more variants — the same model may use two different modules by market."],
            ]),
            ("h2", "The details that decide the part number"),
            ("ul", [
                "<b>Flow and pressure.</b> Two pumps with the same body can be rated differently; fitting the "
                "smaller one leans the engine out at high load.",
                "<b>Return or returnless.</b> A returnless system has the regulator in the module. Mixing the two "
                "gives a permanent pressure fault.",
                "<b>Sender resistance.</b> Empty and full values differ between markets; the wrong sender means a "
                "gauge that reads backwards.",
                "<b>Tank depth and module height.</b> A module that is too short leaves fuel behind, one that is "
                "too long fouls the tank floor.",
                "<b>Connector and locking ring.</b> Pin count and keyway vary even within one model year.",
                "<b>Pump petrol or flex-fuel.</b> Ethanol-resistant seals are a different part number.",
            ]),
            ("h2", "Finding it in our catalogue"),
            ("p", ("Our [[L:cat/fuelpump|fuel pump catalogue]] lists every pump by OE number with cross-references "
                   "and fitment. Typical entries: [[L:part/1GD919051E|1GD919051E]] for the Jetta and Bora family, "
                   "and [[L:part/180919051B|180919051B]] for Bora, Jetta and the new Santana / Lavida range.")),
            ("ul", [
                "Send the OE number from the old pump, plus a photo of the module top — the connector and the "
                "locking ring identify it faster than the model name.",
                "If the number is unreadable, send the VIN and a photo of the tank opening.",
                "State whether you need the bare pump or the complete module; the price is not comparable.",
                "Ask for the packing quantity per carton — pumps ship in foam trays, and that affects the freight "
                "calculation.",
            ]),
        ],
    },

    # ================================================================= 5
    {
        "slug": "oxygen-sensor-codes-and-part-matching",
        "nav": "O2 sensor codes",
        "title": "Oxygen Sensor Codes P0130 to P0135 and How to Match a Sensor",
        "h1": "Oxygen sensor codes P0130 to P0135 and how to match a sensor",
        "desc": ("What P0130 to P0135 really mean, how to tell a dead sensor from a vacuum leak or a wiring fault, "
                 "and the details — wire count, heater, thread and cable length — that decide the part number."),
        "lead": ("An oxygen sensor is the most frequently replaced part that did not need replacing. This guide "
                 "shows what the code is actually accusing, how to prove it in ten minutes, and which four details "
                 "lock down the part number once you do."),
        "date": "2026-11-20",
        "minutes": 7,
        "body": [
            ("h2", "Upstream and downstream do different jobs"),
            ("p", ("The upstream sensor, before the catalyst, is what the engine management uses to trim fuel. The "
                   "downstream sensor, after the catalyst, only watches whether the catalyst is still working. "
                   "Confusing the two is the most common ordering mistake: they often have the same thread and a "
                   "different cable length, connector or heater rating, and they are not interchangeable.")),
            ("table", ["", "Narrowband (zirconia)", "Wideband (planar / AFR)"], [
                ["Wires", "1, 2, 3 or 4 — 4 is the common heated type", "5 or 6"],
                ["Output", "Switches between roughly 0.1 V and 0.9 V", "A current signal that reports a ratio, "
                                                                         "read as lambda"],
                ["Used on", "Most port-injection cars up to the mid 2000s", "Direct injection, and almost everything "
                                                                              "since about 2010"],
                ["Heater check", "Resistance across the two heater pins, typically a few ohms",
                 "Same idea, but the heater is controlled by the ECU — check it in live data, not only with a "
                 "meter"],
            ]),
            ("h2", "What the codes are pointing at"),
            ("table", ["Code", "Reads as", "First thing to check"], [
                ["P0130", "O2 sensor circuit malfunction (bank 1, sensor 1)", "The circuit as a whole — connector "
                                                                              "and harness before the sensor"],
                ["P0131 / P0132", "Circuit low voltage / high voltage", "A lean or rich condition can set both; "
                                                                       "check for a vacuum leak and fuel pressure "
                                                                       "before the sensor"],
                ["P0133", "Circuit slow response", "A genuinely aged sensor — this one usually does need the part"],
                ["P0134", "Circuit no activity", "Open circuit, dead heater or a sensor that never warms up"],
                ["P0135", "Heater circuit malfunction (bank 1, sensor 1)", "Heater resistance and its fuse; the "
                                                                          "sensor may still read fine"],
                ["P0136 – P0141", "The same family for bank 1 sensor 2", "Downstream sensor and its heater"],
            ]),
            ("p", ("Two rules save money here. First, a code that names a sensor does not prove the sensor is "
                   "faulty — a leaking inlet gasket produces a lean mixture and a P0131 within a few miles. Second, "
                   "swap the sensors side to side on a V engine and see whether the fault follows the part or the "
                   "bank. Ten minutes, and it settles the question.")),
            ("h2", "Test before you replace"),
            ("ol", [
                "Look at live data: does the upstream signal switch at all? A signal frozen near 0.45 V is a dead "
                "sensor or an open circuit.",
                "Check the heater circuit: resistance between the two heater wires, then voltage at the connector "
                "with the key on. A blown heater fuse takes out both sensors on some platforms.",
                "Spray brake cleaner around the inlet and vacuum hoses while watching the fuel trims — a jump means "
                "an air leak, not a sensor.",
                "Inspect the cable where it passes the heat shield; chafing there is a classic intermittent.",
                "Check that the sensor is the right one for the position — an upstream fitted downstream reads "
                "plausibly for a while, then sets a catalyst code.",
            ]),
            ("h2", "The four details that lock the part number"),
            ("ul", [
                "<b>Position.</b> Bank 1 or bank 2, upstream or downstream — four different numbers on a V6.",
                "<b>Wire count and connector.</b> A 4-wire and a 6-wire sensor are different generations; the "
                "connector keyway differs too.",
                "<b>Cable length.</b> The same sensor with 150 mm more cable is a different OE number, and the "
                "short one will not reach the clip.",
                "<b>Thread and reach.</b> M18 × 1.5 is the norm, but a long-reach body will bottom out before it "
                "seals on some manifolds.",
            ]),
            ("p", ("Universal \"splice-in\" sensors are cheaper, and for a workshop with the right crimping tool "
                   "they are fine. For export orders they are usually the wrong answer: the customer wants the "
                   "connector, the length and the bracket to be identical to what came off the car, because a "
                   "returned part costs more than the saving.")),
            ("h2", "Finding it in our catalogue"),
            ("p", ("Our [[L:cat/o2|oxygen sensor catalogue]] lists more than 1,300 references with OE numbers, "
                   "cross-references and fitment. A typical entry: "
                   "[[L:part/A0095425618|A0095425618]] for the Mercedes-Benz A260 and B260 range.")),
            ("ul", [
                "Send the number stamped on the old sensor plus a photo of the connector.",
                "Say which position you need — bank and upstream/downstream.",
                "If you only have the VIN, send that with the engine code; we match by the OE list.",
            ]),
        ],
    },

    # ================================================================= 6
    {
        "slug": "throttle-body-cleaning-and-relearn",
        "nav": "Throttle body relearn",
        "title": "Throttle Body Cleaning, P0507 and Electronic Throttle Relearn",
        "h1": "Throttle body cleaning, P0507 and the electronic throttle relearn",
        "desc": ("Why cleaning an electronic throttle body can put the car in limp mode, what P0120, P0122 and "
                 "P0507 mean, the safe cleaning sequence, and what decides the part number."),
        "lead": ("On a cable-operated throttle a dirty body causes a sticky pedal. On a drive-by-wire body it "
                 "causes a fault code, a 1,500 rpm idle and sometimes a limp home — because the control unit has "
                 "learned the carbon as part of the closed position. This guide covers the codes, the safe "
                 "cleaning sequence and the relearn."),
        "date": "2026-11-20",
        "minutes": 6,
        "body": [
            ("h2", "Cable or drive-by-wire"),
            ("p", ("Cable bodies are mechanical: a cable pulls the plate, an idle screw sets the base opening, and "
                   "there is usually a separate idle control valve. Drive-by-wire bodies have a motor, two "
                   "redundant position sensors and no cable. The control unit continuously learns where \"closed\" "
                   "is; carbon on the bore moves that learned position, which is why a freshly cleaned body idles "
                   "high until it relearns.")),
            ("h2", "What the codes say"),
            ("table", ["Code", "Reads as", "Usual cause"], [
                ["P0120", "Throttle position sensor A circuit malfunction", "Sensor track or its wiring inside the "
                                                                           "body"],
                ["P0121", "Throttle position sensor range / performance", "The two tracks disagree — often a worn "
                                                                         "track"],
                ["P0122 / P0123", "Circuit low / high input", "Connector, harness or the sensor itself"],
                ["P0507", "Idle speed higher than expected", "The classic post-cleaning code; also a vacuum leak"],
                ["P2101", "Throttle actuator motor circuit range/performance", "Motor or gearbox inside the body, "
                                                                              "or the plate is sticking"],
                ["P2119", "Throttle actuator control throttle body range/performance", "The plate cannot reach the "
                                                                                      "commanded position"],
                ["P2135", "Throttle position sensor 1 / 2 correlation", "One track has failed; the body is "
                                                                        "usually finished"],
            ]),
            ("h2", "Cleaning an electronic body without creating a fault"),
            ("ol", [
                "Key off, battery negative disconnected, then wait a minute — some bodies are driven to a park "
                "position at shutdown.",
                "Remove the body from the manifold rather than spraying into it on the car, so the solvent and the "
                "carbon do not go into the engine.",
                "Use throttle-body cleaner and a soft cloth. Never push the plate open by hand against the motor, "
                "and never scrape the bore.",
                "Do not soak the motor or the electronics side; keep the solvent on the bore and the plate.",
                "Refit with a new gasket, reconnect the battery, then perform the relearn.",
            ]),
            ("h2", "The relearn"),
            ("p", ("Three routes, depending on the platform: a scan-tool basic setting (VAG calls it throttle "
                   "adaptation, channel 060 on older cars), a key-on / key-off cycle repeated a few times, or a "
                   "drive cycle that lets the control unit re-learn the closed position at idle. If the idle stays "
                   "high after the relearn, look for a vacuum leak — a split intake boot produces exactly the same "
                   "P0507.")),
            ("tip", "If the body will not complete a relearn, stop. Forcing adaptation on a worn body writes bad "
                    "values and the car comes back. Replace it."),
            ("h2", "What decides the part number"),
            ("ul", [
                "<b>Bore size.</b> The same engine family uses different bodies by market and by gearbox.",
                "<b>Motor and sensor integration.</b> Some bodies carry the TPS, some do not.",
                "<b>Coolant or heater pipes.</b> Cold-climate bodies have coolant passages; the bare version does "
                "not.",
                "<b>Connector and pin count.</b> Six-pin and eight-pin housings look alike from outside.",
                "<b>Programming.</b> A few platforms need the body coded to the car; mention it in the quote so the "
                "workshop plans for it.",
            ]),
            ("p", ("Our [[L:cat/throttle|throttle body catalogue]] lists each body by OE number with the "
                   "cross-reference list. Typical entry: [[L:part/06A133062AT|06A133062AT]] for the Polo, Bora and "
                   "Golf 1.6 automatic.")),
        ],
    },

    # ================================================================= 7
    {
        "slug": "crank-cam-sensor-no-start-diagnosis",
        "nav": "Crank / cam sensor",
        "title": "No-Start Diagnosis: Crankshaft and Camshaft Position Sensors",
        "h1": "No-start diagnosis for crankshaft and camshaft position sensors",
        "desc": ("A crank sensor that fails hot leaves no code and no start. How to prove it in ten minutes, what "
                 "P0335 and P0340 mean, and how type, length and connector decide the part number."),
        "lead": ("Two sensors decide whether the engine runs at all: the crankshaft sensor tells the control unit "
                 "where the crank is, the camshaft sensor where the cam is. When the crank signal disappears there "
                 "is no spark and no injection — often with no fault code stored, because the control unit never "
                 "sees a signal to complain about."),
        "date": "2026-11-20",
        "minutes": 6,
        "body": [
            ("h2", "What each one does"),
            ("ul", [
                "Crankshaft sensor: engine speed and crank position. Lose it and the engine stops or never "
                "starts — this is the sensor behind most \"cranks but will not fire\" cases.",
                "Camshaft sensor: which stroke each cylinder is on. Lose it and many engines still run, in batch "
                "or limp mode, with a long crank and a P0340.",
            ]),
            ("table", ["Type", "Wires", "How it works", "How to check it"], [
                ["Inductive (VR)", "2", "A coil generates an AC voltage as the teeth pass",
                 "Resistance and AC volts while cranking — a scope shows the pattern best"],
                ["Hall effect", "3", "Supply, ground, square-wave signal",
                 "Supply voltage with key on, then signal switching while cranking"],
                ["Magneto-resistive", "3", "Supply, ground, and a current-modulated signal",
                 "Live data or a scope; a resistance reading means nothing"],
            ]),
            ("h2", "The codes"),
            ("table", ["Code", "Reads as", "What to do first"], [
                ["P0335", "Crankshaft position sensor A circuit malfunction", "Check the connector and the reluctor "
                                                                             "wheel before the sensor"],
                ["P0336", "Crankshaft position sensor A range / performance", "Air gap, damaged teeth, metal "
                                                                              "debris on the tip"],
                ["P0340", "Camshaft position sensor A circuit malfunction", "Timing first if the engine has had "
                                                                           "belt work"],
                ["P0341", "Camshaft position sensor A range / performance", "Sensor or the target wheel on the "
                                                                            "cam"],
            ]),
            ("h2", "Prove it in ten minutes"),
            ("ol", [
                "Watch engine speed in live data while cranking. A steady 0 rpm with the starter turning means the "
                "control unit is not seeing the crank signal at all.",
                "Check the supply and ground at the connector with the key on — most Hall sensors need a solid "
                "5 V or 12 V feed.",
                "For an inductive sensor, measure resistance and compare with the workshop figure, then crank and "
                "look for AC volts on a meter or a scope.",
                "Inspect the sensor tip for metal debris and the reluctor wheel for a chipped tooth — a chipped "
                "tooth gives a signal that is present but wrong.",
                "If the fault only appears hot, test again with the engine at temperature. Heat-fail sensors are "
                "the reason a car restarts fine twenty minutes later.",
            ]),
            ("h2", "What decides the part number"),
            ("ul", [
                "<b>Sensor type.</b> An inductive and a Hall sensor for the same engine are not interchangeable, "
                "and the connectors differ.",
                "<b>Cable length and bracket.</b> The same sensor is sold with different lengths and mounting "
                "clips.",
                "<b>Target wheel spacing.</b> Air gap is usually under 1.5 mm; a thicker shim or a wrong body "
                "produces a P0336 on a brand-new part.",
                "<b>Position.</b> Crank, cam inlet, cam exhaust — three different numbers on one engine.",
            ]),
            ("p", ("Our catalogues list both families by OE number: "
                   "[[L:cat/ckp|crankshaft position sensors]] and "
                   "[[L:cat/cmp|camshaft position sensors]]. Typical entries: "
                   "[[L:part/39180-22600|39180-22600]] for Hyundai and Kia 1.4 VVT, and "
                   "[[L:part/A11-3611011|A11-3611011]] for the Chery and Geely camshaft range.")),
        ],
    },

    # ================================================================= 8
    {
        "slug": "spark-plug-heat-range-and-cross-reference",
        "nav": "Spark plug heat range",
        "title": "Spark Plug Heat Range, Reach and Cross-Reference Explained",
        "h1": "Spark plug heat range, reach and cross-reference explained",
        "desc": ("Why two plugs with the same thread are not interchangeable: heat range, reach, seat type, "
                 "resistor and electrode material. Plus how to cross-reference NGK, Denso, Bosch and Champion."),
        "lead": ("A spark plug is the cheapest part on the invoice and the easiest to get wrong. Same thread, same "
                 "hex, different heat range — and the engine either fouls plugs or knocks itself apart. This guide "
                 "covers the four dimensions that decide the part number, and how to cross-reference between "
                 "brands without guessing."),
        "date": "2026-11-20",
        "minutes": 6,
        "body": [
            ("h2", "The four dimensions that must all match"),
            ("table", ["Dimension", "Common values", "What happens if it is wrong"], [
                ["Thread", "M14 × 1.25, M12 × 1.25, M10 × 1.0", "Will not screw in at all, or strips the head"],
                ["Reach", "12.7 mm, 19 mm, 26.5 mm", "Too short fouls and loses power; too long hits the piston"],
                ["Seat", "Gasket (crush washer) or taper (no washer)",
                 "The plug sits at the wrong depth or leaks compression"],
                ["Heat range", "Numbered differently by each brand",
                 "Too hot pre-ignites and can hole a piston; too cold fouls and misfires"],
            ]),
            ("h2", "Reading a heat-range number"),
            ("p", ("Every brand numbers heat range in its own direction. Learning the direction prevents the most "
                   "expensive mistake in this list.")),
            ("table", ["Brand", "Numbering", "Example"], [
                ["NGK", "Higher number = colder", "BKR6E is medium; BKR7E is one step colder; BKR5E one step "
                                                  "hotter"],
                ["Denso", "Higher number = colder (same direction as NGK)", "K20R-U11 is medium"],
                ["Bosch", "Higher number = hotter", "FR7DC+ is hotter than FR6DC+ — the opposite of NGK"],
                ["Champion", "Higher number = hotter", "RC9YC is hotter than RC7YC"],
            ]),
            ("p", ("A plug one step colder is the normal fix for a turbocharged or LPG-converted engine that is "
                   "otherwise standard. Two steps and the plug starts fouling in town driving.")),
            ("h2", "Electrode material and gap"),
            ("ul", [
                "Nickel plugs are the baseline and need gapping and frequent replacement.",
                "Platinum and iridium last longer and are pre-gapped; never re-gap an iridium plug by levering the "
                "centre electrode.",
                "Turbo and direct-injection engines are sensitive to gap: an eroded gap of 1.3 mm where 0.7 mm is "
                "specified produces a high-load misfire with no fault code.",
                "Resistor type matters on modern cars — a non-resistor plug can upset the ignition module and the "
                "radio.",
                "LPG and CNG want a colder, harder plug than petrol; the same car on gas will foul the standard "
                "plug.",
            ]),
            ("h2", "How to cross-reference without guessing"),
            ("ol", [
                "Start from the OE number in the parts catalogue, not from the plug that came out — the old plug "
                "may already be wrong.",
                "Decode the plug you have: thread, reach, seat and heat range, in that order.",
                "Compare heat-range directions between brands before swapping numbers; a \"7\" in Bosch is not the "
                "same position as a \"7\" in NGK.",
                "Check the seat type last — a taper-seat plug in a gasket-seat head will not seal.",
                "Verify against the vehicle's OE list on our part page before shipping a bulk order.",
            ]),
            ("tip", "Cross-reference tables are a starting point, not a warranty. The OE number of the car is the "
                    "only thing that settles a claim."),
            ("p", ("Our spark plug ranges are listed by OE number with the cross-reference list: "
                   "[[L:cat/plug|spark plugs]] and [[L:cat/njkspark|NJK spark plugs]]. A typical entry: "
                   "[[L:part/18846-11070|18846-11070]] for the Hyundai Elantra, i30 and Tucson family.")),
        ],
    },
]
