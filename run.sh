#!/bin/bash
set -e

# Activate venv
source .venv/bin/activate

# Add project root to PYTHONPATH
export PYTHONPATH=$(pwd)

# Run Streamlit
streamlit run app/ui.py