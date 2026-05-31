import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class ScoringService:
    @staticmethod
    def get_latest_snapshot() -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent performance snapshot from the database.
        """
        supabase = get_supabase()
        try:
            response = supabase.table("performance_snapshots").select("*").order("snapshot_at", desc=True).limit(1).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching latest performance snapshot: {e}")
            return None

    @staticmethod
    def generate_snapshot() -> Dict[str, Any]:
        """
        Computes the current performance statistics across all recommendations
        and writes a new snapshot record to the database.
        """
        supabase = get_supabase()
        try:
            logger.info("Generating new performance snapshot...")
            
            # Fetch all recommendations
            rec_resp = supabase.table("recommendations").select("edge, status, result").execute()
            recs = rec_resp.data or []

            total_predictions = len(recs)
            correct = sum(1 for r in recs if r.get("result") == "correct")
            incorrect = sum(1 for r in recs if r.get("result") == "incorrect")
            pending = sum(1 for r in recs if r.get("status") == "active")

            # Calculate accuracy rate: correct / (correct + incorrect)
            resolved_count = correct + incorrect
            accuracy_rate = float(correct) / resolved_count if resolved_count > 0 else 0.0

            # Calculate average edge of all published recommendations
            average_edge = 0.0
            if total_predictions > 0:
                edges = [float(r.get("edge", 0)) for r in recs]
                average_edge = sum(edges) / len(edges)

            snapshot_data = {
                "snapshot_at": datetime.now(timezone.utc).isoformat(),
                "total_predictions": total_predictions,
                "correct": correct,
                "incorrect": incorrect,
                "pending": pending,
                "accuracy_rate": accuracy_rate,
                "average_edge": average_edge
            }

            insert_resp = supabase.table("performance_snapshots").insert(snapshot_data).execute()
            if insert_resp.data and len(insert_resp.data) > 0:
                logger.info("Performance snapshot successfully written to DB.")
                return insert_resp.data[0]
            
            raise RuntimeError("Failed to insert performance snapshot.")
        except Exception as e:
            logger.error(f"Error generating performance snapshot: {e}")
            raise e
