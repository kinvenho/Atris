import httpx
import json
import logging
import math
import time
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
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    response = httpx.get(url, params=params, timeout=30.0)
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    logger.warning(
                        "Polymarket fetch attempt %s failed: %s",
                        attempt + 1,
                        exc,
                    )
                    if attempt < 2:
                        time.sleep(2 ** attempt)

            if response is None:
                raise RuntimeError(f"Polymarket fetch failed after retries: {last_error}")
            raw_markets = response.json()
            logger.info(f"Fetched {len(raw_markets)} raw markets. Filtering...")

            filtered_markets = []
            now = datetime.now(timezone.utc)
            min_closing_time = now + timedelta(hours=settings.MIN_HOURS_TO_CLOSE)
            excluded_keywords = [
                keyword.strip().lower()
                for keyword in settings.EXCLUDED_MARKET_KEYWORDS.split(",")
                if keyword.strip()
            ]

            for m in raw_markets:
                question = str(m.get("question") or "")
                description = str(m.get("description") or "")
                searchable_text = f"{question} {description}".lower()
                if any(keyword in searchable_text for keyword in excluded_keywords):
                    continue

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
                no_price = prices[outcomes_upper.index("NO")]

                if yes_price < settings.MIN_MARKET_PROBABILITY or yes_price > settings.MAX_MARKET_PROBABILITY:
                    continue

                # Create normalized candidate object
                candidate = {
                    "polymarket_id": str(m.get("id")),
                    "question": question,
                    "category": m.get("category", "General"),
                    "closing_time": closing_time,
                    "volume": volume,
                    "liquidity": liquidity,
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "outcomes": outcomes,
                    "outcome_prices": prices,
                    "raw_data": m
                }
                candidate["selection_score"] = self._score_candidate(candidate, now)
                filtered_markets.append(candidate)

            logger.info(f"Filtering complete. Found {len(filtered_markets)} valid candidates.")
            
            # Rank candidates by market quality, not raw volume alone. This avoids
            # spending LLM calls on ultra-longshot celebrity/sports outrights that
            # are liquid but rarely actionable for V1 recommendations.
            filtered_markets.sort(key=lambda x: x["selection_score"], reverse=True)
            candidate_limit = min(
                settings.DEFAULT_CANDIDATES_PER_RUN,
                settings.MAX_CANDIDATES_PER_RUN,
            )
            return self._select_diverse_candidates(filtered_markets, candidate_limit)

        except Exception as e:
            logger.error(f"Error fetching markets from Polymarket: {e}")
            raise e

    def _select_diverse_candidates(self, markets: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        event_group_counts: Dict[str, int] = {}

        for market in markets:
            group_key = self._event_group_key(market["question"])
            group_count = event_group_counts.get(group_key, 0)
            if group_count >= settings.MAX_MARKETS_PER_EVENT_GROUP:
                continue

            selected.append(market)
            event_group_counts[group_key] = group_count + 1
            if len(selected) >= limit:
                return selected

        return selected

    def _event_group_key(self, question: str) -> str:
        normalized = " ".join(question.lower().replace("?", "").split())
        if normalized.startswith("will ") and " win the " in normalized:
            return f"win_the::{normalized.split(' win the ', 1)[1]}"
        return normalized

    def _score_candidate(self, candidate: Dict[str, Any], now: datetime) -> float:
        yes_price = float(candidate["yes_price"])
        volume = max(float(candidate["volume"]), 1.0)
        liquidity = max(float(candidate["liquidity"]), 1.0)
        closing_time = candidate["closing_time"]

        probability_balance = 1.0 - min(abs(yes_price - 0.5) / 0.5, 1.0)
        days_to_close = max((closing_time - now).total_seconds() / 86400, 0.0)
        time_score = 1.0 / (1.0 + abs(days_to_close - 30.0) / 30.0)

        return (
            math.log10(volume + 1.0) * 0.45
            + math.log10(liquidity + 1.0) * 0.35
            + probability_balance * 1.4
            + time_score * 0.8
        )
