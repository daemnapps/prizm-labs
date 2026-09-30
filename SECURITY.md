# Security

This repo is public and its history is permanent. Everything below exists so
that a mistake here costs an edit, not a rotation.

## What is exposed, and what is not

**Public:** the site, the sixteen tools and their prompts, and this repo's
history. All of it is words and pictures — no code that runs on anyone's
machine but their own.

**Never public:** API keys, any brand's private data, the competitor sweep
records, and anyone's email address. Those live outside this repo entirely.

**Verified 2026-09-04:** no credential file has ever been added in this repo's
history, and no key-shaped string exists in any tracked file.

## The commit guard

`.githooks/pre-commit` refuses any commit that carries a credential file
(`.env`, `.key`, `.pem`, service-account JSON), a key-shaped string (OpenAI,
Google, GitHub, Slack, AWS, Apify, GitLab, Figma, or a PEM private key block),
or a path off someone's own machine.

Activate it once per clone:

```
git config core.hooksPath .githooks
```

It is deliberately cheap and slightly over-eager. If it blocks something that
is genuinely fine, `--no-verify` exists — but if it blocked a real key, the
key is already compromised on your disk history. Rotate it; do not just
unstage it.

## The receiver

`receiver/worker.js` is the only thing on this project that accepts input from
strangers. It is a Cloudflare Worker and it holds one secret.

What protects it:

- **POST and JSON only**, from one allowed origin.
- **Rate limited** per IP — 5 questions and 3 access requests an hour. Needs a
  KV namespace bound as `RATE`; without it the worker still runs but cannot
  throttle, which is the one thing to check after deploying.
- **A honeypot field** that silently drops bots.
- **Length caps** on every field, so nothing large gets committed.
- **Redaction** — anything key-shaped or email-shaped is blanked before a
  question is written into the public repo.
- **A fine-grained token**, Contents:write on this repo only. It cannot read
  private repos, cannot touch settings, cannot act anywhere else.

Access requests (name, email, who they work for) are **never written to this
repo**. They go to a private KV store bound as `REQUESTS` and are answered by
hand. If that binding is missing the worker refuses the request rather than
dropping it silently.

## If a key ever does leak

1. Rotate it at the provider first. Deleting the commit does not un-publish it.
2. Then remove it from the tree and push.
3. Check the provider's usage log for anything that is not you.

## Reporting something

Open an issue, or use the question form on daemn.co. If it is a live
vulnerability, do not put the details in a public issue — say that you have
found one and how to reach you.
