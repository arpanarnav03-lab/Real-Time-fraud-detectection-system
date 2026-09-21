"""
Generates a synthetic digital-lending transaction dataset for the fraud
detection prototype. Features are modeled after common real-world fraud
signals (distance anomalies, purchase ratio anomalies, channel behavior)
so the model learns meaningful, explainable patterns rather than noise.
"""
import numpy as np
import pandas as pd

np.random.seed(42)
N = 20000
FRAUD_RATE = 0.03

def generate():
    n_fraud = int(N * FRAUD_RATE)
    n_legit = N - n_fraud

    def legit_batch(n):
        return pd.DataFrame({
            "distance_from_home": np.random.exponential(15, n),
            "distance_from_last_transaction": np.random.exponential(5, n),
            "ratio_to_median_purchase": np.random.gamma(2, 0.5, n),
            "repeat_borrower": np.random.binomial(1, 0.85, n),
            "used_chip_or_biometric": np.random.binomial(1, 0.8, n),
            "used_pin_or_otp": np.random.binomial(1, 0.75, n),
            "is_online_channel": np.random.binomial(1, 0.4, n),
            "hour_of_day": np.random.normal(14, 4, n).clip(0, 23),
            "loan_amount": np.random.lognormal(9, 1, n),
            "is_fraud": 0,
        })

    def fraud_batch(n):
        return pd.DataFrame({
            "distance_from_home": np.random.exponential(120, n),
            "distance_from_last_transaction": np.random.exponential(80, n),
            "ratio_to_median_purchase": np.random.gamma(5, 1.5, n),
            "repeat_borrower": np.random.binomial(1, 0.15, n),
            "used_chip_or_biometric": np.random.binomial(1, 0.2, n),
            "used_pin_or_otp": np.random.binomial(1, 0.15, n),
            "is_online_channel": np.random.binomial(1, 0.9, n),
            "hour_of_day": np.random.normal(2, 3, n).clip(0, 23),
            "loan_amount": np.random.lognormal(10.5, 1.3, n),
            "is_fraud": 1,
        })

    df = pd.concat([legit_batch(n_legit), fraud_batch(n_fraud)], ignore_index=True)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)

if __name__ == "__main__":
    df = generate()
    df.to_csv("/home/claude/fraud-detection-hackathon/data/transactions.csv", index=False)
    print(f"Generated {len(df)} rows, {df['is_fraud'].sum()} fraud ({df['is_fraud'].mean():.2%})")
