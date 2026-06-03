"""Load agent configuration from agents/*.json.

Agent configs document the LLM routing, prompt files, and output schema for
each workflow. They are read by eval runners and can be used to extend
LLMClient with agent-aware dispatch.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from services.llm.router import resolve_model

AGENTS_DIR = Path(__file__).parent


def load_agent(agent_id: str) -> Dict[str, Any]:
    """Load agent config by ID e.g. 'policy_generator'."""
    path = AGENTS_DIR / f"{agent_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Agent config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_agent_model(agent_id: str, override: Optional[str] = None) -> str:
    """Resolve the model for an agent, respecting .env overrides."""
    agent = load_agent(agent_id)
    return resolve_model(purpose=agent["purpose"], override=override)


def list_agents() -> list[str]:
    """List available agent IDs."""
    return sorted(p.stem for p in AGENTS_DIR.glob("*.json"))
