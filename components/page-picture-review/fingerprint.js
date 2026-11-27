/* Structural fingerprint of a rendered demo page.

   Run on the ORIGINAL demo and again on the staged BUNDLE, at the SAME
   viewport, then diff the two with `bundle.py compare`. Careful staging cannot
   prove the copy matches; this can — it is the only step that reads what the
   browser actually drew.

   Everything recorded is origin-independent: URLs are reduced to basenames, so
   `../<kit>/src/.../hero-desktop.jpg` and `assets/img/hero-desktop.jpg`
   fingerprint identically. A MISSING file still does not (naturalWidth 0), and
   a missing font still does not (the computed family falls back) — which is the
   whole point.

   Per-element detail is hashed rather than returned: 400 elements of computed
   style is megabytes of noise to carry around, and all we need to know is
   WHETHER an element differs and WHICH. Rerun with window.FP_DETAIL = [i, j]
   to get the raw records for the elements that differ.

   Returns an object; JSON.stringify it and save as <name>.json. */
(async () => {
  // Warm-up. Most of this page's pictures are lazy, so a cold measurement calls
  // 36 of 52 images "broken" when nothing is wrong — they simply have not been
  // asked for yet. Force them, scroll to trip any IntersectionObserver, and wait
  // for decode, so `imgBroken` means MISSING and nothing else.
  const all = [...document.querySelectorAll('img')];
  all.forEach(i => { i.loading = 'eager'; if (!i.complete) i.src = i.src; });
  scrollTo(0, document.body.scrollHeight);
  await new Promise(r => setTimeout(r, 1200));
  scrollTo(0, 0);
  await Promise.all(all.map(i => i.decode().catch(() => {})));
  await document.fonts.ready;
  await new Promise(r => setTimeout(r, 400));

  const base = u => (u || '').split('?')[0].split('/').pop();
  const bg = el => {
    const m = /url\(["']?([^"')]+)/.exec(getComputedStyle(el).backgroundImage || '');
    return m ? base(m[1]) : '';
  };
  // djb2 — short, stable, and good enough to tell two rendered pages apart
  const hash = s => {
    let h = 5381;
    for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  };

  const imgs = [...document.querySelectorAll('img')];

  // A stable, document-order sample of everything whose rendering would change
  // if an asset or a font went missing.
  // The offer box carries a live countdown ("Order within 03:32"). Its rendered
  // width changes with the digits, so two honest measurements of the SAME page
  // disagree on it. Anything clock-shaped is counted and then left out of the
  // digest — otherwise the gate cries wolf on every run.
  const VOLATILE = /\b\d{1,2}:\d{2}\b/;
  const candidates = [...document.querySelectorAll(
    'img, h1, h2, h3, p, button, span[style], div[style*="url("]')].slice(0, 400);
  const volatileCount = candidates.filter(el => VOLATILE.test(el.textContent || '')).length;
  const els = candidates.filter(el => !VOLATILE.test(el.textContent || ''));

  const record = el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      tag: el.tagName.toLowerCase(),
      w: Math.round(r.width), h: Math.round(r.height),
      font: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight, color: cs.color,
      img: el.tagName === 'IMG' ? base(el.currentSrc || el.src) : '',
      natural: el.tagName === 'IMG' ? el.naturalWidth : null,
      bg: bg(el)
    };
  };

  const records = els.map(record);
  const hashes = records.map(r => hash(JSON.stringify(r)));

  // Which families the browser actually loaded — the check that would have
  // caught the missing Marlide/Mundial faces on 2026-09-18.
  const loaded = new Set();
  document.fonts.forEach(f => { if (f.status === 'loaded') loaded.add(f.family); });

  const out = {
    viewport: innerWidth + 'x' + innerHeight,
    imgTotal: imgs.length,
    imgBroken: imgs.filter(i => !i.complete || i.naturalWidth === 0).length,
    brokenList: imgs.filter(i => !i.complete || i.naturalWidth === 0)
      .map(i => base(i.currentSrc || i.src)).slice(0, 20),
    fontsStatus: document.fonts.status,
    fontsLoaded: [...loaded].sort(),
    badges: document.querySelectorAll('#pic-index-layer span').length,
    sampleCount: records.length,
    volatileSkipped: volatileCount,
    digest: hash(hashes.join('|')),
    hashes
  };
  if (window.FP_DETAIL) out.detail = window.FP_DETAIL.map(i => ({ i, ...records[i] }));
  return out;
})()
