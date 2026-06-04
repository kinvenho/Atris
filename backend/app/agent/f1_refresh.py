import logging
import os

from app.config import settings
from app.services.f1_refresh_service import F1RefreshService


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    season = os.environ.get("F1_REFRESH_SEASON", settings.F1_REFRESH_SEASON)
    retrain_models = os.environ.get("F1_REFRESH_RETRAIN_MODELS")
    if retrain_models is None:
        should_retrain = settings.F1_REFRESH_RETRAIN_MODELS
    else:
        should_retrain = retrain_models.strip().lower() in {"1", "true", "yes"}

    result = F1RefreshService.refresh_season(
        season=season,
        retrain_models=should_retrain,
        refresh_live_sessions=True,
    )
    logging.info("F1 refresh completed: %s", result)
