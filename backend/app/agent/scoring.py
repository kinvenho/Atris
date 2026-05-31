import logging

from app.services.scoring_service import ScoringService


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ScoringService.generate_snapshot()
