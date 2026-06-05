# Rzeszów Buy-to-Let Yield Analyser

Surfaces the best buy-to-let investment deals from otodom.pl in **Rzeszów (Podkarpackie)**.  
Ranks sale flats by deal score: discount vs. local median + net ROI on all-in cost (purchase + renovation).

City is locked to Rzeszów. All comps, ranking, and ROI are Rzeszów-only.

---

## Quick start (sample data, no scraping)

```bash
cp .env.example .env
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api
- Health check: http://localhost:8000/api/health

The sample dataset (~50 fake Rzeszów listings across 5 districts) loads automatically on first startup.

---

## Loading your own data (json_cache)

With `DATA_SOURCE=json_cache` (the default), the app loads every data file in
`DATA_DIR` (default `backend/data/`) on each ingestion run. To refresh the data,
drop a file in that folder and restart/redeploy.

**Supported file types** (detected by extension):

| Extension | Format |
|---|---|
| `.json` | a JSON array, a `{"listings": [...]}` object, or a single object |
| `.ndjson` / `.jsonl` | newline-delimited JSON (one listing object per line) |
| `.csv` | header row + one listing per row |

**Flexible column names.** Headers may be English or Polish — they're mapped to
canonical fields automatically. For example: `cena`/`price` → `price_pln`,
`powierzchnia`/`area` → `area_m2`, `dzielnica` → `district`, `pokoje` → `rooms`,
`stan` → `finishing_condition`, `link` → `url` (see `_FIELD_ALIASES` in
`backend/app/datasources/json_cache.py` for the full list).

**Messy numbers are cleaned.** Values like `"450 000 zł"` and `"62,5 m²"` are
normalised to `450000` and `62.5` before ingestion.

**Required per listing:** `url` (used as the unique key for upsert/dedup). Other
fields are optional and default sensibly. A minimal CSV example lives at
[`backend/data/examples/sample_export.csv`](backend/data/examples/sample_export.csv)
(that `examples/` subfolder is **not** auto-loaded — only the top level of
`DATA_DIR` is scanned).

Records are de-duplicated by `url`; when multiple files contain the same URL,
the later file wins.

---

## Running without Docker (development)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

---

## Running the test suite

```bash
cd backend
python3 -m unittest discover -s tests -v
```

Tests use the stdlib `unittest` (no third-party deps required). All metric
functions (reno cost, neighbourhood stats, outlier removal, yield, deal score,
normalization) are covered with hand-checked numbers, and the json_cache loader
helpers (alias mapping, number cleaning, JSON/NDJSON/CSV parsing) are covered too.

---

## Collecting live data from Otodom

> **You** are responsible for compliance with otodom.pl's Terms of Service and
> `robots.txt`. Throttle with `REQUEST_DELAY_S` and keep `OTODOM_MAX_PAGES` modest.

Otodom is a Next.js site behind Cloudflare and offers **no public read API** for
market data (its "Eksport ogłoszeń" feature only exports an *advertiser's own*
listings). So broad market data requires scraping. Two data sources exist:

| `DATA_SOURCE` | How | Notes |
|---|---|---|
| `playwright` | headless Chromium reads each page's `__NEXT_DATA__` JSON | Passes Cloudflare; **recommended** |
| `otodom` | legacy httpx + BeautifulSoup | Usually blocked by Cloudflare; kept for reference |

### Recommended workflow: scrape locally, commit, deploy

Datacenter IPs (Render/Railway) are frequently blocked by Cloudflare, and the
headless-browser image is heavy. The reliable approach is to run the scraper on
your own machine, then commit the output for the `json_cache` source to ingest:

```bash
cd backend
pip install -r requirements.txt -r requirements-scraper.txt
playwright install chromium                       # one-time browser download

# Scrape Rzeszów sale + rent flats into a data file:
python -m scripts.scrape_otodom --out data/otodom_rzeszow.json --pages 5
#   …or CSV:  --out data/otodom_rzeszow.csv
```

Commit the resulting file under `backend/data/` and redeploy. The app ingests
every `.json` / `.ndjson` / `.csv` in `DATA_DIR` on startup (see
"Loading your own data" above). `DATA_SOURCE` can stay `json_cache`.

### Scraping from the running backend (advanced)

To have the backend scrape directly on its schedule, set `DATA_SOURCE=playwright`
and ensure Playwright + Chromium are installed in the runtime image (add
`requirements-scraper.txt` and `RUN playwright install --with-deps chromium` to
`backend/Dockerfile`). The scheduler then re-ingests every
`SCHEDULE_INTERVAL_HOURS` hours (default: 24). Note: this only works if the
host's IP isn't blocked by Cloudflare.

> **Heads-up on `finishing_condition`:** search-result data often omits it, so
> scraped listings may come through as `UNKNOWN` — which the default
> `INCLUDED_CONDITIONS` filters out. To keep them, add `unknown` to
> `INCLUDED_CONDITIONS` (they'll be costed as READY, i.e. zero renovation).

---

## Architecture

```
backend/
├── app/
│   ├── config.py            # All tunable parameters (pydantic-settings)
│   ├── models/listing.py    # SQLAlchemy ORM
│   ├── schemas/listing.py   # Pydantic response models
│   ├── datasources/
│   │   ├── base.py          # DataSource interface
│   │   ├── factory.py       # build_datasource(): json_cache / playwright / otodom
│   │   ├── json_cache.py    # Reads .json/.ndjson/.csv from DATA_DIR (alias + clean)
│   │   ├── playwright_scraper.py # Headless-Chromium scraper (reads __NEXT_DATA__)
│   │   └── otodom_scraper.py# Legacy httpx + BeautifulSoup scraper
│   ├── services/
│   │   ├── metrics.py       # Pure metric functions (testable)
│   │   └── ingestion.py     # DB upsert + condition parsing
│   ├── routers/
│   │   ├── listings.py      # GET /api/listings, GET /api/listings/{id}
│   │   └── overview.py      # GET /api/overview, GET /api/districts
│   └── scheduler.py         # APScheduler job
├── scripts/
│   └── scrape_otodom.py     # CLI: scrape -> data file for json_cache
├── requirements-scraper.txt # Optional Playwright deps
├── data/
│   ├── sample_listings.json # 50 fake Rzeszów listings
│   └── examples/            # illustrative CSV export (not auto-loaded)
└── tests/
    ├── test_metrics.py
    └── test_json_cache.py

frontend/
├── src/
│   ├── types/index.ts
│   ├── api.ts
│   ├── pages/
│   │   ├── Dashboard.tsx    # Table + filters
│   │   └── Overview.tsx     # District overview + chart
│   └── components/
│       ├── ListingTable.tsx
│       ├── FilterSidebar.tsx
│       ├── DetailDrawer.tsx
│       └── OverviewTable.tsx
```

## Metric definitions

| Metric | Formula |
|---|---|
| price_per_m2 | price_pln / area_m2 |
| reno_cost | reno_cost_per_m2[condition] x area_m2 |
| all_in_cost | price_pln + reno_cost |
| all_in_price_per_m2 | all_in_cost / area_m2 |
| discount_pct | (neighbourhood_median - all_in/m2) / neighbourhood_median |
| est_monthly_rent | area_m2 x neighbourhood_mean_rent_per_m2 |
| gross_yield_pct | est_monthly_rent x 12 / all_in_cost x 100 |
| net_yield_pct | est_monthly_rent x (1-vacancy) x (1-costs) x 12 / all_in_cost x 100 |
| deal_score | 0.5xnorm(discount) + 0.4xnorm(net_yield) + 0.1xnorm(-all_in/m2) |

All weights and assumptions are configurable via `.env`.

## Renovation cost model (defaults)

| Condition | PLN/m2 | Polish label |
|---|---|---|
| READY | 0 | do zamieszkania |
| FINISHING | 1,800 | stan deweloperski |
| RENOVATION | 2,800 | do remontu |

## ROI assumptions (defaults)

- Vacancy: 8%
- Annual costs (tax/management/maintenance): 20% of gross rent
- Denominator: **all-in cost**, not purchase price
