"""Transit delay predictor (RandomForestClassifier).

Trains on the daily ``transit_performance`` aggregates produced by the ETL
pipeline and predicts the probability that a given route, at a given hour and
day-of-week, will be "delayed" (avg delay > 5 minutes).

Public API:
    * ``train_and_persist`` — train, evaluate, serialise model, return a
      DataFrame of predictions ready for the ``delay_predictions`` table.
    * ``predict_delay_probability`` — load the persisted model and score a
      single (route_id, hour, day) request.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # imported lazily at runtime to keep the API's memory low
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join("models", "delay_model.pkl")
MODEL_VERSION = "1.0.0"
FEATURES = ["route_enc", "hour_of_day", "day_of_week", "month", "stop_count_on_route"]


def _build_training_frame(
    performance: pd.DataFrame, stops: pd.DataFrame
) -> pd.DataFrame:
    """Expand daily performance into hourly feature rows with a binary target."""
    import numpy as np
    import pandas as pd

    if performance.empty:
        return pd.DataFrame()

    stop_counts = (
        stops.groupby("neighbourhood_id").size().mean() if not stops.empty else 5.0
    )
    rng = np.random.default_rng(7)
    rows: list[dict] = []
    for _, perf in performance.iterrows():
        service_date = pd.to_datetime(perf["service_date"])
        for hour in range(6, 23, 2):  # service hours, every 2h
            # Higher delay likelihood at rush hour.
            rush = 1.0 if hour in (7, 8, 16, 17, 18) else 0.0
            base_delay = float(perf["avg_delay_mins"])
            sample_delay = base_delay + rush * 3 + rng.normal(0, 1.5)
            rows.append(
                {
                    "route_id": perf["route_id"],
                    "hour_of_day": hour,
                    "day_of_week": int(service_date.dayofweek),
                    "month": int(service_date.month),
                    "stop_count_on_route": float(stop_counts),
                    "is_delayed": int(sample_delay > 5.0),
                }
            )
    return pd.DataFrame(rows)


def train_and_persist(
    performance: pd.DataFrame, stops: pd.DataFrame
) -> pd.DataFrame | None:
    """Train the model, print evaluation, persist it, and return predictions.

    Returns a DataFrame matching the ``delay_predictions`` schema, or ``None``
    if there was insufficient data to train.
    """
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    frame = _build_training_frame(performance, stops)
    if frame.empty or frame["is_delayed"].nunique() < 2:
        logger.warning("Insufficient/!balanced data to train delay predictor; skipping")
        return None

    encoder = LabelEncoder()
    frame["route_enc"] = encoder.fit_transform(frame["route_id"].astype(str))

    x = frame[FEATURES]
    y = frame["is_delayed"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)[:, 1]
    print("=== Delay Predictor — Classification Report ===")
    print(classification_report(y_test, y_pred, zero_division=0))
    try:
        print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.4f}")
    except ValueError:
        print("ROC-AUC: undefined (single class in test split)")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "encoder": encoder, "version": MODEL_VERSION}, MODEL_PATH)
    logger.info("Persisted delay model to %s", MODEL_PATH)

    return _build_predictions(model, encoder, frame)


def _build_predictions(
    model: RandomForestClassifier, encoder: LabelEncoder, frame: pd.DataFrame
) -> pd.DataFrame:
    """Score every (route, hour, day) combination for the predictions table."""
    import pandas as pd

    today = datetime.utcnow().date()
    routes = sorted(frame["route_id"].astype(str).unique())
    stop_count = float(frame["stop_count_on_route"].iloc[0])
    rows: list[dict] = []
    for route_id in routes:
        route_enc = int(encoder.transform([route_id])[0])
        for hour in range(6, 23, 2):
            for dow in range(7):
                feats = pd.DataFrame(
                    [[route_enc, hour, dow, today.month, stop_count]], columns=FEATURES
                )
                proba = float(model.predict_proba(feats)[0, 1])
                rows.append(
                    {
                        "prediction_id": f"{route_id}-{hour}-{dow}-{today.isoformat()}",
                        "route_id": route_id,
                        "prediction_date": today,
                        "hour_of_day": hour,
                        "day_of_week": dow,
                        "delay_probability": round(proba, 4),
                        "model_version": MODEL_VERSION,
                    }
                )
    out = pd.DataFrame(rows)
    out["ingested_at"] = datetime.utcnow()
    return out


def _heuristic_probability(route_id: str, hour: int) -> float:
    """Deterministic, dependency-free delay estimate (no scikit-learn needed)."""
    rush = hour in (7, 8, 16, 17, 18)
    return round(
        min(0.95, 0.3 + (0.3 if rush else 0.0) + (hash(route_id) % 20) / 100.0), 4
    )


def _model_enabled() -> bool:
    """Only load the scikit-learn model when explicitly opted in.

    Loading the pickled RandomForest pulls scikit-learn/scipy into memory
    (~150 MB), which overruns small free-tier instances. We default to the
    lightweight heuristic and let larger deployments opt in with
    ``USE_ML_MODEL=1``.
    """
    return os.environ.get("USE_ML_MODEL", "").strip().lower() in {"1", "true", "yes"}


def predict_delay_probability(route_id: str, hour: int, day: int) -> float:
    """Return the delay probability for a (route, hour, day) request.

    Uses the trained scikit-learn model when ``USE_ML_MODEL`` is enabled and a
    model file exists; otherwise falls back to a deterministic heuristic so the
    API stays lightweight.
    """
    if not (_model_enabled() and os.path.exists(MODEL_PATH)):
        return _heuristic_probability(route_id, hour)

    import joblib
    import pandas as pd

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    encoder = bundle["encoder"]
    try:
        route_enc = int(encoder.transform([str(route_id)])[0])
    except ValueError:
        route_enc = 0
    feats = pd.DataFrame(
        [[route_enc, hour, day, datetime.utcnow().month, 5.0]], columns=FEATURES
    )
    return round(float(model.predict_proba(feats)[0, 1]), 4)
