# -*- coding: utf-8 -*-
"""
故障码诊断页正文（英文）
========================
sitegen.py 生成 codes/*.html 时读这个文件。

定位：**不做故障码字典站**，只做「客户手上的码 → 我们真正在库的件」这条链。
  - 码的定义用 SAE J2012 / ISO 15031-6 的标准措辞（公共知识，不编）
  - 原因排序按「我们出口出去的车上实际坏什么」来写，不写百科式罗列
  - 每页都有「先换哪个、别急着换哪个」，这是纯字典站不会写的部分
  - 品类 / 型号内链由 sitegen 渲染成相对链接，找不到就降级，绝不产生死链

正文块格式和 guides_content.py 完全一致（同一套渲染器）：

    ("h2", "小标题")  ("p", "段落")  ("ul", [...])  ("ol", [...])
    ("table", [表头...], [[行...], ...])  ("tip", "提示框")

内链 token：
    [[L:cat/coil|点火线圈]]        品类页
    [[L:part/90919-02248|型号]]    型号页（按 OE 找）
    [[L:code/P0300|P0300]]         另一个故障码页
    [[L:guides/index.html|指南]]   指南目录

**新增一个码**：往 CODES 里加一条即可，slug 自动取 code 的小写。
**收录检查**：`python -c "import codes_content as c; print(len(c.CODES))"`
"""

# ----------------------------------------------------------------- 系统分组
# key, 英文组名, 码段, 中文（只在注释里用）
SYSTEMS = [
    ("misfire", "Misfire & ignition", "P0300–P0358"),
    ("position", "Crank, cam & timing", "P0011–P0345"),
    ("air", "Air metering & mixture", "P0100–P0175"),
    ("fuel", "Injectors & fuel delivery", "P0087–P0233"),
    ("o2", "Oxygen sensor & emissions", "P0130–P0455"),
    ("temp", "Temperature, idle & throttle", "P0115–P0505"),
    ("abs", "Wheel speed & ABS", "P0500, C0035–C0050"),
]

CODES = []

# ================================================================ A · 失火与点火
CODES += [
    {
        "code": "P0300",
        "name": "Random or multiple cylinder misfire detected",
        "system": "misfire",
        "desc": ("P0300 means more than one cylinder is misfiring, or the ECU cannot tell which one. "
                 "Why it is harder to fix than P0301, what to check first, and the coils we stock."),
        "lead": ("P0300 is the vaguest misfire code there is, and that is exactly what makes it expensive. "
                 "It says at least two cylinders are not firing properly, or that the misfire is jumping "
                 "around too fast to pin on a cylinder."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares crankshaft acceleration after every firing stroke. When the pattern "
                   "does not repeat on the same cylinder, it cannot name one, so it stores P0300 instead "
                   "of P0301–P0308. On a four-cylinder engine, a random misfire usually points at something "
                   "shared: fuel pressure, a vacuum leak, a mass air flow reading, or a whole ignition "
                   "circuit — not one coil.")),
            ("p", ("Most scanners give you a misfire counter per cylinder on the live data page. Read that "
                   "before you touch anything. If all four counters climb together, you are chasing a "
                   "shared cause. If one cylinder climbs ten times faster, treat it as that cylinder's "
                   "fault even though the code is P0300.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rough idle that may smooth out at higher rpm, or roughness only under load",
                "A flashing engine light at times — that means unburnt fuel is reaching the catalyst",
                "Loss of power going uphill, sometimes with the gearbox holding a lower gear",
                "Fuel smell at the tailpipe and consumption up by 20–40%",
                "On some cars a vibration you can feel through the floor at a steady 60–80 km/h",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Worn plugs on all cylinders",
                 "[[L:cat/plug|Spark plugs]]",
                 "The classic P0300. A plug gap that has opened up raises the voltage needed and the coils "
                 "start breaking down one by one."],
                ["Fuel pressure low",
                 "[[L:cat/fuelpump|Fuel pumps]]",
                 "A pump that is dying leans out every cylinder. It usually misfires worst under load and "
                 "runs acceptably at idle."],
                ["Vacuum or intake leak",
                 "—",
                 "A split intake hose leans out the whole engine. Look at short-term fuel trim: +15% or more "
                 "at idle that falls towards 0% at 2,500 rpm is a leak, not a sensor."],
                ["Dirty or failing MAF",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "An under-reading MAF makes the ECU lean the mixture. It also sets P0171 eventually."],
                ["All coils aged together",
                 "[[L:cat/coil|Ignition coils]]",
                 "On coil-on-plug engines past 150,000 km, several coils can be marginal at the same time."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read the per-cylinder misfire counters. This decides everything that follows and costs nothing.",
                "Check fuel pressure under load, not at idle — tee a gauge in and watch it while someone holds "
                "the engine at 2,500 rpm. A pressure that sags is the answer.",
                "Spray carb cleaner around the intake gasket and hoses while watching fuel trim. If trim drops "
                "sharply, you found the leak.",
                "Only then start swapping ignition parts, and swap them one at a time with a cylinder you know "
                "is good.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Reading P0300 as \"all four coils are bad\" and quoting a set. On the engines in our "
                     "catalogue the shared cause is fuel or air far more often than ignition. If you sell four "
                     "coils and the car still misfires, you have lost the customer and the coils come back. "
                     "Ask for the four misfire counters first — a photo of the live data screen is enough.")),
        ],
        "parts": [
            ("plug", "Start here on engines over 80,000 km"),
            ("coil", "Only after the shared causes are excluded"),
            ("fuelpump", "Check pressure under load"),
            ("maf", "Watch fuel trim before condemning"),
        ],
        "qa": [
            ("Can I drive with a P0300?",
             "Short distances at low load, yes. A flashing engine light means stop: unburnt fuel is burning "
             "inside the catalyst and that turns a coil job into a catalyst job."),
            ("Why is P0300 harder to fix than P0301?",
             "P0300 does not name a cylinder, so it cannot point at one coil or one injector. It points at "
             "anything the cylinders share, and that list is longer."),
        ],
        "related": ["P0301", "P0302", "P0171", "P0420"],
    },
    {
        "code": "P0301",
        "name": "Cylinder 1 misfire detected",
        "system": "misfire",
        "desc": ("P0301 means cylinder 1 is misfiring. The coil-or-plug test that settles it in ten minutes, "
                 "the order we check parts in, and the coils we keep for this fault."),
        "lead": ("A P0301 is the most useful misfire code you can get: it names a cylinder. Most of the ones "
                 "that reach us are ignition, and most of those are the coil rather than the plug."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU watches how much the crankshaft speeds up after cylinder 1 fires and compares it "
                   "with the other cylinders. When cylinder 1 contributes less, it stores P0301. It is set on "
                   "the second consecutive drive cycle that shows the fault, which is why a P0301 that "
                   "disappears for a week and comes back is usually a part breaking down with heat, not a "
                   "broken wire.")),
            ("p", ("Cylinder 1 is not always the one at the front of the engine. On most transverse fours it "
                   "is at the timing-belt end, but some manufacturers number from the gearbox end. Confirm the "
                   "numbering before you order, especially on French and Korean engines.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A shake at idle that mostly disappears above 2,000 rpm — the signature of a coil breaking "
                "down when hot",
                "The engine light on steady, flashing under hard acceleration",
                "Roughness that starts 10–20 minutes after a cold start and gets worse in damp weather",
                "Fuel smell at the tailpipe, consumption up noticeably",
                "P0301 appearing together with P0171 — that combination usually means a lean cylinder, not a "
                "weak spark",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Spark plug worn, fouled or wrong heat range",
                 "[[L:cat/plug|Spark plugs]]",
                 "Cheapest part and the fastest check. A cracked insulator misfires exactly like a dead coil."],
                ["Coil for cylinder 1",
                 "[[L:cat/coil|Ignition coils]]",
                 "The single most common cause on coil-on-plug engines past 100,000 km."],
                ["Plug wire or boot, on wasted-spark engines",
                 "[[L:cat/wire|Spark plug wire sets]]",
                 "A chafed wire usually kills two cylinders; a cracked boot kills one."],
                ["Injector leaking or clogged",
                 "[[L:cat/injector|Fuel injectors]]",
                 "A lean cylinder misfires. If fuel trim on that bank is high, suspect the injector."],
                ["Intake gasket leak at that runner",
                 "—",
                 "Leans out one cylinder only, and gets worse when the engine is cold."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap the coil with cylinder 2 and clear the code. If the misfire moves to P0302, the coil is "
                "dead. This one test settles most cases and costs nothing.",
                "If the code stays on cylinder 1, pull the plug and read it: black and wet means fuel or weak "
                "spark, white with a blistered electrode means lean or over-advanced.",
                "Compare coil primary resistance with a coil on a cylinder you know is good — never with a "
                "book value, because the value differs between coil families.",
                "Look for a thin grey carbon track down the inside of the boot, and for oil in the plug well. "
                "Both cause a misfire that a new coil will not fix until the oil leak is dealt with.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing all four coils \"while the cover is off\" on a car with 60,000 km. The plug is "
                     "usually the cause and the coil is the victim: a worn plug needs a higher firing voltage, "
                     "and the coil takes the strain. Change the plug with the coil, or you will sell that coil "
                     "again within a year.")),
        ],
        "parts": [
            ("coil", "Cylinder 1 coil — the usual fix"),
            ("plug", "Change it with the coil, do not skip"),
            ("wire", "On wasted-spark engines only"),
            ("injector", "When the cylinder runs lean"),
        ],
        "qa": [
            ("Is P0301 the coil or the plug?",
             "Usually both: the plug wears out, the coil works harder and fails. Swapping the coil to another "
             "cylinder tells you which one is dead right now; the plug should be changed either way."),
            ("Can I drive with a P0301?",
             "Gently, and not far. A steady light is an invitation to fix it this week; a flashing light means "
             "stop, because fuel is burning in the catalyst."),
        ],
        "related": ["P0300", "P0302", "P0351", "P0171"],
    },
    {
        "code": "P0302",
        "name": "Cylinder 2 misfire detected",
        "system": "misfire",
        "desc": ("P0302 means cylinder 2 is misfiring. How to tell a coil from a plug from an injector, "
                 "and the ignition coils we hold for cylinder 2 across common export engines."),
        "lead": ("P0302 is the same fault as P0301 one cylinder along, but the part that fails is often "
                 "different — on many engines cylinder 2 sits where heat and oil vapour collect first."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Cylinder 2 is contributing less power than the others. The ECU measures crankshaft "
                   "acceleration after each firing stroke and stores the code when cylinder 2 falls short on "
                   "two consecutive drive cycles.")),
            ("p", ("Cylinder numbering differs by maker: on most inline fours it runs from the timing end, but "
                   "several Japanese and French engines number from the flywheel end. Check before ordering "
                   "so the customer does not fit the coil into the wrong hole and then blame the part.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Idle vibration, often described as \"a taxi at the lights\", that fades with revs",
                "A misfire that only appears when the engine is hot and disappears after a cold start",
                "The light flashing during acceleration, then steady again",
                "On some engines a slight whistle or hiss from the intake side at idle",
                "P0302 together with P0303 points at a shared coil or a head gasket issue between the two",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Coil on cylinder 2",
                 "[[L:cat/coil|Ignition coils]]",
                 "First suspect on coil-on-plug engines, and the easiest to prove by swapping."],
                ["Spark plug condition",
                 "[[L:cat/plug|Spark plugs]]",
                 "Read the plug from cylinder 2 before you order. A wet plug means fuel, a black dry plug "
                 "means spark."],
                ["Oil in the plug well",
                 "—",
                 "A leaking cam cover gasket floods the well, the coil earths through the oil and misfires. "
                 "No coil survives that."],
                ["Injector imbalance",
                 "[[L:cat/injector|Fuel injectors]]",
                 "Common on engines with a shared rail where cylinder 2 is furthest from the feed."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap the cylinder 2 coil with cylinder 3 and clear. If the code follows the coil, order one "
                "coil. If it stays, the coil is fine.",
                "Pull the plug and check the well for oil before refitting anything.",
                "Listen to the injector with a stethoscope or a long screwdriver: a dead injector is silent.",
                "Check compression on cylinder 2 if plug and coil are both good — a burnt valve misfires in "
                "exactly the same way and no part will fix it.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Ordering a coil for a car where the plug well is full of oil. The new coil will run for a "
                     "few hundred kilometres and misfire again, and the customer will say the part is "
                     "defective. Ask for a photo of the plug well before shipping — it takes one message and "
                     "saves a return.")),
        ],
        "parts": [
            ("coil", "Cylinder 2 coil"),
            ("plug", "Read the old one first"),
            ("injector", "When the bank runs lean"),
        ],
        "qa": [
            ("Which cylinder is cylinder 2?",
             "It depends on the engine family. On most inline fours it is the second from the timing end, but "
             "check the firing order for the exact model before ordering."),
            ("Can a P0302 damage the engine?",
             "Unburnt fuel washes the cylinder wall and burns in the catalyst. Long enough and you add a "
             "catalyst to the bill."),
        ],
        "related": ["P0301", "P0303", "P0352", "P0300"],
    },
    {
        "code": "P0303",
        "name": "Cylinder 3 misfire detected",
        "system": "misfire",
        "desc": ("P0303 means cylinder 3 is misfiring. Why this cylinder fails differently on V6 and "
                 "inline-four engines, and how to prove it is ignition before you order."),
        "lead": ("P0303 on a four-cylinder is usually ignition. On a V6 it is often the cylinder hiding under "
                 "the intake plenum, which is why the labour is what the customer is really complaining about."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Cylinder 3 is not producing its share of torque. The ECU flags it after comparing "
                   "crankshaft acceleration with the other cylinders on two consecutive trips. Nothing in the "
                   "code tells you whether the cause is spark, fuel, air or compression — that is your job.")),
            ("p", ("On V6 engines cylinder 3 is frequently on the bank under the intake manifold. If a garage "
                   "is going to remove the plenum to reach one coil, they will usually ask for all three "
                   "coils on that bank — quote accordingly.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rough idle and a vibration you can feel through the seat at low speed",
                "A hesitation when pulling away, then normal running above 2,500 rpm",
                "Occasional backfire into the intake on a cold engine",
                "Fuel consumption climbing over a few weeks rather than overnight",
                "P0303 plus P0300 together — random misfire with one dominant cylinder",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Coil on cylinder 3",
                 "[[L:cat/coil|Ignition coils]]",
                 "On coil-on-plug engines this is the first and most common answer."],
                ["Spark plug, especially on LPG or CNG conversions",
                 "[[L:cat/plug|Spark plugs]]",
                 "Gas conversions eat plugs faster and misfire on one cylinder first."],
                ["Plug wire set on older wasted-spark engines",
                 "[[L:cat/wire|Spark plug wire sets]]",
                 "Cylinder 3 and 4 wires often share a route past the exhaust and cook together."],
                ["Valve clearance or compression",
                 "—",
                 "Cylinder 3 runs hottest on many inline fours. Burnt valves show up here first."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap coil 3 with coil 1, clear codes, drive. Where the misfire goes, the fault goes.",
                "Do a compression or leak-down test if the misfire stays on 3 with known-good ignition.",
                "On gas-converted cars, check the plug gap — gas likes a wider gap than petrol and the "
                "conversion installer rarely adjusts it.",
                "Check the coil connector for corrosion: cylinder 3 on transverse engines sits where water "
                "from the windscreen scuttle runs.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Assuming a compression problem from one bad leak-down reading on a cold engine. Rings "
                     "seal better hot. If the misfire only appears hot and the compression test is done cold, "
                     "you will quote an engine job for a coil.")),
        ],
        "parts": [
            ("coil", "Cylinder 3 coil"),
            ("plug", "Change with the coil"),
            ("wire", "Wasted-spark engines"),
        ],
        "qa": [
            ("Why does cylinder 3 fail more often?",
             "On many inline fours it is the hottest cylinder and the one where coolant flow is weakest, so "
             "plugs and coils age faster there."),
            ("Should I replace one coil or the set?",
             "One, if the others test good. On high-mileage engines quote the set and let the customer choose "
             "— it is their labour that decides, not the part price."),
        ],
        "related": ["P0302", "P0304", "P0353", "P0300"],
    },
    {
        "code": "P0304",
        "name": "Cylinder 4 misfire detected",
        "system": "misfire",
        "desc": ("P0304 means cylinder 4 is misfiring. The coil, plug and injector checks in the order that "
                 "finds the fault fastest, plus the parts we stock for cylinder 4."),
        "lead": ("P0304 is the last cylinder on most inline fours and the one nearest the gearbox — which "
                 "means the coil is often the easiest to reach and the wiring the most likely to be chafed."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU has decided cylinder 4 contributes less than the rest. It compares crankshaft "
                   "acceleration per firing event and stores P0304 after two consecutive drive cycles show "
                   "the same shortfall. The code names the cylinder; it does not name the cause.")),
            ("p", ("On engines numbered from the flywheel end, cylinder 4 is at the timing end instead. "
                   "Confirm the numbering from the firing order before you quote, or the customer fits the "
                   "coil in the wrong place and the fault does not move.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A steady shake at idle, worse when cold, that mostly clears above 2,000 rpm",
                "Hesitation when accelerating from a standstill",
                "A flashing light under load, steady light at cruise",
                "Slightly rough running right after a service — often a plug that was gapped wrong",
                "P0304 with P0172 means that cylinder is running rich, usually a leaking injector",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Coil on cylinder 4",
                 "[[L:cat/coil|Ignition coils]]",
                 "First suspect on coil-on-plug engines and the cheapest to test by swapping."],
                ["Spark plug",
                 "[[L:cat/plug|Spark plugs]]",
                 "Wrong gap after a service is a real and common cause — ask when the plugs were last changed."],
                ["Chafed coil harness at the gearbox end",
                 "—",
                 "On transverse engines the loom to cylinder 4 runs close to the bell housing and rubs through."],
                ["Leaking injector",
                 "[[L:cat/injector|Fuel injectors]]",
                 "Shows as a rich code on that bank and a misfire that clears when the engine is hot."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap the coil to another cylinder and clear. Fastest test there is.",
                "Wiggle the coil connector and the loom while watching live misfire counters — if the count "
                "jumps, the fault is the harness, not the part.",
                "Check the plug gap with a gauge. Do not trust \"they were changed last month\".",
                "If everything checks good, run a relative compression test through the scanner before "
                "condemning the engine.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Quoting a coil when the loom is chafed. The new coil works for a week, then the vibration "
                     "rubs the same wire through again and the part comes back marked \"defective\". Ask for a "
                     "photo of the connector and the loom before shipping.")),
        ],
        "parts": [
            ("coil", "Cylinder 4 coil"),
            ("plug", "Check the gap first"),
            ("injector", "When the bank runs rich"),
        ],
        "qa": [
            ("Is P0304 serious?",
             "It is as serious as any single-cylinder misfire: it costs fuel, it damages the catalyst over "
             "time, and it will not fix itself."),
            ("Can a bad plug cause P0304 only?",
             "Yes. One plug can fail while the other three are fine, especially after a service where the gap "
             "was set wrong."),
        ],
        "related": ["P0303", "P0301", "P0354", "P0300"],
    },
    {
        "code": "P0351",
        "name": "Ignition coil A primary/secondary circuit malfunction",
        "system": "misfire",
        "desc": ("P0351 is the coil circuit code for coil A (usually cylinder 1). What the ECU is actually "
                 "complaining about, and how to tell a dead coil from a dead driver in the ECU."),
        "lead": ("P0351 is not a misfire code — it is a circuit code. The ECU is telling you the coil's "
                 "electrical signature is outside the window it expects, which is often a different fix than "
                 "P0301."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Coil A is the coil the ECU fires first, which on most engines is cylinder 1. The ECU "
                   "monitors the primary circuit — the low-voltage side it switches — and the secondary side "
                   "through the coil's own feedback. If the current does not rise or fall in the expected "
                   "time, or the secondary does not produce the expected response, it stores P0351.")),
            ("p", ("The important distinction: P0351 is about the circuit, P0301 is about the result. A coil "
                   "can set P0351 without ever causing a misfire code, and a misfire can exist with no P0351. "
                   "When both appear together, the coil is almost certainly the part.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Misfire on cylinder 1 together with the code, often from cold",
                "A no-start or a start-then-die on some engines when the coil is shorted",
                "Rough running that appears and disappears with heat",
                "Sometimes no driveability symptom at all — the light is the only sign",
                "On some cars the tachometer flickers or drops",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed coil A",
                 "[[L:cat/coil|Ignition coils]]",
                 "The overwhelming majority. The primary winding opens or the internal driver dies."],
                ["Corroded or loose coil connector",
                 "—",
                 "A bad pin gives exactly the same circuit signature as a dead coil. Check before ordering."],
                ["Chafed coil harness",
                 "—",
                 "Common where the loom passes the cam cover or the EGR pipe."],
                ["ECU driver stage failure",
                 "—",
                 "Rare but real. If a new coil sets the same code instantly, the driver in the ECU is gone."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap coil A with coil B (usually cylinder 1 with cylinder 2) and clear. If the code becomes "
                "P0352, the coil is the fault.",
                "If the code stays P0351 after the swap, stop — the problem is in the harness or the ECU, and "
                "no coil will fix it.",
                "Check for spark at cylinder 1 with an inline tester while cranking.",
                "Measure primary resistance across the coil pins and compare with a known-good coil of the "
                "same family.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Shipping a coil when the fault is in the loom. If the customer's car sets P0351 again "
                     "immediately after fitting a new coil, it was never the coil — the ECU driver or a "
                     "chafed wire is the cause, and the coil comes back as a warranty claim. Ask for the code "
                     "after the swap before you agree to a replacement.")),
        ],
        "parts": [
            ("coil", "Coil A — the usual answer"),
            ("plug", "Worth changing at the same time"),
        ],
        "qa": [
            ("What does coil A mean?",
             "Coil A is the first coil in the ECU's firing sequence, normally cylinder 1. Coils B, C and D "
             "follow in firing order, not always in physical order."),
            ("Can I drive with a P0351?",
             "If the car runs, only gently and briefly. A shorted coil can also take out the ECU driver, "
             "which turns a cheap fix into an expensive one."),
        ],
        "related": ["P0301", "P0352", "P0353", "P0354"],
    },
    {
        "code": "P0352",
        "name": "Ignition coil B primary/secondary circuit malfunction",
        "system": "misfire",
        "desc": ("P0352 means the coil B circuit is out of range. How coil letters map to cylinders, and how "
                 "to prove the coil before you ship it to the other side of the world."),
        "lead": ("P0352 is the circuit code for coil B — usually cylinder 2, but the letter follows firing "
                 "order, not physical position. Get that wrong and the customer blames the part."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU switches coil B's primary circuit and watches the current profile and the "
                   "secondary response. Anything outside the expected window — open winding, shorted winding, "
                   "a driver that will not switch — sets P0352.")),
            ("p", ("Coil letters follow the firing sequence. On a four-cylinder with firing order 1-3-4-2, "
                   "coil A is cylinder 1, coil B is cylinder 3. On 1-2-4-3, coil B is cylinder 2. Always "
                   "confirm the firing order for the engine before telling a customer which cylinder to work on.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Misfire on whichever cylinder coil B serves, sometimes only when hot",
                "A hard start or a stall right after start-up",
                "Roughness that a scanner shows as a rising misfire count on one cylinder",
                "Occasional P0352 with no P030x code at all — the circuit is out of spec but still firing",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed coil B",
                 "[[L:cat/coil|Ignition coils]]",
                 "Most common, and the cheapest thing to rule in or out by swapping."],
                ["Connector or pin corrosion",
                 "—",
                 "Same circuit signature as a dead coil. Look before you order."],
                ["Damaged harness",
                 "—",
                 "Especially where the loom crosses the cam cover on transverse engines."],
                ["Worn plug raising the firing voltage",
                 "[[L:cat/plug|Spark plugs]]",
                 "A wide gap can push a healthy coil outside the ECU's expected window."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap coil B with a coil you know works and clear. Watch which code returns.",
                "If P0352 returns with a new coil in the B position, the fault is upstream: harness or ECU.",
                "Check the plug gap — a plug opened to 1.5 mm will stress the coil and can trip the circuit "
                "monitor.",
                "Inspect the coil boot for carbon tracking before you fit a replacement.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Using the physical position instead of the firing order to decide which cylinder is coil "
                     "B. On 1-3-4-2 engines that is cylinder 3, not cylinder 2. A customer who fits a coil to "
                     "the wrong cylinder will report \"no change\" and you will ship a second one.")),
        ],
        "parts": [
            ("coil", "Coil B — confirm the firing order first"),
            ("plug", "Gap matters for this code"),
        ],
        "qa": [
            ("Is coil B always cylinder 2?",
             "No. Coil letters follow firing order. On a 1-3-4-2 engine coil B is cylinder 3."),
            ("Can a P0352 come and go?",
             "Yes, if the winding is breaking down with heat. That is also why a cold test can pass and the "
             "fault still be real."),
        ],
        "related": ["P0351", "P0353", "P0302", "P0303"],
    },
    {
        "code": "P0353",
        "name": "Ignition coil C primary/secondary circuit malfunction",
        "system": "misfire",
        "desc": ("P0353 is the coil C circuit code. Which cylinder that is on common export engines, and the "
                 "checks that stop a good coil going back as a warranty claim."),
        "lead": ("P0353 is the third coil circuit in firing order. On most four-cylinders that lands on "
                 "cylinder 4, which is worth knowing before you tell a mechanic which coil to pull."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Coil C's primary current profile or secondary response is outside the window the ECU "
                   "expects. That covers an open winding, a shorted turn, a driver that fails to switch, and "
                   "sometimes a secondary that breaks down only under load.")),
            ("p", ("Which cylinder coil C is depends on firing order: on 1-3-4-2 it is cylinder 4, on 1-2-4-3 "
                   "it is cylinder 4 as well, but on 1-4-3-2 it is cylinder 3. Check the order for the engine "
                   "family, not for the car model.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A misfire that shows on one cylinder, often the one nearest the bulkhead",
                "A slight stumble when the engine is cold and a smooth idle once warm",
                "The light on with no obvious driveability change — circuit codes often lead the symptom",
                "On some engines a brief cut-out at high rpm",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed coil C",
                 "[[L:cat/coil|Ignition coils]]",
                 "Most common. Heat and vibration kill the winding."],
                ["Water or oil in the plug well",
                 "—",
                 "Coil C often sits where the scuttle drains. Water in the well shorts the coil."],
                ["Loom chafe near the bulkhead",
                 "—",
                 "The tightest part of the engine bay and the most common place for a rubbed wire."],
                ["Plug worn",
                 "[[L:cat/plug|Spark plugs]]",
                 "A worn plug raises demand and can push the coil outside the monitored window."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap coil C with a known-good coil and clear. Which code returns after a drive cycle?",
                "Check the plug well for water or oil before fitting anything new.",
                "Wiggle the loom at the bulkhead with the engine running and watch the misfire counters.",
                "Compare the primary resistance with the same coil family on another cylinder.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a new coil into a wet plug well. It will work for a few days and then fail "
                     "again — water is the cause, the coil is the casualty. Ask the customer to dry the well "
                     "and find where the water comes in before you ship a second coil.")),
        ],
        "parts": [
            ("coil", "Coil C — cylinder depends on firing order"),
            ("plug", "Check condition before shipping"),
        ],
        "qa": [
            ("Which cylinder does P0353 refer to?",
             "Whichever cylinder fires third. On a 1-3-4-2 engine that is cylinder 4; on 1-4-3-2 it is "
             "cylinder 3."),
            ("Can P0353 be a wiring fault?",
             "Yes, and it is common on that cylinder because the loom is tightest there."),
        ],
        "related": ["P0352", "P0354", "P0303", "P0304"],
    },
    {
        "code": "P0354",
        "name": "Ignition coil D primary/secondary circuit malfunction",
        "system": "misfire",
        "desc": ("P0354 is the coil D circuit code, usually the last cylinder in firing order. Diagnosis "
                 "steps, and when the coil is not the part that failed."),
        "lead": ("P0354 is the fourth coil circuit. On most fours that is the last cylinder in firing order, "
                 "and the one where a failing plug hides longest because it is hardest to reach."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU fires coil D and expects a specific current rise and a specific secondary "
                   "response. If either falls outside the window, it logs P0354. It is a monitoring code, so "
                   "it can appear before the driver feels anything at all.")),
            ("p", ("Because the ECU is comparing the circuit against a model rather than measuring the spark, "
                   "a worn plug with a wide gap, a corroded pin and a failing coil all produce the same code. "
                   "The order of checks below is what separates them.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Misfire on the last cylinder in firing order, sometimes only under load",
                "A slight roughness that the driver may not notice until it sets P0304 as well",
                "Hard starting when cold on some engines",
                "The light on with the car otherwise running normally",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed coil D",
                 "[[L:cat/coil|Ignition coils]]",
                 "Most common cause, and by far the easiest to prove."],
                ["Plug with an opened gap",
                 "[[L:cat/plug|Spark plugs]]",
                 "Especially on LPG cars, where the gap grows faster."],
                ["Connector corrosion",
                 "—",
                 "Reads exactly like a dead coil on the scanner."],
                ["Loom damage near the exhaust or EGR",
                 "—",
                 "Heat hardens the insulation and the wire breaks inside it."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Swap coil D to another cylinder and clear. If the code moves, the coil is the part.",
                "If the code does not move, inspect and wiggle the harness before considering any part.",
                "Check the plug gap and the plug well condition.",
                "On repeat failures, check whether a leaking cam cover gasket is filling the well with oil.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Treating a repeat P0354 as a coil quality problem. Two coils failing in the same "
                     "position is a car problem — heat, water, oil or a chafed wire — not a parts problem. "
                     "Ask what the plug well and the loom look like before sending a third coil.")),
        ],
        "parts": [
            ("coil", "Coil D"),
            ("plug", "Change with the coil on high-mileage engines"),
        ],
        "qa": [
            ("What does P0354 mean on a 4-cylinder?",
             "The fourth coil circuit in the firing sequence is out of specification, either because the coil "
             "failed or because its wiring or plug load is wrong."),
            ("Do all four coil codes mean the same thing?",
             "Yes, they are the same monitor applied to a different coil. Only the cylinder changes."),
        ],
        "related": ["P0353", "P0304", "P0351"],
    },
]

# ================================================================ B · 位置与正时
CODES += [
    {
        "code": "P0335",
        "name": "Crankshaft position sensor A circuit malfunction",
        "system": "position",
        "desc": ("P0335 means the ECU has lost the crankshaft position signal. Why it stops the engine dead, "
                 "how to test the sensor and the tone ring, and the CKP sensors we stock."),
        "lead": ("P0335 is one of the few codes that stops a car from starting at all. Without a crankshaft "
                 "signal the ECU does not know where the engine is, so it will not fire the coils or the "
                 "injectors."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The crankshaft position sensor reports the position and speed of the crank. The ECU needs "
                   "it to time both spark and injection, so when the signal is missing, intermittent or out "
                   "of range, the engine stops. P0335 is stored when no usable signal is seen during cranking.")),
            ("p", ("Two sensor types share this code: inductive (two wires, generates its own AC voltage) and "
                   "Hall effect (three wires, needs a supply). The test procedure is different, and so is the "
                   "part. Never order from the code alone.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Cranking with no start, often with the tachometer dead while cranking",
                "An engine that starts, runs, then dies within seconds",
                "A stall at speed followed by a no-start until it cools down — classic heat failure",
                "Occasional backfire during cranking",
                "Sometimes P0335 with no driveability problem at all on engines with a redundant sensor",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failing crankshaft position sensor",
                 "[[L:cat/ckp|Crankshaft position sensors]]",
                 "The most common cause, and the sensor that fails with heat more than any other."],
                ["Damaged tone ring or reluctor",
                 "—",
                 "A cracked or rusty ring gives a signal the ECU cannot trust. No sensor fixes it."],
                ["Air gap wrong after a repair",
                 "—",
                 "A sensor fitted with a shim missing sits too far and reads nothing."],
                ["Loom damage near the sensor",
                 "—",
                 "The sensor wire runs close to the crank pulley and to hot parts."],
                ["Worn crank thrust or a broken keyway",
                 "—",
                 "Rare, but it moves the ring and the signal goes out of range."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Crank the engine and watch live cranking rpm on the scanner. Zero rpm means no signal at all — "
                "confirm the sensor or the loom.",
                "Identify the sensor type first. Two wires means inductive: measure resistance and compare with "
                "the spec for that engine, then check for AC volts while cranking. Three wires means Hall: "
                "check the supply voltage with the key on.",
                "Inspect the tone ring for cracks, missing teeth and rust, and check the air gap.",
                "Check continuity from the sensor connector to the ECU before condemning the sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a sensor for a car whose tone ring is cracked. The new sensor reads the same "
                     "broken pattern and the car still does not start, and the part is now \"no good\" in the "
                     "customer's eyes. Ask for a photo of the reluctor before shipping — it is a five-minute "
                     "check that saves a return and a relationship.")),
        ],
        "parts": [
            ("ckp", "Crankshaft position sensor — match the type"),
            ("cmp", "Check for a related cam code too"),
        ],
        "qa": [
            ("Will a bad crankshaft sensor always stop the engine?",
             "Usually yes, because the ECU cannot time spark or injection without it. Some engines use a "
             "second sensor to limp home, which is why you sometimes see the code with the car still running."),
            ("Can I drive with a P0335?",
             "Not reliably. It is a stall-and-no-start code. If the car still runs, it is intermittent and it "
             "will fail completely, often at the worst moment."),
        ],
        "related": ["P0336", "P0340", "P0016", "P0300"],
    },
    {
        "code": "P0336",
        "name": "Crankshaft position sensor A circuit range/performance",
        "system": "position",
        "desc": ("P0336 means the crank signal is present but wrong — the engine sees an implausible pattern. "
                 "What causes that, and why a new sensor often does not fix it."),
        "lead": ("P0336 is the code that means \"the signal is there, but I do not believe it\". That is a "
                 "different problem from P0335, and it is the one where a new sensor most often fails to fix "
                 "anything."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU is receiving crankshaft pulses but the pattern is implausible: wrong tooth count, "
                   "an unexpected gap, or a speed change that the engine could not physically produce. It "
                   "stores P0336 because the signal exists but cannot be trusted for timing.")),
            ("p", ("That makes the tone ring, the air gap and the wiring the prime suspects, not the sensor "
                   "electronics. The sensor is usually reporting accurately what it sees.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rough running or a misfire that moves between cylinders",
                "Hard starting, sometimes with a backfire",
                "An intermittent stall with the engine restarting immediately",
                "The light on with the car driving almost normally in mild cases",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Cracked, rusty or damaged tone ring",
                 "—",
                 "The number one cause of P0336. Missing or deformed teeth make the pattern implausible."],
                ["Incorrect air gap",
                 "—",
                 "A sensor fitted without its shim, or a worn mount, reads a weak and uneven signal."],
                ["Metal debris on the sensor tip",
                 "—",
                 "Iron filings from a worn bearing or a recent repair bridge the gap and distort the signal."],
                ["Failing crankshaft position sensor",
                 "[[L:cat/ckp|Crankshaft position sensors]]",
                 "Real but less common than the ring. Only condemn it after the ring checks out."],
                ["Loom chafe causing intermittent loss",
                 "—",
                 "A partially broken wire drops pulses irregularly, which the ECU reads as range failure."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Remove the sensor and look at the ring through the hole. Cracks, rust and missing teeth are "
                "visible more often than people expect.",
                "Wipe the sensor tip and check for metal debris before refitting.",
                "Check the air gap against the specification for that engine family — do not assume it is the "
                "same as the last car you did.",
                "Scope the signal if you can. A clean square or sine wave rules out the wiring; a ragged one "
                "points at the loom.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the sensor because the code says \"sensor circuit\". P0336 names the circuit, "
                     "not the part. If the tone ring is cracked, a new sensor changes nothing and the return "
                     "comes back as \"still faulty\".")),
        ],
        "parts": [
            ("ckp", "Only after the tone ring checks out"),
            ("cmp", "Check cam signal for comparison"),
        ],
        "qa": [
            ("What is the difference between P0335 and P0336?",
             "P0335 means no usable signal. P0336 means a signal that is present but does not make sense. The "
             "second one is usually mechanical."),
            ("Can a P0336 be intermittent?",
             "Yes, and that is the signature of a partly broken wire or a ring that only distorts when hot."),
        ],
        "related": ["P0335", "P0341", "P0016"],
    },
    {
        "code": "P0340",
        "name": "Camshaft position sensor A circuit malfunction",
        "system": "position",
        "desc": ("P0340 means the ECU has lost the camshaft position signal on bank 1. Why it causes long "
                 "cranking and poor starting, and which cam sensor your engine actually uses."),
        "lead": ("P0340 usually does not stop the engine, it makes it start badly. Without the cam signal the "
                 "ECU cannot tell compression from exhaust stroke, so it guesses — and guessing costs "
                 "cranking time."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The camshaft position sensor tells the ECU which stroke each cylinder is on. The crank "
                   "sensor gives position but is ambiguous by one revolution, so the ECU needs the cam signal "
                   "to fire in the right order. When that signal is missing, P0340 is set.")),
            ("p", ("Most engines will still run on the crank signal alone using a default strategy, which is "
                   "why this code often comes with long cranking rather than a no-start. VVT engines are the "
                   "exception and may refuse to start or run very badly.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Longer cranking than normal, sometimes several seconds, then a start",
                "A rough idle for the first seconds after start",
                "Poor acceleration and a loss of VVT function on engines with variable timing",
                "The light on with otherwise acceptable running",
                "On some cars a P0016 appears alongside it",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failing camshaft position sensor",
                 "[[L:cat/cmp|Camshaft position sensors]]",
                 "The most common cause, and the sensor most likely to fail with heat."],
                ["Oil or sludge on the sensor face",
                 "—",
                 "A sensor buried in sludge reads nothing. Clean it before replacing it."],
                ["Timing chain or belt jumped",
                 "—",
                 "The cam signal arrives at the wrong time and the ECU flags the circuit."],
                ["Loom damage",
                 "—",
                 "The cam sensor wire runs along the head, which is hot and full of vibration."],
                ["Wrong sensor fitted previously",
                 "[[L:cat/cmp|Camshaft position sensors]]",
                 "Hall and inductive sensors are not interchangeable, and the connectors often look alike."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Clear the code and see whether it comes back immediately or after a drive cycle. Immediate "
                "return means a hard electrical fault.",
                "Check the sensor type and the connector — Hall sensors need a supply, inductive ones do not.",
                "Remove the sensor and look for metal debris or sludge on the face.",
                "If the sensor is good, check the cam timing marks before ordering anything else.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Not distinguishing P0340 from P0016. P0340 is the circuit; P0016 is the correlation "
                     "between crank and cam. If both are present, the timing is suspect and a new sensor will "
                     "not fix it.")),
        ],
        "parts": [
            ("cmp", "Camshaft position sensor — check the type"),
            ("ocv", "On VVT engines, check the oil control valve too"),
            ("ckp", "Compare crank signal"),
        ],
        "qa": [
            ("Can I drive with a P0340?",
             "Usually yes, but starting gets worse and VVT engines may run badly. Fix it before it strands "
             "the car."),
            ("Why does the car crank longer with a P0340?",
             "The ECU has to guess the stroke, so it tries combinations until it finds one that fires."),
        ],
        "related": ["P0341", "P0335", "P0016", "P0011"],
    },
    {
        "code": "P0341",
        "name": "Camshaft position sensor A circuit range/performance",
        "system": "position",
        "desc": ("P0341 means the cam signal is present but inconsistent. The timing-chain and VVT causes "
                 "that a new sensor will not fix, and how to tell them apart."),
        "lead": ("P0341 is the cam version of \"the signal is there but I do not trust it\". On engines with "
                 "VVT this code is often about the oil control valve or a stretched chain, not the sensor."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The camshaft sensor is producing pulses, but the pattern does not match what the ECU "
                   "expects for the current crank position. It stores P0341 rather than P0340 because there "
                   "is a signal — it is just implausible.")),
            ("p", ("This is the code that shows up when a timing chain has stretched by a link's worth, when a "
                   "VVT phaser is stuck, or when the cam sensor air gap is wrong. All three look identical on "
                   "the scanner and completely different on the car.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A rattle at cold start on chain engines, followed by this code",
                "Poor low-end torque and late or early cam timing on live data",
                "Rough idle that improves with revs",
                "P0011, P0016 or P0341 combinations",
                "A hesitation when the VVT should advance",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Stretched timing chain or worn tensioner",
                 "—",
                 "The classic P0341 cause on high-mileage chain engines. Listen for the cold-start rattle."],
                ["Stuck or clogged oil control valve",
                 "[[L:cat/ocv|Oil control valves]]",
                 "The phaser cannot move, so the cam sits in the wrong place and the correlation fails."],
                ["Camshaft position sensor air gap or debris",
                 "[[L:cat/cmp|Camshaft position sensors]]",
                 "A weak or uneven signal reads as a performance fault."],
                ["Sludge blocking the VVT oil feed",
                 "—",
                 "Common on engines with long oil change intervals."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch commanded versus actual cam timing on live data while revving. A lag or a stuck value "
                "points at the phaser or the OCV, not the sensor.",
                "Remove and clean the oil control valve screen. If it is full of sludge, that is the fault.",
                "Check for a cold-start chain rattle before ordering any sensor.",
                "Compare the cam and crank signals if you have a scope — the offset tells you whether it is "
                "mechanical.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a cam sensor for a stretched chain. The new sensor reports the same wrong "
                     "pattern and the code returns within a week. Ask two questions first: does it rattle on "
                     "cold start, and what is the commanded versus actual cam angle?")),
        ],
        "parts": [
            ("ocv", "Oil control valve — clean or replace first on VVT engines"),
            ("cmp", "Camshaft position sensor"),
            ("ckp", "For signal comparison"),
        ],
        "qa": [
            ("Does P0341 mean the sensor is bad?",
             "Not usually. It means the signal is implausible. On VVT engines the cause is more often the oil "
             "control valve or the chain."),
            ("Can I drive with a P0341?",
             "Yes, but do not leave it. If a chain is stretching, the next failure is a jump and a bent valve."),
        ],
        "related": ["P0340", "P0011", "P0016", "P0336"],
    },
    {
        "code": "P0011",
        "name": "Camshaft timing over-advanced or system performance (bank 1)",
        "system": "position",
        "desc": ("P0011 means the intake cam on bank 1 is more advanced than commanded. Usually the oil "
                 "control valve, not the sensor — here is how to prove it and what to replace."),
        "lead": ("P0011 is the most common VVT code in the world, and it is nearly always an oil problem "
                 "wearing the mask of an electrical one. The oil control valve is the part to look at first."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU commands the intake cam phaser to a target angle and compares it with the actual "
                   "angle from the cam sensor. When the cam stays more advanced than commanded for longer "
                   "than the calibration allows, it sets P0011.")),
            ("p", ("Phasers are moved by oil pressure through the oil control valve. So P0011 is an oil "
                   "circuit fault far more often than a sensor fault — sludge, a clogged screen, low oil "
                   "pressure or the wrong oil grade all produce it.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rough idle and a stumble just off idle",
                "Poor fuel economy and a lazy throttle response",
                "A rattle or tick from the front of the head on cold start",
                "Sometimes no symptom at all until the light comes on",
                "P0011 together with P0014 (exhaust cam) points at oil supply, not at two valves",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Clogged or failed oil control valve",
                 "[[L:cat/ocv|Oil control valves]]",
                 "The most common single cause. Clean the screen first, replace if the solenoid is dead."],
                ["Sludge in the oil galleries",
                 "—",
                 "Long oil change intervals block the phaser feed and the cam cannot follow the command."],
                ["Low oil pressure or wrong grade",
                 "—",
                 "The phaser needs pressure. Thin or old oil makes it lag."],
                ["Worn phaser or stretched chain",
                 "—",
                 "Mechanical wear — the valve cannot fix it."],
                ["Camshaft position sensor",
                 "[[L:cat/cmp|Camshaft position sensors]]",
                 "Only after the oil side is proven good."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch commanded and actual cam angle on live data while revving. If actual never follows, it "
                "is the valve or the oil feed.",
                "Remove the oil control valve and inspect the screen. Sludge here is the diagnosis.",
                "Check the oil level and condition — a P0011 on dirty oil is not a parts problem.",
                "Measure the solenoid resistance and compare with the specification before ordering a valve.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the phaser before the valve. The valve is a fraction of the price, it is the "
                     "part that fails most often, and it takes minutes to clean. If a customer has already "
                     "been quoted a phaser, ask whether the OCV screen was checked first.")),
        ],
        "parts": [
            ("ocv", "Oil control valve — first suspect"),
            ("cmp", "Check cam signal only after the oil side"),
            ("ckp", "For correlation checks"),
        ],
        "qa": [
            ("Is P0011 the sensor or the oil valve?",
             "Usually the oil control valve or an oil supply problem. The sensor is rarely the cause."),
            ("Can I drive with a P0011?",
             "Yes, but the cam is in the wrong place, so economy and emissions suffer and the phaser wears "
             "faster."),
        ],
        "related": ["P0016", "P0341", "P0340", "P0335"],
    },
    {
        "code": "P0016",
        "name": "Crankshaft / camshaft position correlation (bank 1 sensor A)",
        "system": "position",
        "desc": ("P0016 means the crank and cam signals disagree about engine position — usually a jumped "
                 "chain or a failed phaser. Why it is the code you must not ignore."),
        "lead": ("P0016 is the one diagnostic code that can turn into a bent valve. It means the crank and "
                 "the cam no longer agree on where the engine is, and on an interference engine that is a "
                 "mechanical warning, not an electrical one."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares the crankshaft and camshaft signals and expects a fixed relationship "
                   "between them. When the offset moves outside the tolerance — because the chain has "
                   "stretched or jumped, or because a phaser is stuck — it sets P0016.")),
            ("p", ("There is no sensor that fails in a way that only moves the correlation. If P0016 is "
                   "present, something mechanical has moved. Treat it as urgent.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A rattle at cold start that lasts a second or two",
                "Rough running, misfires and poor power",
                "Hard starting, sometimes a no-start when hot",
                "A P0011, P0017 or misfire codes appearing alongside",
                "On badly jumped engines, valve contact noise and then a dead cylinder",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Stretched timing chain or worn tensioner",
                 "—",
                 "The dominant cause. Chain engines past 150,000 km are the usual candidates."],
                ["Chain jumped a tooth",
                 "—",
                 "Sudden onset after a hard start or a low-oil event."],
                ["Stuck VVT phaser",
                 "[[L:cat/ocv|Oil control valves]]",
                 "The phaser cannot return to base position, so the correlation is wrong from the start."],
                ["Cam or crank sensor misreading",
                 "[[L:cat/cmp|Camshaft position sensors]]",
                 "Rare and easy to rule out by comparing both signals on a scope."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Check the timing marks physically before trusting any sensor reading.",
                "Look for chain stretch: with the crank at TDC, check whether the cam marks line up.",
                "Listen for the cold-start rattle. It is the cheapest evidence you will get.",
                "Do not sell a sensor for P0016 until the mechanical timing has been verified — it almost never "
                "fixes it.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a cam sensor for P0016 and letting the customer keep driving. On an interference "
                     "engine the next event is valve contact, and then the conversation is about an engine, "
                     "not a sensor. Say plainly: this code is mechanical until proven otherwise.")),
        ],
        "parts": [
            ("cmp", "Only after timing is verified"),
            ("ckp", "For signal comparison"),
            ("ocv", "If a stuck phaser is the cause"),
        ],
        "qa": [
            ("Is P0016 serious?",
             "Yes. It means the timing has moved. On an interference engine, continuing to drive can destroy "
             "the valves and pistons."),
            ("Can a P0016 be fixed by a sensor?",
             "Almost never. The correlation fault is mechanical. A sensor can only be the cause if both "
             "signals are electrically wrong in a matching way, which is rare."),
        ],
        "related": ["P0011", "P0341", "P0335", "P0300"],
    },
]

# ================================================================ C · 进气与混合气
CODES += [
    {
        "code": "P0100",
        "name": "Mass or volume air flow circuit malfunction",
        "system": "air",
        "desc": ("P0100 means the ECU has lost the mass air flow signal. Why the engine may still run, how to "
                 "test the sensor and the wiring, and the MAF sensors we stock."),
        "lead": ("P0100 is the circuit code for the mass air flow sensor — no usable signal at all. Unlike the "
                 "P0101 family it is not a plausibility problem, it is silence."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The MAF measures how much air enters the engine, and fuelling is calculated from it. If the "
                   "ECU sees no signal, no implausible signal or a signal outside the electrical range, it sets "
                   "P0100 and falls back to a default airflow map built from throttle position and rpm.")),
            ("p", ("That default is why the car may still run — badly, rich at idle, flat under load. Drivers "
                   "often report the light but no breakdown, which is exactly the profile of this code.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Engine light with no obvious misfire, but the car feels flat above 3,000 rpm",
                "Rich running at idle: black smoke, fuel smell, plug fouling",
                "Poor fuel economy and a lazy throttle response",
                "A stall when coming to a stop on some engines",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed mass air flow sensor",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "The most common answer, and cheap to prove if you can read live data."],
                ["Contaminated sensing element",
                 "—",
                 "Oil from an over-oiled filter or from the crankcase breather coats the element and kills "
                 "the reading before the sensor fails."],
                ["Loose or corroded connector",
                 "—",
                 "Gives a hard no-signal, exactly like a dead sensor."],
                ["Intake leak between the MAF and the throttle",
                 "—",
                 "Unmetered air enters after the sensor. The ECU sees the wrong air mass but the sensor is "
                 "working fine."],
                ["Blown fuse or a shared supply",
                 "—",
                 "Several sensors on one supply rail. Check the fuse before the part."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read live MAF grams per second at idle and at 2,500 rpm. A value stuck at zero or a value that "
                "does not rise with rpm is the diagnosis.",
                "Check the connector for corrosion and the supply voltage with the key on.",
                "Look at the element through the housing. A grey or oily film means clean or replace, not "
                "recalibrate.",
                "Before condemning the sensor, check for a split intake hose after the MAF — the most common "
                "false positive on this code.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Changing the MAF when the intake hose is split after it. The sensor reports the air it "
                     "sees correctly; the engine gets more through the crack. A five-minute smoke test or a "
                     "visual check of the hose saves the part.")),
        ],
        "parts": [
            ("maf", "Mass air flow sensor"),
            ("map", "Check for a related MAP fault"),
        ],
        "qa": [
            ("Can I drive with a P0100?",
             "Yes, but on the default airflow map: rich, thirsty and slow. Long enough and it fouls plugs and "
             "damages the catalyst."),
            ("Will cleaning the MAF fix it?",
             "Sometimes, if the element is only oil-contaminated. If the reading stays flat after cleaning, the "
             "sensor is dead."),
        ],
        "related": ["P0101", "P0102", "P0171", "P0172"],
    },
    {
        "code": "P0101",
        "name": "Mass air flow circuit range/performance",
        "system": "air",
        "desc": ("P0101 means the MAF reading is implausible for the engine speed. Usually an air leak or a dirty "
                 "element — not always a dead sensor. Here is the order we check in."),
        "lead": ("P0101 is the most misdiagnosed code in the intake group. The sensor is reporting a real "
                 "number; the number just does not match what the engine is doing."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares measured airflow against a model built from throttle position, engine "
                   "speed and manifold pressure. When the measured value drifts outside the expected window "
                   "for a set time, it stores P0101.")),
            ("p", ("That makes it a comparison fault. It can be caused by the sensor reading low (contamination), "
                   "reading high (a leak before the sensor), or by the model being wrong (a sticking throttle, "
                   "a restricted intake).")),

            ("h2", "What you will notice"),
            ("ul", [
                "Hesitation on light throttle, then a surge as the ECU corrects",
                "Long-term fuel trim drifting positive or negative",
                "Rough idle on some engines, normal running above 2,000 rpm",
                "Occasional stall at a stop, especially on turbo cars",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Dirty MAF sensing element",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "The classic. Cleaning sometimes restores it; if not, replace."],
                ["Leak between air filter and MAF",
                 "—",
                 "Unmetered air skews the reading high. A missing or split housing seal is enough."],
                ["Restricted air filter or intake",
                 "—",
                 "A collapsed filter makes the sensor read low and the model disagree."],
                ["Sticking throttle body",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "The model uses throttle angle; a body that does not return cleanly breaks the comparison."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Log MAF g/s and throttle position together. Compare the shape with a known-good car of the "
                "same model — not with a number from a manual.",
                "Check fuel trim at idle and at 2,500 rpm. Trim that is bad at idle and good at speed is a "
                "vacuum leak, not a MAF.",
                "Inspect the intake path from the filter to the throttle for splits and missing clamps.",
                "Clean the element with MAF cleaner before replacing — it is the cheapest test there is.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing a good MAF on a car with a leaking intake boot. P0101 names the circuit but "
                     "describes a disagreement. Ask for fuel trim numbers at idle and at 2,500 rpm — that "
                     "single pair tells you whether you are looking at a leak or a sensor.")),
        ],
        "parts": [
            ("maf", "Mass air flow sensor"),
            ("throttle", "Check the throttle body returns cleanly"),
            ("map", "Cross-check manifold pressure"),
        ],
        "qa": [
            ("Is P0101 always the MAF sensor?",
             "No. It is a plausibility fault. Air leaks and restricted filters cause it at least as often as a "
             "failing sensor."),
            ("Can a dirty MAF cause P0101 without any other code?",
             "Yes, and it is common. The sensor is still working, just reading wrong."),
        ],
        "related": ["P0100", "P0102", "P0171", "P0172"],
    },
    {
        "code": "P0102",
        "name": "Mass air flow circuit low input",
        "system": "air",
        "desc": ("P0102 means the MAF signal is below the expected voltage. The wiring, the earth and the sensor "
                 "itself — in the order that finds the fault fastest."),
        "lead": ("P0102 is an electrical fault, not a performance one: the signal is lower than it should be. "
                 "That points at the circuit first and the sensor second."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The MAF output voltage or frequency is below the minimum the ECU expects for the current "
                   "operating point. It can be a genuine low reading (blocked air path, a sensor degrading) or "
                   "a lost supply, a bad earth or a chafed signal wire.")),
            ("p", ("Because a low signal makes the ECU fuel for less air than is really entering, the engine "
                   "runs lean. Lean running is why this code sometimes shows up with P0171 next to it.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Lean running: hesitation, a flat spot off idle, high fuel trim",
                "Rough idle and a possible stall when cold",
                "Poor power at wide-open throttle",
                "On turbo cars, low boost and an engine that feels strangled",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed MAF sensor",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "The element degrades and the output falls away before it fails completely."],
                ["Chafed or broken signal wire",
                 "—",
                 "A partly broken wire drops voltage and reads exactly like a low sensor."],
                ["Bad earth at the sensor or the engine",
                 "—",
                 "A poor earth shifts the whole signal down. Check it before buying anything."],
                ["Blocked air path",
                 "—",
                 "A collapsed filter or a foreign object in the intake genuinely reduces airflow."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Back-probe the signal wire with the key on. Compare with the minimum specification for that "
                "engine family.",
                "Wiggle the loom while watching the reading on live data — a jump means the wire, not the "
                "sensor.",
                "Check supply and earth at the connector with a load test, not a voltmeter alone.",
                "Inspect the intake for a collapsed filter or debris before ordering a sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a new MAF into a circuit with a bad earth. The new sensor reads low in exactly the "
                     "same way and comes back as \"defective\". A two-minute earth voltage drop test prevents "
                     "the whole cycle.")),
        ],
        "parts": [
            ("maf", "Mass air flow sensor"),
        ],
        "qa": [
            ("What is the difference between P0100 and P0102?",
             "P0100 is no usable signal at all. P0102 is a signal that is present but too low."),
            ("Can a P0102 make the engine run rich?",
             "Usually lean, because the ECU fuels for less air than is actually entering."),
        ],
        "related": ["P0100", "P0101", "P0171"],
    },
    {
        "code": "P0105",
        "name": "Manifold absolute pressure circuit malfunction",
        "system": "air",
        "desc": ("P0105 means the MAP sensor circuit has failed. Where the sensor lives, how to test it with a "
                 "vacuum pump, and the MAP sensors we stock for common engines."),
        "lead": ("P0105 is the MAP sensor's no-signal code. On speed-density engines it is as important as the "
                 "MAF, and on some cars a failed MAP sensor is the reason the engine will not start at all."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The MAP sensor reports manifold pressure, which the ECU converts into air mass. No usable "
                   "signal, or a signal outside the electrical range, sets P0105. On engines with both MAF and "
                   "MAP, the MAP is mostly a plausibility check and a boost reference.")),
            ("p", ("Where the sensor takes its vacuum matters. A blocked or leaking reference port reads "
                   "atmospheric pressure all the time, which looks like a sensor fault on the scanner but is "
                   "not.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Poor idle quality and a hunting idle",
                "Excessive fuel consumption and black smoke",
                "Hard starting or a no-start on speed-density engines",
                "A turbo car with no boost or boost limited to a safe value",
                "Altitude-related running problems if the reference port is blocked",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed MAP sensor",
                 "[[L:cat/map|Intake pressure sensors (MAP)]]",
                 "Most common, and easy to test with a hand vacuum pump."],
                ["Blocked or split vacuum reference hose",
                 "—",
                 "The sensor is fine; it is not seeing manifold vacuum. Check this first."],
                ["Oil or carbon in the sensor port",
                 "—",
                 "Especially on engines with a lot of blow-by. Clean it before replacing it."],
                ["Loom damage",
                 "—",
                 "The sensor is usually mounted on the manifold where heat and vibration are worst."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read MAP with the key on, engine off: it should read close to atmospheric. If it does not, the "
                "sensor or the reference is wrong.",
                "Apply vacuum with a hand pump and watch the reading change smoothly. A dead spot or a stuck "
                "value condemns the sensor.",
                "Check the reference hose for cracks and for blockage.",
                "Compare KOEO and idle readings — the difference tells you whether the sensor is seeing vacuum "
                "at all.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the MAP sensor when the vacuum hose to it is blocked with carbon. The new sensor "
                     "reads the same wrong pressure. Pull the hose off and blow through it before you order.")),
        ],
        "parts": [
            ("map", "Intake pressure sensor (MAP)"),
            ("maf", "Cross-check airflow on engines with both"),
        ],
        "qa": [
            ("Can a bad MAP sensor stop the engine starting?",
             "On speed-density engines, yes — the ECU has no other way to calculate fuel."),
            ("What does the MAP sensor read with the engine off?",
             "Atmospheric pressure, roughly 100 kPa at sea level. A very different value means the sensor or "
             "its reference is wrong."),
        ],
        "related": ["P0106", "P0100", "P0171", "P0172"],
    },
    {
        "code": "P0106",
        "name": "Manifold absolute pressure circuit range/performance",
        "system": "air",
        "desc": ("P0106 means the MAP reading does not match engine conditions. Usually a vacuum leak or a "
                 "blocked port — here is how to tell them apart from a failed sensor."),
        "lead": ("P0106 is the plausibility version of the MAP code. The sensor is producing a signal; the ECU "
                 "just does not believe it for the throttle position it is seeing."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares manifold pressure with what it expects from throttle angle and engine "
                   "speed. A reading that stays high when vacuum should be strong, or drops when it should "
                   "not, triggers P0106.")),
            ("p", ("In practice this is a vacuum integrity code. The sensor is usually right and the manifold "
                   "pressure is genuinely wrong, because something is leaking or something is blocked.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A hunting or high idle",
                "Poor fuel economy with fuel trim drifting",
                "Hesitation when accelerating from idle",
                "Sometimes a whistle or hiss from the engine bay",
                "A boost car that over-boosts or under-boosts",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Vacuum leak at a hose, gasket or PCV",
                 "—",
                 "The number one cause. The manifold cannot hold vacuum, so the reading is wrong."],
                ["Blocked MAP port or hose",
                 "—",
                 "Carbon blocks the port and the sensor reads atmospheric pressure all the time."],
                ["Failed MAP sensor",
                 "[[L:cat/map|Intake pressure sensors (MAP)]]",
                 "Real, but only after the vacuum system is proven sound."],
                ["Sticking throttle body",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "The comparison uses throttle angle. A body that does not close cleanly breaks it."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch fuel trim at idle and at 2,500 rpm. High at idle, normal at speed means a vacuum leak.",
                "Spray carb cleaner around the intake gasket and hoses while watching trim and idle.",
                "Pull the MAP hose and check it for blockage and cracks.",
                "Compare the MAP reading at key-on-engine-off with atmospheric pressure.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Chasing a vacuum leak with parts instead of a smoke machine. Replacing the MAP sensor, the "
                     "PCV and the intake gasket in turn costs more than one smoke test and rarely finds the "
                     "split hose that is actually leaking.")),
        ],
        "parts": [
            ("map", "Intake pressure sensor (MAP)"),
            ("vsv", "Check the vacuum control valves too"),
            ("throttle", "Verify the throttle closes cleanly"),
        ],
        "qa": [
            ("Is P0106 a sensor fault?",
             "Rarely. It is a plausibility fault, and the manifold pressure really is wrong most of the time."),
            ("Can a vacuum leak set P0106 and P0171 together?",
             "Yes, that pair is the classic vacuum leak signature."),
        ],
        "related": ["P0105", "P0171", "P0172"],
    },
    {
        "code": "P0171",
        "name": "System too lean (bank 1)",
        "system": "air",
        "desc": ("P0171 means bank 1 is running lean and the ECU cannot correct it. The five real causes, the "
                 "fuel trim test that isolates them, and why the oxygen sensor is usually the victim."),
        "lead": ("P0171 is one of the most searched codes in the world and one of the most misdiagnosed. The "
                 "oxygen sensor is usually the part that reports the problem, not the part that causes it."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU adds fuel until the oxygen sensor reads stoichiometric. When it reaches the limit of "
                   "its correction — typically around +25% long-term trim — and the mixture is still lean, it "
                   "sets P0171. The code literally means \"I have run out of adjustment\".")),
            ("p", ("That limit is the key to diagnosis. Something is letting in air that the ECU did not "
                   "measure, or delivering less fuel than it thinks. The oxygen sensor is the messenger.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A rough or hunting idle, sometimes a stall when coming to a stop",
                "Hesitation on acceleration and a general lack of power",
                "Fuel economy that may go up or down depending on the cause",
                "Long-term fuel trim pinned high on a scanner",
                "Eventually P0300 misfires and P0420 as the lean mixture damages everything downstream",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Vacuum or intake leak after the MAF",
                 "—",
                 "The single most common cause. Splits in intake hoses, intake gaskets, brake booster lines "
                 "and PCV hoses all do it."],
                ["Dirty or under-reading MAF",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "The ECU fuels for less air than enters. Reading low is the same as a leak, from the "
                 "mixture's point of view."],
                ["Low fuel pressure",
                 "[[L:cat/fuelpump|Fuel pumps]], [[L:cat/fuelpress|Fuel pressure regulators]]",
                 "A weak pump or a leaking regulator delivers less fuel at the same injector pulse."],
                ["Clogged injectors",
                 "[[L:cat/injector|Fuel injectors]]",
                 "Partial blockage leans the whole bank. Worse under load."],
                ["Aged oxygen sensor",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "A sensor that reads lean when the mixture is fine makes the ECU add fuel until it hits the "
                 "limit. Less common than people think, and always the last thing to replace."],
                ["Leaking EVAP purge valve",
                 "[[L:cat/purge|Canister purge valves]]",
                 "A stuck-open purge valve feeds unmetered fuel vapour — usually rich, but it can confuse trim "
                 "badly."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read short-term and long-term fuel trim at idle and at 2,500 rpm. High at idle and normal at "
                "speed means a vacuum leak. High at both means fuel delivery or a sensor reading.",
                "Smoke test the intake. It finds in a minute what hands find in an hour.",
                "Check fuel pressure under load. A pump that holds pressure at idle can still fall short at "
                "3,000 rpm.",
                "Only after those check out, compare the upstream oxygen sensor's switching behaviour with the "
                "downstream one.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Changing the oxygen sensor first because the code is \"lean\". The sensor is doing its job: "
                     "it is telling you the engine is lean. If you fit a new sensor and the leak is still there, "
                     "the code comes back and you have spent the customer's money on the wrong part twice.")),
        ],
        "parts": [
            ("maf", "Check the reading, not the part"),
            ("o2", "Last, not first — the sensor reports lean, it rarely causes it"),
            ("injector", "When fuel delivery is the cause"),
            ("fuelpump", "Pressure under load"),
            ("fuelpress", "Check for a leaking regulator"),
            ("purge", "A stuck purge valve skews trim"),
        ],
        "qa": [
            ("Will a new oxygen sensor fix P0171?",
             "Usually not. The sensor is reporting a real lean condition. Fix the air or fuel problem, then "
             "check whether the sensor is still within spec."),
            ("Can I drive with a P0171?",
             "Yes, for a while, but lean running burns valves and catalysts. This is a fix-it-this-week code, "
             "not a fix-it-next-month one."),
            ("What fuel trim number means P0171 is serious?",
             "Long-term trim above +20% is serious. Above +25% the ECU has hit its limit — that is when the "
             "code sets."),
        ],
        "related": ["P0172", "P0174", "P0101", "P0300"],
    },
    {
        "code": "P0172",
        "name": "System too rich (bank 1)",
        "system": "air",
        "desc": ("P0172 means bank 1 is running rich beyond correction. Leaking injectors, a stuck purge valve "
                 "and a misreading MAF are the usual suspects — in the order we check them."),
        "lead": ("P0172 is the mirror of P0171: the ECU has pulled fuel all the way to its limit and the "
                 "mixture is still rich. That usually means too much fuel is getting in, not too little air."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Long-term fuel trim has reached its negative limit — usually around −25% — and the oxygen "
                   "sensor still reports a rich mixture. Too much fuel, or a sensor telling the ECU the engine "
                   "is leaner than it is.")),
            ("p", ("Rich running is worse for the car than lean in one respect: raw fuel washes the cylinder "
                   "walls and overheats the catalyst. Do not leave a P0172 running for months.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Fuel smell at the tailpipe and black smoke under acceleration",
                "Spark plugs fouling black, misfires appearing later",
                "Rough idle and a drop in fuel economy",
                "A strong smell of fuel in the engine oil (dilution)",
                "Long-term fuel trim pinned negative on a scanner",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Leaking injector",
                 "[[L:cat/injector|Fuel injectors]]",
                 "A dripping injector floods one cylinder and the bank runs rich. Smell the oil for fuel."],
                ["Stuck-open EVAP purge valve",
                 "[[L:cat/purge|Canister purge valves]]",
                 "It feeds fuel vapour into the intake continuously, which is unmetered fuel."],
                ["High fuel pressure",
                 "[[L:cat/fuelpress|Fuel pressure regulators]]",
                 "A failed regulator lets full pump pressure through and every injector delivers too much."],
                ["MAF reading high",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "The ECU fuels for more air than is entering. Same effect as a rich mixture."],
                ["Restricted air intake",
                 "—",
                 "A collapsed filter or a blocked housing genuinely reduces air, so the engine runs rich."],
                ["Aged oxygen sensor reading lean",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The sensor lies lean, the ECU adds fuel, and the real mixture goes rich."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Check fuel trim at idle and at 2,500 rpm. Negative at both means a fuel or sensor problem; "
                "negative mostly at idle means a purge valve or an injector.",
                "Pull the vacuum line off the purge valve and check whether fuel vapour or liquid is present.",
                "Check for fuel in the engine oil. A smell and a rising oil level means an injector is leaking.",
                "Measure fuel pressure and compare with the specification.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing all four injectors because one might be leaking. A leaking injector can be found "
                     "with a cylinder drop test or by pulling plugs and reading them — one black plug out of "
                     "four is the diagnosis. Sell one injector, not four.")),
        ],
        "parts": [
            ("injector", "One leaking injector is enough"),
            ("purge", "Stuck-open purge valve"),
            ("fuelpress", "Check fuel pressure before ordering"),
            ("maf", "Verify the reading"),
            ("o2", "Only if the other checks are clean"),
        ],
        "qa": [
            ("Is P0172 dangerous?",
             "It will destroy the catalyst if left. Fuel dilution also thins the engine oil, which accelerates "
             "wear."),
            ("Can a stuck-open purge valve cause P0172?",
             "Yes, and it is a common cause. It feeds unmetered fuel vapour straight into the intake."),
        ],
        "related": ["P0171", "P0174", "P0442", "P0101"],
    },
    {
        "code": "P0174",
        "name": "System too lean (bank 2)",
        "system": "air",
        "desc": ("P0174 is bank 2 running lean beyond correction. On V6 and V8 engines it usually pairs with "
                 "P0171 — and that pairing changes what to check first."),
        "lead": ("P0174 on a V engine almost never arrives alone. If bank 1 is lean too, the cause is shared — "
                 "and chasing it per bank wastes the customer's money."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Bank 2 has run out of positive fuel trim and the mixture is still lean. Bank 2 is the bank "
                   "that does not contain cylinder 1 — on most V engines that is the side away from the front "
                   "of the car, which matters when you are looking for a leak.")),
            ("p", ("The decisive question is whether bank 1 is lean as well. Both banks lean means a shared "
                   "cause: MAF, fuel pressure, or a large intake leak. Only bank 2 lean means something that "
                   "affects that bank alone.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rough idle and a shake that feels like it comes from one side of the engine",
                "Misfires concentrated on bank 2 cylinders",
                "Loss of power under load and poor economy",
                "P0171 alongside it more often than not",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Intake manifold gasket leak on bank 2",
                 "—",
                 "Classic on V engines — the gasket fails on the hotter bank first."],
                ["Under-reading MAF",
                 "[[L:cat/maf|Mass air flow sensors]]",
                 "Affects both banks. Check it before blaming a bank-specific part."],
                ["Low fuel pressure",
                 "[[L:cat/fuelpump|Fuel pumps]], [[L:cat/fuelpress|Fuel pressure regulators]]",
                 "Shared cause. Both banks lean."],
                ["Bank 2 oxygen sensor reading lean",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "If only bank 2 is affected and the exhaust is actually fine, the sensor is a candidate."],
                ["Clogged bank 2 injectors",
                 "[[L:cat/injector|Fuel injectors]]",
                 "Less common, but it produces a bank-specific lean condition."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read fuel trim per bank. Both lean = shared cause; only bank 2 = bank-specific cause.",
                "Smoke test the intake, paying attention to the bank 2 side of the manifold.",
                "Check fuel pressure first if both banks are affected.",
                "Swap the upstream oxygen sensors side to side to see whether the lean reading follows the "
                "sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Treating P0174 as a bank 2 problem when P0171 is also present. That pairing is a shared "
                     "cause every time. Ask for the other code before quoting a manifold gasket job.")),
        ],
        "parts": [
            ("o2", "Only when bank 2 alone is affected"),
            ("maf", "Shared cause — check first"),
            ("injector", "If the injectors are the difference"),
            ("fuelpump", "Both banks lean means fuel delivery"),
        ],
        "qa": [
            ("What is bank 2?",
             "The side of the engine that does not contain cylinder 1. On most V engines that is the side away "
             "from the front of the car."),
            ("Why does P0174 usually come with P0171?",
             "Because most lean causes — MAF, fuel pressure, large intake leaks — affect both banks."),
        ],
        "related": ["P0171", "P0172", "P0101"],
    },
]

# ================================================================ D · 喷油与供油
CODES += [
    {
        "code": "P0201",
        "name": "Injector circuit / open — cylinder 1",
        "system": "fuel",
        "desc": ("P0201 is the cylinder 1 injector circuit code. How to test the injector, the wiring and the "
                 "driver — and why a new injector often does not fix it."),
        "lead": ("P0201 is a circuit code, not a mixture code. The ECU is telling you cylinder 1's injector does "
                 "not have the electrical signature it expects — which is often the loom, not the injector."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU fires each injector and monitors the current through its winding. An open circuit, "
                   "a short, or a driver stage that does not switch correctly sets P0201 for cylinder 1.")),
            ("p", ("Because it is a cylinder-specific circuit code, it is a gift: it names the cylinder. The work "
                   "is deciding whether the fault is the injector, the harness or the ECU driver.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A dead miss on cylinder 1 that does not improve with revs",
                "Strong fuel smell if the injector is stuck open",
                "A no-start or a very rough start on some engines",
                "Cylinder 1 misfire code alongside P0201 in most cases",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed injector winding",
                 "[[L:cat/injector|Fuel injectors]]",
                 "Open or shorted coil in the injector. Measured with an ohm meter."],
                ["Chafed or broken injector harness",
                 "—",
                 "The loom runs along the head where it is hot and where it rubs."],
                ["Corroded connector pins",
                 "—",
                 "Very common on older engines and in humid climates."],
                ["ECU driver stage",
                 "—",
                 "If a new injector sets the same code immediately, the driver is gone."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Measure injector resistance and compare with another cylinder. A reading far outside the group "
                "is the answer.",
                "Listen to the injector with a stethoscope or a long screwdriver while cranking. Silence means it "
                "is not firing.",
                "Swap the coil pack or check the signal with a noid light — the light confirms the driver, not "
                "just the injector.",
                "Check the loom where it bends near the head before ordering anything.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Shipping an injector for a car with a broken loom. If the new injector sets P0201 again "
                     "straight away, the circuit is the fault. Ask for the resistance reading of the old "
                     "injector before you ship — it costs the customer two minutes and saves you a return.")),
        ],
        "parts": [
            ("injector", "Cylinder 1 injector"),
        ],
        "qa": [
            ("Can I drive with a P0201?",
             "Barely. A dead injector means one cylinder is not fuelling, and a stuck-open one can hydro-lock "
             "the engine."),
            ("How do I test an injector without a scanner?",
             "Measure its resistance and listen to it click while cranking. Both are quick and neither needs a "
             "diagnostic tool."),
        ],
        "related": ["P0202", "P0301", "P0087"],
    },
    {
        "code": "P0202",
        "name": "Injector circuit / open — cylinder 2",
        "system": "fuel",
        "desc": ("P0202 is the cylinder 2 injector circuit code. Resistance testing, noid light checks, and the "
                 "injectors we stock for common engines."),
        "lead": ("P0202 is the same circuit check as P0201, one cylinder along. The difference is usually in the "
                 "harness route, not in the injector."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Cylinder 2's injector circuit does not match the expected current profile. Open winding, "
                   "shorted winding, a broken wire or a driver that does not switch — all produce the same "
                   "code.")),
            ("p", ("On many engines the injector loom runs from the ECU across the top of the engine and down "
                   "to the rail. Cylinders in the middle of that run are the ones most often affected by chafe "
                   "and heat.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A hard miss on cylinder 2 at all speeds",
                "Rough idle and a noticeable power loss",
                "Fuel smell if the injector is stuck open",
                "P0302 alongside it in most cases",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed injector",
                 "[[L:cat/injector|Fuel injectors]]",
                 "The winding fails. Easy to confirm with a resistance comparison."],
                ["Harness chafe at the rail",
                 "—",
                 "The loom is clipped to the rail and the clips break with age."],
                ["Connector corrosion",
                 "—",
                 "Humidity and heat cycle the pins until the contact goes."],
                ["ECU driver failure",
                 "—",
                 "Rare. Confirm by fitting a known-good injector into the same position."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Measure resistance across the injector and compare with the same bank.",
                "Fit a noid light to the connector and crank — no flash means the circuit or the driver.",
                "Inspect the loom clips and the insulation where it crosses the head.",
                "Swap the injector to cylinder 3 to see whether the code follows the part.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling an injector without comparing resistance values. A single out-of-range reading is "
                     "proof; a guess is not. The comparison takes one minute with a cheap meter.")),
        ],
        "parts": [
            ("injector", "Cylinder 2 injector"),
        ],
        "qa": [
            ("What is the difference between P0202 and P0302?",
             "P0202 is the electrical circuit. P0302 is the misfire that results. Circuit codes come first "
             "when the injector stops firing entirely."),
            ("Can I replace one injector?",
             "Yes, if its resistance is out of range and the others match each other. Many workshops replace "
             "the set on high-mileage engines for labour reasons."),
        ],
        "related": ["P0201", "P0302", "P0087"],
    },
    {
        "code": "P0230",
        "name": "Fuel pump primary circuit malfunction",
        "system": "fuel",
        "desc": ("P0230 is the fuel pump circuit code. Relay, fuse, inertia switch and pump — the order that "
                 "finds a no-start fuel fault in minutes instead of hours."),
        "lead": ("P0230 is a no-start code. The ECU is not seeing the current it expects on the fuel pump "
                 "circuit, so it does not know whether the pump is running."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU controls the fuel pump through a relay or directly through a driver, and monitors the "
                   "circuit. An open circuit, a short, or a current that is far out of range sets P0230.")),
            ("p", ("On many cars the pump primes for two seconds at key-on and then runs only while the ECU sees "
                   "rpm. So a pump that is silent at key-on is not automatically dead — check whether the "
                   "circuit is being commanded at all.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Cranking with no start, and no pump prime sound at key-on",
                "An engine that starts then dies within a second or two",
                "A stall at speed followed by a no-start",
                "Sometimes an intermittent no-start that resolves itself when the car cools",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed fuel pump",
                 "[[L:cat/fuelpump|Fuel pumps]]",
                 "Worn brushes and a seized impeller. The usual end of the line."],
                ["Fuel pump relay",
                 "—",
                 "Cheap, common and easy to swap. Always check it before ordering a pump."],
                ["Blown fuse or inertia switch",
                 "—",
                 "An inertia cut-off after a bump looks exactly like a dead pump."],
                ["Corroded pump connector at the tank",
                 "—",
                 "Very common on cars from humid regions. The plug overheats and the current drops."],
                ["Bad earth to the pump",
                 "—",
                 "The circuit is complete enough to read voltage but cannot carry current."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Listen for the prime at key-on. No sound, then check the relay and fuse before the pump.",
                "Measure voltage at the pump connector while cranking. Battery voltage there condemns the pump; "
                "near zero condemns the circuit.",
                "Check the pump earth with a voltage drop test, not a continuity test.",
                "If voltage is good and the pump still does not run, the pump is the answer.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the pump when the relay or the tank connector was the fault. The new pump runs "
                     "for a while on the same marginal circuit and then the code returns. Voltage at the "
                     "connector while cranking is the test that separates the two, and it takes one minute.")),
        ],
        "parts": [
            ("fuelpump", "Fuel pump — after the circuit checks out"),
            ("fuelpress", "Check pressure once it runs"),
        ],
        "qa": [
            ("Will a bad relay cause P0230?",
             "Yes. The ECU monitors the circuit and a relay that does not close is an open circuit."),
            ("Can I drive with a P0230?",
             "Only until the pump stops. This is a no-start code that usually becomes a tow."),
        ],
        "related": ["P0087", "P0089", "P0300"],
    },
    {
        "code": "P0087",
        "name": "Fuel rail / system pressure too low",
        "system": "fuel",
        "desc": ("P0087 means rail pressure is below target — usually at high load. Why a pump that is fine at "
                 "idle can still set this code, and how to test pressure properly."),
        "lead": ("P0087 is the code that exposes a weak pump. The car often drives normally around town and only "
                 "falls over when the driver asks for fuel — which is why it gets dismissed."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares measured rail pressure with the target for the current load. When the "
                   "reading stays below target for longer than the calibration allows, it sets P0087.")),
            ("p", ("The comparison is load-based, so the fault often only appears at wide-open throttle or "
                   "uphill. A pump that holds pressure at idle can still be the cause.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A flat spot or a hesitation under hard acceleration",
                "Loss of power climbing hills, then recovery when the load drops",
                "A stall after sustained high-speed running",
                "Sometimes rough running and misfires under load only",
                "On direct-injection cars, a long crank before starting",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Worn fuel pump",
                 "[[L:cat/fuelpump|Fuel pumps]]",
                 "The most common cause. It delivers enough at low flow and falls short at high flow."],
                ["Clogged fuel filter",
                 "—",
                 "Restriction raises the demand on the pump and lowers rail pressure at load."],
                ["Leaking fuel pressure regulator",
                 "[[L:cat/fuelpress|Fuel pressure regulators]]",
                 "Bleeds pressure back to the tank instead of holding it in the rail."],
                ["Blocked pickup strainer in the tank",
                 "—",
                 "A dirty tank clogs the strainer. Common on cars from dusty regions."],
                ["Failing pressure sensor",
                 "—",
                 "The sensor reads low while the pressure is fine. Confirm with a mechanical gauge."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Tee a mechanical gauge into the rail and watch it at idle and under load. This is the only way "
                "to separate a weak pump from a lying sensor.",
                "Check the filter date. A filter that has never been changed is a cheap part of the answer.",
                "Measure pressure drop-off after key-off — a regulator that leaks down fast is the fault.",
                "Inspect the in-tank strainer if the car comes from a dusty market.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the pump because the scanner says pressure is low, when the filter or the "
                     "regulator is the restriction. A mechanical gauge on the rail plus a filter change costs "
                     "less than a pump and answers the question properly.")),
        ],
        "parts": [
            ("fuelpump", "Fuel pump"),
            ("fuelpress", "Pressure regulator"),
            ("injector", "Check for leakage before condemning the pump"),
        ],
        "qa": [
            ("Can a weak pump cause P0087 without any other code?",
             "Yes. The pump can be adequate at low flow and inadequate at high flow, so the car seems fine "
             "until it is loaded."),
            ("Is P0087 dangerous?",
             "Lean running at high load damages pistons and catalysts. It is worth fixing properly."),
        ],
        "related": ["P0089", "P0230", "P0171"],
    },
    {
        "code": "P0089",
        "name": "Fuel pressure regulator performance",
        "system": "fuel",
        "desc": ("P0089 means the fuel pressure regulator is not holding pressure where the ECU wants it. How "
                 "to test it, and when the pump is the real culprit."),
        "lead": ("P0089 says the regulator is not doing its job. Half the time the regulator is fine and the "
                 "pump cannot supply enough for the regulator to work with."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU commands a rail pressure and controls it through a regulator — mechanical on older "
                   "engines, electronic on newer ones. When the achieved pressure does not track the command "
                   "within tolerance, it stores P0089.")),
            ("p", ("It is a performance code, not a circuit code, so it describes a control problem rather than "
                   "a dead part. Both an over-supplying pump and a leaking regulator can produce it.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Hesitation and uneven power delivery",
                "Hard starting when hot, or a long crank",
                "Rich or lean codes appearing alongside",
                "Fuel pressure that drops quickly after the engine is switched off",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed pressure regulator",
                 "[[L:cat/fuelpress|Fuel pressure regulators]]",
                 "Diaphragm failure or a stuck valve. Leaks pressure back to the tank."],
                ["Weak fuel pump",
                 "[[L:cat/fuelpump|Fuel pumps]]",
                 "The regulator cannot regulate what the pump does not deliver."],
                ["Clogged filter",
                 "—",
                 "Restriction upstream of the regulator looks like regulator failure."],
                ["Faulty pressure sensor",
                 "—",
                 "On electronic systems the sensor is part of the loop. Confirm with a gauge."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Measure rail pressure with a gauge and compare with the specification at idle and under load.",
                "Check how fast pressure bleeds off after key-off. Fast bleed-down points at the regulator.",
                "Pull the regulator vacuum line and check for fuel — a ruptured diaphragm is a definite answer.",
                "Test pump flow as well as pressure before ordering a regulator.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a regulator on a car with a tired pump. The new regulator cannot raise pressure the "
                     "pump never produced, and the code returns. Test flow, not only pressure.")),
        ],
        "parts": [
            ("fuelpress", "Fuel pressure regulator"),
            ("fuelpump", "Check pump flow before blaming the regulator"),
        ],
        "qa": [
            ("Can I drive with a P0089?",
             "Yes, but expect rich or lean running depending on which way it fails. Both damage the catalyst."),
            ("Is the regulator a serviceable part?",
             "On most engines yes, and it is usually cheaper than the pump. Confirm the part number by engine, "
             "not by model year alone."),
        ],
        "related": ["P0087", "P0230", "P0172"],
    },
]

# ================================================================ E · 氧传感器与排放
CODES += [
    {
        "code": "P0130",
        "name": "O2 sensor circuit malfunction (bank 1, sensor 1)",
        "system": "o2",
        "desc": ("P0130 means the upstream oxygen sensor circuit has failed. Why it matters more than the "
                 "downstream one, and how to tell a dead sensor from a dead heater."),
        "lead": ("P0130 is the code for the sensor that actually controls fuelling — bank 1, upstream. When it "
                 "fails, the ECU stops trimming and the engine runs on a fixed map."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("Sensor 1 is upstream of the catalyst, the one the ECU uses to calculate mixture. P0130 means "
                   "its signal is absent or outside the electrical range. The heater may still work — the "
                   "sensor is just not producing a usable voltage.")),
            ("p", ("Two heater codes exist separately (P0135 for bank 1 upstream) and they are diagnosed "
                   "differently: heater faults are electrical and can be measured cold, signal faults need the "
                   "engine running and hot.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Fuel economy dropping by 10–25%",
                "Rough running and hesitation when the engine is cold",
                "The engine running rich: black plugs, fuel smell",
                "Poor emissions and a smell of rotten eggs from a hot catalyst",
                "Misfires that appear later as the catalyst degrades",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed oxygen sensor",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The sensing element ages or is poisoned by coolant, oil or silicone."],
                ["Contamination from a coolant or oil leak",
                 "—",
                 "A new sensor fails the same way in weeks if the engine is burning either."],
                ["Harness damage",
                 "—",
                 "The sensor wire runs along the exhaust, which is the worst possible route."],
                ["Wrong sensor fitted previously",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "Wideband and narrowband sensors are not interchangeable and many connectors look identical."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read the sensor voltage on live data with the engine hot. A good narrowband sensor switches "
                "between roughly 0.1 and 0.9 V several times a second.",
                "Watch for a reading stuck at a mid value — that is a dead element, not a lean engine.",
                "Check the heater resistance and the heater supply before replacing the sensor.",
                "Look at the old sensor tip: black soot is normal ageing, white or red deposits mean "
                "contamination and the new sensor will fail too.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a sensor because the code says \"circuit\" without checking the heater supply. "
                     "Half the sensors returned as faulty have nothing wrong with them — the fuse or the supply "
                     "wire is dead. Check power at the connector first.")),
        ],
        "parts": [
            ("o2", "Upstream sensor, bank 1"),
        ],
        "qa": [
            ("What is the difference between sensor 1 and sensor 2?",
             "Sensor 1 is upstream of the catalyst and controls fuelling. Sensor 2 is downstream and only "
             "monitors the catalyst."),
            ("Can I use a universal oxygen sensor?",
             "Sometimes, but the connector and the number of wires must match exactly. For export orders the "
             "plug-and-play sensor avoids a comeback."),
        ],
        "related": ["P0133", "P0134", "P0135", "P0420"],
    },
    {
        "code": "P0133",
        "name": "O2 sensor circuit slow response (bank 1, sensor 1)",
        "system": "o2",
        "desc": ("P0133 means the upstream oxygen sensor has gone lazy — it still works, just too slowly. Why "
                 "that ruins fuel economy and when it is worth replacing."),
        "lead": ("P0133 is the \"old age\" code. The sensor is alive and reading, it just reacts slower than the "
                 "ECU needs, so the mixture drifts rich and lean instead of being held steady."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU counts how often the upstream signal crosses from lean to rich and back. A healthy "
                   "sensor switches many times a second at cruise. When the count falls below the expected "
                   "minimum, the ECU sets P0133.")),
            ("p", ("This is normal ageing accelerated by contamination — coolant, oil, or silicone sealant "
                   "vapour. It is also the most common reason a car passes emissions on paper but burns fuel "
                   "in real life.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Fuel economy slowly dropping with no other symptom",
                "A slight surge at steady cruise",
                "Slightly rough idle that no one can quite describe",
                "Emissions drifting up at inspection time",
                "Sometimes no symptoms at all until the light comes on",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Aged oxygen sensor",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The usual cause on sensors past 100,000 km."],
                ["Contamination from coolant or oil",
                 "—",
                 "Find the leak first or the new sensor ages just as fast."],
                ["Exhaust leak before the sensor",
                 "—",
                 "Air entering upstream of the sensor makes the signal swing wrongly."],
                ["Low fuel pressure",
                 "[[L:cat/fuelpump|Fuel pumps]]",
                 "A lazy pump makes the mixture slow to respond, which looks like a lazy sensor."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read the switching count or the sensor's voltage trace. A slow, wide swing is the signature.",
                "Check the exhaust for leaks between the manifold and the sensor.",
                "Look for coolant loss or oil consumption before fitting a new sensor.",
                "Replace both upstream sensors if the car has two banks and similar mileage — the second one is "
                "usually just as tired.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the downstream sensor. P0133 is specifically about sensor 1, upstream. The "
                     "downstream sensor does not control fuelling and replacing it changes nothing.")),
        ],
        "parts": [
            ("o2", "Upstream sensor, bank 1"),
            ("fuelpump", "Rule out fuel delivery first"),
        ],
        "qa": [
            ("Is P0133 urgent?",
             "No, but it quietly costs fuel every kilometre. On a fleet it is worth fixing quickly."),
            ("Will a P0133 turn into a P0130?",
             "Often. The sensor keeps degrading until the signal goes out of range completely."),
        ],
        "related": ["P0130", "P0134", "P0420"],
    },
    {
        "code": "P0134",
        "name": "O2 sensor circuit no activity (bank 1, sensor 1)",
        "system": "o2",
        "desc": ("P0134 means the upstream oxygen sensor is producing no signal at all. Dead sensor, dead "
                 "heater or dead wiring — how to tell which before you order."),
        "lead": ("P0134 is the flatline code. The sensor is not switching at all — the ECU sees a signal that "
                 "never changes, which usually means the sensor never got hot enough to work."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("A narrowband oxygen sensor only produces voltage above roughly 300 °C. If the heater has "
                   "failed, or the sensor is not reaching temperature, the signal stays flat and the ECU stores "
                   "P0134 rather than a circuit code.")),
            ("p", ("This distinction matters: P0134 is often a heater problem wearing a sensor-shaped costume. "
                   "Check the heater circuit before you replace the sensor.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rich running from cold start that never corrects",
                "Fuel consumption up sharply",
                "Black plugs and a strong exhaust smell",
                "Rough idle when cold, improving slightly when hot",
                "On some cars a limp mode with reduced power",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed oxygen sensor heater",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The heater circuit is inside the sensor. A burnt-out heater gives a flat signal."],
                ["Blown heater fuse",
                 "—",
                 "Always check the fuse before the sensor. It is the cheapest test in the list."],
                ["Open heater wire or connector",
                 "—",
                 "The heater draws several amps, so a marginal connector fails here first."],
                ["Dead sensing element",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The element itself fails. Confirm by measuring heater resistance and supply."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Measure heater resistance across the heater pins. Open circuit means the sensor.",
                "Check for supply voltage at the heater connector with the key on.",
                "Run the engine hot and watch the signal voltage — a stuck mid-value with a good heater means "
                "the element is dead.",
                "Check the fuse and the earth before ordering.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the sensor when the heater fuse is blown because of a chafed wire. The new "
                     "sensor will blow the same fuse. Inspect the loom along the exhaust before fitting "
                     "anything.")),
        ],
        "parts": [
            ("o2", "Upstream sensor, bank 1"),
        ],
        "qa": [
            ("Can I drive with a P0134?",
             "Yes, but in open-loop fuelling: rich, thirsty and damaging to the catalyst over time."),
            ("What does \"no activity\" mean physically?",
             "The sensor output never changes. Usually it never reached operating temperature, so start with "
             "the heater."),
        ],
        "related": ["P0130", "P0135", "P0133"],
    },
    {
        "code": "P0135",
        "name": "O2 sensor heater circuit malfunction (bank 1, sensor 1)",
        "system": "o2",
        "desc": ("P0135 is the oxygen sensor heater circuit code. Why it causes rich running from cold, how to "
                 "measure the heater, and the sensors we stock with the right connector."),
        "lead": ("P0135 is the most common oxygen sensor code there is, and the easiest to diagnose: the heater "
                 "is a resistance wire, and a meter tells you the truth in thirty seconds."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The heater brings the sensor up to operating temperature within seconds of a cold start. "
                   "Without it the engine runs open-loop for minutes. P0135 means the heater circuit is open, "
                   "shorted, or drawing a current the ECU will not accept.")),
            ("p", ("Because the heater is inside the sensor body, a failed heater means a new sensor — there is "
                   "no separate part. But the fuse and the supply wiring are outside, and they fail too.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Rich running and a strong smell for the first few minutes after a cold start",
                "Rough cold idle that smooths as the engine warms",
                "Fuel consumption higher than it should be, especially on short trips",
                "Engine light on within a minute or two of starting",
                "In cold climates, noticeably worse cold-start behaviour",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Burnt-out heater in the sensor",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The most common cause. Measured as open circuit across the heater pins."],
                ["Blown fuse",
                 "—",
                 "Check first. A shorted heater blows the fuse and takes the whole circuit down."],
                ["Chafed heater wire near the exhaust",
                 "—",
                 "Heat and vibration break the insulation and then the wire."],
                ["Corroded connector",
                 "—",
                 "The heater draws high current, so a bad pin heats up and fails."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Measure resistance across the two heater wires at the sensor connector. Open means replace the "
                "sensor.",
                "Check the fuse for that circuit.",
                "With the key on, check for battery voltage at the heater supply pin.",
                "Inspect the wiring run along the exhaust for chafe before fitting a new sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a sensor without checking the fuse. If the fuse is blown, the sensor is probably "
                     "fine and something downstream shorted it. Two minutes with a meter decides which part "
                     "the customer actually needs.")),
        ],
        "parts": [
            ("o2", "Upstream sensor with heater, bank 1"),
        ],
        "qa": [
            ("Is the heater inside the sensor?",
             "Yes on almost all modern sensors. A failed heater means a new sensor."),
            ("Can I drive with a P0135?",
             "Yes. The car runs rich until it warms up, which wastes fuel but does not strand you."),
            ("How many wires does a heated sensor have?",
             "Usually four: two for the signal, two for the heater. The heater pair is the one with the low "
             "resistance."),
        ],
        "related": ["P0130", "P0134", "P0133"],
    },
    {
        "code": "P0420",
        "name": "Catalyst system efficiency below threshold (bank 1)",
        "system": "o2",
        "desc": ("P0420 means the ECU thinks the catalyst is not cleaning well enough. Before you sell a "
                 "catalyst, check the three things that kill them — one of them is your oxygen sensor."),
        "lead": ("P0420 is the most expensive misdiagnosis in this list. The catalyst is usually the victim; "
                 "the cause is upstream, and it is often a part we sell for a fraction of the price."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU compares the upstream and downstream oxygen sensor signals. A working catalyst stores "
                   "and releases oxygen, so the downstream signal should be much steadier than the upstream "
                   "one. When the two signals look too similar, the ECU concludes the catalyst has lost its "
                   "storage capacity and sets P0420.")),
            ("p", ("It never says the catalyst is broken — it says the catalyst is not performing. A lazy "
                   "upstream sensor, a small exhaust leak or a misfire can all produce the same comparison "
                   "result. Diagnose the cause before quoting a catalyst.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Engine light with no driveability change at all — the most common presentation",
                "A sulphur or rotten-egg smell after a hard drive",
                "Slightly worse fuel economy",
                "Failing an emissions test",
                "Sometimes a rattle from the exhaust when the catalyst substrate breaks up",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Lazy upstream oxygen sensor",
                 "[[L:cat/o2|Oxygen sensors]]",
                 "The comparison is only as good as the sensors. A slow upstream sensor mimics a dead "
                 "catalyst."],
                ["Misfires or rich running over time",
                 "[[L:cat/coil|Ignition coils]], [[L:cat/injector|Fuel injectors]]",
                 "Unburnt fuel overheats the substrate and washes the washcoat off. This is how catalysts "
                 "actually die."],
                ["Oil or coolant burning",
                 "—",
                 "Burns or poisons the catalyst. A new one will die the same way if the engine is not fixed."],
                ["Exhaust leak before the downstream sensor",
                 "—",
                 "Air entering the exhaust makes the downstream signal look active, which reads as a failed "
                 "catalyst."],
                ["Genuinely failed catalyst",
                 "—",
                 "Real, but it should be the last conclusion, not the first."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Check for stored misfire and mixture codes. Fix those first — a catalyst will not survive "
                "them.",
                "Compare upstream and downstream switching on live data. Downstream should be much flatter.",
                "Look for exhaust leaks before the downstream sensor, and for a rattle inside the can.",
                "Measure oil consumption and check for coolant loss before fitting a new catalyst.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a catalyst on a car that has had a misfire for months. The new catalyst dies in "
                     "weeks and the customer blames the part. Fix the misfire, then the catalyst. Ask for the "
                     "code history before quoting — that single question protects both of you.")),
        ],
        "parts": [
            ("o2", "Both sensors, before the catalyst"),
            ("coil", "Fix misfires first — they kill catalysts"),
            ("injector", "Rich running does the same"),
        ],
        "qa": [
            ("Do I have to replace the catalyst for P0420?",
             "No, and usually you should not be the first thing you try. Check the sensors, misfires and "
             "exhaust leaks first."),
            ("Can I drive with a P0420?",
             "Yes. It is an emissions fault, not a safety fault. But ignoring the cause will eventually cost a "
             "catalyst as well."),
            ("How long does a catalyst last?",
             "150,000 km and more if the engine is healthy. A catalyst that fails early is a symptom."),
        ],
        "related": ["P0130", "P0133", "P0300", "P0171"],
    },
    {
        "code": "P0442",
        "name": "Evaporative emission system leak detected (small leak)",
        "system": "o2",
        "desc": ("P0442 is a small EVAP leak — most often the fuel cap or a perished hose. How the system "
                 "tests itself, and when the purge valve is the real fault."),
        "lead": ("P0442 is the small-leak code in the evaporative system. It is usually not a part at all — it "
                 "is a seal, a cap, or a hose that has gone hard with age."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The EVAP system seals the fuel tank and vents vapour through a canister into the intake. The "
                   "ECU pulls a slight vacuum on the sealed system and watches how fast it decays. A decay "
                   "faster than a calibrated threshold but slower than a large leak sets P0442.")),
            ("p", ("The test only runs under specific conditions — usually a cold start with the tank between "
                   "a quarter and three quarters full. That is why P0442 can take days to reappear after being "
                   "cleared.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Engine light with no driveability symptom at all",
                "A fuel smell around the filler neck or the engine bay",
                "The code returning days after being cleared",
                "Sometimes a hiss when opening the fuel cap",
                "Hard starting after refuelling on some cars",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Fuel cap seal",
                 "—",
                 "The most common cause by a wide margin. Check the seal and the seating surface first."],
                ["Perished or cracked EVAP hose",
                 "—",
                 "Rubber hoses harden and split, especially in hot climates."],
                ["Sticking canister purge valve",
                 "[[L:cat/purge|Canister purge valves]]",
                 "A valve that does not seal lets vapour escape and can also make the system fail its own "
                 "test."],
                ["Leaking canister or cracked tank vent",
                 "—",
                 "Plastic cracks with age and vibration."],
                ["Filler neck corrosion",
                 "—",
                 "Common on cars from coastal or humid regions."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Inspect the fuel cap seal for cracks and the filler neck for rust.",
                "Look at every EVAP hose under the bonnet and above the tank for hardening and splits.",
                "Smoke test the system — it finds small leaks faster than any other method.",
                "Test the purge valve for sealing and for correct operation with a scan tool.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a purge valve for a leak that is a fuel cap. Ask the customer to check the cap seal "
                     "and click it properly before you quote anything. This code resolves without parts more "
                     "often than any other on this list.")),
        ],
        "parts": [
            ("purge", "Canister purge valve"),
            ("vsv", "Check the vacuum control valves"),
        ],
        "qa": [
            ("Can a loose fuel cap cause P0442?",
             "Yes, it is the number one cause. A cap that is not clicked or has a hardened seal lets the "
             "vacuum decay."),
            ("Why does the code take days to come back?",
             "The self-test only runs under specific conditions — cold start, partial tank. It can take several "
             "drive cycles."),
            ("Can I drive with a P0442?",
             "Yes. It is an emissions fault and does not affect how the car drives."),
        ],
        "related": ["P0455", "P0172"],
    },
    {
        "code": "P0455",
        "name": "Evaporative emission system leak detected (large leak)",
        "system": "o2",
        "desc": ("P0455 is a large EVAP leak — a cap left off, a disconnected hose or a purge valve stuck open. "
                 "Why it sometimes makes the car hard to start after refuelling."),
        "lead": ("P0455 means the evaporative system cannot hold vacuum at all. A large leak usually has an "
                 "obvious cause, and it is often something that was left disconnected."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU pulls vacuum on the sealed EVAP system and the pressure does not move, or moves far "
                   "less than expected. A leak large enough to prevent the system from pulling down at all sets "
                   "P0455.")),
            ("p", ("Because the threshold is large, the cause is usually something visible: a missing cap, a hose "
                   "off, a cracked canister, or a purge valve stuck wide open so the system can never seal.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Engine light, often right after a refuel or a service",
                "A strong fuel smell around the car",
                "Hard starting after refuelling on some engines",
                "Rough idle if the purge valve is stuck open",
                "Sometimes a whistle from the tank area",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Fuel cap missing or not sealing",
                 "—",
                 "Check this before anything else. It is free."],
                ["Disconnected or split EVAP hose",
                 "—",
                 "Often after a service or a tank removal. Look for the obvious first."],
                ["Purge valve stuck open",
                 "[[L:cat/purge|Canister purge valves]]",
                 "The system can never build vacuum and the intake gets fuel vapour continuously."],
                ["Cracked canister or tank vent valve",
                 "—",
                 "Plastic failure, common in hot climates."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Check the fuel cap is present and sealing. Do not skip this.",
                "Smoke test the system — on a large leak it shows immediately.",
                "Pull the purge valve and check whether it holds closed when it should.",
                "Inspect the canister and the vent valve for cracks.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Quoting a canister on a car that left the cap off at the last fill. P0455 is the one code "
                     "most likely to fix itself when the cap is refitted and the codes are cleared.")),
        ],
        "parts": [
            ("purge", "Canister purge valve"),
            ("vsv", "Vacuum control valves"),
        ],
        "qa": [
            ("Will P0455 fix itself?",
             "If the cause was a loose cap, yes — after the cap is refitted and the codes cleared. Otherwise it "
             "needs a repair."),
            ("Can a missing fuel cap cause P0455?",
             "Yes. It is a large leak by definition and the most common cause of this code."),
        ],
        "related": ["P0442", "P0172"],
    },
]

# ================================================================ F · 温度、怠速与节气门
CODES += [
    {
        "code": "P0115",
        "name": "Engine coolant temperature circuit malfunction",
        "system": "temp",
        "desc": ("P0115 means the coolant temperature sensor circuit has failed. Why it makes cold starts rich, "
                 "how to test it with a meter, and the temperature sensors we stock."),
        "lead": ("P0115 is a boring code with expensive consequences. Without a coolant temperature reading the "
                 "ECU assumes a warm engine, so it under-fuels from cold and misjudges everything downstream."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The coolant temperature sensor is a thermistor: resistance falls as temperature rises. The "
                   "ECU reads the voltage across it and converts it to temperature. An open, shorted or "
                   "out-of-range circuit sets P0115.")),
            ("p", ("When the signal is lost the ECU substitutes a default value, usually around 80 °C. That "
                   "default is why the car still runs — and why the cold-start behaviour is wrong.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Hard starting when cold, or a fast idle that never drops",
                "Rich running and a strong fuel smell on cold start",
                "The temperature gauge dead or jumping",
                "Radiator fans running when they should not, or not running when they should",
                "Higher fuel consumption and worse emissions",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed coolant temperature sensor",
                 "[[L:cat/temp|Temperature sensors]]",
                 "The thermistor drifts or opens. Cheap and easy to prove with a meter."],
                ["Corroded connector",
                 "—",
                 "The sensor sits in a wet, hot place. Pins corrode and the reading drifts."],
                ["Damaged wiring",
                 "—",
                 "Rodent damage and chafe are common on the sensor loom."],
                ["Low coolant or airlock",
                 "—",
                 "The sensor must be in coolant to read correctly. An air pocket gives a false cold reading."],
                ["Wrong sensor fitted",
                 "[[L:cat/temp|Temperature sensors]]",
                 "There are often two sensors — one for the gauge and one for the ECU. Do not mix them up."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read coolant temperature on live data from a cold start and compare with the gauge and with "
                "reality.",
                "Measure sensor resistance and compare with the specification at two temperatures.",
                "Check the connector for corrosion and the wiring for continuity.",
                "Check the coolant level and bleed the system before condemning the sensor — an airlock reads "
                "exactly like a fault.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting the sensor for the gauge instead of the one for the ECU. Many engines have two, "
                     "with different resistance curves and sometimes identical connectors. Confirm by "
                     "resistance value, not by appearance.")),
        ],
        "parts": [
            ("temp", "Coolant temperature sensor — check which one"),
            ("thermo", "Check the thermostat at the same time"),
        ],
        "qa": [
            ("Can a bad coolant sensor cause a no-start?",
             "Yes, on cold mornings. The ECU fuels for a warm engine and the mixture is too lean to fire."),
            ("How many coolant sensors does an engine have?",
             "Often two: one for the ECU and one for the gauge. They are not always interchangeable."),
        ],
        "related": ["P0117", "P0128", "P0171"],
    },
    {
        "code": "P0117",
        "name": "Engine coolant temperature circuit low input",
        "system": "temp",
        "desc": ("P0117 means the coolant temperature signal is lower than physically possible — usually a "
                 "shorted sensor or a wiring short. Rich running and fans that never stop."),
        "lead": ("P0117 is a sensor reading that the engine cannot produce: coolant temperature below the "
                 "lowest plausible value. That is an electrical short, not a cold engine."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU converts sensor resistance to temperature. A short to earth, or a sensor whose "
                   "resistance has fallen too far, produces a voltage that converts to an implausibly low "
                   "temperature — below about −40 °C on most calibrations.")),
            ("p", ("Because the reading looks extremely cold, the ECU enriches the mixture heavily and often runs "
                   "the cooling fans continuously, which is why customers notice the fans first.")),

            ("h2", "What you will notice"),
            ("ul", [
                "Cooling fans running from the moment the engine starts, in cold weather",
                "Very rich running, black smoke and plug fouling",
                "Poor fuel economy",
                "Hard starting or flooding on cold start",
                "The temperature gauge reading low or not moving",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Shorted coolant temperature sensor",
                 "[[L:cat/temp|Temperature sensors]]",
                 "Internal short. Measured as very low resistance."],
                ["Signal wire shorted to earth",
                 "—",
                 "A rubbed wire against the block produces the same reading."],
                ["Water in the connector",
                 "—",
                 "Very common after pressure washing or in humid climates."],
                ["Wrong sensor or a resistor fitted",
                 "—",
                 "Someone has tried to fix a gauge problem by fitting the wrong part."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read the temperature value with the engine cold. Below −40 °C means a short, not a cold morning.",
                "Disconnect the sensor and watch the reading. If it jumps to a plausible value, the sensor or "
                "its wiring is shorted.",
                "Measure resistance across the sensor and compare with the specification.",
                "Check the connector for water and corrosion before ordering.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the sensor when the connector is full of water. A quick dry and a clean fixes it, "
                     "and the replacement would have corroded the same way.")),
        ],
        "parts": [
            ("temp", "Coolant temperature sensor"),
            ("thermo", "Verify the actual cooling behaviour too"),
        ],
        "qa": [
            ("Why do the fans run all the time with P0117?",
             "The ECU reads an impossibly cold engine and runs the fans as a precaution, or because the default "
             "strategy assumes the sensor is unusable."),
            ("Is P0117 dangerous?",
             "Mainly to the catalyst and the plugs through rich running. It will not overheat the engine."),
        ],
        "related": ["P0115", "P0128", "P0120"],
    },
    {
        "code": "P0120",
        "name": "Throttle position sensor A circuit malfunction",
        "system": "temp",
        "desc": ("P0120 means the throttle position sensor circuit has failed. Why the engine goes to limp "
                 "mode, how to test the sensor sweep, and the TPS and throttle bodies we stock."),
        "lead": ("P0120 is a limp-mode code. The ECU has lost the throttle position signal, so it no longer knows "
                 "how far open the throttle is — and it will limit power rather than guess."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The throttle position sensor reports the angle of the throttle plate. The ECU uses it for "
                   "fuelling, for the automatic gearbox shift points and for its own plausibility checks. An "
                   "open or shorted circuit sets P0120.")),
            ("p", ("On drive-by-wire cars the relationship between the pedal and the throttle is electronic, so "
                   "a TPS fault can also produce a limp home mode with a very low rev limit — which customers "
                   "often describe as \"the car will not go above 2,000 rpm\".")),

            ("h2", "What you will notice"),
            ("ul", [
                "Limp mode with a low rev limit or reduced power",
                "An idle that hangs high or a car that will not idle at all",
                "Hesitation and a dead spot just off idle",
                "Erratic or harsh gear changes on automatics",
                "Sometimes a stall when coming to a stop",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed throttle position sensor",
                 "[[L:cat/tps|Throttle position sensors]]",
                 "The resistive track wears through where the throttle sits most of the time."],
                ["Dirty throttle body",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "Carbon around the plate makes the closed position wrong and the reading implausible."],
                ["Loose or corroded connector",
                 "—",
                 "A poor contact gives the same no-signal code."],
                ["Worn throttle body (drive-by-wire)",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "The internal sensor is part of the body on many cars and cannot be replaced separately."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch the TPS voltage on live data and sweep the throttle slowly. A dead spot or a jump means "
                 "the track is worn.",
                "Check the connector and the supply voltage.",
                "Clean the throttle body before replacing anything — carbon causes a surprising share of these.",
                "On drive-by-wire cars, confirm whether the sensor is separate or part of the body before "
                 "quoting.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a sensor for a throttle body that needs cleaning and a relearn. Modern throttles "
                     "need an adaptation after cleaning, and without it the engine idles badly and the customer "
                     "assumes the part was wrong.")),
        ],
        "parts": [
            ("tps", "Throttle position sensor"),
            ("throttle", "Complete body where the sensor is integrated"),
            ("stepper", "Check idle control on cable-throttle engines"),
        ],
        "qa": [
            ("Is P0120 the sensor or the throttle body?",
             "It depends on the car. Many modern engines integrate the sensor into the body, so the whole unit "
             "is replaced."),
            ("Can I drive with a P0120?",
             "In limp mode, slowly. It is not a safety failure but the car will be unpleasant and possibly "
             "unable to accelerate normally."),
        ],
        "related": ["P0122", "P0505", "P0101"],
    },
    {
        "code": "P0122",
        "name": "Throttle position sensor A circuit low input",
        "system": "temp",
        "desc": ("P0122 means the throttle position signal is below the expected voltage. Wiring, earth or a "
                 "worn sensor track — the checks that find it in order."),
        "lead": ("P0122 is an electrical fault in the throttle position circuit: the signal is lower than it "
                 "should be for the throttle angle. It is the low-voltage twin of P0120."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The TPS output voltage has fallen below the minimum expected. That can be a worn resistive "
                   "track at the closed-throttle end, a bad earth, or a partly broken signal wire.")),
            ("p", ("Because the ECU uses this signal to know when the throttle is closed, a low reading confuses "
                   "idle control, fuel cut-off on overrun and the gearbox shift logic all at once.")),

            ("h2", "What you will notice"),
            ("ul", [
                "A high or hunting idle",
                "Hesitation when pulling away",
                "Poor gearbox behaviour on automatics",
                "Reduced power and a possible limp mode",
                "Sometimes the engine cutting out on deceleration",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Worn TPS resistive track",
                 "[[L:cat/tps|Throttle position sensors]]",
                 "The track wears at the closed position where the wiper sits most of its life."],
                ["Bad earth",
                 "—",
                 "Shifts the whole signal down. Check it before the part."],
                ["Chafed signal wire",
                 "—",
                 "A partly broken wire drops voltage under vibration."],
                ["Dirty throttle body",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "Carbon stops the plate closing fully, so the sensor reads below its learned zero."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch the TPS voltage at closed throttle and compare with the specification.",
                "Sweep the throttle and look for dips — a worn track shows as a momentary drop.",
                "Check the earth with a voltage drop test.",
                "Clean the throttle body and perform the relearn before replacing the sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing the TPS because the plate is carboned up and cannot reach its closed position. "
                     "The new sensor learns the same wrong zero. Clean first, relearn, then judge.")),
        ],
        "parts": [
            ("tps", "Throttle position sensor"),
            ("throttle", "Body where the sensor is integrated"),
        ],
        "qa": [
            ("What is the difference between P0120 and P0122?",
             "P0120 is a general circuit failure. P0122 is specifically a signal that is too low."),
            ("Can a low TPS signal cause a high idle?",
             "Yes. The ECU cannot tell the throttle is closed, so it holds the idle speed up."),
        ],
        "related": ["P0120", "P0505"],
    },
    {
        "code": "P0128",
        "name": "Coolant thermostat below regulating temperature",
        "system": "temp",
        "desc": ("P0128 means the engine is not reaching operating temperature in time — the thermostat is "
                 "stuck open. Cheap part, real fuel cost, and easy to prove."),
        "lead": ("P0128 is a thermostat code, and it is one of the few codes where the cheapest part in the "
                 "catalogue is usually the right answer. A thermostat stuck open costs fuel every kilometre."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU knows the engine should reach operating temperature within a certain time and load "
                   "profile. When the coolant temperature stays below the threshold for too long, it sets P0128.")),
            ("p", ("That almost always means the thermostat is stuck open and coolant is circulating through the "
                   "radiator from the first second. It can also mean the temperature sensor is lying, so check "
                   "the reading against reality.")),

            ("h2", "What you will notice"),
            ("ul", [
                "The heater blowing only warm, not hot, especially in cold weather",
                "The temperature gauge sitting below normal and taking a long time to move",
                "Fuel consumption up by 5–15%",
                "The engine taking far longer to warm up than it used to",
                "Sometimes a P0115 or P0117 alongside if the sensor is also involved",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Thermostat stuck open",
                 "[[L:cat/thermo|Thermostats]]",
                 "The usual answer. Cheap, and it fixes the fuel cost in the same job."],
                ["Faulty coolant temperature sensor",
                 "[[L:cat/temp|Temperature sensors]]",
                 "Reads low while the engine is actually warm. Confirm with a thermometer."],
                ["Low coolant or airlock",
                 "—",
                 "The sensor reads air, not coolant, and reports a cold engine."],
                ["Wrong thermostat fitted previously",
                 "[[L:cat/thermo|Thermostats]]",
                 "An opening temperature that is too low keeps the engine cold permanently."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Watch the coolant temperature on live data from a cold start. It should climb steadily and "
                "stabilise.",
                "Check the heater output — a strong clue that costs nothing.",
                "Compare the sensor reading with an infrared thermometer on the housing.",
                "Check the coolant level and bleed the system before condemning the thermostat.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Ignoring P0128 because the car runs fine. A cold engine runs rich, dilutes the oil and "
                     "wears faster. On a fleet this is one of the highest-return repairs in the catalogue.")),
        ],
        "parts": [
            ("thermo", "Thermostat — usually the answer"),
            ("temp", "Coolant temperature sensor"),
        ],
        "qa": [
            ("Is P0128 serious?",
             "Not urgent, but expensive in fuel, oil dilution and engine wear. It is one of the cheapest real "
             "repairs there is."),
            ("Can a bad sensor cause P0128?",
             "Yes. If the sensor under-reads, the ECU thinks the engine is cold. Compare with a thermometer "
             "before ordering."),
        ],
        "related": ["P0115", "P0117", "P0128"],
    },
    {
        "code": "P0505",
        "name": "Idle control system malfunction",
        "system": "temp",
        "desc": ("P0505 means the ECU cannot hold the idle speed where it wants it. Dirty throttle body, "
                 "stepper motor or a vacuum leak — in the order we check them."),
        "lead": ("P0505 is not a sensor failure, it is a control failure: the ECU tries to hold idle speed and "
                 "cannot. That means air is getting in somewhere it cannot control."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ECU adjusts idle air — through a stepper motor, a solenoid valve or the electronic "
                   "throttle itself — to hold a target speed. When the actual speed stays outside the tolerance "
                   "band despite full correction, it sets P0505.")),
            ("p", ("So the question is always: is the actuator stuck, or is there an uncontrolled air path? A "
                   "vacuum leak defeats the idle control no matter how healthy the actuator is.")),

            ("h2", "What you will notice"),
            ("ul", [
                "An idle that hunts up and down, or sits too high",
                "A stall when coming to a stop or when the air conditioning engages",
                "Rough idle that improves the moment you touch the throttle",
                "A whistle or hiss from the engine bay",
                "Sometimes a high idle only when cold",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Carboned-up throttle body",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "The plate cannot close to the learned position, so idle air is wrong. Clean and relearn."],
                ["Sticking idle stepper motor",
                 "[[L:cat/stepper|Idle stepper motors]]",
                 "Carbon on the pintle stops it moving. Common on cable-throttle engines."],
                ["Vacuum leak",
                 "—",
                 "Uncontrolled air defeats idle control entirely. Smoke test it."],
                ["Failing throttle body (drive-by-wire)",
                 "[[L:cat/throttle|Throttle bodies]]",
                 "The motor or the internal sensor degrades."],
                ["Dirty or failed idle air control valve",
                 "[[L:cat/vsv|Vacuum solenoid valves]]",
                 "On some engines the idle air valve is a separate solenoid."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Command idle speed up and down with a scan tool and watch whether the actuator responds.",
                "Clean the throttle body and the idle passage, then perform the relearn.",
                "Smoke test the intake for leaks.",
                "Check the stepper motor resistance and its movement with the key on.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a stepper motor or throttle body for an idle problem that is a vacuum leak. The new "
                     "part cannot control air that is entering through a split hose. Smoke test before you "
                     "quote, every time.")),
        ],
        "parts": [
            ("stepper", "Idle stepper motor"),
            ("throttle", "Throttle body — clean before replacing"),
            ("vsv", "Idle air control valves on some engines"),
        ],
        "qa": [
            ("Can cleaning fix P0505?",
             "Often, yes — carbon in the throttle bore and the idle passage is the most common cause."),
            ("Why does the idle drop when the AC comes on?",
             "The ECU should raise idle to compensate. If it cannot, it is the same control fault."),
        ],
        "related": ["P0120", "P0122", "P0171"],
    },
]

# ================================================================ G · 车速与 ABS
CODES += [
    {
        "code": "P0500",
        "name": "Vehicle speed sensor A malfunction",
        "system": "abs",
        "desc": ("P0500 means the ECU has lost the vehicle speed signal. Why the speedometer, the ABS and the "
                 "gearbox all complain at once, and where the signal actually comes from."),
        "lead": ("P0500 is a speed signal fault, and on most modern cars that signal comes from a wheel speed "
                 "sensor — the same part that turns on the ABS light."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The vehicle speed signal is used by the engine ECU, the instrument cluster, the ABS and the "
                   "gearbox. On older cars it comes from a dedicated sensor on the gearbox; on newer ones it is "
                   "calculated by the ABS module from the four wheel speed sensors and broadcast on the CAN bus.")),
            ("p", ("That is why P0500 and a C-code often appear together. If the speed signal is calculated from "
                   "the wheels, the fault is usually one wheel speed sensor, not a separate VSS.")),

            ("h2", "What you will notice"),
            ("ul", [
                "The speedometer dead or jumping",
                "The ABS and traction control lights on at the same time",
                "Harsh or late gear changes on automatics",
                "Cruise control refusing to engage",
                "A P0500 with a C0035 or C0040 type code alongside",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failing wheel speed sensor",
                 "[[L:cat/abs|ABS sensors]]",
                 "On CAN-based cars the speed signal comes from the wheels. One bad sensor can set P0500."],
                ["Dedicated VSS on the gearbox",
                 "—",
                 "On older cars there is a separate sensor with its own gear drive."],
                ["Damaged tone ring",
                 "—",
                 "A cracked ring gives a signal the module will not accept."],
                ["Loom damage at the hub",
                 "—",
                 "The sensor wire flexes with suspension movement and eventually breaks inside."],
                ["Instrument cluster fault",
                 "—",
                 "Rare, but a cluster that drops the bus can take the speed signal with it."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four wheel speeds on live data while driving. One that reads zero or jumps is the "
                "answer.",
                "Check the ABS module for stored C-codes first — P0500 is often a symptom, not the root cause.",
                "Inspect the sensor wiring at the hub for chafe and the connector for corrosion.",
                "On older cars with a dedicated VSS, check the drive gear inside the gearbox.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a VSS on a car that calculates speed from the wheel sensors. There is no separate "
                     "VSS to sell. Check whether the car has one before quoting — the ABS module and the "
                     "sensor datasheet tell you.")),
        ],
        "parts": [
            ("abs", "Wheel speed sensor — the usual cause on modern cars"),
        ],
        "qa": [
            ("Can a wheel speed sensor cause P0500?",
             "Yes, on cars where the ABS module calculates the speed signal from the four wheels."),
            ("Why do the ABS and engine lights come on together?",
             "They share the speed signal. One fault in the shared source lights both."),
        ],
        "related": ["C0035", "C0040", "C0045"],
    },
    {
        "code": "C0035",
        "name": "Left front wheel speed sensor circuit",
        "system": "abs",
        "desc": ("C0035 is the left front wheel speed sensor circuit code. ABS light, no speedometer fault, and "
                 "the sensor or the tone ring — how to tell which in ten minutes."),
        "lead": ("C0035 is the most common ABS code in our catalogue, and the left front is the wheel most often "
                 "affected because it takes the most steering and the most water."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("C0035 is a chassis code, not a powertrain code — some cheap scanners will not read it. It "
                   "means the ABS module has lost the left front wheel speed signal, or the signal is outside "
                   "the expected electrical range.")),
            ("p", ("The module compares all four wheels and expects them to agree. A dead left front sensor "
                   "disables ABS, traction control and stability control, and on some cars the speedometer, "
                   "because they all depend on that one signal.")),

            ("h2", "What you will notice"),
            ("ul", [
                "ABS warning light on steady from start-up",
                "Traction control and ESP lights on at the same time",
                "ABS not working in an emergency stop — the wheels can lock",
                "Sometimes a speedometer fault or a gearbox that shifts harshly",
                "On some cars a pull to one side under braking if the signal is erratic rather than dead",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed left front wheel speed sensor",
                 "[[L:cat/abs|ABS sensors]]",
                 "The most common cause. Water ingress and cable fatigue at the hub."],
                ["Damaged or corroded tone ring",
                 "—",
                 "The ring on the hub cracks or rusts. The sensor reads the damage correctly."],
                ["Chafed sensor cable",
                 "—",
                 "The cable flexes with steering and suspension. A break inside the insulation is common."],
                ["Corroded connector at the hub",
                 "—",
                 "Especially in humid or coastal markets. Clean before replacing."],
                ["ABS module fault",
                 "—",
                 "Rare. Confirm by swapping sensors side to side."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four wheel speeds while rolling slowly. Left front reading zero or jumping confirms "
                "the circuit.",
                "Swap the left front and right front sensors and see whether the code moves to C0040. That "
                "settles sensor versus wiring.",
                "Inspect the tone ring through the sensor hole for cracks and rust.",
                "Check the sensor resistance and compare with the other side before ordering.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Fitting a sensor for a cracked tone ring. The new sensor reads the same broken pattern and "
                     "the light stays on. Ask for a photo through the sensor hole — the ring is visible and the "
                     "check takes a minute.")),
        ],
        "parts": [
            ("abs", "Left front ABS sensor — 2,000+ numbers in stock"),
        ],
        "qa": [
            ("What is the difference between C0035 and C0036?",
             "C0035 is a circuit failure. C0036 is a signal that is present but inconsistent."),
            ("Will the ABS still work with a C0035?",
             "No. The system disables itself because it cannot trust one wheel's speed."),
            ("Can I drive with a C0035?",
             "Yes, but with no ABS and usually no traction control. In rain that is a real risk."),
        ],
        "related": ["C0036", "C0040", "C0045", "P0500"],
    },
    {
        "code": "C0036",
        "name": "Left front wheel speed sensor circuit range/performance",
        "system": "abs",
        "desc": ("C0036 means the left front speed signal is present but inconsistent. The tone ring, the "
                 "bearing and the air gap are the suspects — not the sensor."),
        "lead": ("C0036 means the sensor is talking, but the ABS module does not believe it. That is a mechanical "
                 "problem far more often than an electrical one."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The left front signal exists but drops out, jumps, or disagrees with the other wheels. The "
                   "module stores a range/performance code rather than a circuit code because it is receiving "
                   "something it cannot use.")),
            ("p", ("The usual causes are a cracked tone ring, a loose wheel bearing that changes the air gap, or "
                   "metal debris on the sensor tip. Replacing the sensor alone rarely fixes it.")),

            ("h2", "What you will notice"),
            ("ul", [
                "ABS light that comes on intermittently, often after a bump or in the rain",
                "ABS activating at low speed when no wheel is slipping",
                "Traction control cutting in unexpectedly",
                "A pulse through the brake pedal at walking pace",
                "The light clearing by itself after a restart",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Cracked or corroded tone ring",
                 "—",
                 "The number one cause. The ring is part of the hub or the CV joint on most cars."],
                ["Worn wheel bearing",
                 "—",
                 "Play changes the air gap and the signal drops out under load."],
                ["Metal debris on the sensor tip",
                 "—",
                 "Iron filings bridge the gap. Wipe and retest before ordering."],
                ["Sensor air gap or fitment",
                 "[[L:cat/abs|ABS sensors]]",
                 "A sensor fitted without its shim reads weakly and intermittently."],
                ["Chafed cable that only breaks under steering load",
                 "—",
                 "Classic intermittent: the code appears on full lock."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four wheel speeds while turning the steering to full lock slowly. A dropout at the "
                "limit is a cable problem.",
                "Remove the sensor and inspect the tone ring through the hole.",
                "Check the wheel bearing for play.",
                "Wipe the sensor tip and retest before ordering a part.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Selling a sensor for a car with a rusty or cracked tone ring. The signal stays "
                     "inconsistent and the customer returns a good part. C0036 is mechanical until proven "
                     "otherwise — ask for the ring photo.")),
        ],
        "parts": [
            ("abs", "Left front ABS sensor"),
        ],
        "qa": [
            ("Can a wheel bearing cause C0036?",
             "Yes. Bearing play changes the air gap and the signal becomes inconsistent."),
            ("Why does the light come and go?",
             "Because the fault depends on load, steering angle and speed — the signal is bad only in some "
             "conditions."),
        ],
        "related": ["C0035", "C0040", "C0045"],
    },
    {
        "code": "C0040",
        "name": "Right front wheel speed sensor circuit",
        "system": "abs",
        "desc": ("C0040 is the right front wheel speed sensor circuit code. The same diagnosis as the left "
                 "front, with the connector and cable routing that actually fail on this side."),
        "lead": ("C0040 is the right front wheel speed circuit. On most cars the routing differs from the left — "
                 "and so does what fails."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The ABS module has lost the right front wheel speed signal. Because the module needs all "
                   "four, it disables ABS and stability control and may also drop the speed signal that the "
                   "engine ECU and the gearbox use.")),
            ("p", ("The right front sensor cable often runs closer to the exhaust or the engine mount than the "
                   "left, and on right-hand-drive-derived platforms the routing is completely different. Do "
                   "not assume the left front diagnosis applies.")),

            ("h2", "What you will notice"),
            ("ul", [
                "ABS warning light on, with traction control and ESP lights",
                "No ABS function in an emergency stop",
                "Intermittent light after driving over rough ground",
                "Cruise control dropping out",
                "A P0500 appearing if the speed signal is derived from the wheels",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed right front wheel speed sensor",
                 "[[L:cat/abs|ABS sensors]]",
                 "Water ingress at the connector and cable fatigue are the usual failure modes."],
                ["Damaged tone ring",
                 "—",
                 "Especially on cars where the ring is exposed to road debris."],
                ["Corroded connector",
                 "—",
                 "The right side often sits lower and collects more water on some platforms."],
                ["Cable chafe on a mount or the strut",
                 "—",
                 "Look for the rub mark before you look at the sensor."],
                ["Bearing play",
                 "—",
                 "Changes the air gap and produces a range fault first, then a circuit fault."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four speeds on a road test.",
                "Swap the sensors left to right and recheck — code movement identifies the sensor.",
                "Inspect the tone ring and the cable route.",
                "Measure resistance and compare with the opposite side.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Assuming the right side fails the same way as the left. The cable route and the water "
                     "exposure are different. Diagnostic time spent on the actual car beats experience from "
                     "the other side.")),
        ],
        "parts": [
            ("abs", "Right front ABS sensor"),
        ],
        "qa": [
            ("Does C0040 disable all ABS?",
             "Yes. The system needs all four signals to intervene safely."),
            ("Can I replace just one sensor?",
             "Yes, and that is normal. Sensors fail individually unless there is a shared wiring fault."),
        ],
        "related": ["C0035", "C0045", "C0050", "P0500"],
    },
    {
        "code": "C0045",
        "name": "Left rear wheel speed sensor circuit",
        "system": "abs",
        "desc": ("C0045 is the left rear wheel speed sensor circuit code. Rear sensors fail differently — "
                 "routing under the seat, through the wheel arch and past the suspension."),
        "lead": ("C0045 is the left rear wheel speed circuit. Rear sensors last longer than front ones but fail "
                 "in places that are harder to reach — and that changes the labour, not the part."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The left rear wheel speed signal is missing or out of range. The rear sensors live under the "
                   "car, behind the wheel arch liner and through the body. Water, road salt and suspension "
                   "movement are their main enemies.")),
            ("p", ("On many cars the rear sensor reads a ring pressed onto the hub or the driveshaft. On "
                   "independent rear suspension the cable has to flex constantly, which is where the break "
                   "usually happens.")),

            ("h2", "What you will notice"),
            ("ul", [
                "ABS light on with traction control and ESP",
                "The ABS light appearing more often in wet weather",
                "A speedometer fault on cars with a rear-derived speed signal",
                "Harsh gearbox behaviour on some automatics",
                "The light clearing after the car dries out — a classic water ingress sign",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed left rear wheel speed sensor",
                 "[[L:cat/abs|ABS sensors]]",
                 "The most common answer, and the least accessible one on many cars."],
                ["Water ingress at the connector behind the arch liner",
                 "—",
                 "Very common — the connector sits in a puddle on some platforms."],
                ["Cable break at the suspension arm",
                 "—",
                 "Constant flexing fatigues the copper inside the insulation."],
                ["Damaged tone ring on the hub or driveshaft",
                 "—",
                 "Corrosion and debris damage the ring, especially on rear disc brakes."],
                ["Worn hub bearing",
                 "—",
                 "Play changes the air gap."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four speeds on a road test over a rough surface.",
                "Inspect the connector behind the arch liner for water and corrosion.",
                "Look at the cable at the suspension arm for chafe and for a break under the insulation.",
                "Check the ring and the bearing play before ordering a sensor.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Quoting a rear sensor without warning the customer about the labour. On many cars the rear "
                     "hub or the seat base has to come out. Mention it in the quote so the part price is not "
                     "blamed for the bill.")),
        ],
        "parts": [
            ("abs", "Left rear ABS sensor"),
        ],
        "qa": [
            ("Why do rear sensors fail less often than front ones?",
             "They see less water and less steering movement. When they do fail it is usually the connector or "
             "the cable, not the sensor head."),
            ("Can a rear sensor cause a speedometer fault?",
             "Yes on cars that take the speed signal from the rear wheels, which is common on rear-wheel-drive "
             "platforms."),
        ],
        "related": ["C0050", "C0040", "C0035", "P0500"],
    },
    {
        "code": "C0050",
        "name": "Right rear wheel speed sensor circuit",
        "system": "abs",
        "desc": ("C0050 is the right rear wheel speed sensor circuit code. Diagnosis, tone ring checks, and the "
                 "ABS sensor numbers we stock for the wheel that fails on dusty roads."),
        "lead": ("C0050 is the right rear wheel speed circuit. On the pickups and SUVs common in our export "
                 "markets this is the wheel that sees the most dust and the most flex."),
        "body": [
            ("h2", "What the code actually means"),
            ("p", ("The right rear wheel speed signal is missing or invalid. On solid-axle vehicles the sensor "
                   "sits on the axle or the hub and the cable runs along the axle beam — a route that copes "
                   "with more movement than the front.")),
            ("p", ("On our export markets, dust and mud are a bigger factor than salt. Grit works past seals and "
                   "into connectors, and the sensor tip collects debris until the signal dies.")),

            ("h2", "What you will notice"),
            ("ul", [
                "ABS light on, often after driving on unsealed roads",
                "Traction control and stability control disabled",
                "Intermittent ABS operation on rough surfaces",
                "The light going off after the car is washed — a strong dust or mud clue",
                "A speedometer or gearbox fault on cars using this signal",
            ]),

            ("h2", "Our order of checks"),
            ("table", ["Cause", "Our category", "Why it is on the list"], [
                ["Failed right rear wheel speed sensor",
                 "[[L:cat/abs|ABS sensors]]",
                 "The usual answer. Debris damage and cable fatigue."],
                ["Debris on the sensor tip or the ring",
                 "—",
                 "Very common on dusty roads. Clean and retest before ordering."],
                ["Cable break along the axle beam",
                 "—",
                 "The cable is clipped to the beam and the clips break, letting it rub."],
                ["Damaged tone ring",
                 "—",
                 "Stone damage and corrosion."],
                ["Water or mud in the connector",
                 "—",
                 "Clean, dry, grease and retest."],
            ]),

            ("h2", "Test before you buy"),
            ("ol", [
                "Read all four speeds on a rough road — that is where the fault shows.",
                "Remove the sensor and clean the tip and the ring.",
                "Check the cable clips along the axle beam.",
                "Compare resistance with the left rear before ordering.",
            ]),

            ("h2", "The expensive mistake"),
            ("tip", ("Replacing a sensor that only needed cleaning. On dusty roads a wiped tip and a reseated "
                     "connector fixes a real share of these. Ask the customer to clean and retest before you "
                     "ship — it turns a return into a good relationship.")),
        ],
        "parts": [
            ("abs", "Right rear ABS sensor"),
        ],
        "qa": [
            ("Can dust cause a C0050?",
             "Yes. Debris on the sensor tip or the ring changes the signal, and cleaning often restores it."),
            ("Why does the light go off after washing the car?",
             "The water clears debris or restores contact. That is a clear sign the fault is contamination, not "
             "a dead part."),
        ],
        "related": ["C0045", "C0040", "C0035", "P0500"],
    },
]
