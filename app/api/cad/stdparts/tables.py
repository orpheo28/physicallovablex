"""Standard-part dimension tables (C1, CAD_DETAIL_LEVEL=pro). All mm. Pure data: no imports.

Every row is from the cited standard / datasheet. The values were cross-checked against the data tables of
bd_warehouse 0.3.0 (Gumyr, Apache-2.0: bd_warehouse/data/*.csv) — we vendor the numbers, not the library (see
api/cad/stdparts/README.md for the dependency decision). Unit prices are Estimates at ~2,000 pcs, not quotes.
"""

# ISO 261 coarse pitch
PITCH = {"M1.6": 0.35, "M2": 0.4, "M2.5": 0.45, "M3": 0.5, "M4": 0.7, "M5": 0.8}
NOMINAL = {k: float(k[1:]) for k in PITCH}

# ISO 4762 socket head cap screw: dk head Ø, k head height, s hex key
SOCKET_ISO4762 = {"M1.6": (3.14, 1.6, 1.5), "M2": (3.98, 2.0, 1.5), "M2.5": (4.68, 2.5, 2.0), "M3": (5.68, 3.0, 2.5),
                  "M4": (7.22, 4.0, 3.0), "M5": (8.72, 5.0, 4.0)}
# ISO 14583 hexalobular pan head (M1.6: ISO 1580 slotted pan head — ISO 14583 starts at M2): dk, k, drive
PAN_ISO14583 = {"M1.6": (3.2, 1.0, "slot"), "M2": (4.0, 1.6, "T6"), "M2.5": (5.0, 2.1, "T8"), "M3": (5.6, 2.4, "T10"),
                "M4": (8.0, 3.1, "T20"), "M5": (9.5, 3.7, "T25")}
# ISO 14581 hexalobular countersunk (90°) head (M1.6: ISO 7046): dk, k, drive
CSK_ISO14581 = {"M1.6": (3.0, 0.96, "PH0"), "M2": (4.4, 1.2, "T6"), "M2.5": (5.5, 1.5, "T8"), "M3": (6.3, 1.65, "T10"),
                "M4": (9.4, 2.7, "T20"), "M5": (10.4, 2.7, "T25")}
# ISO 4032 hex nut: m height, s across flats
NUT_ISO4032 = {"M1.6": (1.3, 3.2), "M2": (1.6, 4.0), "M2.5": (2.0, 5.0), "M3": (2.4, 5.5), "M4": (3.2, 7.0), "M5": (4.7, 8.0)}
# ISO 7089 plain washer: d1 inner, d2 outer, h
WASHER_ISO7089 = {"M1.6": (1.7, 4.0, 0.35), "M2": (2.2, 5.0, 0.35), "M2.5": (2.7, 6.0, 0.55), "M3": (3.2, 7.0, 0.55),
                  "M4": (4.3, 9.0, 0.9), "M5": (5.3, 10.0, 1.1)}
# ISO 273 clearance holes: fine / medium / coarse
CLEARANCE_ISO273 = {"M1.6": (1.7, 1.8, 2.0), "M2": (2.2, 2.4, 2.6), "M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6),
                    "M4": (4.3, 4.5, 4.8), "M5": (5.3, 5.5, 5.8)}
# ISO 2306 / DIN 336 tap drill (≈ d − P) for a cut metric thread
TAP_DRILL = {"M1.6": 1.25, "M2": 1.6, "M2.5": 2.05, "M3": 2.5, "M4": 3.3, "M5": 4.2}
# Heat-set threaded insert for thermoplastics (McMaster-Carr 94459A "standard" length, tapered knurl):
# s outer Ø, m length, hole Ø (recommended moulded / drilled hole, ≈ small-end Ø), part number
# (M2.5: not in the 94459A table — interpolated between M2 and M3, Estimate)
INSERT_HEATSET = {"M2": (3.6, 4.0, 3.2, "94459A120"), "M2.5": (4.0, 4.0, 3.6, None), "M3": (4.7, 5.7, 4.0, "94459A140"),
                  "M4": (6.3, 8.2, 5.6, "94459A170"), "M5": (7.1, 9.5, 6.4, "94459A180")}
# EJOT DELTA PT self-tapping screw for thermoplastics (EJOT design guide, ABS / PC-ABS): hole = 0.8·d, boss OD = 2·d
PT_HOLE_K, PT_BOSS_K = 0.8, 2.0

# ISO 15 deep-groove ball bearings: d bore, D outer, B width
BEARING_ISO15 = {"608": (8.0, 22.0, 7.0), "625": (5.0, 16.0, 5.0), "688": (8.0, 16.0, 5.0), "6000": (10.0, 26.0, 8.0),
                 "6001": (12.0, 28.0, 8.0), "6200": (10.0, 30.0, 9.0)}
# ISO 2338 parallel dowel pins m6 (d, lengths are free within the standard series)
DOWEL_ISO2338 = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0)
# DIN 68150 fluted wooden dowels: d, common lengths
WOOD_DOWEL_DIN68150 = {6.0: 30.0, 8.0: 35.0, 10.0: 40.0}
# Häfele Minifix 15 cam connector (catalogue): cam housing Ø, drilling depth for 18 mm board, bolt Ø, edge distance
CAM_MINIFIX15 = {"cam_d": 15.0, "cam_depth": 13.5, "bolt_d": 5.0, "bolt_hole": 8.0, "edge": 24.0}
# NdFeB disc magnets (no ISO; common catalogue sizes, N42, NiCuNi plated): d, h
MAGNET_DISC = {(6.0, 2.0), (8.0, 3.0), (10.0, 2.0), (10.0, 3.0), (12.0, 3.0)}
# ISO 1222 camera tripod socket 1/4"-20 UNC: thread Ø, min thread depth; brass insert OD × length (catalogue)
TRIPOD_ISO1222 = {"d": 6.35, "depth": 5.5, "insert_od": 9.5, "insert_len": 7.0}
# Futures-type single-tab fin box (catalogue): length, width, depth; leash plug cup (catalogue)
FIN_BOX = {"length": 118.0, "width": 18.0, "depth": 16.0}
LEASH_PLUG = {"flange_d": 25.0, "cup_d": 18.0, "depth": 19.0, "bar_d": 3.0}

# Unit price estimates (USD, ~2,000 pcs, distributor catalogue order of magnitude) — labelled Estimate everywhere
PRICE = {
    "screw": {"M1.6": 0.020, "M2": 0.020, "M2.5": 0.022, "M3": 0.025, "M4": 0.035, "M5": 0.045},
    "insert": {"M2": 0.06, "M2.5": 0.07, "M3": 0.08, "M4": 0.11, "M5": 0.14},
    "nut": {"M1.6": 0.01, "M2": 0.01, "M2.5": 0.012, "M3": 0.012, "M4": 0.015, "M5": 0.02},
    "washer": {"M1.6": 0.005, "M2": 0.005, "M2.5": 0.006, "M3": 0.006, "M4": 0.008, "M5": 0.01},
    "bearing": {"608": 0.35, "625": 0.30, "688": 0.30, "6000": 0.45, "6001": 0.50, "6200": 0.55},
    "dowel_pin": 0.03, "wood_dowel": 0.01, "cam_lock": 0.18, "wood_screw": 0.03, "magnet": 0.09, "gear": 0.40,
    "tripod_insert": 0.25, "fin_box": 3.5, "leash_plug": 1.2, "gasket": 0.15, "pt_screw": 0.025,
}

# Human table (README / report): (part, standard, key dimensions)
CITATIONS = [
    ("Socket head cap screw M1.6-M5", "ISO 4762", "dk / k / s per SOCKET_ISO4762"),
    ("Pan head screw M2-M5 (M1.6 ISO 1580)", "ISO 14583", "dk / k / hexalobular drive per PAN_ISO14583"),
    ("Countersunk screw M2-M5 (M1.6 ISO 7046)", "ISO 14581", "90° head, dk / k per CSK_ISO14581"),
    ("Hex nut", "ISO 4032", "m / s per NUT_ISO4032"),
    ("Plain washer", "ISO 7089", "d1 / d2 / h per WASHER_ISO7089"),
    ("Clearance hole fine/medium/coarse", "ISO 273", "CLEARANCE_ISO273"),
    ("Tap drill", "ISO 2306 (d − P)", "TAP_DRILL"),
    ("Heat-set insert", "McMaster-Carr 94459A datasheet", "OD / length / hole per INSERT_HEATSET"),
    ("Self-tapping screw boss", "EJOT DELTA PT design guide", "hole 0.8·d, boss OD 2·d"),
    ("Ball bearing 608/625/688/60xx", "ISO 15", "d / D / B per BEARING_ISO15"),
    ("Dowel pin", "ISO 2338 m6", "d series"),
    ("Wood dowel", "DIN 68150", "8 × 35 etc."),
    ("Cam connector", "Häfele Minifix 15 catalogue", "Ø15 × 13.5 cam, Ø8 bolt hole, 24 mm edge"),
    ("Tripod socket", "ISO 1222", "1/4\"-20 UNC, 5.5 mm min depth"),
    ("Spur gear", "ISO 53 / ISO 54", "20° pressure angle, addendum 1·m, dedendum 1.25·m"),
]
