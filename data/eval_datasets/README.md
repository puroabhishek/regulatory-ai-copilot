# data/eval_datasets/

Input datasets for the eval framework. Each subfolder contains JSON test cases for a specific task.

## Structure

```
eval_datasets/
  gap_analysis/        # Control + policy text → expected coverage status
  policy_generation/   # Profile + controls → expected policy sections
  control_classification/  # Control text → expected category/type/severity
```

## Authoring test cases

### Gap analysis case

```json
{
  "id": "ga-001",
  "task": "gap_analysis_coverage",
  "input": {
    "control_id": "QCB-EKYC-P3-I1",
    "control_statement": "The regulated entity must implement liveness detection...",
    "policy_text_file": "data/samples/Cust_Onboarding_Madad_policy.md"
  },
  "expected_output": {
    "status": "Covered",
    "status_alternatives": ["Partially Covered"],
    "reason_contains": ["liveness", "biometric"]
  },
  "metadata": {
    "annotated_by": "user",
    "regulation": "QCB eKYC Regulation",
    "difficulty": "medium"
  }
}
```

### Policy generation case

```json
{
  "id": "pg-001",
  "task": "policy_generation",
  "input": {
    "profile_file": "data/profiles/madad_profile.json",
    "regulation_controls_file": "data/controls/qcb_ekyc_controls.json",
    "drafting_instructions": "Formal QCB-aligned tone. Include KYC process, fallback handling, record retention.",
    "reference_policy_file": "data/samples/Cust_Onboarding_Madad_policy.md"
  },
  "expected_output": {
    "required_sections": ["Purpose", "Scope", "KYC Process", "Record Keeping"],
    "required_control_ids": ["QCB-EKYC-P3-I1"],
    "min_length_chars": 2000
  },
  "metadata": {
    "annotated_by": "user",
    "regulation": "QCB eKYC Regulation"
  }
}
```

## Running evals

```bash
python -m evals.run_evals --task gap_analysis
python -m evals.run_evals --task policy_generation --model qwen2.5:14b
python -m evals.run_evals --all --report
```
