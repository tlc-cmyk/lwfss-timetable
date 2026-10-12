#!/usr/bin/env python3
"""Build students.js / students.json from 學生Gmail LIST CSV (class + chi only)."""
from __future__ import annotations

import csv
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = Path(__file__).resolve().parent / "students-gmail-list.csv"


def extract_chi(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    m = re.search(r"[A-Za-z]", name)
    if m:
        chi = name[: m.start()].strip()
        if chi:
            return chi
        return name.strip()
    return name.strip()


def build(csv_path: Path) -> dict:
    students = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            cn = row.get("CLASS(NO)") or ""
            name = row.get("Name") or ""
            m = re.match(r"^(\d+[A-Da-d])(\d+)$", cn)
            if not m:
                continue
            cls = m.group(1).upper()
            no = m.group(2).zfill(2)
            chi = extract_chi(name)
            if not chi:
                continue
            students.append({"class": cls, "no": no, "chi": chi})
    students.sort(key=lambda s: (s["class"], s["no"]))
    by_class = Counter(s["class"] for s in students)
    meta = {
        "school": "世界龍岡學校劉皇發中學",
        "source": "學生Gmail LIST",
        "generatedAt": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "timezone": "Asia/Hong_Kong",
        "studentCount": len(students),
        "classCount": len(by_class),
        "classes": dict(sorted(by_class.items())),
        "fields": ["class", "no", "chi"],
        "privacy": "Chinese display name + class + class number only; no emails",
        "note": "CLASS(NO) like 1A01 → class 1A, no 01; chi taken before first Latin letter in Name",
    }
    return {"meta": meta, "students": students}


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1
    payload = build(csv_path)
    (ROOT / "students.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    js = (
        "// Auto-generated student roster for 模擬遊戲 — do not edit by hand.\n"
        "// Rebuild: python3 scripts/build_students.py\n"
        "// Privacy: Chinese names + class only (no emails).\n"
        "window.STUDENTS_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    (ROOT / "students.js").write_text(js, encoding="utf-8")
    print(f"Wrote {payload['meta']['studentCount']} students → students.js / students.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
