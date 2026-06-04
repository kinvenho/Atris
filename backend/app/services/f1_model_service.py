import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from app.services.f1_storage_service import F1StorageService
from app.services.supabase_client import get_supabase


class F1ModelService:
    FEATURE_COLUMNS = [
        "grid",
        "qualifying_position",
        "q3",
        "prior_driver_starts",
        "prior_driver_points_per_start",
        "prior_driver_podium_rate",
        "prior_driver_points_finish_rate",
        "prior_driver_dnf_rate",
        "prior_constructor_starts",
        "prior_constructor_points_per_start",
        "prior_constructor_podium_rate",
        "prior_constructor_points_finish_rate",
        "prior_constructor_dnf_rate",
    ]

    @staticmethod
    def train_baseline(
        season: int,
        outcome_type: str,
        eval_start_round: int = 19,
    ) -> Dict[str, Any]:
        if outcome_type not in {"points_finish", "podium_finish"}:
            raise ValueError("outcome_type must be points_finish or podium_finish")

        examples = F1StorageService.list_training_examples(
            season=season,
            outcome_type=outcome_type,
            limit=2000,
        )
        if not examples:
            raise RuntimeError("No F1 training examples found for season/outcome")

        train_rows = [row for row in examples if int(row["round"]) < eval_start_round]
        eval_rows = [row for row in examples if int(row["round"]) >= eval_start_round]
        if len(train_rows) < 20 or len(eval_rows) < 20:
            raise RuntimeError("Not enough train/eval examples for baseline model")

        train_x_raw = [F1ModelService._feature_vector(row) for row in train_rows]
        train_y = [1 if row["label"] else 0 for row in train_rows]
        eval_x_raw = [F1ModelService._feature_vector(row) for row in eval_rows]
        eval_y = [1 if row["label"] else 0 for row in eval_rows]

        means, scales = F1ModelService._fit_scaler(train_x_raw)
        train_x = [F1ModelService._scale(row, means, scales) for row in train_x_raw]
        eval_x = [F1ModelService._scale(row, means, scales) for row in eval_x_raw]
        coefficients, intercept = F1ModelService._fit_logistic_regression(train_x, train_y)

        train_probabilities = [
            F1ModelService._predict_probability(row, coefficients, intercept)
            for row in train_x
        ]
        eval_probabilities = [
            F1ModelService._predict_probability(row, coefficients, intercept)
            for row in eval_x
        ]
        train_metrics = F1ModelService._classification_metrics(train_y, train_probabilities)
        eval_metrics = F1ModelService._classification_metrics(eval_y, eval_probabilities)

        model_name = "logistic_pre_race_v1"
        version = f"{season}_{outcome_type}_pre_race_v1"
        model_payload = {
            "model_name": model_name,
            "outcome_type": outcome_type,
            "version": version,
            "status": "active",
            "training_window": {
                "season": season,
                "train_rounds": [min(row["round"] for row in train_rows), max(row["round"] for row in train_rows)],
                "eval_rounds": [min(row["round"] for row in eval_rows), max(row["round"] for row in eval_rows)],
                "eval_start_round": eval_start_round,
            },
            "feature_schema": {
                "feature_set": "pre_race_v1",
                "feature_columns": F1ModelService.FEATURE_COLUMNS,
                "means": means,
                "scales": scales,
                "coefficients": coefficients,
                "intercept": intercept,
            },
            "metrics": {
                "train": train_metrics,
                "eval": eval_metrics,
                "train_examples": len(train_rows),
                "eval_examples": len(eval_rows),
                "trained_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        model_version = F1ModelService._upsert_model_version(model_payload)
        predictions = F1ModelService._prediction_rows(
            model_version_id=model_version["id"],
            outcome_type=outcome_type,
            rows=eval_rows,
            probabilities=eval_probabilities,
            split="eval",
        )
        if predictions:
            get_supabase().table("f1_model_backtest_predictions").upsert(
                predictions,
                on_conflict="model_version_id,season,round,driver_id,outcome_type,feature_set",
            ).execute()

        return {
            "status": "success",
            "model_version_id": model_version["id"],
            "model_name": model_name,
            "version": version,
            "outcome_type": outcome_type,
            "train_examples": len(train_rows),
            "eval_examples": len(eval_rows),
            "train_metrics": train_metrics,
            "eval_metrics": eval_metrics,
            "backtest_predictions": len(predictions),
        }

    @staticmethod
    def list_model_versions(outcome_type: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
        query = (
            get_supabase()
            .table("f1_model_versions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if outcome_type:
            query = query.eq("outcome_type", outcome_type)
        response = query.execute()
        return response.data or []

    @staticmethod
    def list_backtest_predictions(
        season: int,
        outcome_type: str | None = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        query = (
            get_supabase()
            .table("f1_model_backtest_predictions")
            .select("*")
            .eq("season", season)
            .order("round")
            .limit(limit)
        )
        if outcome_type:
            query = query.eq("outcome_type", outcome_type)
        response = query.execute()
        return response.data or []

    @staticmethod
    def predict_race(season: int, round_number: int) -> Dict[str, Any]:
        points_model = F1ModelService._active_model_version("points_finish")
        podium_model = F1ModelService._active_model_version("podium_finish")
        points_examples = F1StorageService.list_training_examples(
            season=season,
            outcome_type="points_finish",
            limit=2000,
        )
        podium_examples = F1StorageService.list_training_examples(
            season=season,
            outcome_type="podium_finish",
            limit=2000,
        )
        points_by_driver = {
            row["driver_id"]: row
            for row in points_examples
            if int(row["round"]) == round_number
        }
        podium_by_driver = {
            row["driver_id"]: row
            for row in podium_examples
            if int(row["round"]) == round_number
        }
        if not points_by_driver:
            raise RuntimeError("No training feature rows found for season/round")

        predictions = []
        for driver_id, points_row in sorted(points_by_driver.items(), key=lambda item: F1ModelService._sort_grid(item[1])):
            podium_row = podium_by_driver.get(driver_id)
            points_prediction = F1ModelService._predict_from_model(points_model, points_row)
            podium_prediction = F1ModelService._predict_from_model(podium_model, podium_row or points_row)
            features = points_row.get("features") or {}
            predictions.append({
                "season": season,
                "round": round_number,
                "race_name": points_row.get("race_name"),
                "driver_id": driver_id,
                "driver_code": points_row.get("driver_code"),
                "constructor_id": points_row.get("constructor_id"),
                "constructor_name": points_row.get("constructor_name"),
                "grid": features.get("grid"),
                "qualifying_position": features.get("qualifying_position"),
                "q3": features.get("q3"),
                "points_finish_probability": points_prediction["probability"],
                "podium_finish_probability": podium_prediction["probability"],
                "points_finish_label": points_row.get("label"),
                "podium_finish_label": podium_row.get("label") if podium_row else None,
                "source_result": points_row.get("source_result") or {},
            })

        return {
            "season": season,
            "round": round_number,
            "race_name": predictions[0]["race_name"] if predictions else None,
            "prediction_mode": "pre_race",
            "feature_set": "pre_race_v1",
            "models": {
                "points_finish": F1ModelService._model_summary(points_model),
                "podium_finish": F1ModelService._model_summary(podium_model),
            },
            "predictions": predictions,
        }

    @staticmethod
    def predict_driver(season: int, round_number: int, driver_id: str) -> Dict[str, Any]:
        board = F1ModelService.predict_race(season, round_number)
        for prediction in board["predictions"]:
            if prediction["driver_id"] == driver_id:
                return {
                    **prediction,
                    "prediction_mode": board["prediction_mode"],
                    "feature_set": board["feature_set"],
                    "models": board["models"],
                }
        raise RuntimeError("No prediction found for driver in season/round")

    @staticmethod
    def _upsert_model_version(payload: Dict[str, Any]) -> Dict[str, Any]:
        response = (
            get_supabase()
            .table("f1_model_versions")
            .upsert(payload, on_conflict="model_name,version")
            .execute()
        )
        if response.data:
            return response.data[0]

        fallback = (
            get_supabase()
            .table("f1_model_versions")
            .select("*")
            .eq("model_name", payload["model_name"])
            .eq("version", payload["version"])
            .limit(1)
            .execute()
        )
        if not fallback.data:
            raise RuntimeError("Failed to upsert F1 model version")
        return fallback.data[0]

    @staticmethod
    def _active_model_version(outcome_type: str) -> Dict[str, Any]:
        response = (
            get_supabase()
            .table("f1_model_versions")
            .select("*")
            .eq("model_name", "logistic_pre_race_v1")
            .eq("outcome_type", outcome_type)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise RuntimeError(f"No active F1 model version found for {outcome_type}")
        return response.data[0]

    @staticmethod
    def _predict_from_model(model_version: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        feature_schema = model_version.get("feature_schema") or {}
        means = feature_schema.get("means") or []
        scales = feature_schema.get("scales") or []
        coefficients = feature_schema.get("coefficients") or []
        intercept = float(feature_schema.get("intercept") or 0)
        if not means or not scales or not coefficients:
            raise RuntimeError("Model version is missing feature schema parameters")

        raw_features = F1ModelService._feature_vector(row)
        scaled_features = F1ModelService._scale(raw_features, means, scales)
        probability = F1ModelService._predict_probability(scaled_features, coefficients, intercept)
        return {
            "probability": round(probability, 8),
            "model_version_id": model_version["id"],
            "version": model_version["version"],
        }

    @staticmethod
    def _model_summary(model_version: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": model_version["id"],
            "model_name": model_version["model_name"],
            "version": model_version["version"],
            "outcome_type": model_version["outcome_type"],
            "metrics": model_version.get("metrics") or {},
        }

    @staticmethod
    def _sort_grid(row: Dict[str, Any]) -> tuple[int, str]:
        features = row.get("features") or {}
        grid = features.get("grid")
        try:
            grid_value = int(grid)
        except (TypeError, ValueError):
            grid_value = 99
        return grid_value, str(row.get("driver_id") or "")

    @staticmethod
    def _feature_vector(row: Dict[str, Any]) -> List[float]:
        features = row.get("features") or {}
        vector = []
        for column in F1ModelService.FEATURE_COLUMNS:
            value = features.get(column)
            if column in {"grid", "qualifying_position"} and value is None:
                value = 20
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
            if value is None:
                value = 0.0
            vector.append(float(value))
        return vector

    @staticmethod
    def _fit_scaler(rows: Sequence[Sequence[float]]) -> tuple[List[float], List[float]]:
        column_count = len(rows[0])
        means: List[float] = []
        scales: List[float] = []
        for index in range(column_count):
            values = [row[index] for row in rows]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            scale = math.sqrt(variance) or 1.0
            means.append(round(mean, 8))
            scales.append(round(scale, 8))
        return means, scales

    @staticmethod
    def _scale(row: Sequence[float], means: Sequence[float], scales: Sequence[float]) -> List[float]:
        return [
            (float(value) - means[index]) / scales[index]
            for index, value in enumerate(row)
        ]

    @staticmethod
    def _fit_logistic_regression(
        rows: Sequence[Sequence[float]],
        labels: Sequence[int],
        iterations: int = 1800,
        learning_rate: float = 0.04,
        l2: float = 0.002,
    ) -> tuple[List[float], float]:
        coefficients = [0.0 for _ in rows[0]]
        positive_rate = min(max(sum(labels) / len(labels), 0.001), 0.999)
        intercept = math.log(positive_rate / (1.0 - positive_rate))

        for _ in range(iterations):
            gradients = [0.0 for _ in coefficients]
            intercept_gradient = 0.0
            for row, label in zip(rows, labels):
                probability = F1ModelService._predict_probability(row, coefficients, intercept)
                error = probability - label
                intercept_gradient += error
                for index, value in enumerate(row):
                    gradients[index] += error * value

            sample_count = len(rows)
            intercept -= learning_rate * (intercept_gradient / sample_count)
            for index in range(len(coefficients)):
                gradient = (gradients[index] / sample_count) + (l2 * coefficients[index])
                coefficients[index] -= learning_rate * gradient

        return [round(value, 8) for value in coefficients], round(intercept, 8)

    @staticmethod
    def _predict_probability(row: Sequence[float], coefficients: Sequence[float], intercept: float) -> float:
        score = intercept + sum(value * coefficients[index] for index, value in enumerate(row))
        if score >= 0:
            z = math.exp(-score)
            return 1.0 / (1.0 + z)
        z = math.exp(score)
        return z / (1.0 + z)

    @staticmethod
    def _classification_metrics(labels: Sequence[int], probabilities: Sequence[float]) -> Dict[str, Any]:
        clipped = [min(max(probability, 1e-6), 1 - 1e-6) for probability in probabilities]
        brier = sum((probability - label) ** 2 for probability, label in zip(clipped, labels)) / len(labels)
        log_loss = -sum(
            label * math.log(probability) + (1 - label) * math.log(1 - probability)
            for probability, label in zip(clipped, labels)
        ) / len(labels)
        accuracy = sum((probability >= 0.5) == bool(label) for probability, label in zip(clipped, labels)) / len(labels)
        positive_rate = sum(labels) / len(labels)
        average_probability = sum(clipped) / len(clipped)
        return {
            "brier": round(brier, 6),
            "log_loss": round(log_loss, 6),
            "accuracy": round(accuracy, 6),
            "positive_rate": round(positive_rate, 6),
            "average_probability": round(average_probability, 6),
        }

    @staticmethod
    def _prediction_rows(
        model_version_id: str,
        outcome_type: str,
        rows: Sequence[Dict[str, Any]],
        probabilities: Sequence[float],
        split: str,
    ) -> List[Dict[str, Any]]:
        prediction_rows = []
        for row, probability in zip(rows, probabilities):
            prediction_rows.append({
                "model_version_id": model_version_id,
                "season": row["season"],
                "round": row["round"],
                "race_name": row.get("race_name"),
                "driver_id": row["driver_id"],
                "driver_code": row.get("driver_code"),
                "constructor_id": row.get("constructor_id"),
                "outcome_type": outcome_type,
                "label": bool(row["label"]),
                "probability": round(probability, 8),
                "predicted_label": probability >= 0.5,
                "feature_set": row.get("feature_set") or "pre_race_v1",
                "split": split,
                "features": row.get("features") or {},
            })
        return prediction_rows
