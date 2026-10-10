#!/usr/bin/env python3
"""
從校曆表文字提取（calendar-2026-2027.txt）產生 calendar.json / calendar.js。

用法：
  python3 scripts/build_calendar.py [/path/to/calendar-2026-2027.txt]

預設讀取 /workspace/calendar-2026-2027.txt 或專案上層同名檔。
循環日以校曆上的圈號 ①–⑩ 為準；無圈號日期視為無正規上課循環日（假期／學校活動／考試日／教師發展日等）。
備註欄事項會解析為 events[YYYY-MM-DD] = ["事項名稱", ...]。
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

MONTH_BLOCKS = [
    (range(4, 9), 9, 2026),
    (range(9, 15), 10, 2026),
    (range(16, 22), 11, 2026),
    (range(22, 28), 12, 2026),
    (range(28, 34), 1, 2027),
    (range(34, 41), 2, 2027),
    (range(42, 50), 3, 2027),
    (range(50, 56), 4, 2027),
    (range(56, 64), 5, 2027),
    (range(64, 72), 6, 2027),
    (range(72, 81), 7, 2027),
    (range(81, 87), 8, 2027),
]

TOK_RE = re.compile(r"([@#Δ△\uf0b3◈◊]*)(\d{1,2})\s*([①②③④⑤⑥⑦⑧⑨⑩])")
REMARK_LINE_RANGE = range(4, 87)

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
    "2026-11-02": None,
    "2026-11-09": 6,
    "2026-12-14": None,
    "2026-12-15": 2,
    "2027-01-01": None,
    "2027-01-06": 3,
    "2027-02-01": 1,
    "2027-03-02": None,
    "2027-03-05": 10,
    "2027-03-17": 8,
    "2027-04-05": None,
    "2027-04-09": 10,
    "2027-05-13": None,
    "2027-05-14": 5,
    "2027-06-03": 9,
}

EXPECTED_EVENTS = {
    "2026-09-01": ["開學禮"],
    "2026-09-04": ["中一迎新營"],
    "2026-09-10": ["敬師日"],
    "2026-10-16": ["家長教師會周年大會"],
    "2026-10-01": ["國慶日", "「關愛月」"],
    "2026-10-05": ["「感恩及身心靈健康周」"],
    "2026-10-09": ["「感恩及身心靈健康周」"],
    "2026-11-05": ["學校旅行"],
    "2026-12-25": ["聖誕節及新年假期"],
    "2027-01-01": ["聖誕節及新年假期"],
    "2027-02-20": ["「閱讀周」", "中一至中五級家長日"],
    "2027-03-03": ["陸運會決賽"],
    "2027-05-13": ["佛誕"],
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


def extract_remark_fragment(line: str) -> str:
    for m in re.finditer(r"[\u4e00-\u9fff「」]", line):
        if m.start() >= 40:
            return line[m.start() :].strip()
    return ""


def year_for_month(month: int) -> int:
    if month >= 9:
        return 2026
    return 2027


def daterange(d0: date, d1: date) -> list[date]:
    if d1 < d0:
        d0, d1 = d1, d0
    out: list[date] = []
    d = d0
    while d <= d1:
        out.append(d)
        d += timedelta(days=1)
    return out


def parse_date_expr(expr: str) -> list[date]:
    expr = expr.strip().replace(" ", "").replace("／", "/")
    expr = re.sub(r"(\d+)/-(\d+)/(\d+)", r"\1-\2/\3", expr)
    dates: list[date] = []

    m_month = re.fullmatch(r"(\d{1,2})月", expr)
    if m_month:
        month = int(m_month.group(1))
        year = year_for_month(month)
        last = cal.monthrange(year, month)[1]
        return [date(year, month, d) for d in range(1, last + 1)]

    parts: list[str] = []
    if "：" in expr or ":" in expr:
        for chunk in re.split(r"[；;]", expr):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "：" in chunk or ":" in chunk:
                chunk = re.split(r"[：:]", chunk, maxsplit=1)[-1].strip()
            parts.append(chunk)
    else:
        parts = [expr]

    expanded: list[str] = []
    for p in parts:
        for sub in re.split(r"或", p):
            sub = sub.strip()
            if sub:
                expanded.append(sub)

    for part in expanded:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{1,2})", part)
        if m:
            d1, m1, d2, m2 = map(int, m.groups())
            y1 = year_for_month(m1)
            y2 = year_for_month(m2)
            if m1 >= 9 and m2 <= 8:
                y2 = y1 + 1
            try:
                dates.extend(daterange(date(y1, m1, d1), date(y2, m2, d2)))
            except ValueError:
                pass
            continue

        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})/(\d{1,2})", part)
        if m:
            a, b, month = map(int, m.groups())
            year = year_for_month(month)
            for day in range(a, b + 1):
                try:
                    dates.append(date(year, month, day))
                except ValueError:
                    pass
            continue

        m = re.fullmatch(r"(\d{1,2}(?:,\d{1,2})+)/(\d{1,2})", part)
        if m:
            days_s, month_s = m.group(1), m.group(2)
            month = int(month_s)
            year = year_for_month(month)
            for day_s in days_s.split(","):
                try:
                    dates.append(date(year, month, int(day_s)))
                except ValueError:
                    pass
            continue

        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", part)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            year = year_for_month(month)
            try:
                dates.append(date(year, month, day))
            except ValueError:
                pass
            continue

    seen: set[date] = set()
    uniq: list[date] = []
    for d in dates:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def clean_event_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"^[@Δ#△\uf0b3◈◊\s]+", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" ，,;；")


def parse_events(lines: list[str]) -> OrderedDict[str, list[str]]:
    fragments: list[str] = []
    for li in REMARK_LINE_RANGE:
        if li >= len(lines):
            continue
        frag = extract_remark_fragment(lines[li])
        if not frag:
            continue
        if "本學年" in frag or frag.startswith("學期測驗") or "註:" in frag:
            continue
        fragments.append(frag)

    joined: list[str] = []
    for frag in fragments:
        if not joined:
            joined.append(frag)
            continue
        prev = joined[-1]
        if prev.endswith(")") or prev.endswith(";") or prev.endswith("；"):
            joined.append(";" + frag)
        else:
            # Mid-event line break (e.g. 後備 + 考試日)
            joined.append(frag)
    blob = "".join(joined)
    # Split comma between events, keep commas inside date exprs like 4,5/1
    blob = re.sub(r"\s*,\s*(?=[@Δ#「\u4e00-\u9fff])", ";", blob)

    events: OrderedDict[str, list[str]] = OrderedDict()
    n = len(blob)
    seg_start = 0
    i = 0

    def advance_seg(pos: int) -> int:
        while pos < n and blob[pos] in ";； \t":
            pos += 1
        return pos

    while i < n:
        ch = blob[i]
        if ch in ";；":
            seg_start = advance_seg(i + 1)
            i += 1
            continue
        if ch != "(":
            i += 1
            continue
        depth = 0
        k = -1
        for p in range(i, n):
            if blob[p] == "(":
                depth += 1
            elif blob[p] == ")":
                depth -= 1
                if depth == 0:
                    k = p
                    break
        if k < 0:
            break
        inner = blob[i + 1 : k]
        if not re.search(r"\d", inner):
            i += 1
            continue
        name = clean_event_name(blob[seg_start:i])
        if name and len(name) <= 80:
            for d in parse_date_expr(inner):
                if d < date(2026, 9, 1) or d > date(2027, 8, 31):
                    continue
                iso = d.isoformat()
                bucket = events.setdefault(iso, [])
                if name not in bucket:
                    bucket.append(name)
        seg_start = advance_seg(k + 1)
        i = k + 1

    return events


def parse_cycles(lines: list[str]) -> OrderedDict[str, int]:
    results: OrderedDict[str, int] = OrderedDict()
    for block_range, month, year in MONTH_BLOCKS:
        maxday = cal.monthrange(year, month)[1]
        block_days: dict[str, int] = {}
        for li in block_range:
            if li >= len(lines):
                continue
            part = strip_remarks(lines[li])
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


def build_payload(
    cycles: OrderedDict[str, int], events: OrderedDict[str, list[str]]
) -> dict:
    start = date(2026, 9, 1)
    end = date(2027, 8, 31)
    days: dict[str, int | None] = {}
    d = start
    while d <= end:
        iso = d.isoformat()
        days[iso] = cycles.get(iso)
        d += timedelta(days=1)

    ev_out = {k: events[k] for k in sorted(events.keys()) if k in days}

    return {
        "meta": {
            "school": "世界龍岡學校劉皇發中學",
            "schoolYear": "2026-2027",
            "title": "校曆表(2026-2027)",
            "source": "校曆表-2026-2027.pdf",
            "timezone": "Asia/Hong_Kong",
            "cycleDays": 10,
            "note": "cycle 為校曆圈號①–⑩；null 表示當日無正規循環日課（假期／學校活動／考試日／教師發展日等）。events 來自備註欄。",
            "generatedBy": "scripts/build_calendar.py",
        },
        "days": days,
        "events": ev_out,
    }


def spot_check(payload: dict) -> list[str]:
    fails = []
    days = payload["days"]
    for iso, exp in EXPECTED_SPOTS.items():
        got = days.get(iso)
        if got != exp:
            fails.append(f"{iso}: expected {exp}, got {got}")
    ev = payload.get("events") or {}
    for iso, need in EXPECTED_EVENTS.items():
        got = ev.get(iso) or []
        for name in need:
            if name not in got:
                fails.append(f"event {iso}: missing {name!r} (got {got})")
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
    events = parse_events(lines)
    payload = build_payload(cycles, events)
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
    n_ev_days = len(payload["events"])
    n_ev = sum(len(v) for v in payload["events"].values())
    print(f"Wrote {out_json} and {out_js}")
    print(f"School year {payload['meta']['schoolYear']}: {n_cycle} cycle-mapped days")
    print(f"Events: {n_ev} on {n_ev_days} dates")
    print("Spot-checks OK")
    for iso in (
        "2026-09-01",
        "2026-10-16",
        "2026-11-05",
        "2027-02-20",
        "2027-03-03",
    ):
        print(
            f"  {iso} -> cycle={payload['days'][iso]} events={payload['events'].get(iso, [])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
