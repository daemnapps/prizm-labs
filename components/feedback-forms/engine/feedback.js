/* Feedback form engine — one question at a time, brand-agnostic.
 *
 * Source of truth: ai-workspace components/feedback-forms/engine/feedback.js.
 * A campaign repo carries a COPY written by components/feedback-forms/build.py;
 * edit the source and rebuild rather than editing a copy.
 *
 * Everything that makes a form a brand's lives in its config
 * (brands/<brand>/operations/feedback-questions.json + feedback-stages.json,
 * compiled by build.py into window.FEEDBACK_CONFIG). This file holds no brand.
 *
 * The link in the email:   <form url>?stage=<stage>&e=<email>   (optional: _kx, fid, mid)
 * On submit: ONE Klaviyo Client API event, metric "Submitted Feedback", sent
 * with the brand's PUBLIC company id — no secret key exists in this page.
 * The email is read once, then wiped from the address bar.
 */
(function () {
  "use strict";

  var IDENT = ["e", "email", "_kx"];

  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") el.textContent = attrs[k];
      else if (k === "on") Object.keys(attrs.on).forEach(function (ev) { el.addEventListener(ev, attrs.on[ev]); });
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) el.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return el;
  }

  function uid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "fb-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  function anonId(brand) {
    var k = "feedback_anon_" + brand;
    try {
      var v = window.localStorage.getItem(k);
      if (!v) { v = uid(); window.localStorage.setItem(k, v); }
      return v;
    } catch (e) { return uid(); }
  }

  /* Read the link's params once; wipe the identifying ones from the address bar. */
  function readParams(search, scrub) {
    var p = new URLSearchParams(search || "");
    var out = {
      stage: (p.get("stage") || "").trim().toLowerCase(),
      email: (p.get("e") || p.get("email") || "").trim(),
      kx: (p.get("_kx") || "").trim(),
      flow: p.get("fid") || p.get("utm_campaign") || null,
      message: p.get("mid") || null,
      test: p.get("test") === "1" || p.get("test") === "true"
    };
    if (scrub && window.history && window.history.replaceState) {
      var keep = new URLSearchParams(search || "");
      IDENT.forEach(function (k) { keep.delete(k); });
      var q = keep.toString();
      try { window.history.replaceState(null, "", window.location.pathname + (q ? "?" + q : "") + window.location.hash); } catch (e) { /* sandboxed */ }
    }
    return out;
  }

  function visible(q, answers) {
    var c = q.show_if;
    if (!c) return true;
    var a = answers[c.q];
    var v = a ? a.answer : null;
    if (c.in) return c.in.indexOf(v) >= 0;
    if (c.not_in) return v !== null && v !== undefined && v !== "" && c.not_in.indexOf(v) < 0;
    return true;
  }

  function fill(s, vars) {
    return String(s || "").replace(/\{(\w+)\}/g, function (_, k) { return vars[k] !== undefined ? vars[k] : ""; });
  }

  /* The event body — pure, so tests and the preview can show exactly what is sent. */
  function buildEvent(cfg, stageId, params, answers, order, extra) {
    var st = cfg.stages[stageId];
    var list = [];
    var flat = {};
    order.forEach(function (q) {
      var a = answers[q.id];
      if (!a || a.answer === "" || a.answer === null || a.answer === undefined) return;
      var item = { id: q.id, n: q.n, question: q.text, type: q.type, answer: a.answer };
      if (a.other) item.other = a.other;
      if (q.areas) item.areas = q.areas;
      if (q.yields) item.yields = q.yields;
      list.push(item);
      flat["q_" + q.id.replace(/-/g, "_")] = a.other ? a.answer + ": " + a.other : a.answer;
    });
    var props = Object.assign({
      brand: cfg.brand,
      stage: stageId,
      stage_label: st.label || stageId,
      form_version: cfg.form_version,
      answers: list,
      answered: list.length,
      known: (cfg.known || {})[stageId] || {},
      page: extra.page,
      flow_id: params.flow,
      message_id: params.message,
      stage_fallback: !!extra.fallback,
      test: !!(params.test || cfg.force_test),
      source: "feedback-form"
    }, flat);
    var who = params.email ? { email: params.email } : params.kx ? { _kx: params.kx } : { anonymous_id: extra.anon };
    return {
      data: {
        type: "event",
        attributes: {
          properties: props,
          metric: { data: { type: "metric", attributes: { name: cfg.klaviyo.metric } } },
          profile: { data: { type: "profile", attributes: who } },
          unique_id: extra.id,
          time: extra.time
        }
      }
    };
  }

  function send(cfg, body) {
    var url = "https://a.klaviyo.com/client/events/?company_id=" + encodeURIComponent(cfg.klaviyo.public_id);
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/vnd.api+json", "accept": "application/vnd.api+json", "revision": cfg.klaviyo.revision || "2025-10-15" },
      body: JSON.stringify(body)
    }).then(function (r) {
      if (r.status >= 200 && r.status < 300) return true;
      return r.text().then(function (t) { throw new Error("Klaviyo " + r.status + " " + t.slice(0, 200)); });
    });
  }

  function mount(root, cfg, opts) {
    opts = opts || {};
    var params = opts.params || readParams(window.location.search, opts.scrub !== false);
    var stageId = opts.stage || params.stage;
    var fallback = false;
    if (!cfg.stages[stageId]) { fallback = true; stageId = cfg.default_stage; }
    var st = cfg.stages[stageId];
    var copy = cfg.copy || {};
    var mode = opts.mode || cfg.mode || "live";   // live | preview | local-test
    var answers = {};
    var pos = -1;                                   // -1 = intro
    var sent = false;

    root.classList.add("fb");
    root.setAttribute("data-brand", cfg.brand);

    function order() { return st.questions.filter(function (q) { return visible(q, answers); }); }

    function frame(kids) {
      root.innerHTML = "";
      var head = h("header", { "class": "fb-band" }, [
        cfg.look && cfg.look.logo ? h("img", { "class": "fb-logo", src: cfg.look.logo, alt: cfg.look.logo_alt || cfg.label || "" }) : h("span", { "class": "fb-wordmark", text: cfg.label || "" })
      ]);
      var bar = h("div", { "class": "fb-progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100" }, [h("span", {})]);
      var body = h("main", { "class": "fb-body", "aria-live": "polite" }, kids);
      root.appendChild(head);
      root.appendChild(bar);
      root.appendChild(body);
      if (mode === "preview") root.appendChild(h("div", { "class": "fb-flag", text: "Preview · " + stageId + " · nothing is sent" }));
      if (mode === "local-test") root.appendChild(h("div", { "class": "fb-flag", text: "Test mode · sends a test=true event" }));
      var qs = order();
      var pct = pos < 0 ? 0 : Math.round((pos / qs.length) * 100);
      bar.firstChild.style.width = pct + "%";
      bar.setAttribute("aria-valuenow", String(pct));
      var focus = body.querySelector("textarea, input");
      if (focus && opts.autofocus !== false) setTimeout(function () { try { focus.focus({ preventScroll: true }); } catch (e) { /* old browsers */ } }, 30);
    }

    // The browser's own back (button, swipe, phone gesture) steps back one question, like the form's Back link.
    var stepping = false;
    var canStep = (function () { try { return !!(window.history && window.history.pushState); } catch (e) { return false; } })();
    function mark(p, replace) {
      if (!canStep || stepping) return;
      try { window.history[replace ? "replaceState" : "pushState"]({ fb: p }, ""); } catch (e) { canStep = false; }
    }
    if (canStep) window.addEventListener("popstate", function (e) {
      if (sent) return;                               // after sending, back never reopens the questions
      var p = e.state && typeof e.state.fb === "number" ? e.state.fb : -1;
      stepping = true;
      try { if (p < 0) intro(); else go(p); } finally { stepping = false; }
    });

    function intro() {
      if (pos === -1 && !stepping) mark(-1, true);
      pos = -1;
      frame([
        h("h1", { "class": "fb-title", text: st.title || cfg.label }),
        h("p", { "class": "fb-lede", text: st.intro || "" }),
        h("button", { "class": "fb-cta", type: "button", text: copy.start || "Start", on: { click: function () { go(0); } } })
      ]);
    }

    function go(i) {
      var qs = order();
      if (i >= qs.length) return submit();
      var was = pos;
      pos = Math.max(0, i);
      if (pos > was) mark(pos, false); else mark(pos, true);
      question(qs[pos], qs);
    }

    function nav(qs, nextEnabled, onNext, isLast) {
      var kids = [h("button", { "class": "fb-back", type: "button", text: "← " + (copy.back || "Back"), on: { click: function () {
        if (canStep && window.history.state && typeof window.history.state.fb === "number") { window.history.back(); return; }
        pos === 0 ? intro() : go(pos - 1); } } })];
      if (onNext) kids.push(h("button", { "class": "fb-cta", type: "button", text: isLast ? (copy.submit || "Send") : (copy.next || "Next"), on: { click: onNext } }));
      return h("div", { "class": "fb-nav" }, kids);
    }

    function question(q, qs) {
      var isLast = pos === qs.length - 1;
      var a = answers[q.id] || {};
      var counter = h("p", { "class": "fb-step", text: fill(copy.step || "{n} of {total}", { n: pos + 1, total: qs.length }) });
      var title = h("h2", { "class": "fb-q", id: "fbq-" + q.id, text: q.text });
      var field;
      var advance = function () { if (isLast) submit(); else go(pos + 1); };
      if (q.type === "choice" || q.type === "multi") {
        var opts = (q.options || []).slice();
        if (q.other) opts.push("__other__");
        var otherBox = h("div", { "class": "fb-other" + (a.answer === "Other" ? " on" : "") }, [
          h("textarea", { rows: "2", placeholder: copy.other_placeholder || "", "aria-label": "Other", on: { input: function (ev) { answers[q.id] = { answer: "Other", other: ev.target.value.trim() }; } } })
        ]);
        if (a.other) otherBox.querySelector("textarea").value = a.other;
        field = h("div", { "class": "fb-choices", role: "radiogroup", "aria-labelledby": "fbq-" + q.id }, opts.map(function (o) {
          var label = o === "__other__" ? "Other" : o;
          var on = a.answer === label;
          return h("button", { "class": "fb-choice" + (on ? " on" : ""), type: "button", role: "radio", "aria-checked": on ? "true" : "false", text: label, on: { click: function () {
            if (label === "Other") {
              answers[q.id] = { answer: "Other", other: (answers[q.id] || {}).other || "" };
              question(q, order());
              return;
            }
            answers[q.id] = { answer: label };
            var qs2 = order();
            isLast = pos === qs2.length - 1;
            setTimeout(function () { if (pos === qs2.length - 1) submit(); else go(pos + 1); }, 160);
          } } });
        }));
        var kids = [counter, title, field];
        if (a.answer === "Other") kids.push(otherBox);
        kids.push(nav(qs, true, a.answer === "Other" ? advance : (a.answer ? advance : null), isLast));
        if (!a.answer) kids.push(h("button", { "class": "fb-skip", type: "button", text: copy.skip || "Skip", on: { click: advance } }));
        return frame(kids);
      }
      if (q.type === "scale") {
        var nums = [];
        for (var v = q.min; v <= q.max; v++) nums.push(v);
        field = h("div", { "class": "fb-scale" + (nums.length > 6 ? " wide" : ""), role: "radiogroup", "aria-labelledby": "fbq-" + q.id }, nums.map(function (n) {
          var on = a.answer === n;
          return h("button", { "class": "fb-num" + (on ? " on" : ""), type: "button", role: "radio", "aria-checked": on ? "true" : "false", text: String(n), on: { click: function () {
            answers[q.id] = { answer: n };
            setTimeout(advance, 160);
          } } });
        }));
        var ends = h("div", { "class": "fb-ends" }, [h("span", { text: q.low || "" }), h("span", { text: q.high || "" })]);
        return frame([counter, title, field, ends, nav(qs, true, a.answer !== undefined ? advance : null, isLast),
          a.answer === undefined ? h("button", { "class": "fb-skip", type: "button", text: copy.skip || "Skip", on: { click: advance } }) : null]);
      }
      var box = h(q.short ? "input" : "textarea", q.short
        ? { type: "text", "class": "fb-text", placeholder: copy.text_placeholder || "", "aria-labelledby": "fbq-" + q.id }
        : { rows: "5", "class": "fb-text", placeholder: copy.text_placeholder || "", "aria-labelledby": "fbq-" + q.id });
      box.value = a.answer || "";
      box.addEventListener("input", function () { answers[q.id] = { answer: box.value.trim() }; });
      box.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && (q.short || ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); advance(); }
      });
      return frame([counter, title, box, nav(qs, true, advance, isLast)]);
    }

    function payload() {
      return buildEvent(cfg, stageId, params, answers, order(), {
        page: window.location.origin + window.location.pathname,
        anon: anonId(cfg.brand), id: uid(), time: new Date().toISOString(), fallback: fallback
      });
    }

    function thanks(note) {
      pos = order().length;
      var t = cfg.thanks || {};
      var r = cfg.reward || {};
      var kids = [
        h("h1", { "class": "fb-title", text: t.title || "Thank you." }),
        h("p", { "class": "fb-lede", text: t.body || "" })
      ];
      if (r.line && r.code) {
        kids.push(h("p", { "class": "fb-reward-line", text: r.line }));
        kids.push(h("p", { "class": "fb-code", text: r.code }));
      }
      if (t.sign) kids.push(h("p", { "class": "fb-sign", text: t.sign }));
      if (note) kids.push(note);
      frame(kids);
    }

    function submit() {
      if (sent) return;
      var body = payload();
      if (mode === "preview") {
        var pre = h("details", { "class": "fb-payload" }, [h("summary", { text: "What would be sent to Klaviyo" }), h("pre", { text: JSON.stringify(body, null, 1) })]);
        if (typeof opts.onPreview === "function") opts.onPreview(body);
        return thanks(pre);
      }
      if (mode === "local-test") body.data.attributes.properties.test = true;
      var btn = root.querySelector(".fb-nav .fb-cta");
      if (btn) { btn.disabled = true; btn.textContent = copy.sending || "Sending…"; }
      var err = root.querySelector(".fb-error");
      if (err) err.remove();
      send(cfg, body).then(function () {
        sent = true;
        if (typeof opts.onSent === "function") opts.onSent(body);
        thanks();
      }).catch(function (e) {
        if (btn) { btn.disabled = false; btn.textContent = copy.submit || "Send"; }
        var bodyEl = root.querySelector(".fb-body");
        if (bodyEl) bodyEl.appendChild(h("p", { "class": "fb-error", role: "alert", text: copy.error || "That didn't send." }));
        if (window.console) console.warn("feedback: send failed", e && e.message);
      });
    }

    intro();
    return { stage: stageId, answers: answers, payload: payload, go: go };
  }

  var api = { mount: mount, buildEvent: buildEvent, readParams: readParams, visible: visible };
  if (typeof window !== "undefined") window.FeedbackForm = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;

  function auto() {
    var el = document.querySelector("[data-feedback-root]");
    if (!el || !window.FEEDBACK_CONFIG) return;
    var cfg = window.FEEDBACK_CONFIG;
    var logo = el.getAttribute("data-logo");
    if (logo) cfg.look = Object.assign({}, cfg.look, { logo: logo });
    mount(el, cfg, {});
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", auto);
    else auto();
  }
})();
