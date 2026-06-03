"""Eval runner for policy generation task.

Calls generate_policy_md_from_blueprint() directly — same production path.
Scores on section presence, similarity to reference, and optionally LLM judge.

How to add test cases:
  1. Create a JSON file in data/eval_datasets/policy_generation/ (see README)
  2. Copy or symlink it into evals/cases/policy_generation/
  3. Run: python -m evals.run_evals --task policy_generation [--judge]
"""

import json
from pathlib import Path
from typing import Optional

from core.generator import generate_policy_md_from_blueprint
from evals.runners.base_runner import BaseEvalRunner, EvalCase, EvalResult
from evals.scorecards.section_checker import score_sections
from evals.scorecards.similarity_scorer import score_similarity


class PolicyEvalRunner(BaseEvalRunner):

    def __init__(self, use_judge: bool = False):
        self.use_judge = use_judge

    def task_name(self) -> str:
        return "policy_generation"

    def run_case(self, case: EvalCase) -> EvalResult:
        inp = case.input
        expected = case.expected_output

        # Load blueprint from file or inline
        blueprint_file = inp.get("blueprint_file", "")
        blueprint = inp.get("blueprint", None)
        if blueprint is None and blueprint_file:
            p = Path(blueprint_file)
            if not p.exists():
                raise FileNotFoundError(f"Blueprint file not found: {blueprint_file}")
            blueprint = json.loads(p.read_text(encoding="utf-8"))

        if blueprint is None:
            raise ValueError(f"Case {case.id}: no blueprint or blueprint_file provided")

        generated = generate_policy_md_from_blueprint(blueprint)

        # Section score
        required_sections = expected.get("required_sections", [])
        section_scores = score_sections(generated, required_sections) if required_sections else {}

        # Similarity score
        ref_file = inp.get("reference_policy_file", "")
        sim_scores = score_similarity(generated, reference_file=ref_file or None)

        # Length check
        min_len = expected.get("min_length_chars", 0)
        length_ok = len(generated) >= min_len

        scores: dict = {
            "length_chars": len(generated),
            "min_length_ok": length_ok,
            "similarity": sim_scores,
        }
        if section_scores:
            scores["sections"] = section_scores

        # LLM judge (optional)
        if self.use_judge and ref_file:
            from evals.scorecards.llm_judge import judge_policy
            try:
                judge = judge_policy(generated, reference_policy_file=ref_file)
                scores["judge"] = judge
            except Exception as exc:
                scores["judge"] = {"error": str(exc)}

        # Pass if sections OK (or no required sections) and length OK
        section_pass = section_scores.get("passed", True) if section_scores else True
        passed = section_pass and length_ok

        return EvalResult(
            case_id=case.id,
            task=case.task,
            model="(resolved from env)",
            raw_output=generated,
            scores=scores,
            passed=passed,
        )
