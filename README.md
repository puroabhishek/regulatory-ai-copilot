# Regulatory AI Copilot

An AI-powered regulatory compliance copilot that converts regulations into structured controls, drafts business-specific policies, and generates implementation and audit artifacts.

## What it does

- Ingests regulatory PDFs
- Extracts and indexes regulation text
- Converts regulations into structured controls
- Captures business profile context
- Builds policy blueprints using multiple regulations and reference policies
- Generates:
  - Policy drafts
  - Implementation plans
  - Audit registers
  - Traceability matrices
- Maintains:
  - Global control registry
  - Company control inventory
  - Compliance cockpit for control tracking

## Current Architecture

1. Regulation ingestion
2. Semantic indexing
3. Control extraction + classification
4. Business profile capture
5. Policy blueprint creation
6. Blueprint-driven artifact generation
7. Control registry and compliance cockpit

## Tech Stack

- Python
- Streamlit
- ChromaDB
- Ollama
- Local LLMs (Qwen)
- JSON / CSV based registries

## Project Structure

```bash
app/
core/
data/
requirements.txt
README.md