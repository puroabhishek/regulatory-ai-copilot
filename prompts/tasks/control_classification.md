Classify the following regulatory control statement for a Qatar compliance product.

Return ONLY valid JSON with these keys:
{
  "category": "",
  "control_type": "",
  "severity": "",
  "policy_tags": [],
  "implementation_hint": ""
}

Allowed values:
- control_type: {{control_type_allowed}}
- severity: {{severity_allowed}}

{{category_guidance}}

Control:
"""{{control_text}}"""

Rules:
- category should be concise (2–4 words)
- do not invent values outside the allowed control_type or severity lists
- policy_tags should be likely policy document names this control would appear in (e.g. "KYC Policy", "Data Protection Policy")
- implementation_hint should be practical, specific, and short (one sentence)
