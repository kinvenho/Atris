import logging
from typing import List, Dict, Any
from app.integrations.polymarket import PolymarketClient

logger = logging.getLogger(__name__)

def scan_markets() -> List[Dict[str, Any]]:
    """
    Step 1 in Pipeline: MarketScanner
    Queries Polymarket for open markets and applies basic criteria.
    Returns: Top candidates sorted by volume (up to MAX_CANDIDATES_PER_RUN).
    """
    logger.info("Pipeline Step 1: Running MarketScanner...")
    client = PolymarketClient()
    candidates = client.fetch_active_markets()
    logger.info(f"MarketScanner completed. Found {len(candidates)} candidate markets.")
    return candidates
