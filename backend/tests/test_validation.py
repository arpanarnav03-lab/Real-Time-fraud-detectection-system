"""Input-validation edge cases on the transaction endpoints: the Field
constraints on TransactionIn/StatusUpdate, the duplicate-submission guard,
and the fix for non-finite floats crashing the validation-error response.
"""
import concurrent.futures

VALID_PAYLOAD = {
    "distance_from_home": 10,
    "distance_from_last_transaction": 5,
    "ratio_to_median_purchase": 1,
    "repeat_borrower": 1,
    "used_chip_or_biometric": 1,
    "used_pin_or_otp": 1,
    "is_online_channel": 0,
    "hour_of_day": 12,
    "loan_amount": 1000,
}


def test_negative_loan_amount_rejected(client, auth_headers):
    payload = {**VALID_PAYLOAD, "loan_amount": -5}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


def test_zero_loan_amount_rejected(client, auth_headers):
    payload = {**VALID_PAYLOAD, "loan_amount": 0}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


def test_negative_distance_rejected(client, auth_headers):
    payload = {**VALID_PAYLOAD, "distance_from_home": -1}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


def test_hour_of_day_out_of_range_rejected(client, auth_headers):
    payload = {**VALID_PAYLOAD, "hour_of_day": 99}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


def test_hour_of_day_boundary_23_accepted(client, auth_headers):
    payload = {**VALID_PAYLOAD, "hour_of_day": 23, "loan_amount": 1001}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 200, res.text


def test_binary_flag_out_of_range_rejected(client, auth_headers):
    payload = {**VALID_PAYLOAD, "repeat_borrower": 5}
    res = client.post("/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


def test_missing_field_rejected(client, auth_headers):
    res = client.post("/transactions", json={"distance_from_home": 10}, headers=auth_headers)
    assert res.status_code == 422


def test_infinity_value_rejected_not_500(client, auth_headers):
    # json.dumps() emits the literal (non-standard) `Infinity` token, which
    # Python's own json module round-trips; sent verbatim like this, Pydantic
    # should reject it as non-finite (422), not crash while rendering the
    # error body (which previously produced a 500 — see main.py).
    body = (
        '{"distance_from_home": Infinity, "distance_from_last_transaction": 5,'
        ' "ratio_to_median_purchase": 1, "repeat_borrower": 1,'
        ' "used_chip_or_biometric": 1, "used_pin_or_otp": 1,'
        ' "is_online_channel": 0, "hour_of_day": 12, "loan_amount": 1000}'
    )
    res = client.post(
        "/transactions", content=body, headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert res.status_code == 422


def test_duplicate_rapid_submission_rejected(client, auth_headers):
    # The dedup window is only 3s, and scoring a transaction (embedding +
    # similarity search + two inserts, all round-tripping to Neon) can take
    # longer than that on its own — so two *sequential* calls here could
    # legitimately land outside the window through no fault of the guard.
    # Firing them concurrently, like a double-clicked submit button would,
    # is what the feature actually protects against.
    payload = {**VALID_PAYLOAD, "loan_amount": 4242}

    def submit():
        return client.post("/transactions", json=payload, headers=auth_headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result() for f in [pool.submit(submit), pool.submit(submit)]]

    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 409], [r.text for r in results]


def test_patch_invalid_status_rejected(client, auth_headers):
    res = client.patch("/transactions/1", json={"status": "banana"}, headers=auth_headers)
    assert res.status_code == 422


def test_patch_nonexistent_transaction_404(client, auth_headers):
    res = client.patch("/transactions/999999999", json={"status": "cleared"}, headers=auth_headers)
    assert res.status_code == 404
