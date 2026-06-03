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
source .venv/bin/activate
pytest tests/ -v
```

All metric functions (reno cost, neighbourhood stats, outlier removal, yield, deal score, normalization) are covered with hand-checked numbers.

---

## Enabling the live otodom scraper

> **You** are responsible for compliance with otodom.pl's Terms of Service.  
> The scraper respects `robots.txt`, uses a descriptive User-Agent, and throttles to ≤ 1 req/2s.

```bash
# In .env:
DATA_SOURCE=otodom
REQUEST_DELAY_S=2.0   # do not lower below 2
```

Restart the backend. The scheduler re-ingests every `SCHEDULE_INTERVAL_HOURS` hours (default: 24).

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
│   │   ├── json_cache.py    # Reads *.json files from DATA_DIR
│   │   └── otodom_scraper.py# Live scraper (robots.txt + throttle)
│   ├── services/
│   │   ├── metrics.py       # Pure metric functions (testable)
│   │   └── ingestion.py     # DB upsert + condition parsing
│   ├── routers/
│   │   ├── listings.py      # GET /api/listings, GET /api/listings/{id}
│   │   └── overview.py      # GET /api/overview, GET /api/districts
│   └── scheduler.py         # APScheduler job
├── data/
│   └── sample_listings.json # 50 fake Rzeszów listings
└── tests/test_metrics.py

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
