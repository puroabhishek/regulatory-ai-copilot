"""Base classes for eval runners."""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    id: str
    task: str
    input: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "EvalCase":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            id=data["id"],
            task=data["task"],
            input=data["input"],
            expected_output=data["expected_output"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvalResult:
    case_id: str
    task: str
    model: str
    raw_output: Any
    scores: Dict[str, Any]
    passed: bool
    trace_path: str = ""
    error: Optional[str] = None


class BaseEvalRunner(ABC):
    """Abstract base for task-specific eval runners."""

    TRACES_DIR = Path("evals/traces")
    CASES_DIR = Path("evals/cases")

    def load_cases(self, cases_dir: Path) -> List[EvalCase]:
        cases = []
        for path in sorted(cases_dir.glob("*.json")):
            try:
                cases.append(EvalCase.from_file(path))
            except (KeyError, json.JSONDecodeError) as exc:
                print(f"  [skip] {path.name}: {exc}")
        return cases

    @abstractmethod
    def run_case(self, case: EvalCase) -> EvalResult:
        """Execute one eval case and return a result."""

    def run_all(
        self,
        cases_dir: Optional[Path] = None,
        model: Optional[str] = None,
    ) -> List[EvalResult]:
        if cases_dir is None:
            cases_dir = self.CASES_DIR / self.task_name()
        cases = self.load_cases(cases_dir)
        results = []
        for case in cases:
            print(f"  running {case.id} ...", end=" ", flush=True)
            try:
                result = self.run_case(case)
            except Exception as exc:
                result = EvalResult(
                    case_id=case.id,
                    task=case.task,
                    model=model or "unknown",
                    raw_output=None,
                    scores={},
                    passed=False,
                    error=str(exc),
                )
            self.save_trace(result)
            status = "PASS" if result.passed else ("ERROR" if result.error else "FAIL")
            print(status)
            results.append(result)
        return results

    def save_trace(self, result: EvalResult) -> str:
        self.TRACES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"{result.task}_{result.case_id}_{ts}.json"
        path = self.TRACES_DIR / filename
        path.write_text(
            json.dumps(
                {
                    "case_id": result.case_id,
                    "task": result.task,
                    "model": result.model,
                    "run_at": datetime.now(timezone.utc).isoformat(),
                    "raw_output": result.raw_output,
                    "scores": result.scores,
                    "passed": result.passed,
                    "error": result.error,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result.trace_path = str(path)
        return str(path)

    @abstractmethod
    def task_name(self) -> str:
        """Return the task identifier e.g. 'gap_analysis'."""

    @staticmethod
    def prompt_version_hash(prompt_content: str) -> str:
        return hashlib.sha256(prompt_content.encode()).hexdigest()[:8]
