// Optional subject-group → student map for the classroom game.
// Public site: Chinese name + class + class number only (no emails).
// Populate from S4/S5/S6 subject-group Excels via scripts/build_groups.py when available.
// Shape: { meta, groups: { "GROUP_CODE": [ { class, no, chi }, ... ] } }
window.GROUPS_DATA = {
  "meta": {
    "school": "世界龍岡學校劉皇發中學",
    "generatedAt": "2026-10-13T11:00:00+08:00",
    "timezone": "Asia/Hong_Kong",
    "groupCount": 0,
    "privacy": "Chinese display name + class + class number only; no emails",
    "note": "Stub — timetable cells currently use class codes (1A–6D). Import S4/S5/S6 group Excels when lessons use group codes."
  },
  "groups": {}
};
