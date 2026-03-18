import json
import re
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.classifier import classify_control


# ---- Control classification helpers ----

MODAL_PRIORITY = ["must", "shall", "should", "may"]  # strongest first

TOPIC_RULES = [
    ("approval", "Regulatory Approval"),
    ("qcb", "Regulatory Approval"),
    ("register", "Register & Reporting"),
    ("inventory", "Register & Reporting"),
    ("disclose", "Register & Reporting"),
    ("audit", "Assurance & Audit"),
    ("soc", "Assurance & Audit"),
    ("test", "Security Testing"),
    ("penetration", "Security Testing"),
    ("vulnerability", "Security Testing"),
    ("encrypt", "Security Controls"),
    ("authentication", "Security Controls"),
    ("access", "Security Controls"),
    ("confidential", "Data Protection"),
    ("privacy", "Data Protection"),
    ("personal data", "Data Protection"),
    ("pii", "Data Residency"),
    ("within qatar", "Data Residency"),
    ("outsourcing", "Outsourcing & Vendor Risk"),
    ("csp", "Outsourcing & Vendor Risk"),
    ("risk", "Risk Management"),
    ("governance", "Governance"),
    ("board", "Governance"),
    ("strategy", "Governance"),
    ("business continuity", "Resilience & BCP"),
    ("resilien", "Resilience & BCP"),
]

CLAUSE_RE = re.compile(r"\b(?P<clause>\d+(?:\.\d+){1,3})\.\s+")
SENT_SPLIT_RE = re.compile(r"(?<=[\.\n])\s+")


def _normalize_ws(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_table_like(s: str) -> bool:
    if "✓" in s or "" in s:
        return True
    if len(re.findall(r"\s{4,}", s)) > 0:
        return True
    return False


def _detect_modal(sentence: str) -> Optional[str]:
    low = f" {sentence.lower()} "
    for m in MODAL_PRIORITY:
        if f" {m} " in low or low.startswith(m + " "):
            return m.upper()
    return None


def _topic(sentence: str) -> str:
    low = sentence.lower()
    for needle, label in TOPIC_RULES:
        if needle in low:
            return label
    return "General"


def _make_control_id(prefix: str, clause: Optional[str], page: int, idx: int) -> str:
    if clause:
        return f"{prefix}-{clause}"
    return f"{prefix}-P{page}-I{idx}"


def extract_controls_from_pages(
    pages: List[Dict[str, Any]],
    doc_id: str,
    doc_title: str,
    prefix: str = "QCB-CCR",
    min_len: int = 50,
    max_len: int = 500,
    model: str = "qwen2.5:1.5b",
) -> List[Dict[str, Any]]:
    """
    Extract requirement-like controls from page text and enrich with LLM classification.
    """
    controls: List[Dict[str, Any]] = []
    seen = set()

    for p in pages:
        page_num = int(p.get("page", 0))
        raw = p.get("text", "") or ""
        raw = _normalize_ws(raw)

        parts = SENT_SPLIT_RE.split(raw)

        for i, part in enumerate(parts):
            s = _normalize_ws(part)
            if len(s) < min_len or len(s) > max_len:
                continue
            if _is_table_like(s):
                continue

            modal = _detect_modal(s)
            if not modal:
                continue

            clause = None
            m = CLAUSE_RE.search(s)
            if m:
                clause = m.group("clause")

            statement = re.sub(r"^\s*\d+(?:\.\d+){1,3}\.\s*", "", s).strip()

            dedupe_key = re.sub(r"\s+", " ", statement.lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            control_id = _make_control_id(prefix, clause, page_num, i)

            try:
                extra = classify_control(statement, model=model)
            except Exception:
                extra = {
                    "category": "",
                    "control_type": "",
                    "severity": "",
                    "policy_tags": [],
                    "implementation_hint": "",
                }

            ctrl = {
                "control_id": control_id,
                "doc_id": doc_id,
                "doc_title": doc_title,
                "page": page_num,
                "clause": clause,
                "type": modal,
                "topic": _topic(statement),
                "statement": statement,
                "category": extra["category"],
                "control_type": extra["control_type"],
                "severity": extra["severity"],
                "policy_tags": extra["policy_tags"],
                "implementation_hint": extra["implementation_hint"],
            }

            controls.append(ctrl)

    return controls


def save_controls_json(controls: List[Dict[str, Any]], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(controls, f, ensure_ascii=False, indent=2)
    return out_path


def save_controls_csv(controls: List[Dict[str, Any]], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "control_id",
        "type",
        "topic",
        "clause",
        "statement",
        "doc_title",
        "page",
        "doc_id",
        "category",
        "control_type",
        "severity",
        "policy_tags",
        "implementation_hint",
    ]

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in controls:
            row = dict(c)
            if isinstance(row.get("policy_tags"), list):
                row["policy_tags"] = "; ".join(row["policy_tags"])
            writer.writerow({k: row.get(k) for k in fields})

    return out_path