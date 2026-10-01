/**
 * Stamp every local asset URL with a content hash after the build.
 *
 * Netlify serves these with `max-age=0, must-revalidate`, which is correct —
 * but a browser that has already cached a copy can keep showing it, so a fix
 * that is live on the server still looks broken to whoever is reviewing the
 * page. A hash in the URL makes a changed file a different URL, so there is
 * nothing to revalidate and nothing to get wrong.
 *
 * Images matter more than the stylesheets did: _headers marks every image
 * `max-age=2592000, immutable`, so replacing an icon at the same path leaves
 * every browser that has seen the page showing the old one for a month. That
 * is exactly what happened to the first <brand> icon set.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SITE = path.join(__dirname, '_site');
const hashes = new Map();

function hashFor(urlPath) {
  if (hashes.has(urlPath)) return hashes.get(urlPath);
  const file = path.join(SITE, urlPath.replace(/^\//, ''));
  let h = null;
  if (fs.existsSync(file)) {
    h = crypto.createHash('md5').update(fs.readFileSync(file)).digest('hex').slice(0, 8);
  }
  hashes.set(urlPath, h);
  return h;
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (entry.name.endsWith('.html')) out.push(full);
  }
  return out;
}

let stamped = 0;
for (const page of walk(SITE)) {
  const before = fs.readFileSync(page, 'utf8');
  const after = before.replace(/(["'])(\/icon\/(?:css|js|images|img|video|fonts)\/[^"'?#]+\.(?:css|js|svg|png|jpg|jpeg|webp|gif|avif|mp4|webm|woff2))\1/g, (m, q, url) => {
    const h = hashFor(url);
    return h ? `${q}${url}?v=${h}${q}` : m;
  });
  if (after !== before) {
    fs.writeFileSync(page, after);
    stamped++;
  }
}
console.log(`[stamp] versioned assets in ${stamped} pages`);
