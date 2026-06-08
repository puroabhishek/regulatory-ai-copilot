#!/bin/bash
# Start the Regulatory AI Copilot (tenant app + admin portal)
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Activate virtual environment ──────────────────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: No virtual environment found. Run: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR"

# ── Load environment ───────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "WARNING: .env not found — copying from .env.example"
    cp .env.example .env
fi

# ── Check PostgreSQL (Docker) ──────────────────────────────────────────────────
if grep -q "postgresql" .env 2>/dev/null; then
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        if ! docker ps | grep -q "regulatory-ai-copilot-postgres\|regai.*postgres"; then
            echo "Starting PostgreSQL via Docker..."
            docker-compose up -d postgres
            sleep 3
        else
            echo "PostgreSQL already running."
        fi
    else
        echo "WARNING: DATABASE_URL points to PostgreSQL but Docker is not running."
        echo "         Either start Docker or remove DATABASE_URL from .env to use SQLite."
    fi
fi

# ── Run migrations ────────────────────────────────────────────────────────────
echo "Running database migrations..."
alembic upgrade head 2>&1 | grep -v "^$" || true

# ── Seed admin user (safe — skips if already exists) ─────────────────────────
echo "Checking seed data..."
python scripts/seed.py 2>&1 | grep -v "^$" || true

# ── Kill any existing Streamlit processes on our ports ────────────────────────
lsof -ti:8501 | xargs kill -9 2>/dev/null || true
lsof -ti:8502 | xargs kill -9 2>/dev/null || true
sleep 1

# ── Start apps ────────────────────────────────────────────────────────────────
echo ""
echo "Starting apps..."

streamlit run app/ui.py \
    --server.port 8501 \
    --server.address localhost \
    --server.headless true \
    --browser.gatherUsageStats false \
    &> /tmp/regai_ui.log &
UI_PID=$!

streamlit run app/admin.py \
    --server.port 8502 \
    --server.address localhost \
    --server.headless true \
    --browser.gatherUsageStats false \
    &> /tmp/regai_admin.log &
ADMIN_PID=$!

# ── Wait for both to be ready ─────────────────────────────────────────────────
echo -n "Waiting for apps to start"
for i in $(seq 1 20); do
    sleep 1
    echo -n "."
    UI_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 2>/dev/null)
    ADMIN_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502 2>/dev/null)
    if [ "$UI_UP" = "200" ] && [ "$ADMIN_UP" = "200" ]; then
        break
    fi
done
echo ""

# ── Status ────────────────────────────────────────────────────────────────────
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo ""
    echo "  Tenant App   →  http://localhost:8501"
    echo "  Admin Portal →  http://localhost:8502"
    echo "  pgAdmin      →  http://localhost:5050  (if Docker is running)"
    echo ""
    echo "  Admin login: admin@regai.local / ChangeMe123!"
    echo "  Logs: /tmp/regai_ui.log and /tmp/regai_admin.log"
    echo ""
    echo "  Press Ctrl+C to stop both apps."
else
    echo "ERROR: Apps failed to start. Check /tmp/regai_ui.log and /tmp/regai_admin.log"
    exit 1
fi

# ── Keep running until Ctrl+C ─────────────────────────────────────────────────
trap "echo ''; echo 'Stopping...'; kill $UI_PID $ADMIN_PID 2>/dev/null; exit 0" INT TERM
wait $UI_PID $ADMIN_PID
