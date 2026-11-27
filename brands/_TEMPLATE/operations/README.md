# operations

A new brand's own operations files go here: `brand.json` and `products.json`
(same shape as brands/<brand>/operations/). Tools find a brand by
`brands/<brand>/operations/brand.json` (components/metrics/brand_paths.py).

Shared by every brand, never copied here: `components/metrics/warehouse-fees.json`
(warehouse fees) and `platform/data/metrics/supply-pipeline.json` (stock on the way).
