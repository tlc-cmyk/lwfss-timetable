#!/usr/bin/env python3
"""
從當值表文字（duty-roster.txt）產生 duty.json / duty.js。

用法：
  python3 scripts/build_duty.py [/path/to/duty-roster.txt]

預設讀取 /workspace/duty-roster.txt 或專案上層同名檔。
格式：每月「12  CKYI, HCS」→ 曆日 + Teacher1 / Teacher2 ShortName。
圈號（Wingdings PUA）對應循環日 1–10，一併可選儲存。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Wingdings-like PUA circled digits → cycle day 1–10
CIRCLE_PUA = {
    "\uf06a": 1,  # 
    "\uf06b": 2,  # 
    "\uf06c": 3,  # 
    "\uf06d": 4,  # 
    "\uf06e": 5,  # 
    "\uf06f": 6,  # 
    "\uf070": 7,  # 
    "\uf071": 8,  # 
    "\uf072": 9,  # 
    "\uf073": 10, # 
}

MONTHS = {
    "September": (2026, 9),
    "October": (2026, 10),
    "November": (2026, 11),
    "December": (2026, 12),
    "January": (2027, 1),
    "February": (2027, 2),
    "March": (2027, 3),
    "April": (2027, 4),
    "May": (2027, 5),
    "June": (2027, 6),
    "July": (2027, 7),
}

ENTRY_RE = re.compile(
    r"(\d{1,2})\s+([^\sA-Za-z0-9,]*)\s*([A-Z]{2,5})\s*,\s*([A-Z]{2,5})"
)


def find_source(arg: str | None) -> Path:
    candidates = []
    if arg:
        candidates.append(Path(arg))
    candidates.extend(
        [
            Path("/workspace/duty-roster.txt"),
            ROOT.parent / "duty-roster.txt",
            ROOT / "duty-roster.txt",
        ]
    )
    for p in candidates:
        if p.is_file():
            return p
    raise SystemExit("找不到 duty-roster.txt")


def load_teacher_index() -> dict[str, dict]:
    data_path = ROOT / "data.json"
    if not data_path.is_file():
        return {}
    data = json.loads(data_path.read_text(encoding="utf-8"))
    out = {}
    for t in data.get("teachers") or []:
        code = (t.get("code") or "").upper()
        if code:
            out[code] = {"chi": t.get("chi") or "", "eng": t.get("eng") or ""}
    return out


def parse_circle(raw: str) -> int | None:
    if not raw:
        return None
    for ch in raw:
        if ch in CIRCLE_PUA:
            return CIRCLE_PUA[ch]
    return None


def resolve_teacher(code: str, teachers: dict[str, dict]) -> dict:
    code = code.upper()
    info = teachers.get(code) or {}
    return {
        "code": code,
        "chi": info.get("chi") or "",
        "eng": info.get("eng") or "",
    }


def parse_roster(text: str, teachers: dict[str, dict]) -> dict:
    days: dict[str, dict] = {}
    cur = None
    for ln in text.splitlines():
        stripped = ln.strip()
        for name, ym in MONTHS.items():
            if stripped.startswith(name):
                cur = ym
                break
        if not cur:
            continue
        year, month = cur
        for m in ENTRY_RE.finditer(ln):
            day = int(m.group(1))
            cycle = parse_circle(m.group(2))
            t1 = resolve_teacher(m.group(3), teachers)
            t2 = resolve_teacher(m.group(4), teachers)
            ymd = f"{year:04d}-{month:02d}-{day:02d}"
            entry = {
                "teacher1": t1,
                "teacher2": t2,
            }
            if cycle is not None:
                entry["cycleDay"] = cycle
            days[ymd] = entry
    return days


def main() -> None:
    src = find_source(sys.argv[1] if len(sys.argv) > 1 else None)
    teachers = load_teacher_index()
    text = src.read_text(encoding="utf-8")
    days = parse_roster(text, teachers)

    unresolved = sorted(
        {
            t["code"]
            for e in days.values()
            for t in (e["teacher1"], e["teacher2"])
            if not t.get("chi") and t["code"] not in teachers
        }
    )

    payload = {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "title": "Duty Roster (Sep 2026 – July 2027)",
            "source": src.name,
            "pdf": "當值表.pdf",
            "updated": "2026-09-01",
            "timezone": "Asia/Hong_Kong",
            "dutyDayCount": len(days),
            "roles": {
                "teacher1": "校門檢查校服（早／放學）；小息／午膳巡堂 2/F–6/F",
                "teacher2": "巡堂維持秩序（3/F–6/F、G/F、小賣部）；放學校門檢查",
            },
            "note": "Teacher 1／Teacher 2 職責見當值表第 1 頁（Regular／BF／Half-day）。",
            "unresolvedCodes": unresolved,
            "generatedBy": "scripts/build_duty.py",
        },
        "days": dict(sorted(days.items())),
    }

    json_path = ROOT / "duty.json"
    js_path = ROOT / "duty.js"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    js_path.write_text(
        "window.DUTY_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )

    sample = days.get("2026-10-12")
    print(f"source: {src}")
    print(f"duty days: {len(days)}")
    print(f"unresolved codes: {unresolved or '(none)'}")
    print(f"2026-10-12: {sample}")
    print(f"wrote {json_path.name}, {js_path.name}")


if __name__ == "__main__":
    main()
