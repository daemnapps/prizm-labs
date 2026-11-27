/* flow.js — the design copy's "How it works" renderer, lifted UNCHANGED from
   new-workflow-design/builds/atlas/design-copy/parts/40-flows.html (one renderer for every component),
   with these edits only, each marked "AV edit" where it is not obvious: FLOWS comes from window.AV_FLOWS;
   window.avFlowSvg(name) returns the bare picture; outcome exits wrap in rows of three and every exit gets a tail.
   The atlas-view page sets AV_FLOWS and AV_STATES, then calls avFlowSvg and avMark. */

/* ===== DESIGN COPY · "How it works" compiled from a flow block — ONE renderer for every component ===== */
(function () {
  var FLOWS = window.AV_FLOWS || {};
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function wrap(t, w) { var words = t.split(" "), lines = [], cur = ""; words.forEach(function (x) { if ((cur + " " + x).trim().length > w) { lines.push(cur.trim()); cur = x; } else cur += " " + x; }); if (cur.trim()) lines.push(cur.trim()); return lines.slice(0, 4); }
  function flat(groups) {
    var out = [];
    (groups || []).forEach(function (g) {
      if (g.stack && (g.items || []).length > 1) {
        var wb = g.items.filter(function (it) { return it.writes_back; })[0];
        out.push({ id: "stack:" + g.group, group: g.group, stack: true, home: g.items[0].home, count: g.items.length, noun: g.stack.noun || "items", names: g.items.map(function (it) { return it.label.split(" — ")[0].split(" (")[0]; }), note: g.stack.note || "", label: g.items.length + " " + (g.stack.noun || "items"), writes_back: wb ? wb.writes_back : null, kind: g.items[0].kind });
      } else (g.items || []).forEach(function (it) { out.push(Object.assign({ group: g.group }, it)); });
    });
    return out;
  }
  function icon(g) { return (g === "Manual" || g === "Views") ? "\uD83D\uDC64 " : (g === "Components" ? "\u29C9 " : "\u2699 "); }
  function svg(FLOW) {
    var LBL = { sources: "INPUTS", engine: "ENGINE", outputs: "OUTPUTS", used_by: "USED BY" };  // constant for every kind — the kind is a header fact, not a column word
    var RAW = FLOW.feeds ? 190 : 0; var X = { sources: 78 + RAW, engine: 262 + RAW, outputs: 446 + RAW, used_by: 630 + RAW }, W = 150, H = 44, pad = 16, GAP = 22, groupBox = {};
    var cols = { sources: flat(FLOW.sources), engine: [FLOW.engine], outputs: FLOW.outputs || [], used_by: flat(FLOW.used_by) };
    function itemH(n) { if (n._h) return n._h; var ln = n.stack ? 2 : wrap(n.label, 30).length; n._h = Math.max(H, 12 + ln * 11); return n._h; }
    function colHeight(list) { var h = 0, g = null; list.forEach(function (n) { if (n.group && n.group !== g) { h += GAP; g = n.group; } h += itemH(n) + pad; }); return Math.max(h - pad, 0); }
    var rows = Math.max(colHeight(cols.sources), colHeight(cols.used_by), colHeight(cols.outputs), H, FLOW.engine.definitions ? H + 34 + 50 + 20 + (FLOW.engine.binding ? 84 : 0) : H);
    var wb = cols.used_by.filter(function (n) { return n.writes_back; });
    var inst = FLOW.instances ? 46 : 0, hasOut = !!FLOW.outcomes;
    var top = 44, base = top + rows + inst + 14, oy = base + 22 + wb.length * 30 + 10;
    var outRows = hasOut ? Math.ceil(FLOW.outcomes.exits.length / 3) : 1, outExtra = (outRows - 1) * 74;
    var height = (hasOut ? oy + 104 + outExtra : base + 22 + wb.length * 30 + 10) + 14 + 16 + ((FLOW.who || []).length + 1) * 14 + 10 + (FLOW.notes ? FLOW.notes.length * 13 : 0) + (FLOW.beside ? FLOW.beside.length * 13 : 0) + 20, pos = {};
    var out = ['<svg viewBox="0 0 ' + (780 + RAW) + ' ' + height + '" role="img" aria-label="How this component works, compiled from its declared flow" style="max-width:100%;height:auto;display:block;font-family:inherit">',
      '<defs><marker id="dc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/><\/marker><\/defs>',
      '<g font-size="10" fill="var(--ink-3,#888)" text-anchor="middle" letter-spacing=".04em"><text x="' + (FLOW.feeds ? (X.sources - 95) : X.sources) + '" y="16">' + esc(LBL.sources) + (FLOW.feeds ? ' \u2014 sources feeding the warehouse' : '') + '<\/text><text x="' + X.engine + '" y="16">' + esc(LBL.engine) + '<\/text><text x="' + X.outputs + '" y="16">' + esc(LBL.outputs) + '<\/text><text x="' + X.used_by + '" y="16">' + esc(LBL.used_by) + "<\/text><\/g>"];
    Object.keys(cols).forEach(function (c) {
      var list = cols[c], total = colHeight(list), y = top + (rows - total) / 2, g = null, x = X[c];
      list.forEach(function (n) {
        if (n.group && n.group !== g) {
          g = n.group; var gItems = list.filter(function (m) { return m.group === g; }), gh = gItems.reduce(function (a, m) { return a + itemH(m) + pad; }, 0) - pad; var gCap = (FLOW.sources.concat(FLOW.used_by || []).filter(function (gg) { return gg.group === g; })[0] || {}).caption;
          var gHome = (list.filter(function (m) { return m.group === g; })[0] || {}).home, isHomeGroup = (g === "Supabase" || g === "Repo" || g === "Drive");
          var gStroke = isHomeGroup ? (gHome === "supabase" ? "var(--violet,#8a6fc4)" : gHome === "repo" ? "var(--warn,#d08a1f)" : "var(--ink-3,#888)") : "var(--ink-3,#888)";
          groupBox[g] = { x1: x - W / 2 - 8, y1: y + GAP - 8, y2: y + GAP - 8 + gh + 16 };
          out.push('<rect x="' + (x - W / 2 - 8) + '" y="' + (y + GAP - 8) + '" width="' + (W + 16) + '" height="' + (gh + 16) + '" rx="8" fill="none" stroke="' + gStroke + '" stroke-dasharray="' + (isHomeGroup ? "" : "3 3") + '" stroke-width="' + (isHomeGroup ? 1.3 : 1) + '" opacity=".85"/>');
          var gIcon = isHomeGroup ? (gHome === "supabase" ? "\uD83D\uDDC4 " : gHome === "repo" ? "\uD83D\uDCC1 " : "") : icon(g);
          out.push('<text x="' + (x - W / 2 - 4) + '" y="' + (y + GAP - 12) + '" font-size="9.5" fill="var(--ink-2,#aaa)" letter-spacing=".04em">' + gIcon + esc(g.toUpperCase()) + (isHomeGroup ? ' <tspan fill="var(--ink-3,#888)">· the warehouse' + (gCap ? ' · ' + esc(gCap) : '') + '<\/tspan>' : "") + "<\/text>");
          y += GAP;
        }
        var nh = itemH(n);
        pos[n.id] = { x: x, y: y + nh / 2, h: nh };
        var eng = c === "engine", comp = n.kind === "component", ret = !!n.returned;
        if (n.stack) {
          out.push('<rect x="' + (x - W / 2 + 8) + '" y="' + (y - 8) + '" width="' + W + '" height="' + nh + '" rx="6" fill="var(--panel-2,rgba(128,128,128,.12))" stroke="currentColor" opacity=".45"/>');
          out.push('<rect x="' + (x - W / 2 + 4) + '" y="' + (y - 4) + '" width="' + W + '" height="' + nh + '" rx="6" fill="var(--panel-2,rgba(128,128,128,.12))" stroke="currentColor" opacity=".7"/>');
        }
        out.push('<g data-node="' + esc(n.id) + '"><rect x="' + (x - W / 2) + '" y="' + y + '" width="' + W + '" height="' + nh + '" rx="6" fill="' + (eng ? "var(--accent-bg,rgba(80,120,200,.18))" : comp ? "var(--warn-bg,rgba(208,138,31,.12))" : ret ? "none" : "var(--panel-2,rgba(128,128,128,.12))") + '" stroke="currentColor" stroke-width="' + (eng ? 1.6 : 1) + '"' + ((n.legacy || ret || n.proposed) ? ' stroke-dasharray="4 3"' : "") + "/>");
        if (ret) out.push('<text x="' + (x - W / 2 + 4) + '" y="' + (y + nh - 4) + '" font-size="8.5" fill="var(--ink-3,#888)">returned to the caller, not stored<\/text>');
        if (n.stack) {
          out.push('<text x="' + x + '" y="' + (y + 15) + '" font-size="10" font-weight="600" text-anchor="middle" fill="currentColor">' + esc(n.label) + "<\/text>");
          wrap(n.names.join(" \u00b7 "), 30).slice(0, 2).forEach(function (ln, k) { out.push('<text x="' + x + '" y="' + (y + 28 + k * 10) + '" font-size="8" text-anchor="middle" fill="var(--ink-2,#aaa)">' + esc(ln) + "<\/text>"); });
        } else wrap(n.label, 30).forEach(function (ln, k) { out.push('<text x="' + x + '" y="' + (y + 14 + k * 11) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
        if (n.stack) { out.push('<title>' + esc(n.names.join(", ")) + (n.note ? " \u2014 " + esc(n.note) : "") + "<\/title>"); }
        if (n.proposed) out.push('<text x="' + (x - W / 2 + 4) + '" y="' + (y + nh - 4) + '" font-size="8" fill="var(--warn,#d08a1f)">proposed<\/text>');
        if (n.path) out.push('<text x="' + x + '" y="' + (y + nh + 10) + '" font-size="8" text-anchor="middle" fill="var(--ink-3,#888)" font-family="ui-monospace,Menlo,monospace">' + esc(n.path) + "<\/text>");
        if (eng && FLOW.engine.runs_on) out.push('<text x="' + x + '" y="' + (y + nh + 10) + '" font-size="8" text-anchor="middle" fill="var(--ink-3,#888)">runs ' + esc(FLOW.engine.runs_on) + "<\/text>");
        if (n.home && !eng) { var HT = { supabase: "\uD83D\uDDC4 supabase", repo: "\uD83D\uDCC1 repo", drive: "\u2601 drive", dashboard: "\uD83D\uDDA5 dashboard host", mini: "\u2699 mini worker", session: "\u2328 a session", browser: "\uD83C\uDF10 the browser", external: "\u2197 external" };
          out.push('<text x="' + (x + W / 2 - 4) + '" y="' + (y + nh - 4) + '" font-size="8" text-anchor="end" fill="var(--ink-3,#888)">' + esc(HT[n.home] || n.home) + "<\/text>"); }
        if (n.integration) out.push('<text x="' + (x + W / 2 - 4) + '" y="' + (y + nh - 4) + '" font-size="9" text-anchor="end" fill="var(--warn,#d08a1f)">\uD83D\uDD11 ' + esc(n.integration) + "<\/text>");
        if (n.legacy) out.push('<text x="' + (x - W / 2 + 4) + '" y="' + (y + nh - 4) + '" font-size="8.5" fill="var(--ink-3,#888)">legacy path<\/text>');
        out.push("<\/g>");
        y += nh + pad;
      });
    });
    if (FLOW.engine.definitions) {
      var D = FLOW.engine.definitions, e1 = pos[FLOW.engine.id], dy = e1.y + e1.h / 2 + 34, dh = 50;
      pos[D.id] = { x: e1.x, y: dy + dh / 2 };
      out.push('<text x="' + (e1.x - W / 2 - 4) + '" y="' + (dy - 6) + '" font-size="9" fill="var(--ink-2,#aaa)" letter-spacing=".04em">DEFINITIONS \u00b7 what the engine executes<\/text>');
      out.push('<rect x="' + (e1.x - W / 2 - 8) + '" y="' + (e1.y - e1.h / 2 - 8) + '" width="' + (W + 16) + '" height="' + (dy + dh - (e1.y - e1.h / 2) + 16) + '" rx="8" fill="none" stroke="var(--accent,#6b9bd1)" opacity=".6"/>');
      out.push('<rect x="' + (e1.x - W / 2) + '" y="' + dy + '" width="' + W + '" height="' + dh + '" rx="6" fill="var(--warn-bg,rgba(208,138,31,.10))" stroke="currentColor"/>');
      wrap(D.label, 26).slice(0, 3).forEach(function (ln, k) { out.push('<text x="' + e1.x + '" y="' + (dy + 14 + k * 11) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
      out.push('<text x="' + (e1.x + W / 2 - 4) + '" y="' + (dy + dh - 4) + '" font-size="8" text-anchor="end" fill="var(--ink-3,#888)">\uD83D\uDCC1 repo<\/text>');
      // definitions × binding → the engine: both meet at one junction, and one arrow carries the product up
      var jx = e1.x - W / 2 - 16, jy = dy + dh / 2 + (FLOW.engine.binding ? 42 : 0);
      out.push('<line x1="' + (e1.x - W / 2) + '" y1="' + (dy + dh / 2) + '" x2="' + jx + '" y2="' + (dy + dh / 2) + '" stroke="currentColor" stroke-width="1" opacity=".7"/>');
      out.push('<circle cx="' + jx + '" cy="' + jy + '" r="7" fill="var(--panel,#222)" stroke="currentColor"/><text x="' + jx + '" y="' + (jy + 3.5) + '" font-size="10" text-anchor="middle" fill="currentColor">\u00d7<\/text>');
      out.push('<path d="M' + jx + ',' + (jy - 7) + ' L' + jx + ',' + e1.y + ' L' + (e1.x - W / 2 - 2) + ',' + e1.y + '" fill="none" stroke="currentColor" stroke-width="1.2" opacity=".8" marker-end="url(#dc-arrow)"/>');
      out.push('<text x="' + (jx - 6) + '" y="' + ((jy + e1.y) / 2) + '" font-size="8.5" text-anchor="end" fill="var(--ink-2,#aaa)">definitions \u00d7 binding<\/text><text x="' + (jx - 6) + '" y="' + ((jy + e1.y) / 2 + 11) + '" font-size="8.5" text-anchor="end" fill="var(--ink-2,#aaa)">= the run\u2019s query<\/text>');
      if (FLOW.engine.binding) {
        var B = FLOW.engine.binding, by = dy + dh + 16 + 22, bh = 46; jy = dy + dh + 19;
        pos[B.id] = { x: e1.x, y: by + bh / 2 };
        out.push('<text x="' + (e1.x - W / 2 - 4) + '" y="' + (by - 6) + '" font-size="9" fill="var(--warn,#d08a1f)" letter-spacing=".04em">BINDING \u00b7 per brand \u00b7 NOT the component\u2019s<\/text>');
        out.push('<rect x="' + (e1.x - W / 2) + '" y="' + by + '" width="' + W + '" height="' + bh + '" rx="6" fill="rgba(208,138,31,.10)" stroke="var(--warn,#d08a1f)"/>');
        wrap(B.label, 26).slice(0, 3).forEach(function (ln, k) { out.push('<text x="' + e1.x + '" y="' + (by + 13 + k * 11) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
        out.push('<text x="' + (e1.x + W / 2 - 4) + '" y="' + (by + bh - 4) + '" font-size="8" text-anchor="end" fill="var(--ink-3,#888)">\uD83D\uDCC1 repo<\/text>');
        out.push('<path d="M' + (e1.x - W / 2) + ',' + (by + bh / 2) + ' L' + jx + ',' + (by + bh / 2) + ' L' + jx + ',' + (jy + 7) + '" fill="none" stroke="var(--warn,#d08a1f)" stroke-width="1" opacity=".9"/>');
      }
    }
    (FLOW.links || []).forEach(function (l) {
      var p = pos[l[0]], q = pos[l[1]]; if (!p || !q) return;
      if (Math.abs(p.x - q.x) < 5) {
        var bx = p.x + W / 2 + 22;
        out.push('<path d="M' + (p.x + W / 2) + ',' + p.y + ' C' + bx + ',' + p.y + ' ' + bx + ',' + q.y + ' ' + (q.x + W / 2 + 2) + ',' + q.y + '" fill="none" stroke="var(--warn,#d08a1f)" stroke-width="1.1" marker-end="url(#dc-arrow)" opacity=".9"/>');
        out.push('<text x="' + (bx + 4) + '" y="' + ((p.y + q.y) / 2 + 3) + '" font-size="8.5" fill="var(--warn,#d08a1f)">' + esc(l[2] || "") + "<\/text>");
      } else {
        out.push('<line x1="' + (p.x + W / 2) + '" y1="' + p.y + '" x2="' + (q.x - W / 2 - 2) + '" y2="' + q.y + '" stroke="var(--warn,#d08a1f)" stroke-width="1.1" marker-end="url(#dc-arrow)"/>');
        out.push('<text x="' + ((p.x + q.x) / 2) + '" y="' + ((p.y + q.y) / 2 - 4) + '" font-size="8.5" text-anchor="middle" fill="var(--warn,#d08a1f)">' + esc(l[2] || "") + "<\/text>");
      }
    });
    if (FLOW.feeds) {
      var fN = FLOW.feeds.length, fh = 34, fpad = 12, ftot = fN * (fh + fpad) - fpad, fy = top + (rows - ftot) / 2, FW = 150, FX = 90;
      FLOW.feeds.forEach(function (r, i) {
        var yy = fy + i * (fh + fpad), repo = r.home === "repo";
        out.push('<rect x="' + (FX - FW / 2) + '" y="' + yy + '" width="' + FW + '" height="' + fh + '" rx="5" fill="' + (repo ? "rgba(208,138,31,.10)" : "none") + '" stroke="' + (repo ? "var(--warn,#d08a1f)" : "currentColor") + '" opacity=".85"/>');
        wrap(r.label, 28).slice(0, 3).forEach(function (ln, k) { out.push('<text x="' + FX + '" y="' + (yy + 11 + k * 10) + '" font-size="8.3" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
        if (repo) out.push('<text x="' + (FX + FW / 2 - 3) + '" y="' + (yy + fh - 3) + '" font-size="7.5" text-anchor="end" fill="var(--ink-3,#888)">\uD83D\uDCC1 repo<\/text>');
        (r.into || []).forEach(function (t) { var q = pos[t]; if (!q) return; out.push('<line x1="' + (FX + FW / 2) + '" y1="' + (yy + fh / 2) + '" x2="' + (q.x - W / 2 - 2) + '" y2="' + q.y + '" stroke="' + (repo ? "var(--warn,#d08a1f)" : "currentColor") + '" stroke-width="1" opacity="' + (repo ? ".9" : ".5") + '" marker-end="url(#dc-arrow)"/>'); });
      });
    }
    function edge(a, b, dashed) { var p = pos[a], q = pos[b]; if (!p || !q) return; out.push('<line x1="' + (p.x + W / 2) + '" y1="' + p.y + '" x2="' + (q.x - W / 2 - 2) + '" y2="' + q.y + '" stroke="currentColor" stroke-width="1" opacity=".55"' + (dashed ? ' stroke-dasharray="4 3"' : "") + ' marker-end="url(#dc-arrow)"/>'); }
    cols.sources.forEach(function (s) { edge(s.id, FLOW.engine.id, s.kind === "component"); });
    cols.outputs.forEach(function (o) { edge(FLOW.engine.id, o.id, !!o.legacy); cols.used_by.forEach(function (r) { if (!o.legacy) edge(o.id, r.id); }); });
    if (FLOW.instances) {
      var e = pos[FLOW.engine.id], iy = top + rows + 6;
      out.push('<text x="' + (262 - 115) + '" y="' + (iy + 10) + '" font-size="9" fill="var(--ink-2,#aaa)" letter-spacing=".04em">' + esc(FLOW.instances.label.toUpperCase()) + "<\/text>");
      FLOW.instances.items.forEach(function (it, i) { var ix = 262 - 115 + (i % 3) * 78, iy2 = iy + 16 + Math.floor(i / 3) * 16; out.push('<rect x="' + ix + '" y="' + iy2 + '" width="72" height="13" rx="6" fill="none" stroke="var(--ink-3,#888)"/><text x="' + (ix + 36) + '" y="' + (iy2 + 10) + '" font-size="8" text-anchor="middle" fill="currentColor">' + esc(it) + "<\/text>"); });
      out.push('<line x1="' + e.x + '" y1="' + (e.y + H / 2) + '" x2="' + e.x + '" y2="' + iy + '" stroke="currentColor" stroke-width="1" opacity=".4"/>');
    }
    wb.forEach(function (n, i) {
      var p = pos[n.id], e = pos[FLOW.engine.id], yy = base + 22 + i * 30, human = n.group === "Views", rx = 720 + i * 9;
      out.push('<path d="M' + (p.x + W / 2) + ',' + p.y + ' L' + rx + ',' + p.y + ' L' + rx + ',' + yy + ' L' + (e.x + 20 + i * 10) + ',' + yy + ' L' + (e.x + 20 + i * 10) + ',' + (e.y + H / 2 + 2) + '" fill="none" stroke="' + (human ? "var(--warn,#d08a1f)" : "currentColor") + '" stroke-width="1.1"' + (human ? "" : ' stroke-dasharray="4 3"') + ' marker-end="url(#dc-arrow)" opacity=".85"/>');
      out.push('<text x="' + ((p.x + e.x) / 2 + 30) + '" y="' + (yy - 4) + '" font-size="9.5" text-anchor="middle" fill="' + (human ? "var(--warn,#d08a1f)" : "var(--ink-2,#aaa)") + '">' + (human ? "\uD83D\uDC64 " : "\u2699 ") + esc(n.writes_back.who) + " files: " + esc(n.writes_back.events.join(" \u00b7 ")) + "<\/text>");
    });
    var gy;
    if (hasOut) {
      var ex = FLOW.outcomes.exits, e0 = pos[FLOW.engine.id];
      out.push('<text x="16" y="' + (oy + 4) + '" font-size="10" fill="var(--ink-3,#888)" letter-spacing=".04em">OUTCOME<\/text>');
      out.push('<rect x="' + (262 - 140) + '" y="' + (oy + 10) + '" width="280" height="30" rx="6" fill="var(--accent-bg,rgba(80,120,200,.18))" stroke="currentColor" stroke-width="1.2"/>');
      wrap(FLOW.outcomes.fold, 56).forEach(function (ln, k) { out.push('<text x="262" y="' + (oy + 22 + k * 11) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
      out.push('<line x1="' + (e0.x - 40) + '" y1="' + (e0.y + H / 2) + '" x2="' + (e0.x - 40) + '" y2="' + (oy + 8) + '" stroke="currentColor" stroke-width="1" opacity=".55" marker-end="url(#dc-arrow)"/>');
      var xs = [160, 420, 650];  /* AV edit: exits wrap in rows of three, so a flow may declare any number */
      ex.forEach(function (x, i) {
        var cx = xs[i % 3], cy = oy + 72 + Math.floor(i / 3) * 74, tone = x.to === "workflow" ? "var(--ok,#3a9)" : x.to === "sources" ? "var(--warn,#d08a1f)" : "var(--ink-3,#888)";
        out.push('<line x1="' + (262 + ((i % 3) - 1) * 90) + '" y1="' + (oy + 40) + '" x2="' + cx + '" y2="' + (cy - 20) + '" stroke="' + tone + '" stroke-width="1" marker-end="url(#dc-arrow)"/>');
        out.push('<rect x="' + (cx - 95) + '" y="' + (cy - 18) + '" width="190" height="40" rx="6" fill="none" stroke="' + tone + '" stroke-width="1.1"/>');
        wrap(x.label.split(" — ")[0].split(";")[0], 38).forEach(function (ln, k) { out.push('<text x="' + cx + '" y="' + (cy - 5 + k * 11) + '" font-size="8.8" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
        var tail = x.to === "workflow" ? "leaves the component \u21E2 the workflow continues" : x.to === "sources" ? "\u21E0 back to the sources as a new request" : x.to === "stop" ? "it stops here; the records stand" : x.to === "engine" ? "\u21BA held in the engine until a person acts" : ("\u21E2 " + (x.to || ""));  /* AV edit: every declared exit gets its own tail */
        out.push('<text x="' + cx + '" y="' + (cy + 36) + '" font-size="10" text-anchor="middle" fill="' + tone + '">' + esc(tail) + "<\/text>");
      });
      gy = oy + 104 + outExtra;
    } else gy = base + 22 + wb.length * 30 + 10;
    gy += 14;
    out.push('<text x="16" y="' + gy + '" font-size="10" fill="var(--ink-3,#888)" letter-spacing=".04em">WHO CAN CHANGE THIS<\/text>');
    (FLOW.who || []).forEach(function (w, i) { out.push('<text x="30" y="' + (gy + 16 + i * 14) + '" font-size="9.5" fill="currentColor">\uD83D\uDC64 <tspan fill="var(--ink-2,#aaa)">' + esc(w[0]) + ':<\/tspan> ' + esc(w[1]) + "<\/text>"); });
    var ny = gy + 16 + (FLOW.who || []).length * 14 + 6;
    (FLOW.notes || []).forEach(function (t, i) { out.push('<text x="30" y="' + (ny + i * 13) + '" font-size="9.5" fill="var(--ink-2,#aaa)">\u270E ' + esc(t) + "<\/text>"); });
    ny += (FLOW.notes || []).length * 13;
    (FLOW.beside || []).forEach(function (t, i) { out.push('<text x="30" y="' + (ny + i * 13) + '" font-size="9.5" fill="var(--ink-2,#aaa)">\u2ACB beside the plane, not emitted: ' + esc(t) + "<\/text>"); });
    ny += (FLOW.beside || []).length * 13 + 4;
    out.push('<text x="30" y="' + ny + '" font-size="9" fill="var(--ink-3,#888)">WHERE THINGS LIVE \u2014 the tag in each box\u2019s corner: \uD83D\uDDC4 supabase (the warehouse) \u00b7 \uD83D\uDCC1 repo (git: components, brands, platform/data) \u00b7 \u2601 drive \u00b7 \uD83D\uDDA5 dashboard host \u00b7 \u2699 mini worker \u00b7 \u2328 a session \u00b7 \u2197 external<\/text>');
    out.push("<\/svg>");
    return out.join("");
  }
  function refusesTable(FLOW) {
    return '<table style="font-size:11px;border-collapse:collapse;margin:6px 0"><tr><th style="text-align:left;border:1px solid var(--line,#444);padding:2px 6px">refuses<\/th><th style="text-align:left;border:1px solid var(--line,#444);padding:2px 6px">meaning<\/th><\/tr>'
      + FLOW.refuses.map(function (r) { return "<tr><td style='border:1px solid var(--line,#444);padding:2px 6px'><code>" + esc(r.code) + "<\/code>" + (r.proposed ? ' <span class="pill p-warn">proposed<\/span>' : "") + "<\/td><td style='border:1px solid var(--line,#444);padding:2px 6px'>" + esc(r.means) + "<\/td><\/tr>"; }).join("") + "<\/table>";
  }
  // ---- 3. THE DEPENDENCY MAP: compiled from every component-kind item in every flow block ----
  function relations() {
    var rel = [];
    Object.keys(FLOWS).forEach(function (name) {
      var F = FLOWS[name];
      flat(F.sources).forEach(function (n) { if (n.kind === "component" && n.component) rel.push({ from: name, to: n.component, why: n.why || n.label, kind: "dep" }); });
      flat(F.used_by).forEach(function (n) { if (n.kind === "component" && n.component) rel.push({ from: n.component, to: name, why: n.why || n.label, kind: "dep" }); });
    });
    // mirrored declarations collapse to one edge per (from,to,kind)
    var seen = {}, out = [];
    rel.forEach(function (r) { var k = r.from + ">" + r.to + ":" + r.kind; if (!seen[k]) { seen[k] = 1; out.push(r); } });
    return out;
  }
  window.dcDependencyMapHtml = function (allNames) {
    var rel = relations(), names = allNames.slice();
    var declared = {}; Object.keys(FLOWS).forEach(function (n) { declared[n] = 1; });
    var n = names.length, cx = 360, cy = 200, R = 150, pos = {};
    names.forEach(function (nm, i) { var a = -Math.PI / 2 + i * 2 * Math.PI / n; pos[nm] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) }; });
    var out = ['<svg viewBox="0 0 720 400" role="img" aria-label="Which components depend on which, compiled from their declared flows" style="max-width:100%;height:auto;display:block;font-family:inherit">',
      '<defs><marker id="dc-arrow2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/><\/marker><\/defs>'];
    rel.forEach(function (r) {
      var p = pos[r.from], q = pos[r.to]; if (!p || !q) return;
      var dx = q.x - p.x, dy = q.y - p.y, L = Math.sqrt(dx * dx + dy * dy), ux = dx / L, uy = dy / L, off = -6;
      var x1 = p.x + ux * 40 - uy * off, y1 = p.y + uy * 40 + ux * off, x2 = q.x - ux * 44 - uy * off, y2 = q.y - uy * 44 + ux * off;
      out.push('<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" stroke="currentColor" stroke-width="1.2" marker-end="url(#dc-arrow2)" opacity=".85"><title>' + esc(r.from + " depends on " + r.to + ": " + r.why) + "<\/title><\/line>");
    });
    names.forEach(function (nm) {
      var p = pos[nm], d = declared[nm];
      out.push('<g><rect x="' + (p.x - 40) + '" y="' + (p.y - 12) + '" width="80" height="24" rx="12" fill="' + (d ? "var(--accent-bg,rgba(80,120,200,.18))" : "none") + '" stroke="currentColor" stroke-width="' + (d ? 1.4 : 0.8) + '"' + (d ? "" : ' stroke-dasharray="3 3" opacity=".6"') + '/><text x="' + p.x + '" y="' + (p.y + 4) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(nm) + "<\/text><\/g>");
    });
    out.push('<g font-size="9.5" fill="var(--ink-2,#aaa)"><text x="16" y="386">\u2500\u2500\u25B6 depends on (hover an arrow for why) &nbsp;&nbsp; solid pill = declared \u00b7 dashed pill = not yet declared<\/text><\/g>');
    out.push("<\/svg>");
    return '<div data-design-copy-section="dependency-map" style="margin-top:10px;border:1px dashed #d08a1f;border-radius:6px;padding:8px 10px">'
      + '<div style="font:600 11px ui-monospace,Menlo,monospace;color:#d08a1f;margin-bottom:6px">DESIGN COPY \u00b7 WHO DEPENDS ON WHOM \u2014 compiled from the component-kind items in every declared flow block (' + Object.keys(FLOWS).length + " of " + names.length + " declared)<\/div>"
      + '<h3>Dependency map<\/h3>' + out.join("")
      + '<ul style="padding-left:18px;font-size:11.5px">' + rel.map(function (r) { return "<li><b>" + esc(r.from) + "<\/b> depends on <b>" + esc(r.to) + "<\/b>: " + esc(r.why) + "<\/li>"; }).join("") + "<\/ul><\/div>";
  };

  // ---- the VALUE-CHAIN layout (a flow declares layout: "chain"): the atlas's own columns — sources ·
  // warehouses · resource · views — with the warehouse column split by home so Supabase and the repo, and
  // the traffic between them, are the thing the picture shows. Edges are declared, each with a label.
  function chainSvg(FLOW) {
    var C = FLOW.chain, X = [110, 400, 690, 940], W = [190, 300, 200, 200], BH = 40, PAD = 10, GAP = 24, pos = {}, out = [];
    var HT = { supabase: "🗄 supabase", repo: "📁 repo", drive: "☁ drive", dashboard: "🖥 dashboard host", mini: "⚙ mini worker", session: "⌨ a session", browser: "🌐 the browser", external: "↗ external systems" };
    function wrapN(t, w) { var words = t.split(" "), lines = [], cur = ""; words.forEach(function (x) { if ((cur + " " + x).trim().length > w) { lines.push(cur.trim()); cur = x; } else cur += " " + x; }); if (cur.trim()) lines.push(cur.trim()); return lines; }
    // measure
    var colH = C.columns.map(function (col, ci) { var h = 0; col.groups.forEach(function (g) { h += GAP; g.items.forEach(function (it) { it._lines = wrapN(it.label, Math.floor(W[ci] / 5.6)).slice(0, 3); it._h = Math.max(BH, 14 + it._lines.length * 11); h += it._h + PAD; }); }); return h; });
    var rows = Math.max.apply(null, colH), top = 46, height = top + rows + 60;
    out.push('<svg viewBox="0 0 1060 ' + height + '" role="img" aria-label="The metrics component on the value chain: sources feed the warehouses, the component reads the warehouses and publishes, the views read what it published" style="max-width:100%;height:auto;display:block;font-family:inherit">');
    out.push('<defs><marker id="dc-arrow3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/><\/marker><\/defs>');
    C.columns.forEach(function (col, ci) {
      var x = X[ci], w = W[ci];
      out.push('<text x="' + x + '" y="16" font-size="10" text-anchor="middle" fill="var(--ink-3,#888)" letter-spacing=".04em">' + esc(col.label) + '<\/text><text x="' + x + '" y="28" font-size="9" text-anchor="middle" fill="var(--ink-3,#888)">' + esc(col.sub) + "<\/text>");
      var y = top + (rows - colH[ci]) / 2;
      col.groups.forEach(function (g) {
        var gh = g.items.reduce(function (a, it) { return a + it._h + PAD; }, 0) - PAD;
        out.push('<rect x="' + (x - w / 2 - 8) + '" y="' + (y + GAP - 8) + '" width="' + (w + 16) + '" height="' + (gh + 16) + '" rx="8" fill="none" stroke="' + (g.home === "supabase" ? "var(--violet,#8a6fc4)" : g.home === "repo" ? "var(--warn,#d08a1f)" : "var(--ink-3,#888)") + '" stroke-dasharray="3 3" opacity=".8"/>');
        out.push('<text x="' + (x - w / 2 - 4) + '" y="' + (y + GAP - 12) + '" font-size="9" fill="var(--ink-2,#aaa)" letter-spacing=".04em">' + esc(g.group.toUpperCase()) + ' <tspan fill="var(--ink-3,#888)">· ' + esc(HT[g.home] || g.home) + "<\/tspan><\/text>");
        y += GAP;
        g.items.forEach(function (it) {
          pos[it.id] = { x: x, y: y + it._h / 2, w: w };
          out.push('<rect x="' + (x - w / 2) + '" y="' + y + '" width="' + w + '" height="' + it._h + '" rx="6" fill="' + (it.engine ? "var(--accent-bg,rgba(80,120,200,.18))" : g.home === "supabase" ? "rgba(138,111,196,.12)" : g.home === "repo" ? "rgba(208,138,31,.10)" : "var(--panel-2,rgba(128,128,128,.10))") + '" stroke="currentColor" stroke-width="' + (it.engine ? 1.6 : 1) + '"' + (it.proposed ? ' stroke-dasharray="4 3" opacity=".75"' : "") + "/>");
          if (it.stack) { out.push('<rect x="' + (x - w / 2 + 5) + '" y="' + (y - 5) + '" width="' + w + '" height="' + it._h + '" rx="6" fill="none" stroke="currentColor" opacity=".45"/>'); }
          it._lines.forEach(function (ln, k) { out.push('<text x="' + x + '" y="' + (y + 13 + k * 11) + '" font-size="9" text-anchor="middle" fill="currentColor">' + esc(ln) + "<\/text>"); });
          if (it.proposed) out.push('<text x="' + (x + w / 2 - 4) + '" y="' + (y + it._h - 3) + '" font-size="7.5" text-anchor="end" fill="var(--warn,#d08a1f)">proposed<\/text>');
          y += it._h + PAD;
        });
      });
    });
    C.edges.forEach(function (e) {
      var p = pos[e[0]], q = pos[e[1]]; if (!p || !q) return;
      var dashed = !!e[3], back = e[4] === "back";
      if (back) {
        var yy = top + rows + 26;
        out.push('<path d="M' + p.x + ',' + (p.y + 20) + ' L' + p.x + ',' + yy + ' L' + (q.x + 30) + ',' + yy + ' L' + (q.x + 30) + ',' + (q.y + 22) + '" fill="none" stroke="var(--warn,#d08a1f)" stroke-width="1.1" marker-end="url(#dc-arrow3)" opacity=".85"/>');
        out.push('<text x="' + ((p.x + q.x) / 2) + '" y="' + (yy - 4) + '" font-size="9" text-anchor="middle" fill="var(--warn,#d08a1f)">👤 ' + esc(e[2]) + "<\/text>");
        return;
      }
      var sameCol = Math.abs(p.x - q.x) < 5;
      var x1 = sameCol ? p.x : p.x + p.w / 2, y1 = sameCol ? p.y + 20 : p.y, x2 = sameCol ? q.x : q.x - q.w / 2 - 2, y2 = sameCol ? q.y - 22 : q.y;
      out.push('<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" stroke="currentColor" stroke-width="1" opacity=".55"' + (dashed ? ' stroke-dasharray="4 3"' : "") + ' marker-end="url(#dc-arrow3)"/>');
      var mx = (x1 + x2) / 2, my = (y1 + y2) / 2 - 3;
      out.push('<text x="' + mx + '" y="' + my + '" font-size="8.5" text-anchor="middle" fill="var(--ink-2,#aaa)" style="paint-order:stroke;stroke:var(--bg,#111);stroke-width:3px">' + esc(e[2]) + "<\/text>");
    });
    var ly = height - 12;
    out.push('<text x="16" y="' + ly + '" font-size="9" fill="var(--ink-3,#888)">Columns are the atlas’s value chain. A dashed border around a group is its HOME (🗄 Supabase · 📁 repo · ↗ external · 🖥 dashboard host · ⚙ mini). Dashed boxes are proposed. Labels on arrows say what moves.<\/text>');
    out.push("<\/svg>");
    return out.join("");
  }
  window.avFlowSvg = function (name) { var FLOW = FLOWS[name]; if (!FLOW) return ""; return FLOW.layout === "chain" ? chainSvg(FLOW) : svg(FLOW); };
  window.dcFlowSectionHtml = function (name) {
    var FLOW = FLOWS[name]; if (!FLOW) return "";
    return '<div data-design-copy-section="how-it-works" style="margin-top:10px;border:1px dashed #d08a1f;border-radius:6px;padding:8px 10px">'
      + '<div style="font:600 11px ui-monospace,Menlo,monospace;color:#d08a1f;margin-bottom:6px">DESIGN COPY \u00b7 HOW IT WORKS \u2014 compiled from the flow block in components/' + esc(name) + '/CLAUDE.md (draft); the owner adjusts the picture through Claude<\/div>'
      + '<h3>How it works<\/h3><p style="margin:2px 0 8px;font-size:12.5px"><b>In plain words:<\/b> ' + esc(FLOW.engine.plain) + "<\/p>"
      + (FLOW.layout === "chain" ? chainSvg(FLOW) : svg(FLOW)) + "<\/div>";
  };
  window.dcRefusesHtml = function (name) { var FLOW = FLOWS[name]; return FLOW ? refusesTable(FLOW) : ""; };
})();


/* avMark: colour each drawn node by its worst claim state (conflicts > draft-error > stale), no text. */
window.avMark = function (host, states) {
  var tone = { "conflicts": "var(--crit)", "draft-error": "var(--crit)", "stale": "var(--warn)" };
  Object.keys(states || {}).forEach(function (id) {
    var g = host.querySelector('g[data-node="' + id.replace(/"/g, "") + '"]'); if (!g) return;
    var r = g.querySelector("rect"); if (!r) return;
    r.setAttribute("stroke", tone[states[id]] || "currentColor"); r.setAttribute("stroke-width", "2.4");
    if (states[id] === "stale") r.setAttribute("stroke-dasharray", "5 3");
  });
};
