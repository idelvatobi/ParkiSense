# =============================================================================
# ParkiSense — ml/inference.py
#
# Carga el modelo Random Forest y realiza la predicción sobre un dict
# de features de sesión.
# =============================================================================

import json
import os
import joblib
import pandas as pd


class MLInference:
    """
    Carga el modelo Random Forest una sola vez y lo mantiene en memoria.

    Uso:
        ml = MLInference("ml/models/random_forest_model.pkl",
                         "ml/models/rf_feature_columns.json")
        result = ml.predict(features_dict)
        # result = {
        #     "predicted_label": "high",
        #     "probabilities": {"low": 0.1, "moderate": 0.2, "high": 0.7},
        #     "features": {...}
        # }
    """

    def __init__(self, model_path: str, features_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
        if not os.path.exists(features_path):
            raise FileNotFoundError(f"Features JSON no encontrado: {features_path}")

        self._model = joblib.load(model_path)

        with open(features_path, "r", encoding="utf-8") as f:
            self._feature_columns = json.load(f)

        print(f"[MLInference] Modelo cargado: {model_path}")
        print(f"[MLInference] Features: {self._feature_columns}")

    def predict(self, features: dict) -> dict:
        """
        Realiza la predicción sobre un dict de features.

        Parámetros:
            features : dict con las features de sesión
                       (las mismas que rf_feature_columns.json)

        Retorna:
            dict con:
                predicted_label  : "low" | "moderate" | "high"
                probabilities    : {"low": float, "moderate": float, "high": float}
                features         : el dict de features original
        """
        # Verificar que tenemos todas las columnas necesarias
        missing = [col for col in self._feature_columns if col not in features]
        if missing:
            raise ValueError(f"Faltan features: {missing}")

        # Crear DataFrame con el orden correcto de columnas
        df = pd.DataFrame([features])[self._feature_columns]

        # Predicción
        predicted_label = str(self._model.predict(df)[0])
        predicted_probs = self._model.predict_proba(df)[0]

        probabilities = {
            str(cls): round(float(prob), 4)
            for cls, prob in zip(self._model.classes_, predicted_probs)
        }

        print(f"[MLInference] Predicción: {predicted_label}")
        print(f"[MLInference] Probabilidades: {probabilities}")

        return {
            "predicted_label": predicted_label,
            "probabilities":   probabilities,
            "features":        features,
        }
