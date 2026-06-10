# OPS Platform

A modular Flask operations platform. Every module is **fully self-contained** and can run standalone or together as one combined app.

---

## Running the Platform

### Combined (all modules together)
```
python app.py
```
Serves all modules on a single Flask server (default port 5000).

### Standalone (one module at a time)
```
python bulk/app.py              → http://localhost:5005
python converter/app.py         → http://localhost:5004
python dcn_analytics/app.py     → http://localhost:5009
python dcn_sequence/app.py      → http://localhost:5008
python excel_compare/app.py     → http://localhost:5006
python excel_merge/app.py       → http://localhost:5007
python operations_center/app.py → http://localhost:5001
python report/app.py            → http://localhost:5002
python search/app.py            → http://localhost:5003
```

---

## Architecture

### Module Structure
Every module follows the same self-contained layout (mirroring `excel_compare`):

```
<module>/
├── app.py                  ← Standalone Flask entry point
├── <module>_routes.py      ← Blueprint with template_folder + static_folder
├── templates/
│   └── <module>.html       ← Module page (extends main.html)
├── statics/
│   ├── <module>.css        ← Module-specific styles
│   └── <module>.js         ← Module-specific scripts
├── module/                 ← Business logic
│   ├── logic.py / logic/
│   └── services/
├── uploads/                ← Created at runtime
└── __init__.py
```

### Common Package
Shared layout, CSS, JS, and images live in `common/`:

```
common/
├── common_blueprint.py     ← Flask Blueprint named 'common_static'
├── templates/
│   ├── main.html           ← Base layout template (extended by all modules)
│   ├── home.html           ← Home page base
│   └── index.html          ← Combined platform home page
├── static/
│   ├── css/common.css      ← Global styles
│   ├── js/common.js        ← Global scripts
│   └── images/             ← Shared images (filter.png etc.)
├── config.py
├── home_help_provider.py
├── logger.py
├── path_helper.py
├── data/                   ← SNOW / data fetchers
├── ui/                     ← Shared UI components
└── utils/                  ← Shared utilities
```

### Static Asset URL Conventions

| Asset type        | url_for call                                              |
|-------------------|-----------------------------------------------------------|
| Module CSS/JS     | `url_for('<module>.static', filename='<module>.css')`     |
| excel_merge CSS/JS| `url_for('excel_merge_bp.static', filename='...')`        |
| Common CSS/JS     | `url_for('common_static.static', filename='css/common.css')`     |
| Shared images     | `url_for('common_static.static', filename='images/filter.png')`  |

### Blueprint Registration Pattern

Every `app.py` (standalone or root) follows the same pattern:

```python
app.register_blueprint(common_bp)          # always first
app.register_blueprint(<module>_bp)        # then module blueprints
```

`common_bp` must be registered first so Flask discovers `main.html` and shared static assets before any module template tries to extend it.

---

## Adding a New Module

1. Create `<module>/` following the structure above.
2. Define the Blueprint with:
   ```python
   <module>_bp = Blueprint(
       "<module>",
       __name__,
       template_folder="templates",
       static_folder="statics",
       static_url_path="/<module>/static"
   )
   ```
3. Put `<module>.html`, `<module>.css`, `<module>.js` in the respective folders.
4. In `<module>.html` reference statics as:
   ```
   {{ url_for('<module>.static', filename='<module>.css') }}
   ```
5. Write a standalone `app.py` that registers `common_bp` then your blueprint.
6. Add the blueprint import and registration to the root `app.py`.
