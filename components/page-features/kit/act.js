/* components/page-features/kit/act.js — PF-15 (direct by default): the ONE button script of every page-features
   page. Component-owned, never edited per page: a page carries it whole between its two act.js markers, the way it
   carries the overlay, and the going-live check compares that block with its family template's.

   pfAct(n, fields, opts) runs button n through the page server's POST /act, as the family's run table says
   (_templates/<family>.actions.json `direct`, each entry with its kind):
     quick        200 at once; the answer's last line is the result
     job          202 {job}; GET /job/<id> every 3 s (pfAct.poll) until done or failed, opts.tick(progress) each time
     confirm-job  428 {confirm}; a confirm with the server's own words, then the same body again with confirmed: true,
                  only on OK (Cancel runs nothing)
     409          already working on that item: shown as it is, never retried and never copied (no double spend)
   Not served by a page server (no kit-token meta, or not on 127.0.0.1 / localhost: no fetch at all), or any other
   failure, goes to the fallback: opts.fallback(answer) when the page gives one (its return is pfAct's), else the
   request line for the person's Claude (opts.ask, or a function of the answer; a failed job's own line first) is
   copied and shown.
     fields  the body: {item, part, field, value, note, …}; family (opts.family) and n are set here
     opts    {family, into: an element or its id for the progress and result line, ask, tick, fallback}
   pfUpload(file, item, opts) saves a picked file through POST /upload?family=<opts.family>&item=<item>, answering
   {ok, path} or {ok: false, said}. pfServed() is true when a page server serves this page.
   No page-specific logic here: a page names its family, its numbers, its request line and where its line goes. */
(function (w) {
  "use strict";
  var LOCAL = /^http:\/\/(127\.0\.0\.1|localhost):\d+$/;

  function token() {
    var m = w.document.querySelector('meta[name="kit-token"]');
    return m && LOCAL.test(w.location.origin) ? m.getAttribute("content") || "" : "";
  }
  function box(into) { return typeof into === "string" ? w.document.getElementById(into) : into || null; }
  function lastLine(s) {
    var l = String(s || "").split("\n").filter(function (x) { return x.trim(); });
    return l.length ? l[l.length - 1] : "";
  }
  function show(into, cls, text, ask) {
    var b = box(into);
    if (!b) return;
    b.textContent = "";
    var p = w.document.createElement("p");
    p.className = cls;
    p.textContent = text;
    b.appendChild(p);
    if (ask) {
      var pre = w.document.createElement("pre");
      pre.style.whiteSpace = "pre-wrap";
      pre.textContent = ask;
      b.appendChild(pre);
    }
  }
  function copy(text) {
    try {
      if (w.navigator.clipboard && w.isSecureContext) return w.navigator.clipboard.writeText(text).catch(function () {});
    } catch (x) { /* the textarea below */ }
    try {
      var a = w.document.createElement("textarea");
      a.value = text;
      a.style.position = "fixed";
      a.style.opacity = "0";
      w.document.body.appendChild(a);
      a.select();
      w.document.execCommand("copy");
      a.remove();
    } catch (x) { /* nothing more to try; the line is shown */ }
    return Promise.resolve();
  }
  function wait(ms) { return new Promise(function (z) { setTimeout(z, ms); }); }

  /* The kit call: a JSON body (or a picked file) with the token; 428 → confirm → again with confirmed; 202 → poll. */
  async function call(path, body, tick) {
    var t = token();
    if (!t) return {ok: false, unserved: true, said: "not served by the page kit"};
    var file = typeof Blob !== "undefined" && body instanceof Blob;
    async function post(b) {
      var a = await w.fetch(path, {method: "POST", headers: {
        "Content-Type": file ? (b.type || "application/octet-stream") : "application/json", "X-Kit-Token": t},
        body: file ? b : JSON.stringify(b)});
      var r;
      try { r = await a.json(); } catch (x) { r = {ok: false, said: "the kit answered " + a.status}; }
      r.status = a.status;
      return r;
    }
    var r;
    try { r = await post(body); } catch (x) { return {ok: false, failed: true, said: String((x && x.message) || x)}; }
    if (r.status === 428 && r.confirm) {
      if (!w.confirm(r.confirm)) return {ok: false, cancelled: true, said: "Not run: you pressed Cancel."};
      try { r = await post(Object.assign({}, body, {confirmed: true})); }
      catch (x) { return {ok: false, failed: true, said: String((x && x.message) || x)}; }
    }
    if (r.status !== 202 || !r.job) return r;
    var t0 = Date.now(), j = {state: r.state || "queued", said: "", ask: r.ask};
    for (;;) {
      if (tick) tick({state: j.state, s: Math.round((Date.now() - t0) / 1000), said: j.said, ask: j.ask || r.ask});
      await wait(pfAct.poll);
      try {
        var a = await w.fetch("/job/" + encodeURIComponent(r.job), {cache: "no-store"});
        if (a.status === 404) {
          return {ok: false, job: r.job, state: "failed", said: "the kit no longer knows this job (it restarted?)", ask: r.ask};
        }
        if (a.ok) j = await a.json();
      } catch (x) { /* asked again in 3 s */ }
      if (j.state === "done" || j.state === "failed") {
        return Object.assign(j, {ok: j.state === "done", job: j.job || r.job, ask: j.ask || r.ask});
      }
    }
  }

  async function pfAct(n, fields, opts) {
    opts = opts || {};
    var body = Object.assign({}, fields || {}, {family: opts.family || (fields && fields.family), n: n});
    var into = opts.into, job = false;
    function fallback(r) {
      if (typeof opts.fallback === "function") return opts.fallback(r);
      var ask = (r.job && r.ask) || (typeof opts.ask === "function" ? opts.ask(r) : opts.ask);
      var why = r.unserved ? "Not served by a page server" : (r.job ? "It stopped" : "Didn't run here") +
        ": " + (lastLine(r.said) || "no answer");
      if (!ask) { show(into, "err", why + "."); return r; }
      return copy(ask).then(function () {
        show(into, r.unserved ? "said" : "err", why + ". The request is copied: paste it in Claude.", ask);
        return Object.assign(r, {fallback: true, copied: ask});
      });
    }
    if (!token()) return fallback({ok: false, unserved: true, said: "not served by the page kit"});
    show(into, "said", "Working…");
    var r = await call("/act", body, function (p) {
      job = true;
      var last = lastLine(p.said);
      show(into, "said", "working… " + (p.s || 0) + " s" + (last && last !== "working…" ? " · " + last : ""));
      if (opts.tick) opts.tick(p);
    });
    if (r.ok) {
      var said = lastLine(r.said);
      show(into, "said", "✓ Done" + (said ? " · " + said : ""));
      return r;
    }
    if (r.cancelled) { show(into, "note", r.said); return r; }
    if (r.status === 409) { show(into, "err", (r.said || "already working on it") + ": wait for its line to say done."); return r; }
    if (job && !r.job) r.job = true;
    return fallback(r);
  }
  pfAct.poll = 3000;

  function pfUpload(file, item, opts) {
    opts = opts || {};
    return call("/upload?family=" + encodeURIComponent(opts.family || "") + "&item=" + encodeURIComponent(item), file);
  }

  w.pfAct = pfAct;
  w.pfUpload = pfUpload;
  w.pfServed = function () { return !!token(); };
})(window);
