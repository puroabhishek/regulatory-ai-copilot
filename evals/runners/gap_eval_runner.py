"""Eval runner for gap analysis coverage task.

Calls analyze_policy_coverage() directly — the same production function —
so eval results reflect exactly what the app does.

How to add test cases:
  1. Create a JSON file in data/eval_datasets/gap_analysis/ (see README there)
  2. Copy or symlink it into evals/cases/gap_analysis/
  3. Run: python -m evals.run_evals --task gap_analysis
"""

from pathlib import Path
from typing import Optional

from domain.gaps.policy_coverage import analyze_policy_coverage
from schemas.control import Control
from evals.runners.base_runner import BaseEvalRunner, EvalCase, EvalResult


class GapEvalRunner(BaseEvalRunner):

    def task_name(self) -> str:
        return "gap_analysis"

    def run_case(self, case: EvalCase) -> EvalResult:
        inp = case.input
        expected = case.expected_output

        # Load policy text from file or inline
        policy_text = inp.get("policy_text", "")
        policy_file = inp.get("policy_text_file", "")
        if not policy_text and policy_file:
            p = Path(policy_file)
            if not p.exists():
                raise FileNotFoundError(f"Policy file not found: {policy_file}")
            policy_text = p.read_text(encoding="utf-8")

        if not policy_text:
            raise ValueError(f"Case {case.id}: no policy_text or policy_text_file provided")

        control = Control(
            control_id=inp["control_id"],
            statement=inp["control_statement"],
        )

        result = analyze_policy_coverage(control=control, policy_text=policy_text)

        # Score
        expected_status = expected.get("status", "")
        alternatives = expected.get("status_alternatives", [])
        reason_keywords = expected.get("reason_contains", [])

        status_exact = result.status == expected_status
        status_partial = result.status in alternatives
        keywords_found = [kw for kw in reason_keywords if kw.lower() in result.reason.lower()]
        keywords_missing = [kw for kw in reason_keywords if kw.lower() not in result.reason.lower()]

        passed = status_exact or status_partial

        scores = {
            "status_exact_match": status_exact,
            "status_in_alternatives": status_partial,
            "actual_status": result.status,
            "expected_status": expected_status,
            "reason_keywords_found": keywords_found,
            "reason_keywords_missing": keywords_missing,
            "passed": passed,
        }

        return EvalResult(
            case_id=case.id,
            task=case.task,
            model="(resolved from env)",
            raw_output={"status": result.status, "reason": result.reason, "remediation": result.remediation},
            scores=scores,
            passed=passed,
        )
