# Kestrel data platform (my notes)

Practice kit for the **Bronze to Gold** course. Everything here is fictional: Kestrel Valley Credit Union,
its members, complaints, disputes and staff are generated data. Phone numbers use 555-01xx, emails use
example.* domains, card numbers are public test numbers and SSNs use never-issued 000/666 prefixes.

## Start
1. Python 3.13, VS Code and Git installed (or open this folder in a GitHub Codespace).
2. `py -3.13 -m venv .venv` then `.venv\Scripts\Activate.ps1` (Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`)
3. `python -m pip install -r requirements.txt`
4. `copy .env.example .env` (Mac/Linux: `cp .env.example .env`)
5. `python tools/check_setup.py`

## What's inside
| Folder | What |
|---|---|
| `data/raw/` | Source files: members extract, Reg E dispute log (Excel), chat transcripts, comment cards, policy PDFs |
| `data/reference/` | Lookup tables: category map, branch aliases, holidays, regulations, theme rules, labeled complaints |
| `mockapi/` | Practice APIs: FormsHub (OData), GRC (table API), Boards (GraphQL). Start with `python mockapi/server.py` |
| `labs/` | Starter files for specific labs (broken scripts to fix, slow code to speed up) |
| `notebooks/databricks/` | Notebooks to import into Databricks Free Edition (Phase 10) |
| `tools/` | `check_setup.py`, `runsql.py` (run a .sql file), `q.py` (one quick query) |
| `src/kvcu/` | Your Python package. You build it during the course. |

Folders like `scripts/`, `sql/`, `tests/` and `dbt/` start empty: you create their files in the labs.
