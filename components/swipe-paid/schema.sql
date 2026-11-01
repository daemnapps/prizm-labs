-- Swipe corpus. One row per brand, copy block, ad, page.
--
-- A BLOCK is ads that share one paragraph of copy — mechanical, a GROUP BY.
-- It is NOT an angle: an angle is the read on a problem, signed in the
-- brand's strategy/angles.json, and it lives on `creatives.angle` where a
-- person put it. One angle can run across many blocks.
--
-- Rebuilt from each brand's blocks.json + pages.json by `build.py db`.
-- Derived and disposable: nothing lives here that isn't in those files,
-- so it is gitignored and rebuilt rather than migrated.

CREATE TABLE IF NOT EXISTS brands (
  brand         TEXT PRIMARY KEY,
  domain        TEXT,
  swept         TEXT,
  creatives     INTEGER,
  blocks        INTEGER,
  pages         INTEGER,
  video         INTEGER,
  image         INTEGER,
  per_block     REAL,      -- creatives / blocks: copy-lock vs copy-churn
  drive_path    TEXT
);

CREATE TABLE IF NOT EXISTS blocks (
  brand         TEXT NOT NULL,
  nn            TEXT,      -- rank by creative volume, "01" carries the most
  slug          TEXT NOT NULL,
  headline      TEXT,
  primary_text  TEXT,
  stage         TEXT,      -- bottom | mid | top | unclassified (heuristic, see STAGE_RULES)
  seasonal      INTEGER,   -- 1 = dated promo (Back To School, Black Friday…): a volume play, not strategy
  creatives     INTEGER,
  video_count   INTEGER,
  image_count   INTEGER,
  variants      INTEGER,   -- summed ad variants across the block: heat signal #1
  max_variants  INTEGER,   -- the single most-cloned creative in the block
  landing_page  TEXT,
  page_slug     TEXT,      -- joins pages.slug
  drive_path    TEXT,
  PRIMARY KEY (brand, slug)
);

CREATE TABLE IF NOT EXISTS ads (
  ad_id         TEXT NOT NULL,
  brand         TEXT NOT NULL,
  block_slug    TEXT NOT NULL,
  media_type    TEXT,      -- video | image, as the ad tool reports it
  variants      INTEGER,   -- near-identical ad variants running this creative
  video_url     TEXT,
  image_url     TEXT,
  drive_file    TEXT,      -- path under the brand's Drive folder
  -- The naming convention's own fields (components/naming/names.py,
  -- CREATIVE_FIELDS), so a swiped ad and one of ours group on the same
  -- columns. `media` is the convention's word (static, not image);
  -- media_type above is kept as the tool said it, unedited.
  -- Everything but media and ratio is 'unclassified' until a person judges
  -- it — written, never blank, because blank reads as an answer.
  swipe_id      TEXT,      -- swipe:<brand>:<ad_id> — what a manifest keeps
  media         TEXT,      -- static | video | carousel
  source        TEXT,      -- ai | ugc | studio | mixed
  talent        TEXT,      -- who is in it, or none
  problem       TEXT,      -- the customer problem it speaks to
  angle         TEXT,      -- the angle on that problem
  concept       TEXT,      -- the execution of that angle
  format        TEXT,      -- the template it was built in
  ratio         TEXT,      -- 9x16 | 4x5 | 1x1 | 16x9 | WxH, measured
  -- The swipe library's own call, deliberately NOT one of the shared fields:
  -- the fields describe a creative, the verdict decides what we do about it.
  verdict       TEXT,      -- swipe | pass | '' (not yet decided)
  PRIMARY KEY (brand, ad_id)
);

CREATE TABLE IF NOT EXISTS pages (
  brand         TEXT NOT NULL,
  slug          TEXT NOT NULL,
  url           TEXT,
  page_type     TEXT,      -- quiz | listicle | advertorial | product-page
  height        INTEGER,
  blocks_served INTEGER,
  ads_served    INTEGER,
  drive_path    TEXT,
  PRIMARY KEY (brand, slug)
);

CREATE INDEX IF NOT EXISTS idx_blocks_brand   ON blocks(brand);
CREATE INDEX IF NOT EXISTS idx_blocks_volume  ON blocks(creatives DESC);
CREATE INDEX IF NOT EXISTS idx_ads_angle      ON ads(brand, block_slug);
CREATE INDEX IF NOT EXISTS idx_pages_type     ON pages(page_type);

-- Every copy block with its page, across all brands.
CREATE VIEW IF NOT EXISTS block_page AS
SELECT a.brand, a.nn, a.headline, a.creatives, a.video_count, a.image_count,
       p.page_type, p.height, a.landing_page
FROM blocks a LEFT JOIN pages p ON p.brand = a.brand AND p.slug = a.page_slug
ORDER BY a.brand, a.creatives DESC;

-- The copy-lock signal: how hard each brand rides one block of copy.
CREATE VIEW IF NOT EXISTS copy_lock AS
SELECT brand, creatives, blocks, per_block,
       (SELECT COUNT(*) FROM blocks x WHERE x.brand = b.brand AND x.creatives = 1)
         AS singleton_blocks
FROM brands b ORDER BY per_block DESC;

-- Every swiped creative in the naming convention's columns. Group this the
-- way you group a Meta export, and the two answers are comparable.
CREATE VIEW IF NOT EXISTS swipe_creatives AS
SELECT a.swipe_id, a.brand AS origin, a.media, a.source, a.talent,
       a.problem, a.angle, a.concept, a.format, a.ratio, a.verdict,
       a.variants, g.stage, g.headline, g.landing_page
FROM ads a JOIN blocks g ON g.brand = a.brand AND g.slug = a.block_slug;

-- What still needs a human. The judging queue, biggest blocks first.
CREATE VIEW IF NOT EXISTS to_judge AS
SELECT a.brand, g.nn, g.headline, COUNT(*) AS creatives,
       SUM(a.source = 'unclassified') AS need_source,
       SUM(a.problem = 'unclassified') AS need_problem,
       SUM(a.concept = 'unclassified') AS need_concept
FROM ads a JOIN blocks g ON g.brand = a.brand AND g.slug = a.block_slug
GROUP BY a.brand, g.slug
HAVING need_source + need_problem + need_concept > 0
ORDER BY creatives DESC;

-- What we decided to steal. The shortlist a production run is built from.
CREATE VIEW IF NOT EXISTS swiped AS
SELECT a.swipe_id, a.brand AS origin, g.nn, g.headline, a.variants,
       a.media, a.source, a.talent, a.problem, a.angle, a.concept,
       a.format, a.ratio, a.drive_file, g.landing_page
FROM ads a JOIN blocks g ON g.brand = a.brand AND g.slug = a.block_slug
WHERE a.verdict = 'swipe'
ORDER BY a.variants DESC;
