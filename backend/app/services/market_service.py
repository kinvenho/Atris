import logging
from typing import Optional, Dict, Any
from app.services.supabase_client import get_supabase
from app.models.market import MarketCreate

logger = logging.getLogger(__name__)

class MarketService:
    @staticmethod
    def get_by_polymarket_id(polymarket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a market record by its Polymarket ID.
        """
        supabase = get_supabase()
        try:
            response = supabase.table("markets").select("*").eq("polymarket_id", polymarket_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching market {polymarket_id}: {e}")
            return None

    @staticmethod
    def upsert_market(market_data: MarketCreate) -> Dict[str, Any]:
        """
        Upserts a market record (inserts if doesn't exist, updates if it does).
        """
        supabase = get_supabase()
        # Convert Pydantic model to dict, formatting datetimes as ISO strings
        data = {
            "polymarket_id": market_data.polymarket_id,
            "question": market_data.question,
            "category": market_data.category,
            "closing_time": market_data.closing_time.isoformat()
        }

        try:
            # Check if it exists
            existing = MarketService.get_by_polymarket_id(market_data.polymarket_id)
            if existing:
                # Update
                response = supabase.table("markets").update(data).eq("id", existing["id"]).execute()
            else:
                # Insert
                response = supabase.table("markets").insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            raise RuntimeError("Database query failed to return data.")
        except Exception as e:
            logger.error(f"Error upserting market {market_data.polymarket_id}: {e}")
            raise e
