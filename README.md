# Regulatory AI Copilot

A multi-tenant, enterprise-ready compliance AI copilot for Qatar-regulated entities. Turns regulation documents into structured controls, drafts QCB-quality policies, runs gap analysis, and measures output quality through an eval framework grounded in real QCB-reviewed work.

## Architecture Overview

Two Streamlit apps, one codebase, one PostgreSQL database.

```
app/ui.py       →  Tenant App    (port 8501)   4-step guided compliance journey
app/admin.py    →  Admin Portal  (port 8502)   Control registry, evals, users, analytics
```

```
Browser
   ↓
nginx (port 443, TLS)
   ├── /        → Tenant App  (Streamlit :8501)
   └── /admin   → Admin App   (Streamlit :8502)

PostgreSQL  (Docker, :5432)
Ollama      (Docker or native, :11434)
data/orgs/{org_slug}/   (org-scoped local file storage)
```

## Who This Is For

- **Users**: Startups, banks, compliance managers — create policies and run gap analysis
- **Admin**: Company-internal portal for control registry, eval management, user tracking, prompt tuning

## Tenant App — 4-Step Journey (`app/ui.py`)

### Step 1: Business Profile
Fill in sector, country, sub-sector, activity, business model, data handled, cloud usage, and lending model. The system maps applicable Qatar regulations to your profile.

### Step 2: Compliance Work
Two options after profile is saved:

**Create Policy** — Selects mapped controls + QCB-approved reference policies as style examples → generates a bespoke policy. Thumbs up/down feedback on every output.

**Analyse Existing Policy** — Upload or paste your existing policy text → gap analysis against all mapped controls → Covered / Partially Covered / Missing per control with remediation.

### Step 3: Policy Vault
All org policies with compliance scores. Per-policy drill-down: control-by-control status, remediation tasks, download links (policy MD, implementation plan CSV, audit register CSV).

### Step 4: Audit Report
Auto-generated from vault data. Executive summary, open gaps, compliance score across all regulations. Export as markdown.

## Admin Portal — 6 Tabs (`app/admin.py`)

| Tab | Purpose |
|-----|---------|
| Control Registry | Upload regulation PDFs/CSVs → LLM extracts controls → review + save to registry |
| Policy Version Library | Upload QCB-submitted/approved policies, set QCB status, mark as reference |
| Eval Manager | Excel import for gap cases, run evals, view results vs pass threshold |
| Prompt Manager | Inline edit all `prompts/*.md` files, shows sha256 hash per prompt |
| Usage Analytics | Per-org LLM usage, feedback summary, audit log viewer |
| User & Org Management | Create orgs/users, deactivate, edit AppSettings (eval threshold, models) |

## "Training" on QCB Data

This is **not fine-tuning**. It is RAG + eval-driven prompt optimization:

1. **Upload** the company's QCB-reviewed policies → Admin → Policy Version Library → mark as `is_reference_policy`
2. **Import** QCB gap feedback Excel sheets → Admin → Eval Manager → 50–100 eval cases auto-created
3. **Run baseline evals** → see current pass rate (typically 40–60% before tuning)
4. **Tune prompts** → Admin → Prompt Manager → edit `prompts/tasks/gap_analysis_coverage.md` → re-run evals
5. **Target** ≥ 90% pass rate (configurable via `AppSetting: eval_pass_threshold`)

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/puroabhishek/regulatory-ai-copilot.git
cd regulatory-ai-copilot

# 2. Configure environment
cp .env.example .env
# Edit .env — set your Ollama models

# 3. Start PostgreSQL
docker-compose up -d postgres

# 4. Run migrations
source .venv/bin/activate
export PYTHONPATH=$(pwd)
alembic upgrade head

# 5. Seed admin user
python scripts/seed.py
# Creates: admin@regai.local / ChangeMe123!

# 6. Start apps
streamlit run app/ui.py --server.port 8501 &
streamlit run app/admin.py --server.port 8502
```

Open:
- Tenant app: `http://localhost:8501`
- Admin portal: `http://localhost:8502`

## Full Docker Compose (all services)

```bash
docker-compose up
```

This starts:
- `postgres` on `:5432`
- `pgadmin` on `:5050` (admin@regai.local / admin)
- `app` (tenant) on `:8501`
- `admin` on `:8502`

Then run migrations and seed once:
```bash
docker-compose exec app alembic upgrade head
docker-compose exec app python scripts/seed.py
```

## Manual Setup (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Use SQLite fallback (no PostgreSQL needed)
# DATABASE_URL is unset → data/app.db is used automatically

export PYTHONPATH=$(pwd)
python scripts/seed.py        # creates tables + admin user
streamlit run app/ui.py
```

## Environment Variables

```env
# LLM Models (must exist in your Ollama instance)
DEFAULT_LLM_MODEL=qwen2.5:3b
CONTROL_CLASSIFIER_MODEL=qwen2.5:3b
GAP_ANALYSIS_MODEL=qwen2.5:3b
POLICY_GENERATION_MODEL=qwen2.5:3b   # use 14b+ for Qatar-quality output

# Eval judge — use a different/larger model than POLICY_GENERATION_MODEL
# EVAL_JUDGE_MODEL=qwen2.5:14b

# LLM endpoint
OLLAMA_URL=http://localhost:11434/api/chat
LLM_TIMEOUT_SECONDS=600

# Database (leave unset for SQLite fallback)
# DATABASE_URL=postgresql+psycopg2://regai:regai_dev@localhost:5432/regulatory_ai

# Optional debugging
# SQLALCHEMY_ECHO=false
```

## Auth

Login with **email or phone number + password**. No self-registration — admin creates all users.

Default superadmin: `admin@regai.local` / `ChangeMe123!` (change immediately after first login).

Roles: `user` → `org_admin` → `admin` → `superadmin`

## Database Schema

### Existing models (unchanged)
`Organization`, `User`, `OrganizationProfile`, `Policy`, `Control`, `EvidenceItem`, `GapAssessment`, `Task`, `AuditReadiness`

### New models
| Model | Purpose |
|-------|---------|
| `RegistryControl` | Central MECE control registry — country × sector × regulation × controls |
| `PolicyVersion` | QCB-reviewed policy library (approved policies become style references) |
| `EvalCase` | DB-backed eval cases (replaces JSON files) |
| `EvalRun` / `EvalResult` | Eval run history with per-case results |
| `OutputFeedback` | Thumbs up/down per LLM output with reason codes |
| `AuditLog` | Every LLM call recorded: org_id, user_id, model, prompt_hash, duration_ms |
| `AppSetting` | Company-level config: eval threshold, feature flags, model defaults |

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "description"

# Check current migration state
alembic current
```

## 4-Folder AI Project Structure

```
prompts/     ← LLM prompt templates as versioned Markdown files
data/        ← regulation material, reference policies, eval datasets, runtime storage
agents/      ← declarative agent configs (model, temperature, prompt files)
evals/       ← evaluation framework for measuring and improving output quality
```

### `prompts/`

All LLM prompts are `.md` files with `{{variable}}` placeholders. Edit prompts to improve output quality without touching Python code.

```
prompts/
  system/
    policy_drafter.md          # Qatar-regulatory drafting persona
    compliance_reviewer.md     # Strict QCB/QFCRA reviewer persona
    control_classifier.md      # Control classification persona
  tasks/
    policy_generation.md       # Full policy drafting prompt
    gap_analysis_coverage.md   # Control coverage analysis prompt
    control_classification.md  # Control classification prompt
    eval_judge_policy.md       # LLM-as-judge scoring prompt
  tools/
    json_output_strict.md      # Reusable JSON-only instruction block
    qatar_regulatory_context.md # Qatar regulation reference block
  loader.py                    # Zero-dependency template loader
```

### `evals/`

End-to-end evaluation framework. Run before shipping any prompt change.

```bash
# Gap analysis pass rate (highest ROI — start here)
python -m evals.run_evals --task gap_analysis

# Policy generation quality
python -m evals.run_evals --task policy_generation --judge

# All tasks with scorecard
python -m evals.run_evals --all --report
```

Target: **≥ 90% pass rate** on gap analysis before shipping to a client (configurable in AppSettings).

**Eval case format** (`data/eval_datasets/gap_analysis/ga_001.json`):

```json
{
  "id": "ga-001",
  "task": "gap_analysis_coverage",
  "input": {
    "control_id": "QCB-EKYC-LIVENESS-01",
    "control_statement": "The regulated entity must implement liveness detection...",
    "policy_text_file": "data/samples/your_onboarding_policy.md"
  },
  "expected_output": {
    "status": "Covered",
    "status_alternatives": ["Partially Covered"],
    "reason_contains": ["liveness", "eKYC"]
  }
}
```

## Org-Scoped File Storage

All runtime files are stored under `data/orgs/{org_slug}/`:

```
data/orgs/{slug}/
  profiles/         saved business profiles
  blueprints/       saved policy blueprints
  samples/          reference policies (gitignored)
  artifacts/        generated policies + CSVs
  controls/         extracted control JSON files
  gap_analysis/     saved gap run results
  generation_runs/  generation run history
```

Use `services.storage.paths` to resolve paths:

```python
from services.storage.paths import artifacts_dir, ensure_org_dirs

ensure_org_dirs(org_slug)
policy_path = artifacts_dir(org_slug) / "my_policy.md"
```

## Audit Logging

Every LLM call is logged automatically to `AuditLog`:

```python
from services.llm.context import set_llm_context

# Set before any LLM call (done automatically at login in app/ui.py)
set_llm_context(org_id="...", user_id="...")
```

Fields captured: `org_id`, `user_id`, `action` (purpose), `model_used`, `prompt_hash` (sha256[:8]), `duration_ms`, `error`.

## User Feedback

Every LLM output (policy, gap finding) shows thumbs up/down. Stored in `OutputFeedback` with `model_used` and `prompt_hash`. Visible in Admin → Usage Analytics to identify which prompts need improvement.

## Repository Structure

```
app/
  ui.py              Tenant app — 4-step guided journey
  admin.py           Admin portal — 6-tab internal tool
alembic/             Database migrations
models/              SQLAlchemy ORM models
orchestrators/       Workflow sequencing
domain/              Business logic (policies, gaps, controls, regulations)
services/
  auth/              bcrypt passwords + Streamlit session helpers
  db/                SQLAlchemy engine, session scope
  llm/               LLM client, router, parser, context vars, audit logging
  storage/           Org-scoped path resolver
  ingestion/         PDF/DOCX text extraction
prompts/             Versioned Markdown prompt templates
agents/              Declarative agent configs
evals/               Evaluation framework
schemas/             Pydantic validation models
scripts/
  seed.py            Creates company org + superadmin + default AppSettings
configs/             Control taxonomy and classification configs
data/
  orgs/              Org-scoped runtime storage (gitignored)
  samples/           Reference policies (gitignored)
  eval_datasets/     Annotated eval cases
  controls/          Extracted control JSON files
  regulations/       Raw PDFs + processed JSONL (gitignored)
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Tenant + Admin frontend | Streamlit |
| Auth | bcrypt + Streamlit session state |
| ORM + migrations | SQLAlchemy + Alembic |
| Database | PostgreSQL (Docker) / SQLite (fallback) |
| LLM | Ollama (local, data-sovereign) |
| Containers | Docker Compose |
| File storage | `data/orgs/{slug}/` local directories |

## Troubleshooting

**App starts but LLM features fail** — check Ollama is running, `.env` exists, model names are valid, models are pulled locally.

**`No LLM model configured`** — set `DEFAULT_LLM_MODEL=qwen2.5:3b` in `.env`.

**DB connection error** — check `DATABASE_URL` in `.env`, ensure `docker-compose up -d postgres` is running.

**`alembic upgrade head` fails** — ensure `PYTHONPATH=$(pwd)` is exported and `.venv` is activated.

**Login fails after seed** — run `python scripts/seed.py` again; it is idempotent.

**PDF upload extracts no text** — the PDF is scanned/image-based; OCR is not supported yet.

## Current Limitations

- No OCR for scanned PDFs
- No SSO / SAML (add in a later phase when a bank requires it)
- No vector/semantic search (keyword search is the default)
- No Kubernetes / auto-scaling (single server is sufficient for early customers)
- No fine-tuning of the LLM (by design — RAG + eval-driven prompt optimization is used instead)
