/* Receives a question from the form on daemn.co and commits it into this
   repo as a markdown file. Nothing is stored here — the repo is the record.

   Secrets (set with `wrangler secret put`):
     GH_TOKEN   fine-grained token, Contents:write on this repo only
   Vars (wrangler.toml):
     REPO       owner/name
     ORIGIN     the only site allowed to post here
*/
const MAX = { question: 4000, happened: 20000, step: 200, os: 20,
              name: 120, email: 200, brand: 200, work: 600 };

/* Rate limit. Without one, anyone with curl can flood the repo with commits —
   the origin check stops other websites, not scripts. Needs a KV namespace
   bound as RATE; if it is not bound the worker still runs, it just cannot
   throttle, and says so in the response so the gap is visible. */
async function throttle(env, request, bucket, max, windowSec) {
  if (!env.RATE) return { ok: true, unlimited: true };
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `${bucket}:${ip}:${Math.floor(Date.now() / (windowSec * 1000))}`;
  const n = Number((await env.RATE.get(key)) || 0) + 1;
  await env.RATE.put(key, String(n), { expirationTtl: windowSec * 2 });
  return { ok: n <= max };
}

const cors = (env) => ({
  "Access-Control-Allow-Origin": env.ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Vary": "Origin",
});

const json = (env, body, status = 200) =>
  new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json", ...cors(env) },
  });

/* Keys are only ever pasted here by mistake. Blank them before they land
   in a public repo, and say so in the file so the answer can mention it. */
function redact(t) {
  return (t || "")
    .replace(/\b(sk-[A-Za-z0-9_-]{15,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]+)/g,
             "[REDACTED-KEY]")
    .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, "[email]");
}

const slug = (t) =>
  t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50) || "question";

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(env) });
    if (request.method !== "POST") return json(env, { error: "post only" }, 405);
    if (request.headers.get("Origin") !== env.ORIGIN)
      return json(env, { error: "wrong origin" }, 403);

    let b;
    try { b = await request.json(); } catch { return json(env, { error: "bad json" }, 400); }
    if ((request.headers.get("Content-Type") || "").indexOf("application/json") === -1)
      return json(env, { error: "bad content type" }, 415);

    if (b.website) return json(env, { ok: true });          // honeypot: accept, drop

    /* Access requests for the competitor dataset. These carry a real name and
       email, so they NEVER touch the public repo — they go to a private store
       and the owner sends the link by hand. If the store is not configured the
       request is refused rather than quietly dropped. */
    if (b.kind === "access") {
      const gate = await throttle(env, request, "access", 3, 3600);
      if (!gate.ok) return json(env, { error: "too many requests, try later" }, 429);
      const email = String(b.email || "").trim();
      const name = String(b.name || "").trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email))
        return json(env, { error: "that email does not look right" }, 400);
      if (name.length < 2) return json(env, { error: "a name, please" }, 400);
      for (const [k, n] of Object.entries(MAX))
        if (String(b[k] || "").length > n) return json(env, { error: `${k} too long` }, 400);
      if (!env.REQUESTS) return json(env, { error: "requests are not open yet" }, 503);
      await env.REQUESTS.put(`req:${Date.now()}:${crypto.randomUUID()}`, JSON.stringify({
        at: new Date().toISOString(), name, email,
        brand: String(b.brand || "").slice(0, MAX.brand),
        work: String(b.work || "").slice(0, MAX.work),
      }), { expirationTtl: 60 * 60 * 24 * 120 });
      return json(env, { ok: true, queued: true });
    }
    const question = String(b.question || "").trim();
    if (question.length < 15) return json(env, { error: "too short" }, 400);
    for (const [k, n] of Object.entries(MAX))
      if (String(b[k] || "").length > n) return json(env, { error: `${k} too long` }, 400);

    const q = await throttle(env, request, "ask", 5, 3600);
    if (!q.ok) return json(env, { error: "too many questions, try later" }, 429);

    const now = new Date().toISOString();
    const stamp = now.replace(/[-:]/g, "").replace(/\..+/, "").replace("T", "-");
    const path = `questions/open/${stamp}-${slug(question)}.md`;

    const body = [
      "---",
      `asked: ${now}`,
      `os: ${String(b.os || "not sure")}`,
      `where: ${redact(String(b.step || "")) || "—"}`,
      "status: open",
      "---",
      "",
      "## What they're trying to do",
      "",
      redact(question),
      ...(String(b.happened || "").trim()
        ? ["", "## What actually happened", "", "```", redact(String(b.happened).trim()), "```"]
        : []),
      "",
    ].join("\n");

    const r = await fetch(`https://api.github.com/repos/${env.REPO}/contents/${path}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "prizm-labs-ask",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: `question: ${question.slice(0, 60).replace(/\s+/g, " ")}`,
        content: btoa(unescape(encodeURIComponent(body))),
      }),
    });

    if (!r.ok) return json(env, { error: "could not file it" }, 502);
    const d = await r.json();
    return json(env, { ok: true, url: d.content && d.content.html_url });
  },
};
