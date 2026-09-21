"""Scoring behavior: known high-risk and low-risk feature patterns should
land in the expected risk band. These hit the real trained XGBoost model
via POST /transactions, not a mock.
"""

# Mirrors the frontend's "Try a suspicious pattern" preset: far from home,
# far from the last transaction, way above the median purchase, odd hour,
# no chip/PIN, online — the model consistently scores this as high risk.
SUSPICIOUS_PAYLOAD = {
    "distance_from_home": 300,
    "distance_from_last_transaction": 180,
    "ratio_to_median_purchase": 7.5,
    "repeat_borrower": 0,
    "used_chip_or_biometric": 0,
    "used_pin_or_otp": 0,
    "is_online_channel": 1,
    "hour_of_day": 3,
    "loan_amount": 80000,
}

# Mirrors the frontend's "Try a normal pattern" preset: close to home,
# typical purchase size, midday, chip+PIN, in person.
NORMAL_PAYLOAD = {
    "distance_from_home": 8,
    "distance_from_last_transaction": 3,
    "ratio_to_median_purchase": 1.0,
    "repeat_borrower": 1,
    "used_chip_or_biometric": 1,
    "used_pin_or_otp": 1,
    "is_online_channel": 0,
    "hour_of_day": 14,
    "loan_amount": 5000,
}


def test_suspicious_pattern_scores_high_risk(client, auth_headers):
    res = client.post("/transactions", json=SUSPICIOUS_PAYLOAD, headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["risk_level"] == "high"
    assert body["fraud_probability"] >= 0.7


def test_normal_pattern_scores_low_risk(client, auth_headers):
    res = client.post("/transactions", json=NORMAL_PAYLOAD, headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["risk_level"] == "low"
    assert body["fraud_probability"] < 0.3


def test_risk_level_from_prob_boundaries():
    from main import risk_level_from_prob

    assert risk_level_from_prob(0.0) == "low"
    assert risk_level_from_prob(0.29) == "low"
    assert risk_level_from_prob(0.3) == "medium"
    assert risk_level_from_prob(0.69) == "medium"
    assert risk_level_from_prob(0.7) == "high"
    assert risk_level_from_prob(1.0) == "high"
