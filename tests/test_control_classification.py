"""Unit tests for external control taxonomy and override handling."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import configs.control_taxonomy as taxonomy_config
import core.classifier as control_classifier
from domain.regulations.classifier import detect_topic


class ControlClassificationTests(unittest.TestCase):
    def test_save_taxonomy_merges_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            taxonomy_path = Path(temp_dir) / "taxonomy.json"
            saved = taxonomy_config.save_control_taxonomy(
                {
                    "topic": {
                        "default": "Custom Default",
                    }
                },
                path=taxonomy_path,
            )

            self.assertEqual(saved["topic"]["default"], "Custom Default")
            self.assertIn("fields", saved)
            self.assertIn("modality", saved)

    def test_normalize_classification_uses_aliases(self) -> None:
        taxonomy = taxonomy_config.load_control_taxonomy()

        result = taxonomy_config.normalize_classification(
            {
                "category": "Data Handling",
                "control_type": "Implementation",
                "severity": "critical",
                "policy_tags": "Policy One; Policy Two",
                "implementation_hint": "  Do the thing  ",
            },
            taxonomy=taxonomy,
        )

        self.assertEqual(result["category"], "Data Handling")
        self.assertEqual(result["control_type"], "Operational")
        self.assertEqual(result["severity"], "High")
        self.assertEqual(result["policy_tags"], ["Policy One", "Policy Two"])
        self.assertEqual(result["implementation_hint"], "Do the thing")

    def test_save_and_apply_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            overrides_path = Path(temp_dir) / "overrides.json"

            taxonomy_config.save_control_override(
                "Control text",
                {"control_type": "Governance", "severity": "High"},
                note="SME correction",
                path=overrides_path,
            )

            merged = taxonomy_config.apply_control_override(
                "Control text",
                {"category": "Technical", "control_type": "Technical", "severity": "Low"},
                path=overrides_path,
            )

            self.assertEqual(merged["category"], "Technical")
            self.assertEqual(merged["control_type"], "Governance")
            self.assertEqual(merged["severity"], "High")

    def test_detect_topic_reads_external_taxonomy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            taxonomy_path = Path(temp_dir) / "control_taxonomy.json"
            custom_taxonomy = taxonomy_config.load_control_taxonomy()
            custom_taxonomy["topic"]["rules"].insert(0, {"label": "Consent Management", "keywords": ["consent"]})

            with open(taxonomy_path, "w", encoding="utf-8") as handle:
                json.dump(custom_taxonomy, handle)

            with mock.patch.object(taxonomy_config, "DEFAULT_TAXONOMY_PATH", taxonomy_path):
                self.assertEqual(detect_topic("The institution must document consent withdrawals."), "Consent Management")

    def test_classify_control_normalizes_llm_output_and_applies_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.json"
            overrides_path = Path(temp_dir) / "overrides.json"

            taxonomy_config.save_control_override(
                "Access must be reviewed regularly.",
                {"control_type": "Governance"},
                path=overrides_path,
            )

            with mock.patch.object(control_classifier, "CACHE_PATH", cache_path), mock.patch.object(
                taxonomy_config, "DEFAULT_OVERRIDES_PATH", overrides_path
            ), mock.patch.object(
                control_classifier,
                "llm_json",
                return_value={
                    "category": "Governance",
                    "control_type": "Implementation",
                    "severity": "critical",
                    "policy_tags": ["Access Policy"],
                    "implementation_hint": "Review access on schedule.",
                },
            ):
                result = control_classifier.classify_control("Access must be reviewed regularly.", model="test-model")

            self.assertEqual(result["category"], "Governance")
            self.assertEqual(result["control_type"], "Governance")
            self.assertEqual(result["severity"], "High")
            self.assertEqual(result["policy_tags"], ["Access Policy"])


if __name__ == "__main__":
    unittest.main()
