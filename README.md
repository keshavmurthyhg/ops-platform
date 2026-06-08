# OPS Platform

A modular Flask application for Operations, Reporting, and Analytics tools.

---

## Project Structure

```
my-apps/
│
├── app.py                      ← Combined app (runs ALL modules)
│
├── common/                     ← Shared utilities used across modules
│   ├── config.py               ← Central config (API toggles, credentials)
│   ├── path_helper.py          ← sys.path helper for standalone runs
│   ├── logger.py
│   ├── data/                   ← Shared data loaders (SNOW, etc.)
│   ├── ui/                     ← Shared UI components (preview, buttons)
│   └── utils/                  ← Shared utilities (parsers, links, etc.)
│
├── operations_center/          ← Operations Center module
│   ├── app.py                  ← Standalone app (port 5001)
│   ├── operations_center_routes.py
│   └── module/                 ← All business logic
│
├── report/                     ← RCA Report Generator
│   ├── app.py                  ← Standalone app (port 5002)
│   ├── report_routes.py
│   └── module/
│
├── search/                     ← Incident Search
│   ├── app.py                  ← Standalone app (port 5003)
│   ├── search_routes.py
│   └── module/
│
├── converter/                  ← PPT → Word Converter
│   ├── app.py                  ← Standalone app (port 5004)
│   ├── converter_routes.py
│   └── module/
│
├── bulk/                       ← Bulk Report Generator
│   ├── app.py                  ← Standalone app (port 5005)
│   ├── bulk_routes.py
│   └── module/
│
├── excel_compare/              ← Excel Compare (v2)
│   ├── app.py                  ← Standalone app (port 5006)
│   └── module/
│
├── excel_merge/                ← Excel Merge / Deduplication
│   ├── app.py                  ← Standalone app (port 5007)
│   ├── excel_merge_routes.py
│   └── module/
│
├── dcn_sequence/               ← DCN Sequence Processor
│   ├── app.py                  ← Standalone app (port 5008)
│   ├── dcn_sequence_routes.py
│   └── module/
│
├── dcn_analytics/              ← DCN Analytics Dashboard
│   ├── app.py                  ← Standalone app (port 5009)
│   ├── dcn_analytics_routes.py
│   └── module/
│
├── static/                     ← CSS / JS / Images (shared)
├── templates/                  ← HTML templates (shared)
├── data/                       ← Local Excel/CSV data files
├── jobs/                       ← Background/scheduled jobs
│
├── uploads/                    ← Auto-created on first run
├── outputs/                    ← Auto-created on first run
│
├── .env.example                ← Copy to .env and fill credentials
└── README.md
```

---

## Running the App

### Run All Modules Together

```bash
python app.py
```

Opens at: http://localhost:5000

---

### Run a Single Module (Standalone)

Each module has its own `app.py` and runs independently. Useful for sharing
a single tool without the whole platform.

| Module            | Command                              | Port  |
|-------------------|--------------------------------------|-------|
| Operations Center | `python operations_center/app.py`    | 5001  |
| Report Generator  | `python report/app.py`               | 5002  |
| Search            | `python search/app.py`               | 5003  |
| PPT Converter     | `python converter/app.py`            | 5004  |
| Bulk Generator    | `python bulk/app.py`                 | 5005  |
| Excel Compare     | `python excel_compare/app.py`        | 5006  |
| Excel Merge       | `python excel_merge/app.py`          | 5007  |
| DCN Sequence      | `python dcn_sequence/app.py`         | 5008  |
| DCN Analytics     | `python dcn_analytics/app.py`        | 5009  |

> **Important:** Always run from the **project root**, not from inside a
> module folder. The modules resolve templates, static files, and data
> files relative to the project root.
>
> ```bash
> cd /path/to/my-apps
> python operations_center/app.py   ✅
> cd operations_center && python app.py   ❌ (paths will break)
> ```

---

## Configuration

Copy `.env.example` to `.env` and fill in credentials:

```bash
cp .env.example .env
```

Then edit `.env`:

```
SNOW_PASSWORD=your_password
AZURE_PAT=your_pat_token
PTC_PASSWORD=your_password
```

API toggles are in `common/config.py`:

```python
USE_SNOW_API  = False   # True = live ServiceNow API
USE_AZURE_API = True    # True = live Azure DevOps API
USE_PTC_API   = False   # True = live PTC REST API
```

When an API is off, the module falls back to the local Excel/CSV files in `data/`.

---

## Adding a New Module

1. Create a folder: `my_module/`
2. Add `my_module/my_module_routes.py` with a Flask Blueprint
3. Add `my_module/module/` with business logic
4. Add `my_module/app.py` (copy from any existing module, change blueprint import + port)
5. Register the blueprint in `app.py`
