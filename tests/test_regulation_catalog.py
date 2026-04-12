"""Unit tests for profile-linked regulation recommendations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.regulations.catalog import recommend_regulations_for_profile, resolve_control_files_for_regulations


class RegulationCatalogTests(unittest.TestCase):
    def test_recommendations_match_qatar_fintech_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controls_dir = Path(temp_dir)
            controls_dir.joinpath("data_handling_and_protection_regulation_controls.json").write_text("[]", encoding="utf-8")
            controls_dir.joinpath("cloud_computing_regulation_controls.json").write_text("[]", encoding="utf-8")
            controls_dir.joinpath("qcb_-_ekyc_regulation_controls.json").write_text("[]", encoding="utf-8")
            controls_dir.joinpath(
                "ncsa-ncgaa-law_no._(13)_of_2016__on_protecting_personal_data_privacy_-_english_controls.json"
            ).write_text("[]", encoding="utf-8")
            controls_dir.joinpath("ncsa_csga_national_data_classification_policy_en_v3.0_controls.json").write_text("[]", encoding="utf-8")

            profile = {
                "country": "Qatar",
                "regulator": "QCB",
                "sector": "Fintech",
                "business_type": "Lending",
                "cloud_use": "Yes",
                "handles_pii": "Yes",
                "handles_financial_data": "Yes",
                "performs_kyc": "Yes",
                "mandated_kyc": "Yes",
            }

            recommendations = recommend_regulations_for_profile(profile, controls_dir=str(controls_dir))
            titles = {item["title"] for item in recommendations}

            self.assertIn("QCB Data Handling and Protection Regulation", titles)
            self.assertIn("QCB Cloud Computing Regulation", titles)
            self.assertIn("QCB eKYC Regulation", titles)
            self.assertIn("Qatar Personal Data Privacy Law (Law No. 13 of 2016)", titles)
            self.assertIn("National Data Classification Policy v3.0", titles)
            self.assertTrue(all(item["control_file_available"] for item in recommendations))

    def test_resolve_control_files_reports_missing_titles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controls_dir = Path(temp_dir)
            controls_dir.joinpath("cloud_computing_regulation_controls.json").write_text("[]", encoding="utf-8")

            resolution = resolve_control_files_for_regulations(
                [
                    "QCB Cloud Computing Regulation",
                    "QCB eKYC Regulation",
                    "Unmapped Custom Guideline",
                ],
                controls_dir=str(controls_dir),
            )

            self.assertEqual(resolution["control_files"], ["cloud_computing_regulation_controls.json"])
            self.assertIn("QCB eKYC Regulation", resolution["missing_regulations"])
            self.assertIn("Unmapped Custom Guideline", resolution["missing_regulations"])


if __name__ == "__main__":
    unittest.main()
