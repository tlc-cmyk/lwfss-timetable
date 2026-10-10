#!/usr/bin/env python3
"""
從校曆表文字提取（calendar-2026-2027.txt）產生 calendar.json / calendar.js。

用法：
  python3 scripts/build_calendar.py [/path/to/calendar-2026-2027.txt]

預設讀取 /workspace/calendar-2026-2027.txt 或專案上層同名檔。
循環日以校曆上的圈號 ①–⑩ 為準；無圈號日期視為無正規上課循環日（假期／活動／考試等）。
"""
from __future__ import annotations

import calendar as cal
import json
import re
import sys
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CIRCLES = {
    "①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
    "⑥": 6, "⑦": 7, "⑧": 8, "⑨": 9, "⑩": 10,
}

# 0-indexed inclusive line ranges carefully scoped per month (no cross-month bleed)
MONTH_BLOCKS = [
    (range(4, 9), 9, 2026),    # Sept
    (range(9, 15), 10, 2026),  # Oct
    (range(16, 22), 11, 2026), # Nov
    (range(22, 28), 12, 2026), # Dec
    (range(28, 34), 1, 2027),  # Jan
    (range(34, 41), 2, 2027),  # Feb
    (range(42, 50), 3, 2027),  # Mar
    (range(50, 56), 4, 2027),  # Apr
    (range(56, 64), 5, 2027),  # May
    (range(64, 72), 6, 2027),  # Jun
    (range(72, 81), 7, 2027),  # Jul
    (range(81, 87), 8, 2027),  # Aug
]

TOK_RE = re.compile(r"([@#Δ△\uf0b3◈◊]*)(\d{1,2})\s*([①②③④⑤⑥⑦⑧⑨⑩])")

EXPECTED_SPOTS = {
    "2026-09-01": None,
    "2026-09-02": 3,
    "2026-09-07": 6,
    "2026-09-11": 10,
    "2026-09-14": 1,
    "2026-09-30": None,
    "2026-10-01": None,
    "2026-10-02": 5,
    "2026-10-09": 10,
    "2026-10-10": None,
    "2026-10-20": 7,
    "2026-11-02": None,  # 統測 # 無圈號
    "2026-11-09": 6,
    "2026-12-14": None,  # 開放日後假期
    "2026-12-15": 2,
    "2027-01-01": None,
    "2027-01-06": 3,
    "2027-02-01": 1,
    "2027-03-02": None,  # 陸運會
    "2027-03-05": 10,
    "2027-03-17": 8,
    "2027-04-05": None,  # 清明
    "2027-04-09": 10,
    "2027-05-13": None,  # 佛誕
    "2027-05-14": 5,
    "2027-06-03": 9,
}


def strip_remarks(line: str) -> str:
    s = line
    s = re.sub(
        r"^(九月|十月|十一月|十二月|一月|二月|三月|四月|五月|六月|七月|八月)\s*",
        "",
        s,
    )
    s = re.sub(
        r"^(SEPT|OCT|NOV|DEC|JAN|FEB|MAR|APR|MAY|JUNE|JULY|AUG)\s*",
        "",
        s,
        flags=re.I,
    )
    for m in re.finditer(r"[\u4e00-\u9fff]", s):
        if m.start() >= 35:
            s = s[: m.start()]
            break
    return s


def parse_cycles(lines: list[str]) -> OrderedDict[str, int]:
    results: OrderedDict[str, int] = OrderedDict()
    for block_range, month, year in MONTH_BLOCKS:
        maxday = cal.monthrange(year, month)[1]
        block_days: dict[str, int] = {}
        for li in block_range:
            if li >= len(lines):
                continue
            part = strip_remarks(lines[li])
            # Drop leading week-number column (e.g. "  1    " / "  14   ")
            part2 = re.sub(r"^\s*\d{1,2}\s{4,}", "  ", part)
            for m in TOK_RE.finditer(part2):
                d = int(m.group(2))
                if d < 1 or d > maxday:
                    continue
                try:
                    dt = date(year, month, d)
                except ValueError:
                    continue
                iso = dt.isoformat()
                if iso not in block_days:
                    block_days[iso] = CIRCLES[m.group(3)]
        for iso, cycle in sorted(block_days.items()):
            results[iso] = cycle
    return results


def build_payload(cycles: OrderedDict[str, int]) -> dict:
    start = date(2026, 9, 1)
    end = date(2027, 8, 31)
    days: dict[str, int | None] = {}
    d = start
    while d <= end:
        iso = d.isoformat()
        days[iso] = cycles.get(iso)
        d += timedelta(days=1)

    return {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "schoolYear": "2026-2027",
            "title": "校曆表(2026-2027)",
            "source": "校曆表-2026-2027.pdf",
            "timezone": "Asia/Hong_Kong",
            "cycleDays": 10,
            "note": "cycle 為校曆圈號①–⑩；null 表示當日無正規循環日課（假期／學校活動／考試日／教師發展日等）。",
            "generatedBy": "scripts/build_calendar.py",
        },
        "days": days,
    }


def spot_check(payload: dict) -> list[str]:
    fails = []
    days = payload["days"]
    for iso, exp in EXPECTED_SPOTS.items():
        got = days.get(iso)
        if got != exp:
            fails.append(f"{iso}: expected {exp}, got {got}")
    return fails


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None:
        for cand in (
            Path("/workspace/calendar-2026-2027.txt"),
            ROOT.parent / "calendar-2026-2027.txt",
            ROOT / "calendar-2026-2027.txt",
        ):
            if cand.is_file():
                src = cand
                break
    if src is None or not src.is_file():
        print("找不到 calendar-2026-2027.txt", file=sys.stderr)
        return 1

    lines = src.read_text(encoding="utf-8").splitlines()
    cycles = parse_cycles(lines)
    payload = build_payload(cycles)
    fails = spot_check(payload)
    if fails:
        print("Spot-check FAILED:", file=sys.stderr)
        for f in fails:
            print(" ", f, file=sys.stderr)
        return 2

    out_json = ROOT / "calendar.json"
    out_js = ROOT / "calendar.js"
    out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    out_js.write_text(
        "window.CALENDAR_DATA = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )

    n_cycle = sum(1 for v in payload["days"].values() if v is not None)
    print(f"Wrote {out_json} and {out_js}")
    print(f"School year {payload['meta']['schoolYear']}: {n_cycle} cycle-mapped days")
    print("Spot-checks OK")
    for iso in ("2026-09-01", "2026-09-02", "2026-10-09", "2026-10-10", "2026-10-20"):
        print(f"  {iso} -> {payload['days'][iso]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
