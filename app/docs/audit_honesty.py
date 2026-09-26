"""Honesty audit helper (W9). `uv run python docs/audit_honesty.py` → walks the fixtures of both demo projects and the
network seed and prints: (1) labelled values with a bad/missing source, (2) bare numbers outside a LabeledValue
(grouped by key), (3) 'measured' values, (4) real-company hits in factory data. Results are interpreted in docs/HONESTY_AUDIT.md."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "api" / "fixtures"
URL, DATE = re.compile(r"https?://"), re.compile(r"20\d\d-\d\d-\d\d")
REAL = ["foxconn", "flex ", "jabil", "shenzhen sunway", "byd", "luxshare", "goertek", "pegatron", "wistron", "apple", "samsung",
        "xiaomi", "huawei", "anker", "ikea", "jlcpcb", "pcbway", "alibaba", "protolabs", "xometry", "fictiv", "hubs"]


def walk(o, path=""):
    if isinstance(o, dict):
        if {"value", "unit", "label"} <= o.keys():
            yield path, "LV", o
            return
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, "NUM", o
    elif isinstance(o, str):
        yield path, "STR", o


def main() -> None:
    for ex in ("desk_lamp", "tracker_card", "network"):
        bad, bare, meas, reals = [], defaultdict(list), [], []
        for f in sorted((FIX / ex).glob("*.json")):
            data = json.loads(f.read_text())
            for p, kind, v in walk(data):
                loc = f"{f.name}:{p}"
                if kind == "LV":
                    s = v["source_or_assumption"]
                    if v["label"] == "sourced" and not (URL.search(s) and DATE.search(s)):
                        bad.append((loc, f"sourced without {'URL' if not URL.search(s) else 'date'}: {s[:90]}"))
                    if v["label"] == "estimate" and not s.strip():
                        bad.append((loc, "estimate without assumption"))
                    if v["label"] == "measured":
                        meas.append((loc, s[:80]))
                elif kind == "NUM":
                    key = re.sub(r"\[\d+\]", "[]", p.split(".")[-1])
                    bare[(f.name, re.sub(r"\[\d+\]", "[]", p))].append(v)
                elif kind == "STR" and ex == "network":
                    low = v.lower()
                    reals += [(loc, r) for r in REAL if r in low]
        print(f"\n=== {ex}: {len(bad)} labelled values with bad source, {len(meas)} measured, {len(reals)} real-name hits")
        for b in bad[:60]:
            print("  BAD", *b)
        for r in reals:
            print("  REAL?", *r)
        if "-v" in sys.argv:
            for (fn, p), vals in sorted(bare.items()):
                print(f"  BARE {fn}:{p} = {vals[:4]}")
        else:
            print(f"  bare numeric paths: {len(bare)} (rerun with -v to list)")
        c = Counter(m[1] for m in meas)
        print("  measured sources:", dict(c.most_common(6)))


main()
