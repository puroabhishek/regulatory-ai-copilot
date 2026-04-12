# Regulatory AI Copilot

Regulatory AI Copilot is a local-first compliance workbench for turning regulatory documents into structured controls, drafting business-specific policies, and producing implementation and audit artifacts.

It is designed for teams who want to:

- capture organization-specific business context
- recommend likely regulations and guidelines from that business profile
- draft policies from profile context plus applicable regulations
- run policy gap assessments against profile-linked regulation sources
- upload regulatory PDFs and extract usable text
- search regulation content
- generate structured controls from regulation text
- build reusable policy blueprints
- generate implementation and audit artifacts from those blueprints
- maintain a control registry and company control inventory
- review and tune statement classification behavior

## Who This Is For

This project is useful for:

- compliance teams
- internal audit teams
- governance, risk, and compliance consultants
- product or security teams building regulated products
- developers extending a compliance copilot internally

## Current Product Capabilities

The current Streamlit app provides 9 tabs:

1. `Business Profile`
   Capture business context, review suggested regulations and guidelines, and save the applicable set with the profile.
2. `Policy Generator`
   Draft a policy from scratch using the selected profile, applicable regulations, optional uploaded PDFs, and optional reference policy text.
3. `Gap Analysis`
   Compare a policy or current-state narrative against controls resolved from the selected profile's regulations, existing control files, and optional uploaded PDFs.
4. `Policy Implementation`
   Generate a policy document, implementation plan, audit register, traceability matrix, and company control inventory from a saved blueprint.
5. `Regulation Upload`
   Save text-based PDF pages into JSONL for downstream indexing and control extraction.
6. `Index & Search`
   Build a searchable index from saved JSONL files and retrieve requirement-like statements.
7. `Controls`
   Extract controls from processed regulations and save them as JSON and CSV.
8. `Control Registry`
   Review the control master and update company-specific control inventory fields like status and owner.
9. `Classification Admin`
   Review and edit the external control taxonomy and statement-level classification overrides.

## Important Product Notes

- The app is currently local-first and file-backed for most workflows.
- The LLM layer expects a locally reachable Ollama-compatible endpoint by default.
- On macOS, the app now performs a startup Ollama health check and will try to auto-launch `Ollama.app` once if the local endpoint is unavailable.
- The current search backend defaults to a safe keyword index, not semantic vector search.
- Business profiles now store `applicable_regulations` and `recommended_regulations`, which feed the policy-generation and gap-analysis workflows.
- A curated regulation catalog is bundled in code so the app can recommend likely obligations and map them back to local control files when available.
- OCR is not implemented yet. Scanned PDFs are not supported.
- The database layer exists as a foundation, but the main user workflows are still mostly file-based today.

## Tech Stack

- Python
- Streamlit
- Pydantic
- SQLAlchemy
- Ollama-compatible LLM endpoint
- JSON / CSV local persistence

## Editable Control Taxonomy

Control classification is now externalized into two files:

- `configs/control_taxonomy.json`
  Holds the editable taxonomy for modality priority, topic keyword rules, and the allowed values and aliases for `category`, `control_type`, and `severity`.
- `data/control_classification_overrides.json`
  Holds user corrections keyed by a stable hash of the control statement. These overrides are applied after the model output is normalized, so corrections win without changing Python code.

Useful helper functions:

- `core.classifier.save_classification_override(control_text, updates, note="...")`
- `core.classifier.list_classification_overrides()`
- `core.classifier.delete_classification_override(control_text)`

Example:

```python
from core.classifier import save_classification_override

save_classification_override(
    "Access to customer data must be reviewed quarterly.",
    {
        "control_type": "Governance",
        "severity": "High",
    },
    note="Updated after SME review",
)
```

This keeps the default taxonomy editable in config, while keeping statement-specific corrections in a separate runtime store.

## Profile-Linked Regulation Catalog

The app now includes a curated regulation catalog in `domain/regulations/catalog.py`.

What it does:

- recommends likely regulations and guidelines from a saved business profile
- marks whether each catalog entry already has a matching local control file
- lets shared workflows resolve a mix of catalog-linked regulations, uploaded PDFs, and manually selected control files

Current bundled catalog entries include:

- `QCB Data Handling and Protection Regulation`
- `QCB Cloud Computing Regulation`
- `QCB eKYC Regulation`
- `Qatar Personal Data Privacy Law (Law No. 13 of 2016)`
- `National Data Classification Policy v3.0`

Saved profiles now persist both:

- `applicable_regulations`
- `recommended_regulations`

Those fields are then reused by:

- `Policy Generator`
- `Gap Analysis`
- `orchestrators/regulation_source_workflow.py`

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

Copy the example file and then edit it if needed:

```bash
cp .env.example .env
```

The repo now includes a real `.env.example` with sensible defaults for local development.

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

Current startup behavior:

- when the app starts, it checks whether Ollama is reachable
- on macOS with a local Ollama URL, it will try to launch `Ollama.app` automatically one time
- if Ollama is still unavailable, the app shows a startup warning banner instead of only failing later inside generation
- if Ollama is running but the configured model is missing, the app tells you which `ollama pull ...` command to run

This means you may not always need to start Ollama manually first, but you still need the configured models to exist locally.

Example:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen2.5:3b
```

If you use different models, update `.env` accordingly.

If the app is configured for a different model, pull that exact model instead. For example:

```bash
ollama pull qwen2.5:1.5b
```

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

1. Go to `Business Profile`
   Save the organization profile and confirm the applicable regulations suggested for that business.
2. Go to `Regulation Upload`
   Upload any text-based regulation PDFs that are not already represented in the local control library.
3. Go to `Controls`
   Extract controls from the newly uploaded regulations when needed.
4. Go to `Policy Generator`
   Select the profile, choose the applicable regulations or guidelines, and draft a policy from scratch.
5. Go to `Policy Implementation`
   Generate the supporting implementation plan, audit register, traceability matrix, and company control inventory.
6. Go to `Gap Analysis`
   Compare an existing policy or current-state text against the profile-linked regulations and controls.
7. Use `Index & Search` when you need clause lookup or requirement discovery from saved regulations.
8. Use `Control Registry` and `Classification Admin` to maintain the shared control library and classification quality.

If the needed regulations already have control files in `data/controls/`, you can often start at `Business Profile` and go straight to `Policy Generator` or `Gap Analysis`.

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
- `.docx` support uses `python-docx`
- `.xlsx` support uses `pandas` and `openpyxl`

These ingestion dependencies are now included in `requirements.txt`, so setup is one-command for the currently supported file types.

## Current Storage Model

The app creates and uses local folders under `data/`.

Examples:

- `data/processed/`
  extracted page-level JSONL files
- `data/controls/`
  extracted controls JSON and CSV, including catalog-linked control files used by profile-led workflows
- `data/profiles/`
  saved business profiles with applicable and recommended regulations
- `data/blueprints/`
  saved reusable policy blueprints plus source-context metadata
- `data/artifacts/`
  generated policy and CSV artifacts
- `data/control_registry/`
  local control registry data, including the control master and company inventory
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

Also note:

- on macOS the app will try to auto-launch `Ollama.app` once
- auto-launch does not pull models for you
- if you see a startup banner saying models are missing, run the exact `ollama pull ...` command shown there

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

If you are using the default local setup on macOS:

```bash
open -a Ollama
curl http://localhost:11434/api/tags
```

If the health check works but generation still fails, the model in `.env` is likely missing locally.

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
cp .env.example .env
./run.sh
```

Edit `.env` if you want different models or endpoints before the first real LLM-backed run.

## Current Limitations

- no OCR for scanned PDFs
- DB-backed persistence is not the default flow yet
- keyword search is the default search backend today
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
5. create a `Business Profile`, then use the profile-led `Policy Generator` / `Gap Analysis` flow or the advanced regulation-upload workspaces when you need new source documents

That should be enough for a new user to clone the repo, start the product locally, and use the main workflows without reading the code first.
