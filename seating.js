/**
 * 座位表 — teacher picks class (1A–6D) or S4–S6 subject group;
 * randomize + drag students onto seats; auto-persist + named layouts in localStorage.
 * Privacy: Chinese names + class + no only (no emails). Depends on students.js / groups.js.
 */
(function (global) {
  'use strict';

  var LS_PREFIX = 'tt_seating_v1:';
  var LS_NAMED_PREFIX = 'tt_seating_named_v1:';
  var saveHintTimer = null;
  var DEFAULT_ROWS = 5;
  var DEFAULT_COLS = 8;

  var mode = 'class'; // 'class' | 'group'
  var rows = DEFAULT_ROWS;
  var cols = DEFAULT_COLS;
  /** @type {(string|null)[]} seat slot -> student key "class|no" */
  var seats = [];
  var roster = []; // { key, class, no, chi }
  var byKey = {};
  var ready = false;
  var opts = { getTeacherCode: function () { return ''; } };

  var drag = null; // { key, from: 'pool'|'seat', seatIndex, el, floatEl }

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function studentKey(s) {
    return String(s.class || '') + '|' + String(s.no || '');
  }

  function parseIntClamp(v, min, max, fallback) {
    var n = parseInt(v, 10);
    if (!isFinite(n)) n = fallback;
    return Math.max(min, Math.min(max, n));
  }

  function teacherCode() {
    var el = $('seatTeacherCode');
    var raw = el ? String(el.value || '').trim() : '';
    if (!raw && typeof opts.getTeacherCode === 'function') {
      raw = String(opts.getTeacherCode() || '').trim();
    }
    return raw.toUpperCase();
  }

  function storageKey() {
    var t = teacherCode();
    var id;
    if (mode === 'group') {
      id = ($('seatGroupSelect') && $('seatGroupSelect').value) || '';
      return LS_PREFIX + 'group:' + id + (t ? ':t:' + t : '');
    }
    id = ($('seatClassSelect') && $('seatClassSelect').value) || '';
    return LS_PREFIX + 'class:' + id + (t ? ':t:' + t : '');
  }

  function namedStoreKey() {
    return storageKey().replace(LS_PREFIX, LS_NAMED_PREFIX);
  }

  function scopeReady() {
    var key = storageKey();
    return !!(key && !key.endsWith('class:') && !key.endsWith('group:'));
  }

  function showSaveHint(msg, isError) {
    var el = $('seatSaveHint');
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('is-error', !!isError);
    if (saveHintTimer) clearTimeout(saveHintTimer);
    if (msg && !isError) {
      saveHintTimer = setTimeout(function () {
        if ($('seatSaveHint') === el && el.textContent === msg) {
          el.textContent = '';
        }
      }, 4000);
    }
  }

  function readNamedStore() {
    if (!scopeReady()) return {};
    try {
      var raw = localStorage.getItem(namedStoreKey());
      if (!raw) return {};
      var data = JSON.parse(raw);
      if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
      var layouts = data.layouts;
      if (!layouts || typeof layouts !== 'object' || Array.isArray(layouts)) return {};
      return layouts;
    } catch (e) {
      return {};
    }
  }

  function writeNamedStore(layouts) {
    if (!scopeReady()) return false;
    try {
      localStorage.setItem(namedStoreKey(), JSON.stringify({
        layouts: layouts || {},
        updated: new Date().toISOString()
      }));
      return true;
    } catch (e) {
      return false;
    }
  }

  function listNamedLayoutNames() {
    var layouts = readNamedStore();
    return Object.keys(layouts).sort(function (a, b) {
      return a.localeCompare(b, 'zh-HK');
    });
  }

  function refreshNamedSelect(preferName) {
    var sel = $('seatNamedSelect');
    if (!sel) return;
    var layouts = readNamedStore();
    var names = Object.keys(layouts).sort(function (a, b) {
      return a.localeCompare(b, 'zh-HK');
    });
    var prev = preferName != null ? preferName : sel.value;
    if (!names.length) {
      sel.innerHTML = '<option value="">（尚未命名儲存）</option>';
      return;
    }
    sel.innerHTML = names.map(function (n) {
      var u = layouts[n] && layouts[n].updated ? layouts[n].updated : '';
      var label = n;
      if (u) {
        try {
          var d = new Date(u);
          if (!isNaN(d.getTime())) {
            label = n + ' · ' + d.toLocaleString('zh-HK', { hour12: false });
          }
        } catch (e) {}
      }
      return '<option value="' + esc(n) + '">' + esc(label) + '</option>';
    }).join('');
    if (prev && names.indexOf(prev) !== -1) sel.value = prev;
    else sel.value = names[0];
  }

  function applyLayoutData(data) {
    if (!data) return false;
    if (data.rows && data.cols) {
      rows = parseIntClamp(data.rows, 1, 12, rows);
      cols = parseIntClamp(data.cols, 1, 12, cols);
      var rowsEl = $('seatRows');
      var colsEl = $('seatCols');
      if (rowsEl) rowsEl.value = String(rows);
      if (colsEl) colsEl.value = String(cols);
    }
    ensureSeatArray();
    var saved = Array.isArray(data.seats) ? data.seats : [];
    var valid = {};
    roster.forEach(function (s) { valid[s.key] = true; });
    var used = {};
    seats = new Array(rows * cols).fill(null);
    for (var i = 0; i < seats.length; i++) {
      var k = saved[i];
      if (k && valid[k] && !used[k]) {
        seats[i] = k;
        used[k] = true;
      }
    }
    return true;
  }

  function saveNamedLayout(name) {
    name = String(name || '').trim();
    if (!name) return { ok: false, reason: 'empty' };
    if (!scopeReady()) return { ok: false, reason: 'scope' };
    ensureSeatArray();
    var layouts = readNamedStore();
    layouts[name] = {
      name: name,
      rows: rows,
      cols: cols,
      seats: seats.slice(),
      mode: mode,
      updated: new Date().toISOString()
    };
    if (!writeNamedStore(layouts)) return { ok: false, reason: 'quota' };
    return { ok: true, name: name };
  }

  function loadNamedLayout(name) {
    name = String(name || '').trim();
    if (!name) return { ok: false, reason: 'empty' };
    var layouts = readNamedStore();
    var data = layouts[name];
    if (!data) return { ok: false, reason: 'missing' };
    buildRoster();
    applyLayoutData(data);
    saveLayout();
    renderMeta();
    renderPool();
    renderGrid();
    refreshNamedSelect(name);
    var nameEl = $('seatLayoutName');
    if (nameEl) nameEl.value = name;
    return { ok: true, name: name };
  }

  function deleteNamedLayout(name) {
    name = String(name || '').trim();
    if (!name) return { ok: false, reason: 'empty' };
    var layouts = readNamedStore();
    if (!layouts[name]) return { ok: false, reason: 'missing' };
    delete layouts[name];
    if (!writeNamedStore(layouts)) return { ok: false, reason: 'quota' };
    refreshNamedSelect('');
    return { ok: true, name: name };
  }

  function explicitSave() {
    if (!scopeReady()) {
      showSaveHint('請先選擇班別或科組。', true);
      return;
    }
    saveLayout();
    var nameEl = $('seatLayoutName');
    var name = nameEl ? String(nameEl.value || '').trim() : '';
    if (name) {
      var res = saveNamedLayout(name);
      if (!res.ok) {
        showSaveHint(res.reason === 'quota' ? '儲存失敗（本機空間不足）。' : '儲存失敗。', true);
        return;
      }
      refreshNamedSelect(name);
      showSaveHint('已儲存「' + name + '」✓');
    } else {
      showSaveHint('已儲存 ✓（自動暫存；可輸入名稱以建立命名佈局）');
      refreshNamedSelect();
    }
  }

  function ensureSeatArray() {
    var n = rows * cols;
    if (seats.length !== n) {
      var next = new Array(n);
      for (var i = 0; i < n; i++) next[i] = (i < seats.length) ? seats[i] : null;
      seats = next;
    }
  }

  function loadStudentsData() {
    var data = global.STUDENTS_DATA || {};
    return {
      meta: data.meta || {},
      students: data.students || []
    };
  }

  function loadGroupsData() {
    var data = global.GROUPS_DATA || {};
    return {
      meta: data.meta || {},
      groups: data.groups || {},
      entries: data.entries || {}
    };
  }

  function fillClassSelect() {
    var sel = $('seatClassSelect');
    if (!sel) return;
    var meta = loadStudentsData().meta;
    var classes = (meta.classes && typeof meta.classes === 'object')
      ? Object.keys(meta.classes)
      : [];
    if (!classes.length) {
      classes = [];
      for (var f = 1; f <= 6; f++) {
        ['A', 'B', 'C', 'D'].forEach(function (l) { classes.push(String(f) + l); });
      }
    }
    classes.sort(function (a, b) {
      var ma = /^(\d+)([A-D])$/i.exec(a) || [];
      var mb = /^(\d+)([A-D])$/i.exec(b) || [];
      var fa = parseInt(ma[1] || '0', 10);
      var fb = parseInt(mb[1] || '0', 10);
      if (fa !== fb) return fa - fb;
      return String(ma[2] || '').localeCompare(String(mb[2] || ''));
    });
    var prev = sel.value;
    sel.innerHTML = classes.map(function (c) {
      var count = meta.classes && meta.classes[c] != null ? '（' + meta.classes[c] + '人）' : '';
      return '<option value="' + esc(c) + '">' + esc(c) + count + '</option>';
    }).join('');
    if (prev && classes.indexOf(prev) !== -1) sel.value = prev;
    else if (classes.length) sel.value = classes[0];
  }

  function fillGroupSelect() {
    var formEl = $('seatGroupForm');
    var sel = $('seatGroupSelect');
    if (!formEl || !sel) return;
    var form = parseInt(formEl.value, 10) || 4;
    var gdata = loadGroupsData();
    var entries = gdata.entries;
    var keys = Object.keys(entries).filter(function (k) {
      return Number(entries[k].form) === form;
    });
    keys.sort(function (a, b) {
      var ea = entries[a];
      var eb = entries[b];
      var sa = String(ea.subject || '');
      var sb = String(eb.subject || '');
      if (sa !== sb) return sa.localeCompare(sb, 'zh-HK');
      var ta = String(ea.teacher || '');
      var tb = String(eb.teacher || '');
      if (ta !== tb) return ta.localeCompare(tb);
      return a.localeCompare(b);
    });
    var prev = sel.value;
    if (!keys.length) {
      sel.innerHTML = '<option value="">（此年級無科組資料）</option>';
      return;
    }
    sel.innerHTML = keys.map(function (k) {
      var e = entries[k];
      var label = (e.teacher || '') + ' · ' + (e.subject || '') +
        (e.group ? '（' + e.group + '）' : '') +
        ' · ' + (e.count != null ? e.count : (gdata.groups[k] || []).length) + '人';
      return '<option value="' + esc(k) + '">' + esc(label) + '</option>';
    }).join('');
    if (prev && keys.indexOf(prev) !== -1) sel.value = prev;
    else sel.value = keys[0];
  }

  function buildRoster() {
    roster = [];
    byKey = {};
    if (mode === 'class') {
      var cls = ($('seatClassSelect') && $('seatClassSelect').value) || '';
      var all = loadStudentsData().students;
      all.filter(function (s) { return s && s.class === cls; })
        .sort(function (a, b) {
          return String(a.no || '').localeCompare(String(b.no || ''), undefined, { numeric: true });
        })
        .forEach(function (s) {
          var item = {
            key: studentKey(s),
            class: s.class,
            no: s.no,
            chi: s.chi || ''
          };
          roster.push(item);
          byKey[item.key] = item;
        });
    } else {
      var gk = ($('seatGroupSelect') && $('seatGroupSelect').value) || '';
      var list = (loadGroupsData().groups[gk]) || [];
      list.forEach(function (s) {
        if (!s) return;
        var item = {
          key: studentKey(s),
          class: s.class,
          no: s.no,
          chi: s.chi || ''
        };
        if (byKey[item.key]) return;
        roster.push(item);
        byKey[item.key] = item;
      });
      roster.sort(function (a, b) {
        if (a.class !== b.class) return String(a.class).localeCompare(String(b.class));
        return String(a.no || '').localeCompare(String(b.no || ''), undefined, { numeric: true });
      });
    }
  }

  function loadLayout() {
    ensureSeatArray();
    var key = storageKey();
    try {
      var raw = localStorage.getItem(key);
      if (!raw) {
        seats = new Array(rows * cols).fill(null);
        return;
      }
      applyLayoutData(JSON.parse(raw));
    } catch (e) {
      seats = new Array(rows * cols).fill(null);
    }
  }

  function saveLayout() {
    ensureSeatArray();
    var key = storageKey();
    if (!key || key.endsWith('class:') || key.endsWith('group:')) return;
    try {
      localStorage.setItem(key, JSON.stringify({
        rows: rows,
        cols: cols,
        seats: seats,
        mode: mode,
        updated: new Date().toISOString()
      }));
    } catch (e) { /* quota / private mode */ }
  }

  function seatedSet() {
    var set = {};
    seats.forEach(function (k) { if (k) set[k] = true; });
    return set;
  }

  function unassigned() {
    var set = seatedSet();
    return roster.filter(function (s) { return !set[s.key]; });
  }

  function chipHtml(s) {
    return (
      '<span class="sc-name">' + esc(s.chi || '—') + '</span>' +
      '<span class="sc-meta">' + esc(s.class) + ' #' + esc(s.no) + '</span>'
    );
  }

  function makeChipEl(s) {
    var el = document.createElement('div');
    el.className = 'seat-chip';
    el.dataset.key = s.key;
    el.setAttribute('draggable', 'false');
    el.innerHTML = chipHtml(s);
    el.title = (s.chi || '') + '（' + s.class + ' #' + s.no + '）';
    bindChipPointer(el);
    return el;
  }

  function renderMeta() {
    var el = $('seatMeta');
    if (!el) return;
    var assigned = seats.filter(Boolean).length;
    var total = roster.length;
    var label;
    if (mode === 'class') {
      label = '班別 ' + (($('seatClassSelect') && $('seatClassSelect').value) || '—');
    } else {
      var gk = ($('seatGroupSelect') && $('seatGroupSelect').value) || '';
      var e = loadGroupsData().entries[gk];
      label = e
        ? ('科組 ' + (e.teacher || '') + ' · S' + e.form + ' · ' + (e.subject || ''))
        : '科組 —';
    }
    var t = teacherCode();
    el.textContent =
      label + ' · 已入座 ' + assigned + '／' + total +
      ' · 座位 ' + rows + '×' + cols + '（' + (rows * cols) + '）' +
      (t ? ' · 儲存鍵教師 ' + t : ' · 共用儲存（無教師代碼）');
    var poolTitle = $('seatPoolTitle');
    if (poolTitle) {
      poolTitle.textContent = '未編排學生（' + unassigned().length + '）';
    }
  }

  function renderPool() {
    var pool = $('seatPool');
    if (!pool) return;
    pool.innerHTML = '';
    unassigned().forEach(function (s) {
      pool.appendChild(makeChipEl(s));
    });
  }

  function renderGrid() {
    var grid = $('seatGrid');
    if (!grid) return;
    ensureSeatArray();
    grid.style.gridTemplateColumns = 'repeat(' + cols + ', auto)';
    grid.innerHTML = '';
    for (var i = 0; i < seats.length; i++) {
      var cell = document.createElement('div');
      cell.className = 'seat-cell' + (seats[i] ? ' has-student' : '');
      cell.dataset.seatIndex = String(i);
      cell.setAttribute('role', 'gridcell');
      var idx = document.createElement('span');
      idx.className = 'seat-idx';
      idx.textContent = String(i + 1);
      cell.appendChild(idx);
      if (seats[i] && byKey[seats[i]]) {
        cell.appendChild(makeChipEl(byKey[seats[i]]));
      }
      bindCellDrop(cell);
      grid.appendChild(cell);
    }
  }

  function renderAll() {
    if (!ready) return;
    buildRoster();
    loadLayout();
    refreshNamedSelect();
    renderMeta();
    renderPool();
    renderGrid();
  }

  function setMode(next) {
    mode = next === 'group' ? 'group' : 'class';
    var btnClass = $('seatModeClass');
    var btnGroup = $('seatModeGroup');
    if (btnClass) btnClass.classList.toggle('active', mode === 'class');
    if (btnGroup) btnGroup.classList.toggle('active', mode === 'group');
    var classRow = $('seatClassRow');
    var groupRow = $('seatGroupRow');
    if (classRow) classRow.hidden = mode !== 'class';
    if (groupRow) groupRow.hidden = mode !== 'group';
    if (mode === 'group') fillGroupSelect();
    renderAll();
  }

  function applyGridSize(optsKeepSeats) {
    rows = parseIntClamp($('seatRows') && $('seatRows').value, 1, 12, DEFAULT_ROWS);
    cols = parseIntClamp($('seatCols') && $('seatCols').value, 1, 12, DEFAULT_COLS);
    if ($('seatRows')) $('seatRows').value = String(rows);
    if ($('seatCols')) $('seatCols').value = String(cols);
    var old = seats.slice();
    seats = new Array(rows * cols).fill(null);
    if (optsKeepSeats !== false) {
      var used = {};
      for (var i = 0; i < seats.length && i < old.length; i++) {
        var k = old[i];
        if (k && byKey[k] && !used[k]) {
          seats[i] = k;
          used[k] = true;
        }
      }
    }
    saveLayout();
    renderMeta();
    renderPool();
    renderGrid();
  }

  function randomize() {
    buildRoster();
    ensureSeatArray();
    var keys = roster.map(function (s) { return s.key; });
    // Fisher–Yates
    for (var i = keys.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = keys[i];
      keys[i] = keys[j];
      keys[j] = tmp;
    }
    seats = new Array(rows * cols).fill(null);
    var n = Math.min(keys.length, seats.length);
    for (var k = 0; k < n; k++) seats[k] = keys[k];
    saveLayout();
    renderMeta();
    renderPool();
    renderGrid();
  }

  function clearSeats() {
    seats = new Array(rows * cols).fill(null);
    saveLayout();
    renderMeta();
    renderPool();
    renderGrid();
  }

  function placeStudent(key, toIndex) {
    if (!byKey[key]) return;
    ensureSeatArray();
    var fromIndex = seats.indexOf(key);
    if (toIndex == null || toIndex < 0 || toIndex >= seats.length) {
      // back to pool
      if (fromIndex !== -1) seats[fromIndex] = null;
      saveLayout();
      renderMeta();
      renderPool();
      renderGrid();
      return;
    }
    var existing = seats[toIndex];
    if (fromIndex === toIndex) return;
    if (fromIndex !== -1) {
      // move / swap within seats
      seats[toIndex] = key;
      seats[fromIndex] = existing || null;
    } else {
      // from pool onto seat (swap occupant back to pool)
      seats[toIndex] = key;
    }
    saveLayout();
    renderMeta();
    renderPool();
    renderGrid();
  }

  function clearDragVisual() {
    document.querySelectorAll('.seat-cell.drop-target').forEach(function (c) {
      c.classList.remove('drop-target');
    });
    if (drag && drag.floatEl && drag.floatEl.parentNode) {
      drag.floatEl.parentNode.removeChild(drag.floatEl);
    }
    if (drag && drag.el) drag.el.classList.remove('is-ghost');
    drag = null;
  }

  function bindChipPointer(el) {
    el.addEventListener('pointerdown', function (ev) {
      if (ev.button != null && ev.button !== 0) return;
      ev.preventDefault();
      var key = el.dataset.key;
      if (!key) return;
      var cell = el.closest('.seat-cell');
      var from = cell ? 'seat' : 'pool';
      var seatIndex = cell ? parseInt(cell.dataset.seatIndex, 10) : -1;

      var rect = el.getBoundingClientRect();
      var floatEl = el.cloneNode(true);
      floatEl.classList.add('drag-float');
      floatEl.style.width = rect.width + 'px';
      floatEl.style.left = rect.left + 'px';
      floatEl.style.top = rect.top + 'px';
      document.body.appendChild(floatEl);
      el.classList.add('is-ghost');

      drag = {
        key: key,
        from: from,
        seatIndex: seatIndex,
        el: el,
        floatEl: floatEl,
        ox: ev.clientX - rect.left,
        oy: ev.clientY - rect.top,
        pointerId: ev.pointerId
      };
      try { el.setPointerCapture(ev.pointerId); } catch (e) {}
    });

    el.addEventListener('pointermove', function (ev) {
      if (!drag || drag.el !== el) return;
      if (drag.floatEl) {
        drag.floatEl.style.left = (ev.clientX - drag.ox) + 'px';
        drag.floatEl.style.top = (ev.clientY - drag.oy) + 'px';
        drag.floatEl.style.visibility = 'hidden';
      }
      var target = document.elementFromPoint(ev.clientX, ev.clientY);
      if (drag.floatEl) drag.floatEl.style.visibility = 'visible';
      document.querySelectorAll('.seat-cell.drop-target, .seat-pool.drop-target').forEach(function (c) {
        c.classList.remove('drop-target');
      });
      var cell = target && target.closest ? target.closest('.seat-cell') : null;
      var pool = target && target.closest ? target.closest('.seat-pool') : null;
      if (cell) cell.classList.add('drop-target');
      else if (pool) pool.classList.add('drop-target');
    });

    el.addEventListener('pointerup', function (ev) {
      if (!drag || drag.el !== el) return;
      if (drag.floatEl) drag.floatEl.style.visibility = 'hidden';
      var target = document.elementFromPoint(ev.clientX, ev.clientY);
      if (drag.floatEl) drag.floatEl.style.visibility = 'visible';
      var cell = target && target.closest ? target.closest('.seat-cell') : null;
      var pool = target && target.closest ? target.closest('.seat-pool') : null;
      var key = drag.key;
      clearDragVisual();
      if (cell && cell.dataset.seatIndex != null) {
        placeStudent(key, parseInt(cell.dataset.seatIndex, 10));
      } else if (pool) {
        placeStudent(key, null);
      }
    });

    el.addEventListener('pointercancel', function () {
      if (!drag || drag.el !== el) return;
      clearDragVisual();
    });
  }

  function bindCellDrop(cell) {
    // pointer handling is on chips; cells just need the drop-target class via move
    cell.addEventListener('dblclick', function () {
      var idx = parseInt(cell.dataset.seatIndex, 10);
      if (seats[idx]) placeStudent(seats[idx], null);
    });
  }

  // Allow dropping onto empty pool area (not only chips)
  function bindPoolDropZone() {
    var pool = $('seatPool');
    if (!pool || pool._seatBound) return;
    pool._seatBound = true;
    // pool highlight cleanup when not over
    pool.addEventListener('pointerup', function () { /* chips handle */ });
  }

  function bindUI() {
    var btnClass = $('seatModeClass');
    var btnGroup = $('seatModeGroup');
    if (btnClass) btnClass.addEventListener('click', function () { setMode('class'); });
    if (btnGroup) btnGroup.addEventListener('click', function () { setMode('group'); });

    var classSel = $('seatClassSelect');
    if (classSel) classSel.addEventListener('change', function () { renderAll(); });

    var formSel = $('seatGroupForm');
    if (formSel) formSel.addEventListener('change', function () {
      fillGroupSelect();
      renderAll();
    });
    var groupSel = $('seatGroupSelect');
    if (groupSel) groupSel.addEventListener('change', function () { renderAll(); });

    var teacherEl = $('seatTeacherCode');
    if (teacherEl) {
      teacherEl.addEventListener('change', function () { renderAll(); });
      teacherEl.addEventListener('blur', function () { renderAll(); });
    }

    var randomBtn = $('seatRandomBtn');
    if (randomBtn) randomBtn.addEventListener('click', randomize);
    var clearBtn = $('seatClearBtn');
    if (clearBtn) clearBtn.addEventListener('click', clearSeats);
    var applyBtn = $('seatApplyGridBtn');
    if (applyBtn) applyBtn.addEventListener('click', function () { applyGridSize(true); });
    var printBtn = $('seatPrintBtn');
    if (printBtn) printBtn.addEventListener('click', function () { window.print(); });

    var saveBtn = $('seatSaveBtn');
    if (saveBtn) saveBtn.addEventListener('click', explicitSave);

    var loadNamedBtn = $('seatLoadNamedBtn');
    if (loadNamedBtn) {
      loadNamedBtn.addEventListener('click', function () {
        var sel = $('seatNamedSelect');
        var name = sel ? sel.value : '';
        var res = loadNamedLayout(name);
        if (!res.ok) {
          if (res.reason === 'empty') showSaveHint('請先選擇要載入的佈局。', true);
          else showSaveHint('找不到該佈局。', true);
          return;
        }
        showSaveHint('已載入「' + res.name + '」✓');
      });
    }

    var deleteNamedBtn = $('seatDeleteNamedBtn');
    if (deleteNamedBtn) {
      deleteNamedBtn.addEventListener('click', function () {
        var sel = $('seatNamedSelect');
        var name = sel ? sel.value : '';
        if (!name) {
          showSaveHint('請先選擇要刪除的佈局。', true);
          return;
        }
        if (!window.confirm('確定刪除命名佈局「' + name + '」？')) return;
        var res = deleteNamedLayout(name);
        if (!res.ok) {
          showSaveHint('刪除失敗。', true);
          return;
        }
        var nameEl = $('seatLayoutName');
        if (nameEl && String(nameEl.value || '').trim() === name) nameEl.value = '';
        showSaveHint('已刪除「' + res.name + '」');
      });
    }

    var namedSel = $('seatNamedSelect');
    if (namedSel) {
      namedSel.addEventListener('change', function () {
        var nameEl = $('seatLayoutName');
        if (nameEl && namedSel.value) nameEl.value = namedSel.value;
      });
    }

    var layoutNameEl = $('seatLayoutName');
    if (layoutNameEl) {
      layoutNameEl.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') {
          ev.preventDefault();
          explicitSave();
        }
      });
    }

    bindPoolDropZone();
  }

  function initSeatingChart(options) {
    if (options && typeof options === 'object') {
      if (typeof options.getTeacherCode === 'function') {
        opts.getTeacherCode = options.getTeacherCode;
      }
    }
    if (!$('panel-seating')) return;
    if (ready) return;
    fillClassSelect();
    fillGroupSelect();
    rows = parseIntClamp($('seatRows') && $('seatRows').value, 1, 12, DEFAULT_ROWS);
    cols = parseIntClamp($('seatCols') && $('seatCols').value, 1, 12, DEFAULT_COLS);
    seats = new Array(rows * cols).fill(null);
    bindUI();
    ready = true;
    // Prefill teacher from host app if empty
    var teacherEl = $('seatTeacherCode');
    if (teacherEl && !teacherEl.value && opts.getTeacherCode()) {
      teacherEl.value = opts.getTeacherCode();
    }
    setMode('class');
  }

  function renderSeatingChart() {
    if (!ready) initSeatingChart(opts);
    else renderAll();
  }

  /**
   * Read a saved 座位表 layout for game.html / other consumers.
   * Tries teacher-keyed storage first, then shared (no teacher).
   * @param {{ mode?: 'class'|'group', id: string, teacherCode?: string }} options
   * @returns {{ key: string, mode: string, id: string, rows: number, cols: number, seats: (string|null)[], teacherCode: string, updated?: string }|null}
   */
  function loadSeatingLayoutFor(options) {
    options = options || {};
    var m = options.mode === 'group' ? 'group' : 'class';
    var id = String(options.id || '').trim();
    var teacher = String(options.teacherCode || '').trim().toUpperCase();
    if (!id) return null;
    var base = LS_PREFIX + m + ':' + id;
    var keys = [];
    if (teacher) keys.push(base + ':t:' + teacher);
    keys.push(base);
    for (var i = 0; i < keys.length; i++) {
      try {
        var raw = localStorage.getItem(keys[i]);
        if (!raw) continue;
        var data = JSON.parse(raw);
        if (!data || !Array.isArray(data.seats)) continue;
        var hasAny = data.seats.some(function (k) { return !!k; });
        if (!hasAny) continue;
        var r = parseIntClamp(data.rows, 1, 12, DEFAULT_ROWS);
        var c = parseIntClamp(data.cols, 1, 12, DEFAULT_COLS);
        return {
          key: keys[i],
          mode: m,
          id: id,
          rows: r,
          cols: c,
          seats: data.seats.slice(),
          teacherCode: teacher || '',
          updated: data.updated || ''
        };
      } catch (e) { /* ignore */ }
    }
    return null;
  }

  global.initSeatingChart = initSeatingChart;
  global.renderSeatingChart = renderSeatingChart;
  global.loadSeatingLayoutFor = loadSeatingLayoutFor;
  global.studentSeatKey = studentKey;
})(typeof window !== 'undefined' ? window : this);
