import pandas as pd
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# INPUT DATASET
# =========================
DATASET_PATH = Path("data/synthetic_ml_dataset.csv")

# =========================
# LOAD DATA
# =========================
df = pd.read_csv(DATASET_PATH)

print("Dataset loaded.")
print(f"Shape: {df.shape}")
print("\nClass distribution:")
print(df["label"].value_counts())
print()

# =========================
# FEATURES AND TARGET
# =========================
feature_columns = [
    "session_duration_s",
    "events_count",
    "emg_duration_s",
    "emg_rms_mean",
    "emg_rms_max",
    "emg_rms_std",
    "emg_contractions_count",
    "emg_rest_count",
    "emg_contraction_ratio",
    "hr_duration_s",
    "hr_raw_mean",
    "hr_filtered_mean",
    "hr_filtered_max",
    "hr_filtered_std",
    "hr_valid_ratio",
    "hr_above_threshold_ratio",
]

target_column = "label"

X = df[feature_columns].copy()
y = df[target_column].copy()

# =========================
# TRAIN / TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"Train size: {X_train.shape[0]}")
print(f"Test size: {X_test.shape[0]}")
print()

# =========================
# MODEL
# =========================
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=6,
    random_state=42
)

model.fit(X_train, y_train)

# =========================
# PREDICTIONS
# =========================
y_pred = model.predict(X_test)

# =========================
# EVALUATION
# =========================
acc = accuracy_score(y_test, y_pred)
cm = confusion_matrix(y_test, y_pred, labels=["low", "moderate", "high"])
report = classification_report(y_test, y_pred)

print("=== RESULTS ===")
print(f"Accuracy: {acc:.4f}")
print("\nConfusion Matrix (rows=true, cols=pred):")
print(cm)
print("\nClassification Report:")
print(report)

# =========================
# FEATURE IMPORTANCE
# =========================
importances = pd.DataFrame({
    "feature": feature_columns,
    "importance": model.feature_importances_
}).sort_values(by="importance", ascending=False)

print("\nFeature importances:")
print(importances)
