"""
Generates a human-readable fraud explanation + recommended action from the
ML score and top contributing features. Calls the Anthropic API if
ANTHROPIC_API_KEY is set; otherwise falls back to a deterministic
rule-based explanation so the system degrades gracefully instead of
failing (mirrors the confidence-fallback pattern used in the interlinking
engine this prototype builds on).
"""
import os
import json

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

_client = None
if ANTHROPIC_API_KEY:
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception:
        _client = None


def _rule_based_explanation(risk_level: str, top_features: list, fraud_probability: float) -> dict:
    feature_str = ", ".join(f"{f['name']} ({f['value']:.1f})" for f in top_features[:3])
    if risk_level == "high":
        action = "block"
        explanation = (
            f"Flagged as high risk ({fraud_probability:.0%} fraud probability). "
            f"Primary signals: {feature_str}. This pattern deviates sharply from "
            f"the borrower's typical behavior and matches known fraud indicators."
        )
    elif risk_level == "medium":
        action = "flag_for_review"
        explanation = (
            f"Flagged for manual review ({fraud_probability:.0%} fraud probability). "
            f"Contributing signals: {feature_str}. Not conclusive on its own, but "
            f"warrants a closer look before approval."
        )
    else:
        action = "approve"
        explanation = (
            f"Low fraud risk ({fraud_probability:.0%}). Transaction behavior is "
            f"consistent with the borrower's normal pattern."
        )
    return {"explanation": explanation, "recommended_action": action, "source": "rule_based_fallback"}


def explain_transaction(fraud_probability: float, risk_level: str, top_features: list) -> dict:
    if _client is None:
        return _rule_based_explanation(risk_level, top_features, fraud_probability)

    feature_desc = "\n".join(f"- {f['name']}: {f['value']:.2f}" for f in top_features)
    prompt = f"""A fraud detection model scored a digital lending transaction:
Fraud probability: {fraud_probability:.2%}
Risk level: {risk_level}
Top contributing features:
{feature_desc}

Respond ONLY with JSON, no preamble, no markdown fences:
{{"explanation": "<2-3 sentence plain-English explanation a fraud analyst can act on>", "recommended_action": "<one of: approve, flag_for_review, block>"}}"""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        parsed["source"] = "llm"
        return parsed
    except Exception:
        # Graceful degradation: never let an LLM/API failure break scoring
        return _rule_based_explanation(risk_level, top_features, fraud_probability)
