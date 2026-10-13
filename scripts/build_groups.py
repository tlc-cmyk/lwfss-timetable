#!/usr/bin/env python3
"""Build groups.js / groups.json from S4/S5/S6 subject-group Excels (optional).

Expected input: Excel files listing students per subject group.
Public output: Chinese display name + class + class number only (no emails).

Usage:
  python3 scripts/build_groups.py [s4.xls s5.xls s6.xls ...]

Until real group files are provided, writes an empty groups map so game.html
can still load groups.js safely.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = [Path(p) for p in sys.argv[1:]]
    groups: dict[str, list] = {}
    note = "Stub — no group Excels parsed"
    if sources:
        missing = [str(p) for p in sources if not p.is_file()]
        if missing:
            print("Missing files:", ", ".join(missing), file=sys.stderr)
            return 1
        # Placeholder: real parsing can be added when group sheet layout is confirmed.
        note = "Files provided but parser not yet configured for sheet layout: " + ", ".join(
            p.name for p in sources
        )
        print(note, file=sys.stderr)

    payload = {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "generatedAt": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds"),
            "timezone": "Asia/Hong_Kong",
            "groupCount": len(groups),
            "privacy": "Chinese display name + class + class number only; no emails",
            "note": note,
            "sources": [p.name for p in sources],
        },
        "groups": groups,
    }
    (ROOT / "groups.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "groups.js").write_text(
        "// Auto-generated optional group roster — do not edit by hand.\n"
        "// Rebuild: python3 scripts/build_groups.py [s4.xls ...]\n"
        "// Privacy: Chinese names + class only (no emails).\n"
        "window.GROUPS_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote groups.js / groups.json ({len(groups)} groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
