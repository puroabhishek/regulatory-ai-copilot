"""Eval runner CLI.

Usage:
  python -m evals.run_evals --task gap_analysis
  python -m evals.run_evals --task policy_generation [--judge]
  python -m evals.run_evals --all [--report]

The --report flag writes a summary scorecard JSON to evals/traces/.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Ensure project root is on path when running as a module
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.runners.base_runner import EvalResult


TASKS = ["gap_analysis", "policy_generation"]

CASES_DIR = Path("evals/cases")
DATA_EVAL_DIR = Path("data/eval_datasets")
TRACES_DIR = Path("evals/traces")


def _cases_dir_for(task: str) -> Path:
    """Return cases dir, falling back to data/eval_datasets if evals/cases is empty."""
    curated = CASES_DIR / task
    if curated.exists() and any(curated.glob("*.json")):
        return curated
    fallback = DATA_EVAL_DIR / task
    if fallback.exists():
        return fallback
    return curated


def run_gap_analysis(judge: bool = False) -> List[EvalResult]:
    from evals.runners.gap_eval_runner import GapEvalRunner
    runner = GapEvalRunner()
    return runner.run_all(cases_dir=_cases_dir_for("gap_analysis"))


def run_policy_generation(judge: bool = False) -> List[EvalResult]:
    from evals.runners.policy_eval_runner import PolicyEvalRunner
    runner = PolicyEvalRunner(use_judge=judge)
    return runner.run_all(cases_dir=_cases_dir_for("policy_generation"))


def print_summary(task: str, results: List[EvalResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errored = sum(1 for r in results if r.error)
    pass_rate = round(passed / total * 100, 1) if total else 0

    print(f"\n{'─' * 50}")
    print(f"Task: {task}")
    print(f"Cases: {total}  |  Passed: {passed}  |  Failed: {total - passed - errored}  |  Errors: {errored}")
    print(f"Pass rate: {pass_rate}%")

    for r in results:
        status = "✓" if r.passed else ("!" if r.error else "✗")
        print(f"  {status} {r.case_id}: {r.error or r.scores}")

    return {
        "task": task,
        "total": total,
        "passed": passed,
        "failed": total - passed - errored,
        "errored": errored,
        "pass_rate_pct": pass_rate,
    }


def main():
    parser = argparse.ArgumentParser(description="Run regulatory AI copilot evals")
    parser.add_argument("--task", choices=TASKS, help="Run a specific task")
    parser.add_argument("--all", action="store_true", dest="all_tasks", help="Run all tasks")
    parser.add_argument("--judge", action="store_true", help="Enable LLM-as-judge scoring (policy_generation only)")
    parser.add_argument("--report", action="store_true", help="Write scorecard JSON to evals/traces/")
    args = parser.parse_args()

    if not args.task and not args.all_tasks:
        parser.print_help()
        sys.exit(1)

    tasks_to_run = TASKS if args.all_tasks else [args.task]
    summaries = []

    for task in tasks_to_run:
        print(f"\n{'=' * 50}")
        print(f"Running evals: {task}")
        print(f"{'=' * 50}")

        if task == "gap_analysis":
            results = run_gap_analysis()
        elif task == "policy_generation":
            results = run_policy_generation(judge=args.judge)
        else:
            print(f"Unknown task: {task}")
            continue

        summary = print_summary(task, results)
        summaries.append(summary)

    if args.report:
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        report_path = TRACES_DIR / f"scorecard_{ts}.json"
        report_path.write_text(
            json.dumps({"run_at": datetime.now(timezone.utc).isoformat(), "summaries": summaries}, indent=2),
            encoding="utf-8",
        )
        print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
