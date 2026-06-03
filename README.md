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

## 4-Folder AI Project Structure

The project now follows the standard 4-folder AI project structure that makes prompts versioned, output measurable, and the system tunable without touching Python code.

```
prompts/     ← LLM prompt templates as versioned Markdown files
data/        ← regulation material, reference policies, eval datasets, runtime storage
agents/      ← declarative agent configs (model, temperature, prompt files)
evals/       ← evaluation framework for measuring and improving output quality
```

### `prompts/`

All LLM prompts are externalized as `.md` files with `{{variable}}` placeholders.

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

**Template loader usage:**

```python
from prompts.loader import render_prompt, system_prompt

# Render a task prompt with variables
prompt = render_prompt("tasks.policy_generation",
    blueprint_json=json.dumps(blueprint),
    reference_policy_block=reference_excerpt,
    drafting_instructions_block=instructions,
)

# Load a system persona
system = system_prompt("policy_drafter")
```

Variables use `{{double_brace}}` syntax. Substitution is a simple `str.replace` loop — no template engine dependency.

**Why this matters for output quality:** Every LLM call now sends a Qatar-specific system persona. Policy generation also injects the first 1500 characters of a user-supplied reference policy as a style example, grounding the model in Qatar-regulatory-quality writing rather than generic boilerplate.

### `data/samples/`

Place your own previously authored policy documents here as style references and evaluation ground truth.

```
data/samples/
  README.md         # explains confidentiality, gitignore rules
  [your_policy.md]  # gitignored — not committed to the repo
```

Supported formats: `.md`, `.docx`, `.pdf` (text-based only).

These files serve two purposes:
1. **Style grounding**: In the Policy Generator, select a reference policy from the dropdown. The first 1500 characters are injected into the generation prompt so the LLM mirrors your Qatar-regulatory writing style.
2. **Eval ground truth**: Reference these files in `data/eval_datasets/` cases. When you run evals, the eval runner loads the policy text and scores model output against your real policies.

Files in `data/samples/` (except `README.md`) are gitignored because they may contain confidential policy text.

### `agents/`

Declarative JSON configs that document each agent's model, temperature, and prompt configuration.

```
agents/
  policy_generator.json
  gap_analyzer.json
  control_classifier.json
  loader.py
```

Example — `agents/policy_generator.json`:

```json
{
  "id": "policy_generator",
  "purpose": "policy_generation",
  "env_model_key": "POLICY_GENERATION_MODEL",
  "temperature": 0.1,
  "system_prompt": "prompts/system/policy_drafter.md",
  "task_prompt": "prompts/tasks/policy_generation.md",
  "output_format": "markdown",
  "few_shot_source": "data/samples/",
  "notes": "Larger models (14B+) produce noticeably better output for this task."
}
```

These configs are readable documentation for the agent system. They also serve as the source of truth when `services/llm/router.py` resolves which model to use for each workflow purpose.

### `evals/`

End-to-end evaluation framework for measuring and improving output quality.

```
evals/
  cases/                  # curated eval cases (symlink or copy from data/eval_datasets/)
  runners/
    base_runner.py        # EvalCase + EvalResult dataclasses, load_cases(), run_all()
    gap_eval_runner.py    # calls analyze_policy_coverage() directly
    policy_eval_runner.py # calls generate_policy_md_from_blueprint() directly
  scorecards/
    section_checker.py    # checks required ## Section headings are present
    similarity_scorer.py  # difflib.SequenceMatcher ratio vs. reference policy
    llm_judge.py          # second LLM call scoring output 1-10 against criteria
    scorecard.py          # aggregator
  traces/
    .gitkeep              # trace files gitignored (large and may contain policy text)
  run_evals.py            # CLI entry point
```

**Running evals:**

```bash
# Gap analysis — highest ROI, start here
python -m evals.run_evals --task gap_analysis

# Policy generation — requires reference policies in data/samples/
python -m evals.run_evals --task policy_generation

# With LLM judge scoring (needs EVAL_JUDGE_MODEL set)
python -m evals.run_evals --task policy_generation --judge

# Run all tasks
python -m evals.run_evals --all

# Print a summary report
python -m evals.run_evals --task gap_analysis --report
```

**Eval case format** (`data/eval_datasets/gap_analysis/ga_001_ekyc_liveness_detection.json`):

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
  },
  "metadata": { "annotated_by": "user", "regulation": "QCB eKYC Regulation" }
}
```

Author these by going through each control in a regulation and annotating whether your reference policy covers it. Around 30–50 annotated cases gives a meaningful pass rate signal.

**Scoring dimensions:**

| Task | Scorer | What it measures |
|------|--------|-----------------|
| Gap analysis | `status_exact_match` | Exact match to expected Covered/Partially Covered/Missing |
| Gap analysis | `reason_keywords_found` | Expected keywords appear in model's reason text |
| Policy generation | `section_checker` | Required `## Section` headings are present |
| Policy generation | `similarity_scorer` | difflib ratio vs. reference policy (threshold: 0.15) |
| Policy generation | `llm_judge` | Score 1–10 against Qatar alignment, specificity, completeness, tone |

**Trace files** are written to `evals/traces/` on every run. Each trace records the prompt version hash so you can correlate score changes to prompt edits.

## Important Product Notes

- The app is currently local-first and file-backed for most workflows.
- The LLM layer expects a locally reachable Ollama-compatible endpoint by default.
- On macOS, the app performs a startup Ollama health check and will try to auto-launch `Ollama.app` once if the local endpoint is unavailable.
- The current search backend defaults to a safe keyword index, not semantic vector search.
- Business profiles store `applicable_regulations` and `recommended_regulations`, which feed the policy-generation and gap-analysis workflows.
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

Control classification is externalized into two files:

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

## Profile-Linked Regulation Catalog

The app includes a curated regulation catalog in `domain/regulations/catalog.py`.

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

Saved profiles persist both `applicable_regulations` and `recommended_regulations`. Those fields are reused by Policy Generator, Gap Analysis, and `orchestrators/regulation_source_workflow.py`.

## Repository Structure

```text
prompts/           LLM prompt templates (versioned Markdown)
agents/            Declarative agent configs (JSON + loader)
evals/             Evaluation framework
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
  samples/         Reference policies (gitignored, user-supplied)
  eval_datasets/   Annotated eval cases for gap analysis, policy gen, classification
  regulations/
    pdfs/          Raw regulation PDFs (gitignored)
    processed/     Extracted JSONL (gitignored)
  controls/
  profiles/
  blueprints/
  artifacts/
  gap_analysis/
  generation_runs/
  control_registry/
  cache/
```

Layer summary:

- `prompts/`
  Versioned Markdown prompt templates. Edit these to improve output quality without touching Python.
- `agents/`
  JSON configs documenting each agent's model, temperature, and prompt files.
- `evals/`
  Runners, scorecards, and CLI for measuring output quality against annotated ground truth.
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

Key variables:

```env
# Model selection
DEFAULT_LLM_MODEL=qwen2.5:3b
CONTROL_CLASSIFIER_MODEL=qwen2.5:3b
GAP_ANALYSIS_MODEL=qwen2.5:3b
POLICY_GENERATION_MODEL=qwen2.5:3b

# For Qatar production: policy generation benefits significantly from >=14B models
# POLICY_GENERATION_MODEL=qwen2.5:14b

# LLM endpoint
OLLAMA_URL=http://localhost:11434/api/chat
LLM_TIMEOUT_SECONDS=600

# Eval judge — set to a larger or different model than POLICY_GENERATION_MODEL
# EVAL_JUDGE_MODEL=qwen2.5:14b

# Search
INDEX_BACKEND=keyword
KEYWORD_INDEX_PATH=data/chroma_db/keyword_chunks.json
```

**`EVAL_JUDGE_MODEL`** is used by `evals/scorecards/llm_judge.py`. Set it to a larger or different model than `POLICY_GENERATION_MODEL` so the judge gives an unbiased score. If unset, the LLM judge scorer is skipped during eval runs.

## 4. Start Ollama

If you want the LLM-backed features to work, start Ollama and make sure your selected models are available.

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen2.5:3b
```

For Qatar production, pull a larger model for policy generation:

```bash
ollama pull qwen2.5:14b
```

Then update `.env`:

```env
POLICY_GENERATION_MODEL=qwen2.5:14b
EVAL_JUDGE_MODEL=qwen2.5:14b
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
   Upload any text-based regulation PDFs not already represented in the local control library.
3. Go to `Controls`
   Extract controls from the newly uploaded regulations when needed.
4. **Add a reference policy** (optional but recommended for Qatar output quality)
   Save one of your existing, human-authored policies to `data/samples/your_policy.md`.
5. Go to `Policy Generator`
   Select the profile, choose the applicable regulations, select your reference policy as the style guide, and draft.
6. Go to `Policy Implementation`
   Generate the supporting implementation plan, audit register, traceability matrix, and company control inventory.
7. Go to `Gap Analysis`
   Compare an existing policy or current-state text against the profile-linked regulations and controls.
8. **Run evals** (recommended before shipping)
   ```bash
   python -m evals.run_evals --task gap_analysis --report
   ```

## Adding Reference Policies (Style Grounding)

To ground the LLM in Qatar-regulatory-quality writing:

1. Copy an existing policy you've authored to `data/samples/`:
   ```bash
   cp /path/to/your/policy.md data/samples/onboarding_policy.md
   ```
2. In the Streamlit Policy Generator, select it from the "Reference Policy" dropdown.
3. The first 1500 characters are injected into the generation prompt as a style example.

These files are gitignored because they may contain confidential policy text. They stay on your machine only.

## Running Evals

After adding reference policies and authoring eval cases in `data/eval_datasets/`:

```bash
# Activate your venv
source .venv/bin/activate
export PYTHONPATH=$(pwd)

# Gap analysis pass rate (highest ROI — start here)
python -m evals.run_evals --task gap_analysis --report

# Policy generation quality
python -m evals.run_evals --task policy_generation --report

# With LLM judge (requires EVAL_JUDGE_MODEL in .env)
python -m evals.run_evals --task policy_generation --judge --report

# All tasks
python -m evals.run_evals --all --report
```

Target a gap analysis pass rate above 80% before shipping to clients.

Trace files are written to `evals/traces/` on every run. Each trace records the prompt version hash (`sha256` of prompt content) so you can correlate score changes to specific prompt edits.

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

## Current Storage Model

The app creates and uses local folders under `data/`.

Examples:

- `data/samples/`
  user-supplied reference policies (gitignored)
- `data/eval_datasets/`
  annotated eval cases for gap analysis, policy generation, and classification
- `data/regulations/processed/`
  extracted page-level JSONL files (gitignored)
- `data/controls/`
  extracted controls JSON and CSV, including catalog-linked control files
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

The project includes a DB foundation with SQLAlchemy models under `models/` and setup helpers under `services/db/`.

This is optional for current usage.

To initialize the local SQLite database:

```bash
source .venv/bin/activate
python -c "from services.db.session import create_all_tables; create_all_tables()"
```

By default this creates `data/app.db`.

To use PostgreSQL later, set:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/regulatory_ai
```

## Search Backend Note

The current index/search feature defaults to a safe keyword backend.

- the app will still let you build and query an index
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

```bash
curl http://localhost:11434/api/tags
```

### PDF upload says little or no text was extracted

The PDF is probably scanned or image-based. No OCR support yet.

### DOCX support fails

```bash
pip install python-docx
```

### XLSX support fails

```bash
pip install pandas openpyxl
```

### Streamlit port already in use

```bash
streamlit run app/ui.py --server.port 8502
```

### I changed code and imports behave strangely

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
streamlit run app/ui.py
```

### Eval runner says `No cases found`

Check that `data/eval_datasets/<task>/` contains `.json` case files. See `data/eval_datasets/README.md` for the case format and authoring guidance.

### LLM judge scorer is skipped

Set `EVAL_JUDGE_MODEL` in `.env` to enable it:

```env
EVAL_JUDGE_MODEL=qwen2.5:14b
```

## Developer Notes

- `prompts/` is the first place to look when output quality is poor. Edit the `.md` files rather than the Python callers.
- `evals/` is how you confirm that a prompt change actually improved things. Run before and after.
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

Edit `.env` to configure your models before the first LLM-backed run. For Qatar-quality output, use at least a 14B model for `POLICY_GENERATION_MODEL`.

## Current Limitations

- no OCR for scanned PDFs
- DB-backed persistence is not the default flow yet
- keyword search is the default search backend today
- parts of the codebase still use compatibility modules under `core/`
- eval cases in `data/eval_datasets/` must be authored manually; no auto-generation tooling yet

## Contributing

If you are extending the project:

- keep page files thin
- put workflow sequencing in `orchestrators/`
- put business rules in `domain/`
- put transport, IO, and integration logic in `services/`
- edit prompts in `prompts/` and run evals before merging prompt changes
- avoid aggressive deletion of legacy modules until replacement paths are fully migrated

## Support

If someone new is onboarding to the project, the fastest path is:

1. install dependencies
2. configure `.env`
3. start Ollama and pull your models
4. (optional) add a reference policy to `data/samples/`
5. run Streamlit
6. create a `Business Profile`, then use the profile-led `Policy Generator` / `Gap Analysis` flow

That should be enough for a new user to clone the repo, start the product locally, and use the main workflows without reading the code first.
