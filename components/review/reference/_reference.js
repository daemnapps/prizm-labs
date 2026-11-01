/* ===========================================================================
 * The review reference block — the fold, the two calls, and the ONE panel
 * keyed on `type`. Card RV-6 (reference panels).
 *
 * ONE COPY, LINKED — the five pages in this folder load this file with a
 * <script src>, so the fold and the panel exist ONCE and a fix is one fix.
 * That is the difference between a reference page and a shipped viewer: the
 * viewer route serves exactly one html file per request and cannot fetch a
 * sibling, which is why every viewer template INLINES its shared bootstrap
 * (CP-8, inline_bootstrap.py). These pages are never promoted and are opened
 * from the repo, so they may link instead of copy — and anyone moving one into
 * `platform/views/viewers/` inlines this file and the css there, by that
 * script's precedent. README.md says so where a copier will read it.
 *
 * THIS IS THE BLOCK RV-10 (PM review integration) LIFTS. Its drawer keys on
 * `type` exactly as `reviewPanelFor()` does below; the card says the block is
 * lifted from here and not rewritten, so every name in it is prefixed
 * `review*` / `REVIEW_*` and nothing here touches a page-global that pm.html
 * already spends (`esc`, `records`, `post`, `fold*`).
 *
 * STATUS IS NEVER STORED, IT IS FOLDED. `reviewFold()` is a PORT of `fold()`
 * in components/review/review_request.py — the one implementation, which a
 * browser cannot import. The port is not a second opinion: the declared test
 * cuts this function out of each shipped page, runs it in node over fixtures,
 * and asserts its answer equals the Python module's answer field for field. A
 * drift fails there, in one line. Nothing on these pages remembers a status
 * between renders — after a write the records are re-read and re-folded.
 *
 * THE MANIFEST IS THE CONTRACT (platform/data/kinds/review.json, `_frozen`).
 * The vocabularies below are MIRRORED from it for validation only; the test
 * cross-checks every one of them against the file. A field beyond the frozen
 * block is a ruling, never a maker's judgment, so nothing here invents one.
 *
 * CREDENTIALS ARE THE SHARED BOOTSTRAP'S — the viewers' one credential module,
 * `platform/views/viewers/_templates/_session-bootstrap.js`, which each page
 * loads before this file. This block calls `API`, `hdrs()`, `creds()`,
 * `authed()` and `dropKey()` and never reads or writes a key itself. When that
 * script did not load, `reviewBootstrapped()` says so by name rather than
 * letting the page fail as a blank box.
 * ======================================================================== */

const REVIEW_KIND = "review";

// The frozen grammar (platform/data/kinds/review.json), mirrored for
// validation only. Cross-checked against the manifest by the declared test.
//
// `seen` (the team, ruled 2026-09-09, card RV-16a) is a reviewer OPENING the
// request: no judgment, no close, and it never satisfies the close rule's "one
// reviewer". THIS LINE IS INLINED BYTE-FOR-BYTE INTO pm.html — it is edited
// HERE and mirrored there, never the other way round (ONE FIX, NOT THREE), and
// new-workflow-design/builds/pm-tool/test_pm_view.py proves the two are equal.
// `url` (the team, ruled 2026-09-10, card RV-34 (url and viewport)) is a thing that
// lives somewhere the platform does not own — a Figma file, a Netlify preview,
// any link — whose `ref` IS the url. It exists so `blob` can keep meaning A
// CAPTURE WE MADE AND HOLD: until this word, a link could only be filed as a
// blob, which is a lie about provenance nothing catches. IT GOES LAST, in the
// order the manifest's `asset` note declares the words, because pm.html's
// lifted copy of the line below is compared against that note.
// `page` (the team, ruled 2026-09-10, card RV-47 (type page)) is a DEPLOYED WEB
// PAGE, FRAMED AT A DECLARED WIDTH, beside `link` — a thing we deliberately do
// NOT embed, a Figma frame whose comments belong in Figma. ONE VALUE AND NO NEW
// WAREHOUSE WORD: both species are warehouse `url`, and the distinction is not
// where the thing lives but whether the panel EMBEDS it. THE SPECIES IS
// DECLARED BY THE FILER, NEVER INFERRED FROM A HOSTNAME, here or anywhere else.
// It goes LAST for the same reason `url` does: the line below is compared with
// the manifest's own list element for element.
const REVIEW_EVENTS = ["request", "verdict", "close", "seen"];
const REVIEW_TYPES = ["text", "md", "image", "video", "doc", "link", "page"];
const REVIEW_WAREHOUSES = ["repo", "drive", "blob", "supabase", "url"];
const REVIEW_VERDICTS = ["approve", "reject", "fix"];
const REVIEW_DECISIONS = ["accepted", "rejected", "parked"];

/* ---------- the two optional fields RV-23 declares ------------------------ */
// `anchors: [{quote, prefix, suffix, comment, row?}]` on the verdict block, and
// `at` on a repo `asset` pointer — the team's rulings A and B of 2026-09-09, the
// second amendment the frozen manifest has taken. MIRRORED FOR VALIDATION ONLY:
// the manifest owns both shapes and the declared test reads them OFF THE
// MANIFEST and compares them with these, so this file agrees with the CONTRACT
// rather than with review_request.py's copy of it.
//
// THIS PAIR IS NOT INLINED INTO pm.html AND MUST NOT BE. The vocabulary block
// above is mirrored there byte-for-byte because the board composes requests and
// verdicts; the anchor shape has NO third copy by the card's own never, and the
// board's panel work is RV-28 (anchors panel)'s.
const REVIEW_ANCHOR_FIELDS = ["quote", "prefix", "suffix", "comment", "row"];
// `row` is the ONE optional key inside an anchor: it names WHICH TEXT the
// anchor lives in — a teardown's fourteen stage outputs are fourteen documents
// under one request — and is omitted when the request has a single text.
const REVIEW_ANCHOR_OPTIONAL = ["row"];
// THE NEIGHBOURHOOD: always present, and allowed to be EMPTY where the quote
// sits at the very start or the very end of a text, because refusing that would
// refuse the first sentence of every document.
const REVIEW_ANCHOR_NEIGHBOURHOOD = ["prefix", "suffix"];
// A COMMIT, never a branch and never a tag — a branch name moves, and a pointer
// that moves is the rot the ref pair exists to stop.
const REVIEW_COMMIT_RE = /^[0-9a-f]{7,40}$/;

// An anchor is a TEXT-QUOTE SELECTOR, NEVER A LINE NUMBER: a repo path carries
// no version and a line number rots the moment somebody edits above it, while a
// quote with its neighbourhood re-finds itself — and when it genuinely cannot,
// the panel says "not found in this version" rather than pointing at the wrong
// line. Resolution order is the exact neighbourhood first, then the quote alone.
//
// NOTHING IS TRIMMED OR NORMALIZED HERE. The selector resolves by MATCHING, so
// the whitespace inside a quote or its neighbourhood is part of the selector; a
// writer that trimmed it would hand back an anchor that no longer resolves
// against the text it was taken from. This refuses, or it passes through.
function reviewAnchors(anchors) {
  if (!Array.isArray(anchors)) {
    throw new ReviewRefused(`anchors must be a LIST of anchors, one per commented passage. Nothing was filed.`);
  }
  anchors.forEach((a, i) => {
    const where = `anchors[${i}]`;
    if (!a || typeof a !== "object" || Array.isArray(a)) {
      throw new ReviewRefused(`${where} must be an anchor {${REVIEW_ANCHOR_FIELDS.join(", ")}}. Nothing was filed.`);
    }
    for (const field of REVIEW_ANCHOR_FIELDS) {
      if (REVIEW_ANCHOR_OPTIONAL.indexOf(field) >= 0 && a[field] == null) continue;
      if (!Object.prototype.hasOwnProperty.call(a, field)) {
        throw new ReviewRefused(`${where}.${field} is missing — an anchor is a text-quote selector {${REVIEW_ANCHOR_FIELDS.join(", ")}} and only \`row\` is optional. Nothing was filed.`);
      }
      if (typeof a[field] !== "string") {
        throw new ReviewRefused(`${where}.${field} must be text. Nothing was filed.`);
      }
      if (REVIEW_ANCHOR_NEIGHBOURHOOD.indexOf(field) < 0 && !a[field].trim()) {
        throw new ReviewRefused(`${where}.${field} is empty — an anchor with no ${field} cannot say what it selected or why. Nothing was filed.`);
      }
    }
    // A key the shape does not name is REFUSED, where a media row's unknown key
    // rides through: a media row's shape is the manifest's to widen, while an
    // anchor's shape IS the ruling — a sixth key is a ruling nobody has made,
    // and this is where that surfaces.
    for (const field of Object.keys(a)) {
      if (REVIEW_ANCHOR_FIELDS.indexOf(field) < 0) {
        throw new ReviewRefused(`${where}.${field} is not part of the anchor shape the manifest declares (${REVIEW_ANCHOR_FIELDS.join(", ")}) — a sixth key on an anchor is a RULING, never a maker's judgment. Nothing was filed.`);
      }
    }
  });
  return anchors;
}

// THE REF PAIR's second half: a path AND the commit it was read at. Only a
// `repo` pointer has one — a Drive file id, a blob url and a supabase pointer
// carry their own version or none, so an `at` beside them names nothing.
function reviewAssetAt(at, warehouse) {
  if (warehouse !== "repo") {
    throw new ReviewRefused(`asset.at is the commit half of a REF PAIR and only a \`repo\` pointer has one — this asset names warehouse ${warehouse || "(none)"}. Nothing was filed.`);
  }
  const value = String(at).trim();
  if (!REVIEW_COMMIT_RE.test(value)) {
    throw new ReviewRefused(`asset.at ${value || "(empty)"} is not a commit (hex, 7-40) — a ref pair is a path AND a commit, and a branch or a tag MOVES, which is the rot the pair exists to stop. Nothing was filed.`);
  }
  return value;
}

// THE WRITE DOOR'S CHECK, in one place. `reviewFileRecord` below calls this on
// every record it is about to POST, whatever composed it — the same seam
// `file_record()` uses in review_request.py, and for the same reason: it is the
// ONE place every record passes through. Anchors ride with a VERDICT, but
// nothing here refuses them on another event; the ruling declared an optional
// field and said where it belongs, and turning "belongs" into "refused
// elsewhere" would be a rule nobody ruled.
function reviewCheckOptionalFields(verdict) {
  const v = verdict && typeof verdict === "object" ? verdict : {};
  if (v.anchors != null) reviewAnchors(v.anchors);
  if (v.asset && typeof v.asset === "object" && v.asset.at != null) {
    reviewAssetAt(v.asset.at, String(v.asset.warehouse == null ? "" : v.asset.warehouse).trim().toLowerCase());
  }
  return verdict;
}

// What this page calls itself on a record it files (`via`), so a record filed
// from a reference page is legible as one on the plane.
const REVIEW_CLIENT = "review-reference/1";

const reviewEsc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// The credential module, present or named absent. A page whose relative path
// to the viewers' bootstrap is wrong would otherwise render an empty box and
// blame the records plane.
const REVIEW_BOOTSTRAP = "platform/views/viewers/_templates/_session-bootstrap.js";

function reviewBootstrapped(el) {
  if (typeof authed === "function" && typeof hdrs === "function"
      && typeof creds === "function" && typeof API !== "undefined") return true;
  if (el) {
    el.innerHTML = `<p class="warn">The shared session bootstrap did not load, so this page
      has no credential module. It links <code>${reviewEsc(REVIEW_BOOTSTRAP)}</code> by a path
      relative to <code>components/review/reference/</code> — open the page from the repo
      (or inline that file, as every viewer template does). Nothing was read and nothing
      was filed.</p>`;
  }
  return false;
}

/* ---------- the two calls, and nothing else ------------------------------ */
// EVERY record for one request, ascending — the kind is served as `history`
// (the manifest's `serve_records`), so this is the event stream the fold folds.
async function reviewRecords(item) {
  const r = await fetch(`${API}/api/reviews?kind=${REVIEW_KIND}&item=${encodeURIComponent(item)}`,
    { headers: hdrs(), ...creds() });
  if (r.status === 401) { const cleared = dropKey(); throw { auth: true, cleared }; }
  if (!r.ok) throw new Error("HTTP " + r.status);
  const j = await r.json().catch(() => ({}));
  return Array.isArray(j.records) ? j.records : [];
}

// ONE record onto the review plane. Same route the module's API door uses
// (components/review/review_request.py `_post`): the server stamps `reviewer`
// from the declared identity, `via` from X-Client and `created` from its own
// clock, so nothing here fabricates any of the three.
async function reviewFileRecord(item, verdict, notes) {
  // THE SHAPE CHECK, BEFORE THE POST (card RV-23). A malformed anchor or a
  // pointer claiming a version it cannot pin is refused BY NAME and NOTHING is
  // sent — the refusal is returned in this function's own `{err}` shape rather
  // than thrown, because every caller below already reads that and none of them
  // wraps this call in a try.
  try { reviewCheckOptionalFields(verdict); }
  catch (e) { return { err: String((e && e.message) || e) }; }
  const r = await fetch(`${API}/api/review`, {
    method: "POST", ...creds(),
    headers: { ...hdrs(), "Content-Type": "application/json", "X-Client": REVIEW_CLIENT },
    body: JSON.stringify({ kind: REVIEW_KIND, item, verdict, notes: notes || "" }),
  });
  if (r.status === 401) return { err: dropKey() ? "Key rejected — get a fresh link." : "Your session was refused." };
  if (!r.ok) return { err: "Save failed: " + ((await r.json().catch(() => ({}))).error || r.status) };
  return {};
}

/* ---------- THE FOLD (ported; parity asserted by the declared test) ------ */
// Records carrying one of the grammar's events, in `created` order. The sort
// is STABLE and compares the raw strings — the same rule as `_events()` in
// review_request.py, not a locale comparison, which would treat the ISO
// stamp's separators as noise.
function reviewEventsOf(records) {
  return (records || [])
    .filter((r) => r && typeof r === "object" && r.verdict && typeof r.verdict === "object"
      && REVIEW_EVENTS.indexOf(r.verdict.event) >= 0)
    .map((r, i) => [r, i])
    .sort((a, b) => {
      const x = String(a[0].created || ""), y = String(b[0].created || "");
      return x < y ? -1 : x > y ? 1 : a[1] - b[1];
    })
    .map((p) => p[0]);
}

// Records for ONE item -> its state. Never stored, always derived:
//   - a request with no close is OPEN;
//   - the LATEST close wins, whatever came before;
//   - the LATEST verdict per reviewer is that reviewer's verdict;
//   - a second `request` record on the same id is an EDIT;
//   - `request_notes` is THE ENVELOPE'S OWN WORDS on the latest request — the
//     ask (RV-17 (ask structure)), when the filer wrote one;
//   - `seen_by` is WHO LOOKED, one entry per reviewer in the order they FIRST
//     looked, however many times they looked after that.
// `seen` CHANGES NOTHING ELSE ABOUT THIS ANSWER (the team, ruled 2026-09-09, card
// RV-16a; carried into this port by RV-16b). It carries no judgment, so it
// never enters `verdicts`; it never closes, so `status`, `decision` and
// `accepted` cannot move on it; and it never satisfies the close rule's "one
// reviewer", because that rule reads `verdicts` and a `seen` is not one.
// `request_notes` (card RV-32 (ask in the fold)) changes nothing else either:
// the ask rides in the ENVELOPE and the fold carried only the verdict block, so
// every consumer of this fold could show a reviewer the work and not the ask.
// It is carried WHOLE AND UNPARSED — whether the filer's words are an ask in
// RV-17's four lines or their own commentary is a RENDERING question, asked
// once where the panel is, never twice.
function reviewFold(records) {
  const evs = reviewEventsOf(records);
  const state = {
    item: null, status: "open", request: null, requested_by: null,
    request_notes: "", close: null, decision: null, accepted: false,
    verdicts: {}, seen_by: [], records: evs.length,
  };
  for (const r of evs) {
    const v = r.verdict;
    state.item = r.item || state.item;
    if (v.event === "request") {
      state.request = v;                       // latest request = the edit
      // WHO ASKED is the envelope's `reviewer` — the filer. The frozen block
      // declares no requester field and none is invented here.
      state.requested_by = r.reviewer === undefined ? null : r.reviewer;
      // AND WHAT THEY ASKED FOR, from the same envelope and for the same
      // reason: the frozen block declares no ask field, so the ask lives in
      // `notes` (RV-17 (ask structure)) and a panel that dropped it could not
      // tell an absent ask from one it never carried.
      state.request_notes = r.notes == null ? "" : String(r.notes);
    } else if (v.event === "verdict") {
      const who = String(r.reviewer == null ? "" : r.reviewer).trim().toLowerCase();
      if (who) state.verdicts[who] = r;        // latest per reviewer
    } else if (v.event === "close") {
      state.close = r;                         // latest close wins
    } else if (v.event === "seen") {
      const who = String(r.reviewer == null ? "" : r.reviewer).trim().toLowerCase();
      // once per reviewer, in the order they FIRST looked. AT MOST ONE PER
      // REVIEWER is a fold property, not a refusal at the door: the plane is
      // append-only, so a second `seen` from one person is filed and DEDUPED
      // here, exactly as a second verdict is collapsed to the latest.
      if (who && state.seen_by.indexOf(who) < 0) state.seen_by.push(who);
    }
  }
  if (state.close) {
    state.status = "closed";
    const d = state.close.verdict.decision;
    state.decision = d === undefined ? null : d;
    state.accepted = state.decision === "accepted";
  }
  return state;
}

// THE CLOSE RULE, in the manifest's words: "auto on one reviewer + no
// on_accept; else explicit by requester/owner; the panel labels which". This
// returns the LABEL. It never files a close: which surface owns that write is
// not RV-6 (reference panels)'s to decide, and a reference page inventing one
// would be a second writer of the same event.
function reviewCloseRule(state) {
  const req = state && state.request;
  if (!req) return { mode: "unknown", label: "no request record — nothing to close" };
  const one = Array.isArray(req.reviewers) && req.reviewers.length === 1;
  if (one && !req.on_accept) {
    return { mode: "auto", label: `auto-close: one reviewer (${req.reviewers[0]}) and no on_accept — this request closes on that verdict` };
  }
  const why = !one ? `${(req.reviewers || []).length} reviewers` : "an on_accept is declared";
  return { mode: "explicit", label: `explicit close: ${why} — the requester or the owner files the close record` };
}

/* ---------- THE PANEL, KEYED ON `type` ----------------------------------- */
// One entry per type the manifest declares. An UNKNOWN type is not a panel:
// it degrades to a link and NAMES the value it was given, which is the
// manifest's own rule ("an unknown value degrades to a link rather than to an
// empty box"). RV-10 (PM review integration)'s drawer keys the same way.
//
// `page` IS KEYED HERE BECAUSE THE MANIFEST DECLARES IT (RV-47 (type page)),
// and it declares NO MEDIA AND NO WORDS ON PURPOSE — the same shape `link` has.
// THE FRAME IS RV-40 (link page panel)'s AND NOT THIS CARD'S: until it is
// built, a `page` is drawn as the link it points at, which is the honest
// rendering of a thing this block does not embed. What it must never be is an
// empty frame, and the last line of `reviewPanelHtml` is where a type carrying
// neither words nor media says so instead.
const REVIEW_PANELS = {
  text: { label: "text", words: true },
  md: { label: "md", words: true },
  image: { label: "image", media: true },
  video: { label: "video", media: true },
  doc: { label: "doc", words: false },
  link: { label: "link", words: false },
  page: { label: "page", words: false },
};

// The four pages this folder ships, keyed the same way. `video` and `doc` are
// declared types the BLOCK keys on and no reference page ships for — the card
// names four panels, and inventing two more would be styling investment a
// panel author has to undo rather than a reference to read.
const REVIEW_REFERENCE_PAGES = {
  text: "panel-text.html", md: "panel-md.html",
  image: "panel-image.html", link: "panel-link.html",
};

function reviewPanelFor(type) {
  const t = String(type == null ? "" : type);
  if (Object.prototype.hasOwnProperty.call(REVIEW_PANELS, t)) {
    return { type: t, known: true, ...REVIEW_PANELS[t] };
  }
  return {
    type: t, known: false, words: false, media: false,
    label: `unknown type ${t || "(none)"} — shown as a link`,
  };
}

// RV-5 (media renderer) IS the renderer: `render(pointer, type) -> element`,
// routed by `pointer.warehouse` (repo -> /api/file, drive -> /api/media, blob
// -> the url). IT HAS MERGED, so this seam is WIRED rather than pending.
//
// THE GLOBAL TO USE IS `pageMedia`, not `MediaRender`. `MediaRender` is the
// ENGINE (components/media-render/media-render.js) and its `render` takes a
// third argument carrying the two facts that belong to the PAGE and cannot
// live in a component: the api base, and the page's own authenticated fetch
// (an `<img src>` carries neither an auth header nor a cross-host cookie).
// `pageMedia` is the shim (platform/views/viewers/_templates/_media.js) that
// binds exactly those two and nothing else. Reaching past it to the engine
// would make THIS file supply them — a second copy of the shim, which is the
// defect RV-5 exists to end — and would read a repo or drive pointer against
// base "" with no credential. So: the shim, or a notice that names what is
// missing. No warehouse is inferred from a url's shape and no type is sniffed
// on either path (both are RV-5's nevers, and this page's).
function reviewRenderer() {
  const g = typeof globalThis === "undefined" ? {} : globalThis;
  const shim = g.pageMedia;
  return (shim && typeof shim.render === "function") ? shim : null;
}

// The element the panel last rendered, per PANEL ROOT — the one thing that
// survives a re-mount, since every repaint discards the `#rvmedia` hook it was
// hung in. RV-5 mints an object url for gated bytes and says plainly that
// nothing inside it can know when a panel dropped the element, so the panel
// gives it back. RV-10 (PM review integration) lifts this block, and a leak
// lifted with it would be a leak per verdict in the drawer.
const REVIEW_MEDIA_NODES = new WeakMap();

function reviewReleaseMedia(root) {
  const node = REVIEW_MEDIA_NODES.get(root);
  if (!node) return false;
  REVIEW_MEDIA_NODES.delete(root);
  const media = reviewRenderer();
  return !!(media && media.release(node));
}

// `data-media-state` off an element RV-5 built, without assuming a browser:
// the engine writes `dataset` when there is one and attributes when there is
// not, so the panel reads it the same way round.
function reviewMediaAttr(node, key) {
  const attr = "data-media-" + key;
  if (node.dataset && node.dataset["media" + key[0].toUpperCase() + key.slice(1)] != null) {
    return node.dataset["media" + key[0].toUpperCase() + key.slice(1)];
  }
  return typeof node.getAttribute === "function" ? node.getAttribute(attr) : null;
}

async function reviewMediaInto(el, pointer, type, root) {
  const media = reviewRenderer();
  if (!media) {
    const g = typeof globalThis === "undefined" ? {} : globalThis;
    // TWO ABSENCES, NAMED APART, because the fix is different for each.
    const engineOnly = !!g.MediaRender;
    el.innerHTML = `<p class="warn">${engineOnly
      ? `RV-5 (media renderer)'s ENGINE is on this page but its page shim is not, so
         <code>pageMedia</code> is undefined — load
         <code>platform/views/viewers/_templates/_media.js</code> AFTER
         <code>components/media-render/media-render.js</code>. This panel will not bind the
         api base and this page's fetch itself; that is the shim's job, and doing it here
         would be a second copy of it.`
      : `RV-5 (media renderer) is not on this page yet — wiring pending.`}
      The pointer is <code>${reviewEsc(pointer.warehouse)}</code> / <code>${reviewEsc(pointer.ref)}</code>,
      type <code>${reviewEsc(type)}</code> from the record. This panel does not guess a url for it.</p>`;
    return engineOnly ? "shim-missing" : "pending";
  }
  let node;
  // A pointer the renderer has no route for — `supabase` is declared in the
  // manifest and routed nowhere — is REFUSED BY NAME by RV-5 itself. The panel
  // repeats its words rather than inventing its own.
  try { node = media.render(pointer, type); }
  catch (e) {
    el.innerHTML = `<p class="warn">the renderer refused this pointer: ${reviewEsc(e && e.message || e)}</p>`;
    return "refused";
  }
  el.innerHTML = "";
  el.appendChild(node);
  if (root) REVIEW_MEDIA_NODES.set(root, node);
  // `ready` NEVER REJECTS: it records the failure on the element and resolves
  // either way. So the state is READ rather than caught, and a failed read says
  // so by name instead of leaving a blank box on the page.
  await media.ready(node);
  if (reviewMediaAttr(node, "state") === "error") {
    const said = reviewMediaAttr(node, "error") || "no reason recorded";
    el.innerHTML = `<p class="warn">the bytes did not arrive: ${reviewEsc(said)}
      (<code>${reviewEsc(pointer.warehouse)}</code> / <code>${reviewEsc(pointer.ref)}</code>)</p>`;
    return "error";
  }
  return "rendered";
}

// Words for a `text` / `md` asset. Two carriers only, both already the
// platform's: the repo mirror through /api/file, and public blob bytes with NO
// credential on the request because there is nothing there to authenticate to.
// A drive or supabase pointer has no words route and says so.
async function reviewWords(pointer) {
  if (pointer.warehouse === "repo") {
    const r = await fetch(`${API}/api/file?path=${encodeURIComponent(pointer.ref)}`, { headers: hdrs(), ...creds() });
    if (r.status === 401) { dropKey(); return { error: "the records plane refused this read (401)" }; }
    if (!r.ok) return { error: "HTTP " + r.status };
    const j = await r.json().catch(() => ({}));
    return j.error ? { error: String(j.error) } : { text: typeof j.text === "string" ? j.text : "" };
  }
  if (pointer.warehouse === "blob") {
    const r = await fetch(pointer.ref).catch((e) => ({ ok: false, status: String(e) }));
    return r.ok ? { text: await r.text() } : { error: "HTTP " + r.status };
  }
  return { error: `no words route for a ${pointer.warehouse} pointer — open it where it lives` };
}

/* ---------- the create body (create.html posts exactly this) ------------- */
// `RQ-<yyyymmddHHMMSS>-<slug>`, the same mint as `mint_item()` in
// review_request.py: time-based, because sequential ids need a coordinator and
// timestamps do not, and round two is a NEW id on the same asset pointer.
function reviewMintItem(title, created) {
  const p = String(created).replace(/[-:]/g, "").replace("T", "").slice(0, 14);
  const slug = String(title || "").toLowerCase().replace(/[^a-z0-9]+/g, "-")
    .slice(0, 40).replace(/^-+|-+$/g, "");
  return `RQ-${p}-${slug || "request"}`;
}

class ReviewRefused extends Error {}

// The `event: request` body, validated against the frozen grammar and
// carrying NOTHING beyond it — event, type, asset, reviewers, lane, and the
// two optionals due / on_accept. Key order mirrors `request_verdict()` in
// review_request.py, which the declared test compares this against field for
// field. Every refusal names the field a person can act on.
function reviewRequestBody(input) {
  const type = String(input.type || "");
  if (REVIEW_TYPES.indexOf(type) < 0) {
    throw new ReviewRefused(`type ${type || "(none)"} is not one the grammar declares (${REVIEW_TYPES.join("|")}). Nothing was filed.`);
  }
  const lane = String(input.lane || "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(lane)) {
    throw new ReviewRefused(`lane ${lane || "(none)"} is not a lane label ([a-z0-9-]); it is a LABEL, never a gate. Nothing was filed.`);
  }
  const body = { event: "request", type, asset: reviewAsset(input), reviewers: reviewPeople(input.reviewers), lane };
  if (input.due) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(input.due))) {
      throw new ReviewRefused(`due ${input.due} is not YYYY-MM-DD. Nothing was filed.`);
    }
    body.due = String(input.due);
  }
  if (input.on_accept) {
    if (typeof input.on_accept !== "object" || !input.on_accept.action) {
      throw new ReviewRefused("on_accept must be an object naming an `action` — RV-3 (on_accept adapter) files exactly what the request declared and never more. Nothing was filed.");
    }
    body.on_accept = input.on_accept;
  }
  if (input.media && input.media.length) {
    // LAST, after the two older optionals, exactly where `request_verdict()` in
    // review_request.py appends it — this body is compared against that one
    // field for field. `media` is OPTIONAL and always was: a request that needs
    // no byte-serving carries no such key, and is byte-identical to what this
    // form wrote before the Drive half existed (RV-18d).
    body.media = input.media;
  }
  return body;
}

// {warehouse, ref, title} — the POINTER, never the bytes (workspace rule 3).
// Checked for SHAPE only: whether a repo ref exists on disk is not this
// page's question, exactly as it is not the module's.
//
// ...AND `viewport?` SINCE RV-34 (url and viewport), the team's ruling of
// 2026-09-10: at what width the thing was meant to be read, `mobile` or
// `desktop`. LAST AND ONLY WHEN GIVEN, so a pointer that names none carries
// the exact keys it carried before the field existed — ABSENT IS UNSTATED,
// never `desktop`. The two words are written here rather than lifted into a
// constant because `review_request.py`'s `_viewport` is the mirror of record
// and the declared test compares this door's BEHAVIOUR with that one's; a
// third word is a RULING, which is why it is refused by name rather than
// stored. `at` is NOT widened alongside it: only a `repo` pointer has one,
// and RV-34 changed nothing about that.
function reviewAsset(input) {
  const warehouse = String(input.warehouse || "").trim().toLowerCase();
  if (REVIEW_WAREHOUSES.indexOf(warehouse) < 0) {
    throw new ReviewRefused(`warehouse ${warehouse || "(none)"} is not one the grammar declares (${REVIEW_WAREHOUSES.join("|")}). Nothing was filed.`);
  }
  const ref = String(input.ref || "").trim();
  if (!ref) throw new ReviewRefused("asset.ref is empty — the pointer IS the thing under review. Nothing was filed.");
  const title = String(input.title || "").trim();
  if (!title) throw new ReviewRefused("asset.title is empty — a reviewer must know what they are being asked to judge without opening the id. Nothing was filed.");
  const out = { warehouse, ref, title: title.slice(0, 200) };
  if (input.viewport != null) {
    const viewport = String(input.viewport).trim().toLowerCase();
    if (["mobile", "desktop"].indexOf(viewport) < 0) {
      throw new ReviewRefused(`asset.viewport ${viewport} is not one the grammar declares (mobile|desktop) — two words were ruled and a third is a RULING, never a filer's move. Omit it to leave the width UNSTATED. Nothing was filed.`);
    }
    out.viewport = viewport;
  }
  return out;
}

function reviewPeople(reviewers) {
  const list = (Array.isArray(reviewers) ? reviewers : String(reviewers || "").split(/[,\s]+/))
    .map((r) => String(r).trim().toLowerCase()).filter(Boolean);
  if (!list.length) {
    throw new ReviewRefused("reviewers is empty — a request names who is asked, so the queue can answer 'what is waiting on me'. Nothing was filed.");
  }
  const bad = list.filter((r) => !/^[a-z0-9][a-z0-9-]{0,30}$/.test(r));
  if (bad.length) throw new ReviewRefused(`reviewers ${bad[0]} is not a person id ([a-z0-9-]). Nothing was filed.`);
  return list;
}

// The `event: verdict` body — one reviewer's judgement, with its tags and its
// own words. `reasons` may be empty: a one-tap verdict is a complete verdict.
function reviewVerdictBody(verdict, reasons, note) {
  if (REVIEW_VERDICTS.indexOf(String(verdict)) < 0) {
    throw new ReviewRefused(`verdict ${verdict || "(none)"} is not one the grammar declares (${REVIEW_VERDICTS.join("|")}). Nothing was filed.`);
  }
  const body = { event: "verdict", verdict: String(verdict) };
  const tags = (Array.isArray(reasons) ? reasons : String(reasons || "").split(","))
    .map((t) => String(t).trim()).filter(Boolean);
  body.reasons = tags;
  const words = String(note || "").trim();
  if (words) body.note = words;
  return body;
}

/* ---------- the credential prompt, and the item on the URL --------------- */
const reviewItemOnUrl = () => {
  const q = new URLSearchParams(String(location.search || "").replace(/^\?/, ""));
  const h = new URLSearchParams(String(location.hash || "").replace(/^#/, ""));
  return (q.get("item") || h.get("item") || "").trim();
};

function reviewSignIn(el, after) {
  el.innerHTML = `<form class="card" id="rvkey">
    <p><b>No credential in this browser.</b> These pages talk to the real records plane,
    so they need the same key any viewer link carries — paste it once (it stays in this
    browser's localStorage and is never written into a record), or open this page from a
    <code>#k=…&amp;as=…</code> link.</p>
    <label>review key <input name="k" type="password" autocomplete="off"></label>
    <label>your name <input name="as" placeholder="steph"></label>
    <button>Use this key</button></form>`;
  el.querySelector("#rvkey").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const k = String(f.get("k") || "").trim(), as = String(f.get("as") || "").trim().toLowerCase();
    if (!k) return;
    localStorage.setItem("rk", k);
    if (as) localStorage.setItem("rn", as);
    after();
  });
}

/* ---------- the panel, mounted ------------------------------------------- */
// ONE mount for all four panel pages. The page passes the type IT is the
// reference for; a request of a different declared type is REFUSED BY NAME
// and points at the page that does key on it, because a panel that quietly
// rendered another type would teach the wrong thing about how the block keys.
async function mountReviewPanel(pageType, el) {
  if (!reviewBootstrapped(el)) return;
  absorbCred(new URLSearchParams(String(location.hash || "").replace(/^#/, "")));
  // Every paint below discards whatever the last one hung here, so the object
  // url RV-5 may have minted for it goes back FIRST — a verdict re-mounts this
  // panel, and a panel that never released would leak one per verdict filed.
  reviewReleaseMedia(el);
  const paint = (html) => { el.innerHTML = html; };
  const item = reviewItemOnUrl();
  const bar = `<form class="card" id="rvitem"><label>request id
      <input name="item" value="${reviewEsc(item)}" placeholder="RQ-…" size="52"></label>
      <button>Open</button></form>`;
  const wire = () => {
    const f = el.querySelector("#rvitem");
    if (f) f.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = String(new FormData(e.target).get("item") || "").trim();
      location.search = v ? "?item=" + encodeURIComponent(v) : "";
    });
  };
  if (!authed()) { paint(""); return reviewSignIn(el, () => mountReviewPanel(pageType, el)); }
  if (!item) { paint(`${bar}<p class="none">Name a request to open — an <code>RQ-…</code> id
    that has been FILED. RV-1 (review kind manifest)'s three seeds in
    <code>components/review/seed/</code> are example records, not filed ones;
    <code>create.html</code> files a real request and hands back its id.</p>`); return wire(); }

  paint(`${bar}<p class="none">reading ${reviewEsc(item)}…</p>`);
  wire();
  let recs;
  try { recs = await reviewRecords(item); }
  catch (e) {
    if (e && e.auth) { paint(bar); wire(); return reviewSignIn(el.appendChild(document.createElement("div")), () => mountReviewPanel(pageType, el)); }
    paint(`${bar}<p class="warn">could not read the records: ${reviewEsc(e && e.message || e)}</p>`);
    return wire();
  }
  const state = reviewFold(recs);
  if (!state.request) {
    paint(`${bar}<p class="warn">${reviewEsc(item)} has no <code>request</code> record — ${state.records} record(s) on the item. There is nothing to show.</p>`);
    return wire();
  }
  const panel = reviewPanelFor(state.request.type);
  // TWO REFUSALS, BOTH BY NAME. A request of another DECLARED type belongs to
  // that type's panel. A request of an UNDECLARED type belongs to the link
  // panel, because the manifest's rule is that an unknown value degrades to a
  // link rather than to an empty box — so the link panel takes it and says
  // what it was, and the other three refuse it and say where it goes.
  if (panel.known && panel.type !== pageType) {
    const page = REVIEW_REFERENCE_PAGES[panel.type];
    paint(`${bar}<p class="warn">This is the <b>${reviewEsc(pageType)}</b> panel and
      ${reviewEsc(item)} is <b>type ${reviewEsc(panel.type)}</b> — refused, rather than
      rendered by the wrong panel. ${page ? `Open <code>${reviewEsc(page)}?item=${reviewEsc(item)}</code>.`
        : `No reference panel ships for that type.`}</p>`);
    return wire();
  }
  if (!panel.known && pageType !== "link") {
    paint(`${bar}<p class="warn">This is the <b>${reviewEsc(pageType)}</b> panel and
      ${reviewEsc(item)} declares <b>type ${reviewEsc(panel.type || "(none)")}</b>, which the
      manifest does not — refused here. An undeclared type degrades to a link:
      open <code>panel-link.html?item=${reviewEsc(item)}</code>.</p>`);
    return wire();
  }
  paint(bar + reviewPanelHtml(state, panel));
  wire();
  const words = el.querySelector("#rvwords"), media = el.querySelector("#rvmedia");
  // `el` — the panel ROOT — is handed in so the element can be given back on
  // the next mount; the hook itself does not survive one.
  if (media) await reviewMediaInto(media, state.request.asset, state.request.type, el);
  if (words) {
    const got = await reviewWords(state.request.asset);
    const pinned = reviewWordsLabel(state.request.asset);
    words.innerHTML = got.error
      ? `<p class="warn">${reviewEsc(got.error)}</p>`
      : `${pinned ? `<p class="warn">${reviewEsc(pinned)}</p>` : ""}<pre>${reviewEsc(got.text)}</pre>`;
  }
  const form = el.querySelector("#rvverdict");
  if (form) form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target), out = el.querySelector("#rvsaid");
    const btn = e.target.querySelector("button");
    let body;
    try { body = reviewVerdictBody(f.get("verdict"), f.get("reasons"), f.get("note")); }
    catch (err) { out.textContent = String(err.message || err); return; }
    btn.disabled = true; out.textContent = "filing…";
    // The envelope's `notes` stays empty on a verdict: the reviewer's own
    // words are the grammar's `note`, and writing them twice would make two
    // fields disagree the first time one is edited.
    const res = await reviewFileRecord(item, body, "");
    btn.disabled = false;
    if (res.err) { out.textContent = res.err; return; }
    // The write landed; the status on the screen is RE-FOLDED from the records,
    // never patched in place — that is what "status is never stored" means on
    // a page as much as on the plane.
    mountReviewPanel(pageType, el);
  });
}

/* ---------- create.html, mounted ----------------------------------------- */
// The create form and the one composer it posts. The BODY is
// `reviewRequestBody()` above — the same fields, in the same order, as
// `request_verdict()` in review_request.py, which the declared test compares
// them against. The item id is minted here, by the requester, because
// `open_items` is on and no request id is ever added to the manifest.
function mountReviewCreate(el) {
  if (!reviewBootstrapped(el)) return;
  absorbCred(new URLSearchParams(String(location.hash || "").replace(/^#/, "")));
  if (!authed()) return reviewSignIn(el, () => mountReviewCreate(el));
  el.innerHTML = `<form class="card" id="rvcreate">
    <label>title <input name="title" size="60" placeholder="what the reviewer is being asked to judge"></label>
    <label>type <select name="type">${REVIEW_TYPES.map((t) => `<option>${t}</option>`).join("")}</select></label>
    <label>warehouse <select name="warehouse">${REVIEW_WAREHOUSES.map((w) => `<option>${w}</option>`).join("")}</select></label>
    <label>ref <input name="ref" size="60" placeholder="repo path · drive file id · blob url"></label>
    <label>reviewers <input name="reviewers" placeholder="steph, damon"></label>
    <label>lane <input name="lane" value="dev-qc" placeholder="email-sends · static-ads · dev-qc · …"></label>
    <label>due <span class="faint">(optional)</span> <input name="due" placeholder="YYYY-MM-DD"></label>
    <label>your words <span class="faint">(optional, rides in the envelope's notes)</span>
      <textarea name="notes" rows="3"></textarea></label>
    <button>File the request</button> <span id="rvsaid" class="faint"></span>
    </form><div id="rvout"></div>`;
  el.querySelector("#rvcreate").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target), said = el.querySelector("#rvsaid");
    const btn = e.target.querySelector("button");
    let body;
    try {
      body = reviewRequestBody({
        title: f.get("title"), type: f.get("type"), warehouse: f.get("warehouse"),
        ref: f.get("ref"), reviewers: f.get("reviewers"), lane: f.get("lane"),
        due: String(f.get("due") || "").trim() || null,
      });
    } catch (err) { said.textContent = String(err.message || err); return; }
    // The server stamps `created` from its own clock; this stamp is the one
    // the ID is minted from, and the two are allowed to differ by the flight
    // time — the id is a name, never a timestamp anyone reads back as truth.
    const item = reviewMintItem(body.asset.title, new Date().toISOString().replace(/\.\d+Z$/, "Z"));
    said.textContent = "filing…"; btn.disabled = true;
    const res = await reviewFileRecord(item, body, String(f.get("notes") || ""));
    btn.disabled = false;
    if (res.err) { said.textContent = res.err; return; }
    said.textContent = "";
    const page = REVIEW_REFERENCE_PAGES[body.type];
    const open = page
      ? `<a href="${reviewEsc(page)}?item=${encodeURIComponent(item)}">open the ${reviewEsc(body.type)} panel</a>`
      : `no reference panel ships for type <b>${reviewEsc(body.type)}</b> — the block keys on it
         (<code>REVIEW_PANELS</code>) and the page is the panel author's to add`;
    el.querySelector("#rvout").innerHTML = `<div class="card"><p><b>Filed.</b>
      <code>${reviewEsc(item)}</code> — ${open}.</p>
      <pre>${reviewEsc(JSON.stringify(body, null, 2))}</pre></div>`;
  });
}

// Where the asset's link goes (RV-66 (writer enforces the frozen grammar),
// finding rev-7). A `blob` ref is the platform blob url, as it always was; a
// `url` ref IS the link, but only after a scheme check — a `javascript:` ref is
// a filer-typed string, never a link this page will hand a reviewer. Every
// other warehouse has no public address, so it stays `#`.
function reviewAssetHref(asset) {
  const a = asset || {};
  if (a.warehouse === "blob") return a.ref;
  if (a.warehouse === "url") {
    try {
      const u = new URL(String(a.ref));
      return u.protocol === "http:" || u.protocol === "https:" ? a.ref : "#";
    } catch (e) { return "#"; }
  }
  return "#";
}

// What the words box owes a reader of a PINNED document (RV-66 (writer enforces
// the frozen grammar), finding rev-8). `at` binds a repo request to a commit,
// but /api/file reads only the current file and takes no commit, so the words
// shown are the latest — and the box says so rather than passing HEAD's words
// off as the pinned ones.
function reviewWordsLabel(asset) {
  const a = asset || {};
  if (a.warehouse !== "repo" || !a.at) return "";
  return `showing the latest words, not the pinned commit ${a.at} — the file route reads the current file only`;
}

function reviewPanelHtml(state, panel) {
  const req = state.request, rule = reviewCloseRule(state);
  const pill = state.status === "open"
    ? `<span class="pill open">open</span>`
    : `<span class="pill closed">closed · ${reviewEsc(state.decision)}</span>`;
  const asset = `<code>${reviewEsc(req.asset.warehouse)}</code> / <code>${reviewEsc(req.asset.ref)}</code>`;
  const votes = Object.keys(state.verdicts).sort().map((who) => {
    const v = state.verdicts[who].verdict;
    return `<li><b>${reviewEsc(who)}</b> — ${reviewEsc(v.verdict)}
      ${(v.reasons || []).length ? `<span class="faint">${reviewEsc((v.reasons || []).join(", "))}</span>` : ""}
      ${v.note ? `<div class="faint">${reviewEsc(v.note)}</div>` : ""}</li>`;
  }).join("");

  return `<div class="card">
    <h2>${reviewEsc(req.asset.title)} ${pill}</h2>
    <p class="faint">${reviewEsc(state.item)} · type <b>${reviewEsc(req.type)}</b> ·
      lane ${reviewEsc(req.lane)} · asked of ${reviewEsc((req.reviewers || []).join(", "))} ·
      filed by ${reviewEsc(state.requested_by || "(unstamped)")}${req.due ? " · due " + reviewEsc(req.due) : ""}</p>
    <p class="faint">${reviewEsc(rule.label)}</p>
    <p class="faint">the asset: ${asset}</p>
    ${panel.media ? `<div id="rvmedia"></div>` : ""}
    ${panel.words ? `<div id="rvwords" class="none">reading the words…</div>` : ""}
    ${panel.known ? "" : `<p class="warn">${reviewEsc(panel.label)}</p>`}
    ${!panel.words && !panel.media ? `<p><a href="${reviewEsc(reviewAssetHref(req.asset))}">${reviewEsc(req.asset.ref)}</a></p>` : ""}
  </div>
  <div class="card">
    <h3>Verdicts so far <span class="faint">(latest per reviewer, folded)</span></h3>
    ${votes ? `<ul>${votes}</ul>` : `<p class="none">none yet</p>`}
  </div>
  <form class="card" id="rvverdict">
    <h3>File a verdict</h3>
    <p>${REVIEW_VERDICTS.map((v) => `<label><input type="radio" name="verdict" value="${v}"${v === "approve" ? " checked" : ""}> ${v}</label>`).join(" ")}</p>
    <label>reasons <input name="reasons" placeholder="comma,separated,tags"></label>
    <label>note <textarea name="note" rows="3"></textarea></label>
    <button>File verdict</button> <span id="rvsaid" class="faint"></span>
  </form>`;
}
