import httpx
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from app.services.supabase_client import get_supabase
from app.services.recommendation_service import RecommendationService
from app.models.recommendation import StatusEnum, ResultEnum

logger = logging.getLogger(__name__)

def check_and_update_outcomes() -> List[Dict[str, Any]]:
    """
    Cron Job Step: OutcomeTracker
    Runs every 2 hours.
    Fetches all active recommendations, checks if their Polymarket markets have resolved,
    and updates their status, result, and resolved_at time.
    """
    logger.info("Running OutcomeTracker cron job...")
    supabase = get_supabase()
    
    try:
        # Fetch active recommendations with joined market data
        response = supabase.table("recommendations").select("*, markets(polymarket_id, closing_time)").eq("status", "active").execute()
        active_recs = response.data or []
        logger.info(f"Found {len(active_recs)} active recommendations to track.")
    except Exception as e:
        logger.error(f"Error fetching active recommendations from DB: {e}")
        return []

    updated_recs = []
    now = datetime.now(timezone.utc)

    for rec in active_recs:
        rec_id = rec["id"]
        question = rec["market_question"]
        side_recommended = rec["side"] # YES or NO
        
        market_info = rec.get("markets")
        if not market_info:
            logger.warning(f"No market info found for recommendation {rec_id}. Skipping.")
            continue

        polymarket_id = market_info.get("polymarket_id")
        closing_time_str = market_info.get("closing_time")
        
        # Parse closing time
        try:
            closing_time = datetime.fromisoformat(closing_time_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.error(f"Error parsing closing time '{closing_time_str}': {e}")
            continue

        logger.info(f"Checking status of market '{question}' (Polymarket ID: {polymarket_id})")

        # Fetch market status from Polymarket API
        url = "https://gamma-api.polymarket.com/markets"
        params = {"id": polymarket_id}
        
        try:
            resp = httpx.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            market_list = resp.json()
            
            if not market_list or len(market_list) == 0:
                logger.warning(f"Market {polymarket_id} not found in Polymarket API.")
                continue
                
            m = market_list[0]
            
            # Check if resolved / closed
            closed = m.get("closed", False)
            
            # Parse outcome prices
            prices_raw = m.get("outcomePrices")
            prices = []
            if prices_raw:
                try:
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    prices = [float(p) for p in prices]
                except Exception:
                    pass

            # Check if one price has hit 1.0 (settled)
            is_settled = False
            winning_outcome = None
            
            if len(prices) == 2:
                # If a market is resolved, one price is 1.0 and the other is 0.0
                if prices[0] >= 0.99 or prices[0] <= 0.01 or prices[1] >= 0.99 or prices[1] <= 0.01:
                    is_settled = True
                    
                    # Parse outcomes to find which index corresponds to YES
                    outcomes_raw = m.get("outcomes")
                    outcomes = []
                    if outcomes_raw:
                        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                    
                    outcomes_upper = [o.upper() for o in outcomes]
                    
                    if "YES" in outcomes_upper:
                        yes_index = outcomes_upper.index("YES")
                        no_index = 1 - yes_index
                        
                        yes_price = prices[yes_index]
                        if yes_price >= 0.99:
                            winning_outcome = "YES"
                        elif yes_price <= 0.01:
                            winning_outcome = "NO"
            
            # Logic:
            # 1. If settled on-chain
            if is_settled and winning_outcome:
                result = ResultEnum.CORRECT if side_recommended == winning_outcome else ResultEnum.INCORRECT
                logger.info(f"Market resolved! Winning outcome: {winning_outcome}. Atris recommended: {side_recommended}. Result: {result.value}")
                
                updated = RecommendationService.update_resolution(
                    rec_id=rec_id,
                    status=StatusEnum.RESOLVED,
                    result=result,
                    resolved_at=now
                )
                if updated:
                    updated_recs.append(updated)
            
            # 2. If not settled but past closing date
            elif now > closing_time:
                # If it's closed but not resolved yet, we wait (maybe UMA oracle delay)
                # But if it's past closing date and closed flag is not set, or we've waited a while:
                # Let's check if UMA resolution is in progress. If past closing time by more than 48 hours with no resolution, mark as expired.
                if now > closing_time + timedelta(days=2):
                    logger.info(f"Market past closing date by > 48 hours without resolution. Marking as expired.")
                    updated = RecommendationService.update_resolution(
                        rec_id=rec_id,
                        status=StatusEnum.EXPIRED,
                        result=ResultEnum.PENDING,
                        resolved_at=now
                    )
                    if updated:
                        updated_recs.append(updated)
                else:
                    logger.info(f"Market past closing date but within resolution grace period. Keeping active.")
            
            else:
                logger.info("Market is still active and trading. No update needed.")

        except Exception as e:
            logger.error(f"Error checking outcome for recommendation {rec_id}: {e}")

    logger.info(f"OutcomeTracker completed. Updated {len(updated_recs)} recommendations.")
    return updated_recs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_and_update_outcomes()
