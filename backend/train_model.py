"""
Trains the fraud scoring model: XGBoost with class-weight balancing
(scale_pos_weight, equivalent in effect to SMOTE for this dataset size)
and stratified train/test split. Saves the model + feature list for the
API to load at startup.
"""
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

FEATURES = [
    "distance_from_home",
    "distance_from_last_transaction",
    "ratio_to_median_purchase",
    "repeat_borrower",
    "used_chip_or_biometric",
    "used_pin_or_otp",
    "is_online_channel",
    "hour_of_day",
    "loan_amount",
]

def train():
    df = pd.read_csv("/home/claude/fraud-detection-hackathon/data/transactions.csv")
    X, y = df[FEATURES], df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        random_state=42,
    )
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    preds = model.predict(X_test)

    print(f"ROC-AUC: {auc:.4f}")
    print(classification_report(y_test, preds, target_names=["legit", "fraud"]))

    joblib.dump({"model": model, "features": FEATURES}, "/home/claude/fraud-detection-hackathon/backend/fraud_model.joblib")
    print("Model saved to backend/fraud_model.joblib")

if __name__ == "__main__":
    train()
