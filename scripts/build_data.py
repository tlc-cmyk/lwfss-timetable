#!/usr/bin/env python3
"""
從 Google Sheet 匯出（或 Drive read_file JSON 包裝）產生 data.js / data.json。

用法：
  1) 若已有 Drive 工具下載的 JSON 包裝檔：
       python3 scripts/build_data.py /path/to/export.json
  2) 若已有純 CSV（第一行可為 ## MailMergeDB）：
       python3 scripts/build_data.py /path/to/timetable.csv
  3) 預設會嘗試讀取環境變數 TIMETABLE_SRC，否則提示用法。

輸出寫入本專案目錄的 data.js 與 data.json。
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE_ID = "14UPpVtyrCCzM_uExw7hsfKxKk-5F_kzZMy00j1RYFoM"


def simplify_subject(su: str) -> str:
    if not su:
        return ""
    s = su.strip()
    if "AI" in s.upper() or "課程" in s:
        return s
    if s.upper().startswith("ICT-") or re.match(r"^ICT(?:-ICT\d+)?(?:-[A-Z0-9_]+)*$", s, re.I):
        return "ICT"
    if len(s) > 20 and "-" in s:
        parts = s.split("-")
        known = {
            "ICT", "MATH", "CHI", "ENG", "SCI", "PHY", "CHEM", "BIO",
            "HIST", "GEOG", "ECON", "BAFS", "VA", "MUS", "PE", "LS", "CSD", "STEM",
        }
        if parts[0].upper() in known:
            return parts[0]
    return s


def simplify_class(cl: str) -> str:
    if not cl:
        return ""
    parts = [p.strip() for p in cl.split(",") if p.strip()]
    if len(parts) <= 1:
        return cl.strip()
    by_form: dict[str, list[str]] = {}
    for p in parts:
        m = re.match(r"^(\d+)([A-Z]+)$", p, re.I)
        if not m:
            return cl.strip()
        form, letter = m.group(1), m.group(2).upper()
        by_form.setdefault(form, []).append(letter)
    bits = []
    for form in sorted(by_form.keys(), key=lambda x: int(x)):
        letters = sorted(by_form[form])
        expected = [chr(c) for c in range(ord(letters[0]), ord(letters[-1]) + 1)]
        if len(letters) >= 3 and letters == expected:
            bits.append(f"{form}{letters[0]}-{letters[-1]}")
        elif len(letters) == 2:
            bits.append(f"{form}{letters[0]},{form}{letters[1]}")
        else:
            bits.append(",".join(f"{form}{L}" for L in letters))
    return ",".join(bits)


def load_csv_text(path: Path) -> tuple[str, dict]:
    raw = path.read_text(encoding="utf-8")
    meta = {"sourceName": path.name}
    # Drive MCP wrapper JSON
    if raw.lstrip().startswith("{"):
        try:
            wrapper = json.loads(raw)
            if isinstance(wrapper, dict) and "content" in wrapper:
                content = wrapper["content"]
                meta["sourceName"] = wrapper.get("name", path.name)
                meta["sourceFileId"] = wrapper.get("id", FILE_ID)
                if content.startswith("##"):
                    content = content.split("\n", 1)[1]
                return content, meta
        except json.JSONDecodeError:
            pass
    content = raw
    if content.startswith("##"):
        content = content.split("\n", 1)[1]
    return content, meta


def build(content: str, src_meta: dict) -> dict:
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    teachers = []
    for r in rows:
        short = (r.get("ShortName") or "").strip()
        if not short:
            continue
        schedule: dict[str, dict] = {}
        lesson_count = 0
        for d in range(1, 11):
            maxp = 8 if d in (5, 10) else 7
            day: dict[str, dict] = {}
            for p in range(1, maxp + 1):
                cl = (r.get(f"D{d}P{p}Cl") or "").strip()
                su = (r.get(f"D{d}P{p}Su") or "").strip()
                te = (r.get(f"D{d}P{p}Te") or "").strip()
                rm = (r.get(f"D{d}P{p}Rm") or "").strip()
                if cl or su or rm:
                    day[str(p)] = {
                        "class": cl,
                        "classShort": simplify_class(cl),
                        "subject": su,
                        "subjectShort": simplify_subject(su),
                        "teacher": te,
                        "room": rm,
                    }
                    lesson_count += 1
            schedule[str(d)] = day
        teachers.append(
            {
                "code": short,
                "eng": (r.get("EngName") or "").strip(),
                "chi": (r.get("ChiName") or "").strip(),
                "lessonCount": lesson_count,
                "schedule": schedule,
            }
        )
    teachers.sort(key=lambda t: t["code"].upper())
    return {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "sourceFileId": src_meta.get("sourceFileId", FILE_ID),
            "sourceName": src_meta.get("sourceName", "timetablegrok"),
            "teacherCount": len(teachers),
            "days": 10,
            "periodsNormal": 7,
            "periodsExtraDays": [5, 10],
            "generatedFrom": "MailMergeDB CSV export",
        },
        "teachers": teachers,
    }


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TIMETABLE_SRC")
    if not src:
        print(
            "用法: python3 scripts/build_data.py <export.json|csv>\n"
            "或設定 TIMETABLE_SRC。\n"
            f"Sheet fileId: {FILE_ID}",
            file=sys.stderr,
        )
        return 1
    path = Path(src)
    if not path.exists():
        print(f"找不到檔案: {path}", file=sys.stderr)
        return 1
    content, src_meta = load_csv_text(path)
    data = build(content, src_meta)
    (ROOT / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "data.js").write_text(
        "// Auto-generated timetable data — do not edit by hand.\n"
        "// Regenerate with: python3 scripts/build_data.py <export>\n"
        "window.TIMETABLE_DATA = "
        + json.dumps(data, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    print(f"OK: {data['meta']['teacherCount']} teachers -> data.js / data.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
