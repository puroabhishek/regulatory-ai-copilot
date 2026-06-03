# data/samples/

This folder contains **human-authored, known-good policy documents** — the gold standard for what this product should produce.

## What goes here

- Real policy documents authored by domain experts for Qatar-regulated entities
- Documents that have been reviewed against QCB/QFCRA requirements
- Documents that represent the quality bar for generated output

## How they are used

1. **Style reference at generation time** — the first ~1500 chars of a selected sample are injected into the policy generation prompt as a `REFERENCE POLICY EXAMPLE`. This grounds the LLM in professional Qatar-regulatory tone and structure rather than generic boilerplate.

2. **Eval ground truth** — samples are referenced in `data/eval_datasets/` test cases as the expected policy text. The eval runner measures whether LLM output matches the quality and coverage of these samples.

## Confidentiality

These documents are internal and confidential. They are gitignored by default (see `.gitignore`). Do not commit them to the repository.

To add a new sample: save it as a `.md` file in this folder. It will automatically appear in the Streamlit "Style Reference" dropdown when drafting a new policy.
