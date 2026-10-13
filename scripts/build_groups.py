#!/usr/bin/env python3
"""Build groups.js / groups.json from S4/S5/S6 subject-group Excels.

Each subject sheet has one or more blocks:
  Teacher : SHORTNAME
  Group|Subj | CL | No | English Name | | 中文姓名 | ...

Public output: Chinese display name + class + class number only (no emails).

Keys: "{TEACHER}|{form}|{sheetSubject}" e.g. "TLC|4|ICT", "LPL|4|中文"
Also indexes byTeacherForm for lookup when a teacher has multiple subjects.

Usage:
  source /tmp/xlsvenv/bin/activate
  python3 scripts/build_groups.py path/to/s4.xls path/to/s5.xls path/to/s6.xls
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORM_RE = re.compile(r"^[4-6][A-Da-d]$")
SHEET_FORM_RE = re.compile(r"^S([456])\b", re.I)
SKIP_SHEETS = {
    "工作表1",
    "All",
    "數學分布",
    "APL 全部學生",
    "S3升S4 選修科名單",
    "工作紙",
}


def cell_str(v) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip().replace("\xa0", "").strip()


def is_teacher_row(row: list) -> str | None:
    """Return teacher shortname if this row is a Teacher header."""
    if len(row) < 5:
        return None
    label = cell_str(row[3]).replace(" ", "")
    if label.startswith("Teacher:") or label.startswith("Teacher："):
        code = cell_str(row[4]).upper()
        return code or None
    # sometimes Teacher in col0
    label0 = cell_str(row[0]).replace(" ", "")
    if label0.startswith("Teacher:") or label0.startswith("Teacher："):
        code = cell_str(row[1]).upper()
        return code or None
    return None


def is_header_row(row: list) -> bool:
    if len(row) < 3:
        return False
    h = cell_str(row[1])
    return h in ("Group", "Subj") and cell_str(row[2]) == "CL"


def parse_workbook(path: Path, form_hint: int | None = None) -> list[dict]:
    try:
        import xlrd
    except ImportError as e:
        raise SystemExit(
            "xlrd required. Try: source /tmp/xlsvenv/bin/activate"
        ) from e

    wb = xlrd.open_workbook(str(path))
    blocks: list[dict] = []

    for sheet_name in wb.sheet_names():
        if sheet_name in SKIP_SHEETS or "各科分組" in sheet_name:
            continue
        m = SHEET_FORM_RE.match(sheet_name)
        if not m:
            continue
        form = int(m.group(1))
        if form_hint is not None and form != form_hint:
            continue
        sheet_subj = SHEET_FORM_RE.sub("", sheet_name).strip()
        if not sheet_subj:
            continue

        sh = wb.sheet_by_name(sheet_name)
        teacher: str | None = None
        group_name = ""
        students: list[dict] = []

        def flush() -> None:
            nonlocal students, group_name
            if not teacher or not students:
                students = []
                return
            # dedupe by class+no
            seen: set[tuple[str, str]] = set()
            uniq: list[dict] = []
            for s in students:
                k = (s["class"], s["no"])
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(s)
            uniq.sort(key=lambda s: (s["class"], s["no"]))
            key = f"{teacher}|{form}|{sheet_subj}"
            blocks.append(
                {
                    "key": key,
                    "teacher": teacher,
                    "form": form,
                    "subject": sheet_subj,
                    "sheet": sheet_name,
                    "group": group_name or sheet_subj,
                    "students": uniq,
                }
            )
            students = []

        for r in range(sh.nrows):
            row = [sh.cell_value(r, c) for c in range(sh.ncols)]
            tcode = is_teacher_row(row)
            if tcode is not None:
                flush()
                teacher = tcode
                group_name = ""
                continue
            if is_header_row(row):
                continue

            g = cell_str(row[1]) if len(row) > 1 else ""
            cl = cell_str(row[2]) if len(row) > 2 else ""
            no_raw = cell_str(row[3]) if len(row) > 3 else ""
            chi = cell_str(row[6]) if len(row) > 6 else ""
            eng = cell_str(row[4]) if len(row) > 4 else ""

            if not cl or not FORM_RE.match(cl) or not no_raw:
                continue
            try:
                no_i = int(float(no_raw))
            except (TypeError, ValueError):
                continue
            if no_i < 1 or no_i > 99:
                continue
            if not chi:
                if not eng:
                    continue
                chi = eng.title() if eng.isupper() else eng
            if g:
                group_name = g
            students.append(
                {"class": cl.upper(), "no": f"{no_i:02d}", "chi": chi}
            )

        flush()

    return blocks


def build_payload(blocks: list[dict], sources: list[Path]) -> dict:
    groups: dict[str, dict] = {}
    by_tf: dict[str, list[str]] = defaultdict(list)
    student_rows = 0

    for b in blocks:
        key = b["key"]
        if key in groups:
            # merge rare duplicates
            existing = { (s["class"], s["no"]) for s in groups[key]["students"] }
            for s in b["students"]:
                if (s["class"], s["no"]) not in existing:
                    groups[key]["students"].append(s)
                    existing.add((s["class"], s["no"]))
            groups[key]["students"].sort(key=lambda s: (s["class"], s["no"]))
            continue
        groups[key] = {
            "teacher": b["teacher"],
            "form": b["form"],
            "subject": b["subject"],
            "sheet": b["sheet"],
            "group": b["group"],
            "students": b["students"],
        }
        tf = f"{b['teacher']}|{b['form']}"
        if key not in by_tf[tf]:
            by_tf[tf].append(key)
        student_rows += len(b["students"])

    # flat map for game: key -> student list (compat) plus rich entries
    flat = {k: v["students"] for k, v in groups.items()}

    return {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "generatedAt": datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "timezone": "Asia/Hong_Kong",
            "groupCount": len(groups),
            "studentRows": student_rows,
            "privacy": "Chinese display name + class + class number only; no emails",
            "note": (
                "S4/S5/S6 subject-group Excels; key = TEACHER|form|sheetSubject "
                "(e.g. TLC|4|ICT). Classroom prefers teacher+form+subject match "
                "over whole-class register for senior lessons."
            ),
            "sources": [p.name for p in sources],
            "keyFormat": "TEACHER|form|sheetSubject",
        },
        "groups": flat,
        "entries": {
            k: {
                "teacher": v["teacher"],
                "form": v["form"],
                "subject": v["subject"],
                "sheet": v["sheet"],
                "group": v["group"],
                "count": len(v["students"]),
            }
            for k, v in groups.items()
        },
        "byTeacherForm": dict(sorted(by_tf.items())),
    }


def write_outputs(payload: dict) -> None:
    (ROOT / "groups.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "groups.js").write_text(
        "// Auto-generated subject-group roster for 模擬遊戲 — do not edit by hand.\n"
        "// Rebuild: python3 scripts/build_groups.py s4.xls s5.xls s6.xls\n"
        "// Privacy: Chinese names + class only (no emails).\n"
        "// Key: TEACHER|form|sheetSubject (e.g. TLC|4|ICT, LPL|5|中文)\n"
        "window.GROUPS_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python3 scripts/build_groups.py s4.xls [s5.xls s6.xls ...]",
            file=sys.stderr,
        )
        return 1
    sources = [Path(p) for p in sys.argv[1:]]
    missing = [str(p) for p in sources if not p.is_file()]
    if missing:
        print("Missing files:", ", ".join(missing), file=sys.stderr)
        return 1

    blocks: list[dict] = []
    for path in sources:
        # infer form hint from filename order only if sheet names carry S4/S5/S6
        parsed = parse_workbook(path)
        print(f"{path.name}: {len(parsed)} blocks", file=sys.stderr)
        blocks.extend(parsed)

    payload = build_payload(blocks, sources)
    write_outputs(payload)
    m = payload["meta"]
    print(
        f"Wrote groups.js / groups.json — {m['groupCount']} groups, "
        f"{m['studentRows']} student-rows"
    )
    # sample
    for sample in ("TLC|4|ICT", "LPL|4|中文", "KWY|4|MATH", "CCC|4|地理 G1"):
        n = len(payload["groups"].get(sample, []))
        print(f"  sample {sample}: {n} students")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
