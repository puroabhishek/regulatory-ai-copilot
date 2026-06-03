"""Load and render prompt templates from the prompts/ directory.

Prompts are .md files with {{variable}} placeholders. Rendering is simple
str.replace — no template engine dependency.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by dotted path e.g. 'tasks.policy_generation'.

    Maps dots to path separators: 'tasks.policy_generation' → tasks/policy_generation.md
    """
    parts = name.split(".")
    path = PROMPTS_DIR.joinpath(*parts).with_suffix(".md")
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **variables: str) -> str:
    """Load a prompt and substitute {{variable}} placeholders."""
    template = load_prompt(name)
    for key, value in variables.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def system_prompt(name: str) -> str:
    """Load a system/ prompt by short name e.g. 'policy_drafter'."""
    return load_prompt(f"system.{name}")


def tool_block(name: str) -> str:
    """Load a tools/ reusable block by short name e.g. 'json_output_strict'."""
    return load_prompt(f"tools.{name}")
