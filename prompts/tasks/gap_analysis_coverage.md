Compare the policy text against the regulatory control and decide whether the control is:
- Covered
- Partially Covered
- Missing

Return ONLY valid JSON in this exact format:
{
  "status": "Covered | Partially Covered | Missing",
  "reason": "short explanation referencing the specific policy text that does or does not address this control",
  "remediation": "specific, actionable addition or fix to make the control fully covered"
}

CONTROL ID:
{{control_id}}

CONTROL:
{{control_statement}}

POLICY TEXT:
"""
{{policy_text_excerpt}}
"""

Rules:
1. Be strict and practical.
2. "Covered" only if the policy clearly and explicitly addresses the control requirement.
3. "Partially Covered" if the policy touches the topic but misses key specificity or a required sub-requirement.
4. "Missing" if the control topic is not addressed at all.
5. The reason must cite the specific clause or section (or note its absence).
6. Remediation must be concise and actionable — one to two sentences.
