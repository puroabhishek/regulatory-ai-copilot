#!/bin/bash
set -e

# 1) Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# 2) Activate venv
source .venv/bin/activate

# 3) Upgrade pip (optional but recommended)
python -m pip install --upgrade pip

# 4) Install dependencies
pip install -r requirements.txt

echo "✅ Setup complete. To start: source .venv/bin/activate"
