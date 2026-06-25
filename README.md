# EventLens 📊

Upload a CSV of your event data and get an **automated data report** —
column profiling, summary statistics, and interactive charts — in one click.

EventLens is a small Flask web app. Drop in a CSV and it:

- profiles every column (type, unique values, missing data)
- summarises your numeric fields (min/max/mean/median/std/sum)
- charts category breakdowns and numeric distributions
- detects a date column and plots activity over time
- keeps a history of past reports

## Features

| | |
|---|---|
| **Upload** | Drag in any `.csv` (up to 10 MB) |
| **Auto analysis** | Powered by pandas — no configuration needed |
| **Charts** | Rendered client-side with a vendored copy of Chart.js (works offline) |
| **History** | Recent reports listed on the home page |
| **Storage** | MySQL when available, with a transparent in-memory fallback |

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional — see "Database" below)
cp .env.example .env            # then edit values

# 4. Run
python app.py                   # or: flask --app app run --debug
```

Then open <http://127.0.0.1:5000>, upload `sample_events.csv` (included), and
view your report.

## Database (optional)

EventLens runs fine **without a database** — reports are simply held in memory
and don't survive a restart. To persist report history, point it at MySQL via
`.env`:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=eventlens
```

The `reports` table is created automatically on startup (see `schema.sql` for
the definition, or apply it manually with `mysql -u root -p < schema.sql`).
Verify connectivity with:

```bash
python test_db.py
```

## Project layout

```
app.py            Flask routes (home, upload, report, delete)
analysis.py       CSV → report dictionary (pandas)
storage.py        Save/list/get reports; MySQL + in-memory fallback
db.py             MySQL connection + schema bootstrap
schema.sql        Reference DDL for the reports table
templates/        Jinja2 templates (base, index, report, 404)
static/           CSS, charts.js, and vendored Chart.js
tests/            pytest suite for analysis and routes
sample_events.csv Example data to try the app
```

## Running the tests

```bash
pip install pytest
pytest
```

## Notes

- `.env` is gitignored — never commit real credentials. Use `.env.example`
  as the template.
- Chart.js is vendored under `static/js/vendor/` so charts render without a CDN.
