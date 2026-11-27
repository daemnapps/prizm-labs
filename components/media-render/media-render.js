/* ===========================================================================
 * MEDIA-RENDER — one renderer, routed by warehouse. Card RV-5.
 *
 * SOURCE OF TRUTH: components/media-render/media-render.js (this file), and
 * there is no second copy of it anywhere. `platform/views/viewers/_templates/
 * _media.js` is a SHIM that calls this engine and re-implements none of it;
 * a template carries the pair, engine first, built by
 * `components/media-render/bundle.py` (the viewer route serves exactly one
 * html file per request, so a page cannot fetch a sibling asset and both have
 * to travel inlined). ONE FIX, NOT FOUR: the fourth surface that shows a
 * Drive image calls `render`.
 *
 * WHAT IT IS — a LIBRARY. It emits no record, writes no file, holds no
 * credential and knows no secret (components rule 7: consumers touch planes
 * and manifests only). Everything that reaches outside is INJECTED — the
 * document, the fetch, the api base — which is also why the declared test can
 * run the real decision layer on bare `node` instead of a copy of it.
 *
 * TWO RULES, AND THEY ARE THE WHOLE COMPONENT:
 *
 *   1. THE WAREHOUSE ROUTES, AND NOTHING ELSE DOES. `pointer.warehouse` is a
 *      declared word off the record — `repo`, `drive`, `blob` — and it picks
 *      the url shape. A url's SHAPE is never inspected to decide where a thing
 *      lives, and a warehouse this table does not carry is REFUSED BY NAME
 *      (`supabase` is declared in the review manifest and has no route here;
 *      it says so in the refusal rather than falling through to a guess).
 *
 *   2. THE TYPE COMES FROM THE RECORD AND IS NEVER SNIFFED. `type` is the
 *      caller's second argument, straight off the record's `type` field, and
 *      it alone decides the element. No extension is parsed, no magic bytes
 *      are read, no response header is consulted: `{ref: "notes.txt"}` with
 *      type `image` renders an <img>, and `{ref: "cat.png"}` with type `video`
 *      renders a <video>. An unknown type DEGRADES TO A LINK rather than to an
 *      empty box — the review manifest's own words for its `type` vocabulary.
 *
 * THE URL SHAPES, DECLARED (the contract; `test_rv5_media_render.py` asserts
 * each one against the routes as merged):
 *
 *   repo   ->  <api>/api/file?path=<ref>                 ref = repo path
 *   drive  ->  <api>/api/media?kind=<kind>&run=<item>&file=<name>
 *   blob   ->  <ref>                                     ref = the url itself
 *
 * AND ONE OF THE THREE ANSWERS AN ENVELOPE (RV-5b). `/api/file` returns JSON
 * carrying the document under `text` — so a text/md pane on a `repo` pointer
 * takes `.text` off the parsed body, the same single line five viewers already
 * use. `drive` and `blob` answer the bytes themselves and are unwrapped by
 * nothing. The warehouse the record declared decides this, as it decides
 * everything else here; the body's own shape is never inspected.
 *
 * WHY A DRIVE POINTER CARRIES kind + item + name AND NOT THE DRIVE ID. The
 * merged /api/media (RV-4) takes `?run=&file=[&kind=]`, matches `file` EXACTLY
 * against the rows of that record's declared media inventory, and resolves the
 * Drive id itself — the inventory record is the allowlist and that is the
 * whole security model. A client that sent a Drive id would be naming a file
 * no record published, which is precisely what the route exists to refuse. So
 * the drive branch names the RECORD (kind + item) and the ROW (name); the
 * row's `ref` is carried on the pointer for provenance and never spent on a
 * url. `kind` is REQUIRED here even though the route defaults it: defaulting
 * a review's media to `teardown-runs` is the kind of silent guess this
 * component exists not to make.
 *
 * BYTES ARE THE CALLER'S CREDENTIAL, NOT OURS. `<img src>` cannot carry a
 * Bearer token or a cross-host cookie, so a page that reads gated bytes hands
 * in its OWN authenticated fetch as `opts.fetch`; the element then swaps to an
 * object url. With no fetch handed in, a picture points at the url (right for
 * a public blob, and honest everywhere else) and a text pane says it is
 * waiting for bytes instead of pretending to be empty.
 * ======================================================================== */
;(function (global) {
  "use strict";

  /* THE ROUTING TABLE. Four warehouses, each a function of the pointer and
   * the api base. Adding another is editing this object — there is nowhere
   * else in the file where a warehouse name appears as a branch.
   *
   * `url` ARRIVED WITH RV-34 (url and viewport), developer's ruling of 2026-09-10,
   * and it arrived here rather than only in the manifest FOR A NAMED REASON:
   * declaring a warehouse the router does not know ships a grammar nobody can
   * render. A panel keyed on such a pointer mounts nothing and says nothing —
   * the record right, the validator happy, the reviewer shown a blank — which
   * is the worst of the three outcomes, because there is no thread to pull.
   * `supabase` is STILL out, and the two facts do not contradict each other:
   * a declared word gets a route when something actually points there, and
   * nothing points at Supabase Storage. */
  var ROUTES = {
    repo: function (p, base) {
      return base + "/api/file?path=" + encodeURIComponent(need(p, "ref", "repo"));
    },
    drive: function (p, base) {
      return base + "/api/media"
        + "?kind=" + encodeURIComponent(need(p, "kind", "drive"))
        + "&run=" + encodeURIComponent(need(p, "item", "drive"))
        + "&file=" + encodeURIComponent(need(p, "name", "drive"));
    },
    blob: function (p) {
      var url = need(p, "ref", "blob");
      // NOT a warehouse guess — the warehouse was declared. This refuses a
      // scheme a browser must never be handed from record data (`javascript:`
      // in an href is the whole of the attack), and it refuses it by name.
      if (!/^https?:\/\//i.test(url)) {
        throw refusal('a blob pointer\'s ref must be an http(s) url; this one is "'
          + String(url).slice(0, 24) + '…"');
      }
      return url;
    },
    url: function (p) {
      // THE REF IS THE URL — a Figma file, a Netlify preview, anything the
      // platform does not own. There is no api in front of it because there is
      // no gate to open, so this route resolves to what the record already
      // says and adds nothing. The `blob` refusal is repeated rather than
      // shared, in the one shape this file allows a warehouse to be a branch:
      // a scheme handed to a browser out of record data (`javascript:` in an
      // href) is the whole of the attack, and it is refused BY NAME.
      var link = need(p, "ref", "url");
      if (!/^https?:\/\//i.test(link)) {
        throw refusal('a url pointer\'s ref must be an http(s) url; this one is "'
          + String(link).slice(0, 24) + '…"');
      }
      return link;
    },
  };

  var WAREHOUSES = Object.keys(ROUTES);

  /* THE TYPE TABLE — the review manifest's vocabulary, verbatim, and the one
   * place an element is chosen. `doc` and `link` are references: a link is the
   * honest rendering of a thing this component does not embed.
   *
   * `page` (RV-47 (type page), 2026-09-10) IS CARRIED HERE BECAUSE THE MANIFEST
   * DECLARES IT, and it is carried as a REFERENCE for now. This entry changes
   * no behaviour — an unlisted word already degrades to `link` — it says out
   * loud that the degradation is the DECLARED shape for this word and not an
   * unknown falling through. THE FRAME IS NOT THIS COMPONENT'S: RV-40 (link
   * page panel) lays a page out at its declared pixel width and scales it, in
   * the panel, and this table is where that word would be re-shaped if the
   * frame ever became an element rather than a layout. */
  var TYPES = {
    image: "image",
    video: "video",
    text:  "text",
    md:    "md",
    doc:   "link",
    link:  "link",
    page:  "link",
  };

  var READY = new WeakMap();   // element -> promise, for callers that await
  var OBJECT_URLS = new WeakMap();
  var RELEASED = new WeakSet(); // released before its bytes arrived (RV-5c (release while loading))

  function refusal(msg) {
    var e = new Error("media-render: " + msg);
    e.mediaRender = true;
    return e;
  }

  function need(p, field, warehouse) {
    var v = p[field];
    if (typeof v !== "string" || v === "") {
      throw refusal('a ' + warehouse + ' pointer needs `' + field + '`, and this one carries none');
    }
    return v;
  }

  /**
   * The routed url for a pointer. Refuses by name; never returns a guess.
   *
   * @param {{warehouse:string, ref?:string, kind?:string, item?:string,
   *          name?:string, title?:string}} pointer
   * @param {{apiBase?:string}} [opts]
   * @returns {string}
   */
  function url(pointer, opts) {
    if (!pointer || typeof pointer !== "object" || Array.isArray(pointer)) {
      throw refusal("a pointer must be an object off the record");
    }
    var w = pointer.warehouse;
    if (typeof w !== "string" || w === "") {
      throw refusal("the pointer names no warehouse, and a url's shape is never "
        + "read to guess one — the routed warehouses are " + WAREHOUSES.join(", "));
    }
    if (!Object.prototype.hasOwnProperty.call(ROUTES, w)) {
      throw refusal('warehouse "' + w + '" has no route here — the routed '
        + "warehouses are " + WAREHOUSES.join(", ")
        + ". A pointer is never resolved by reading its url's shape.");
    }
    var base = (opts && typeof opts.apiBase === "string") ? opts.apiBase : "";
    return ROUTES[w](pointer, base);
  }

  /**
   * The element for a pointer, keyed on the type THE RECORD carries.
   *
   * @param {object} pointer   see `url`
   * @param {string} type      the record's `type` — text|md|image|video|doc|link|page
   * @param {{apiBase?:string, document?:Document, fetch?:function,
   *          URL?:object}} [opts]
   * @returns {Element}
   */
  function render(pointer, type, opts) {
    opts = opts || {};
    var doc = opts.document || global.document;
    if (!doc || typeof doc.createElement !== "function") {
      throw refusal("no document to build an element with — pass `opts.document`");
    }
    var href = url(pointer, opts);
    var given = typeof type === "string" ? type : "";
    // Unknown degrades to a link, per the manifest. It is recorded as GIVEN on
    // the element so a panel can say "we did not know this type" out loud.
    var shape = Object.prototype.hasOwnProperty.call(TYPES, given) ? TYPES[given] : "link";
    var words = (typeof pointer.title === "string" && pointer.title)
      ? pointer.title
      : (pointer.name || pointer.ref || href);

    var el;
    if (shape === "image") {
      el = doc.createElement("img");
      el.setAttribute("alt", words);
    } else if (shape === "video") {
      el = doc.createElement("video");
      el.setAttribute("controls", "");
      el.setAttribute("playsinline", "");
    } else if (shape === "text" || shape === "md") {
      el = doc.createElement(shape === "text" ? "pre" : "div");
    } else {
      el = doc.createElement("a");
      el.setAttribute("href", href);
      el.setAttribute("rel", "noreferrer noopener");
      el.setAttribute("target", "_blank");
      el.textContent = words;
    }

    // Provenance on the element itself: what warehouse it came from, what the
    // record called it, and what that made us draw. A panel never has to
    // re-derive any of the three, and a reader can see them in the inspector.
    set(el, "mediaWarehouse", pointer.warehouse);
    set(el, "mediaType", given || "(none)");
    set(el, "mediaShape", shape);
    set(el, "mediaUrl", href);

    if (shape === "link") {
      state(el, "ready");
      READY.set(el, resolved(el));
      return el;
    }

    var fetcher = typeof opts.fetch === "function" ? opts.fetch : null;
    if (!fetcher) {
      // No credential offered, so no gated read is attempted. A picture points
      // at the url — correct for a public blob, and a visible 401 rather than
      // a silent blank anywhere else. Bytes-into-text panes wait, and say so.
      if (shape === "image" || shape === "video") {
        el.setAttribute("src", href);
        state(el, "ready");
      } else {
        state(el, "needs-bytes");
      }
      READY.set(el, resolved(el));
      return el;
    }

    state(el, "loading");
    var URLish = opts.URL || global.URL;
    var p = Promise.resolve()
      .then(function () { return fetcher(href); })
      .then(function (res) {
        if (res && res.ok === false) {
          throw refusal("the fetch answered " + res.status + " for this pointer");
        }
        if (shape === "image" || shape === "video") {
          return Promise.resolve(res.blob()).then(function (blob) {
            var objectUrl = URLish.createObjectURL(blob);
            // A panel that let go of this element mid-load will never call
            // `release` again, so the url goes back here, with the same api
            // that minted it, and the element never paints.
            if (RELEASED.has(el)) {
              URLish.revokeObjectURL(objectUrl);
              return;
            }
            OBJECT_URLS.set(el, objectUrl);
            el.setAttribute("src", objectUrl);
          });
        }
        // THE REPO ROUTE ANSWERS AN ENVELOPE, AND ONLY IT DOES (RV-5b). The
        // gated `/api/file?path=` read returns JSON with the document under
        // `text`; five viewers already read it that way — `email-cards.html`
        // in one line, `(await fr.json()).text` — and this component was the
        // outlier, painting the wrapper into the pane. The unwrap is
        // conditioned on the WAREHOUSE THE RECORD DECLARED, never on what the
        // body looks like: a `blob` pointer is the file itself and is read raw
        // even when its bytes happen to look like an envelope.
        var body = pointer.warehouse === "repo"
          ? Promise.resolve(res.json()).then(function (env) {
              return (env && typeof env.text === "string") ? env.text : "";
            })
          : Promise.resolve(res.text());
        return body.then(function (txt) {
          // Text is DATA, never markup (workspace rule 8): textContent, always,
          // on both panes. A md panel renders from `el.textContent` with its
          // own renderer — this component ships none and escapes nothing,
          // because it never builds markup out of what it read.
          el.textContent = txt;
        });
      })
      .then(function () { state(el, "ready"); return el; })
      .catch(function (err) {
        state(el, "error");
        set(el, "mediaError", (err && err.message) ? err.message : String(err));
        return el;
      });
    READY.set(el, p);
    return el;
  }

  /** The promise for an element `render` returned — resolves to the element,
   *  whether the bytes arrived or the failure was recorded on it. */
  function ready(el) {
    return READY.get(el) || resolved(el);
  }

  /** Give back an object url this component minted. A panel that drops an
   *  element calls this; nothing here can know when that happened. Released
   *  while its bytes are still loading, there is no url yet: the element is
   *  remembered, the load path revokes the url it mints for it, and this still
   *  answers `false` (RV-5c (release while loading)). */
  function release(el, URLish) {
    var u = OBJECT_URLS.get(el);
    if (!u) {
      if (el && typeof el === "object") RELEASED.add(el);
      return false;
    }
    var api = URLish || global.URL;
    if (api && typeof api.revokeObjectURL === "function") api.revokeObjectURL(u);
    OBJECT_URLS.delete(el);
    return true;
  }

  function resolved(el) { return Promise.resolve(el); }

  function state(el, s) { set(el, "mediaState", s); }

  // dataset when there is one (a browser), attributes when there is not (a
  // node stub, and any DOM-alike a caller hands in).
  function set(el, key, value) {
    var attr = "data-" + key.replace(/[A-Z]/g, function (c) { return "-" + c.toLowerCase(); });
    if (el.dataset) el.dataset[key] = value;
    else if (typeof el.setAttribute === "function") el.setAttribute(attr, value);
  }

  var MediaRender = {
    render: render,
    url: url,
    ready: ready,
    release: release,
    WAREHOUSES: WAREHOUSES.slice(),
    TYPES: Object.freeze(Object.assign({}, TYPES)),
  };

  global.MediaRender = MediaRender;
  if (typeof module === "object" && module && module.exports) module.exports = MediaRender;
})(typeof globalThis !== "undefined" ? globalThis : this);
