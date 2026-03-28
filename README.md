# Regulatory AI Copilot

Regulatory AI Copilot is a local-first compliance workbench for turning regulatory documents into structured controls, drafting business-specific policies, and producing implementation and audit artifacts.

It is designed for teams who want to:

- upload regulatory PDFs and extract usable text
- search regulation content
- generate structured controls from regulation text
- capture organization-specific business context
- build policy blueprints
- draft policies from those blueprints
- maintain a control registry and company control inventory
- run policy gap assessments against controls

## Who This Is For

This project is useful for:

- compliance teams
- internal audit teams
- governance, risk, and compliance consultants
- product or security teams building regulated products
- developers extending a compliance copilot internally

## Current Product Capabilities

The current Streamlit app provides 8 tabs:

1. `Upload & Save`
   Save text-based PDF pages into JSONL for downstream processing.
2. `Index & Search`
   Build a searchable index from saved JSONL files and retrieve requirement-like statements.
3. `Controls`
   Extract controls from processed regulations and save them as JSON and CSV.
4. `Business Profile`
   Capture organization context such as regulator, sector, business model, and cloud/data posture.
5. `Policy Blueprint`
   Create a saved blueprint using controls, profile context, and optional reference policy text.
6. `Artifact Generator`
   Generate a policy draft, implementation plan, audit register, and traceability matrix from a blueprint.
7. `Control Registry`
   Review the control master and update company-specific control inventory fields like status and owner.
8. `Policy Gap Analyzer`
   Compare a policy or current-state narrative against controls and produce gap results.

## Important Product Notes

- The app is currently local-first and file-backed for most workflows.
- The LLM layer expects a locally reachable Ollama-compatible endpoint by default.
- The current search backend defaults to a safe keyword index, not semantic vector search.
- OCR is not implemented yet. Scanned PDFs are not supported.
- The database layer exists as a foundation, but the main user workflows are still mostly file-based today.

## Tech Stack

- Python
- Streamlit
- Pydantic
- SQLAlchemy
- Ollama-compatible LLM endpoint
- JSON / CSV local persistence

## Repository Structure

High-level structure:

```text
app/
  pages/
  components/
core/
domain/
models/
orchestrators/
schemas/
services/
tests/
configs/
data/
```

Layer summary:

- `app/`
  Streamlit UI and page routing.
- `orchestrators/`
  Workflow-level sequencing so pages do not call low-level modules directly.
- `domain/`
  Business logic for regulations, controls, policies, evidence, gaps, readiness, and tasks.
- `services/`
  LLM, ingestion, exports, DB, and storage-oriented modules.
- `schemas/`
  Pydantic models used to reduce loose dict passing.
- `models/`
  SQLAlchemy ORM models for the DB foundation.
- `core/`
  Compatibility and legacy modules still used during migration.
- `data/`
  Local runtime storage for processed files, controls, blueprints, artifacts, gap runs, and registry data.

## Prerequisites

Minimum recommended setup:

- Python `3.9+`
- `pip`
- `venv`
- Ollama installed and available locally if you want LLM-backed features

Optional but helpful:

- Git
- a local SQLite-capable Python environment

## 1. Clone The Repository

```bash
git clone https://github.com/puroabhishek/regulatory-ai-copilot.git
cd regulatory-ai-copilot
```

## 2. Install Dependencies

### Option A: Use the provided setup script

```bash
chmod +x setup.sh
./setup.sh
```

### Option B: Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure Environment Variables

Create a local `.env` file in the project root.

Example:

```env
DEFAULT_LLM_MODEL=qwen2.5:3b
CONTROL_CLASSIFIER_MODEL=qwen2.5:3b
GAP_ANALYSIS_MODEL=qwen2.5:3b
POLICY_GENERATION_MODEL=qwen2.5:3b

OLLAMA_URL=http://localhost:11434/api/chat

LLM_TIMEOUT_SECONDS=600
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=1

INDEX_BACKEND=keyword
KEYWORD_INDEX_PATH=data/chroma_db/keyword_chunks.json

# Optional DB override
# DATABASE_URL=sqlite:///data/app.db
```

What matters most:

- `DEFAULT_LLM_MODEL`
  Fallback model used when no workflow-specific model is set.
- `CONTROL_CLASSIFIER_MODEL`
  Used for control classification.
- `GAP_ANALYSIS_MODEL`
  Used for policy coverage analysis in the gap analyzer.
- `POLICY_GENERATION_MODEL`
  Used for policy drafting.
- `OLLAMA_URL`
  Default is `http://localhost:11434/api/chat`.

## 4. Start Ollama

If you want the LLM-backed features to work, start Ollama and make sure your selected models are available.

Example:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen2.5:3b
```

If you use different models, update `.env` accordingly.

## 5. Run The App

### Option A: Use the run script

```bash
chmod +x run.sh
./run.sh
```

### Option B: Manual run

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
streamlit run app/ui.py
```

Then open:

```text
http://localhost:8501
```

## First-Time Usage Flow

If you are starting from scratch, the smoothest order is:

1. Go to `Upload & Save`
   Upload a text-based regulatory PDF and save the extracted pages.
2. Go to `Index & Search`
   Build the index and search for clauses or obligations.
3. Go to `Controls`
   Extract controls from the saved processed regulation.
4. Go to `Business Profile`
   Save the organization profile you want the generated outputs to reflect.
5. Go to `Policy Blueprint`
   Select controls and a business profile, then save a blueprint.
6. Go to `Artifact Generator`
   Generate the policy draft and supporting CSV artifacts.
7. Go to `Control Registry`
   Review and update the company-specific control inventory.
8. Go to `Policy Gap Analyzer`
   Compare an existing policy or current-state text against selected controls.

## Supported Input Files

Current ingestion support:

- `.txt`
- `.md`
- `.pdf`
- `.docx`
- `.csv`
- `.xlsx`

Important caveats:

- `.pdf` must be text-based. OCR is not available yet.
- legacy `.doc` is not supported directly
- `.docx` support requires `python-docx`
- `.xlsx` support requires `pandas` and a compatible Excel engine such as `openpyxl`

If you need those optional readers, install:

```bash
pip install python-docx pandas openpyxl
```

If you only use PDF, TXT, and MD workflows, the base setup is enough.

## Current Storage Model

The app creates and uses local folders under `data/`.

Examples:

- `data/processed/`
  extracted page-level JSONL files
- `data/controls/`
  extracted controls JSON and CSV
- `data/profiles/`
  saved business profiles
- `data/blueprints/`
  saved policy blueprints
- `data/artifacts/`
  generated policy and CSV artifacts
- `data/control_registry/`
  local control registry data
- `data/gap_analysis/`
  saved gap runs

These folders are created automatically on startup by `app/ui.py`.

## Optional Database Initialization

The project now includes a DB foundation with SQLAlchemy models under `models/` and setup helpers under `services/db/`.

This is optional for current usage.

To initialize the local SQLite database:

```bash
source .venv/bin/activate
python -c "from services.db.session import create_all_tables; create_all_tables()"
```

By default this creates:

```text
data/app.db
```

To use PostgreSQL later, set:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/regulatory_ai
```

## Search Backend Note

The current index/search feature defaults to a safe keyword backend.

That means:

- the app will still let you build and query an index
- the current behavior is more stable in local environments
- semantic vector search is not the default runtime path right now

This is intentional to avoid Python crashes caused by native ML/vector dependencies in some environments.

## Troubleshooting

### The app starts but LLM features fail

Check:

- Ollama is running
- your `.env` file exists
- the configured model names are valid
- the model is actually pulled locally

### I get `No LLM model configured`

Set at least:

```env
DEFAULT_LLM_MODEL=qwen2.5:3b
```

### I get a timeout or connection error to Ollama

Check:

- `OLLAMA_URL`
- Ollama server status
- firewall or localhost access issues

### PDF upload says little or no text was extracted

The PDF is probably scanned or image-based.

Current limitation:

- no OCR support yet

### DOCX support fails

Install:

```bash
pip install python-docx
```

### XLSX support fails

Install:

```bash
pip install pandas openpyxl
```

### Streamlit port already in use

Run on a different port:

```bash
streamlit run app/ui.py --server.port 8502
```

### I changed code and imports behave strangely

Use:

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
streamlit run app/ui.py
```

## Developer Notes

- `core/` still contains compatibility modules during migration.
- `orchestrators/` is the preferred place for multi-step workflows.
- `domain/` is the preferred place for business rules.
- `services/` is the preferred place for infrastructure integrations.
- `schemas/` should be preferred over loose dicts for feature areas already modeled.

## Recommended Git Workflow For New Users

```bash
git clone https://github.com/puroabhishek/regulatory-ai-copilot.git
cd regulatory-ai-copilot
./setup.sh
./run.sh
```

Create `.env` manually using the example in this README before the first real LLM-backed run.

## Current Limitations

- no OCR for scanned PDFs
- DB-backed persistence is not the default flow yet
- keyword search is the default search backend today
- some optional file readers require extra packages not listed in `requirements.txt`
- parts of the codebase still use compatibility modules under `core/`

## Contributing

If you are extending the project:

- keep page files thin
- put workflow sequencing in `orchestrators/`
- put business rules in `domain/`
- put transport, IO, and integration logic in `services/`
- avoid aggressive deletion of legacy modules until replacement paths are fully migrated

## Support

If someone new is onboarding to the project, the fastest path is:

1. install dependencies
2. configure `.env`
3. start Ollama
4. run Streamlit
5. follow the 8 tabs in order from ingestion to gap analysis

That should be enough for a new user to clone the repo, start the product locally, and use the main workflows without reading the code first.
