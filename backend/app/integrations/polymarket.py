import httpx
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com"

    def fetch_active_markets(self) -> List[Dict[str, Any]]:
        """
        Fetches active markets from Polymarket Gamma API and filters them:
        - Volume above threshold
        - Liquidity above threshold
        - Closing date at least 48 hours away
        - Binary markets only (YES/NO)
        """
        url = f"{self.base_url}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "volume_num_min": settings.MIN_VOLUME,
            "liquidity_num_min": settings.MIN_LIQUIDITY,
            "limit": 100  # Fetch a good pool to filter locally
        }

        try:
            logger.info("Fetching active markets from Polymarket Gamma API...")
            response = httpx.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            raw_markets = response.json()
            logger.info(f"Fetched {len(raw_markets)} raw markets. Filtering...")

            filtered_markets = []
            now = datetime.now(timezone.utc)
            min_closing_time = now + timedelta(hours=settings.MIN_HOURS_TO_CLOSE)

            for m in raw_markets:
                # 1. Parse outcomes
                outcomes_raw = m.get("outcomes")
                if not outcomes_raw:
                    continue
                try:
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                except Exception:
                    continue

                # Filter: Binary markets only (exactly 2 outcomes)
                if not outcomes or len(outcomes) != 2:
                    continue
                
                # Check for standard YES/NO side labels (case-insensitive)
                outcomes_upper = [o.upper() for o in outcomes]
                if not ("YES" in outcomes_upper and "NO" in outcomes_upper):
                    # Sometimes they are represented differently, but we start with YES/NO only
                    continue

                # 2. Parse closing time (endDate)
                end_date_str = m.get("endDate")
                if not end_date_str:
                    continue
                try:
                    # Handle Z suffix for UTC
                    if end_date_str.endswith("Z"):
                        clean_date_str = end_date_str[:-1] + "+00:00"
                    else:
                        clean_date_str = end_date_str
                    closing_time = datetime.fromisoformat(clean_date_str)
                except Exception as e:
                    logger.warning(f"Could not parse endDate '{end_date_str}': {e}")
                    continue

                # Filter: Closing date at least 48 hours away
                if closing_time < min_closing_time:
                    continue

                # 3. Parse volume and liquidity to double-check
                try:
                    volume = float(m.get("volume", 0))
                    liquidity = float(m.get("liquidity", 0))
                except (ValueError, TypeError):
                    continue

                if volume < settings.MIN_VOLUME or liquidity < settings.MIN_LIQUIDITY:
                    continue

                # 4. Parse outcome prices
                prices_raw = m.get("outcomePrices")
                if not prices_raw:
                    continue
                try:
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    prices = [float(p) for p in prices]
                except Exception:
                    continue

                if len(prices) != 2:
                    continue

                # Determine YES price and market probability
                yes_index = outcomes_upper.index("YES")
                yes_price = prices[yes_index]

                # Create normalized candidate object
                candidate = {
                    "polymarket_id": str(m.get("id")),
                    "question": m.get("question"),
                    "category": m.get("category", "General"),
                    "closing_time": closing_time,
                    "volume": volume,
                    "liquidity": liquidity,
                    "yes_price": yes_price,
                    "outcomes": outcomes,
                    "outcome_prices": prices,
                    "raw_data": m
                }
                filtered_markets.append(candidate)

            logger.info(f"Filtering complete. Found {len(filtered_markets)} valid candidates.")
            
            # Sort by volume descending and take up to the configured limit
            filtered_markets.sort(key=lambda x: x["volume"], reverse=True)
            return filtered_markets[:settings.MAX_CANDIDATES_PER_RUN]

        except Exception as e:
            logger.error(f"Error fetching markets from Polymarket: {e}")
            raise e
