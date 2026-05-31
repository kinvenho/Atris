import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from app.services.supabase_client import get_supabase
from app.models.recommendation import RecommendationCreate, StatusEnum, ResultEnum

logger = logging.getLogger(__name__)

class RecommendationService:
    @staticmethod
    def get_active_by_market_and_side(market_id: UUID, side: str) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        try:
            response = (
                supabase.table("recommendations")
                .select("*")
                .eq("market_id", str(market_id))
                .eq("side", side)
                .eq("status", StatusEnum.ACTIVE.value)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error checking active recommendation duplicate: {e}")
            raise e

    @staticmethod
    def create_recommendation(rec_data: RecommendationCreate) -> Dict[str, Any]:
        """
        Creates a recommendation and its associated evidence in the database.
        """
        supabase = get_supabase()
        if rec_data.market_id:
            existing = RecommendationService.get_active_by_market_and_side(
                rec_data.market_id,
                rec_data.side.value,
            )
            if existing:
                logger.info(
                    "Skipping duplicate active recommendation for market_id=%s side=%s",
                    rec_data.market_id,
                    rec_data.side.value,
                )
                existing["evidence"] = []
                return existing
        
        # Prepare recommendation data
        rec_insert = {
            "market_id": str(rec_data.market_id) if rec_data.market_id else None,
            "market_question": rec_data.market_question,
            "side": rec_data.side.value,
            "market_probability": float(rec_data.market_probability),
            "atris_probability": float(rec_data.atris_probability),
            "edge": float(rec_data.edge),
            "confidence": float(rec_data.confidence),
            "reasoning": rec_data.reasoning,
            "evidence_summary": rec_data.evidence_summary,
            "status": rec_data.status.value,
            "result": rec_data.result.value
        }

        try:
            # Insert recommendation
            response = supabase.table("recommendations").insert(rec_insert).execute()
            if not response.data or len(response.data) == 0:
                raise RuntimeError("Failed to insert recommendation into Supabase.")
            
            created_rec = response.data[0]
            rec_id = created_rec["id"]

            evidence_records = []
            if rec_data.evidence:
                evidence_inserts = []
                for ev in rec_data.evidence:
                    evidence_inserts.append({
                        "recommendation_id": rec_id,
                        "source_url": ev.source_url,
                        "summary": ev.summary
                    })
                ev_resp = supabase.table("recommendation_evidence").insert(evidence_inserts).execute()
                if ev_resp.data and len(ev_resp.data) > 0:
                    evidence_records.extend(ev_resp.data)

            created_rec["evidence"] = evidence_records
            return created_rec
        except Exception as e:
            logger.error(f"Error creating recommendation: {e}")
            raise e

    @staticmethod
    def get_active_recommendations() -> List[Dict[str, Any]]:
        """
        Fetches all active recommendations from the database.
        """
        supabase = get_supabase()
        try:
            response = supabase.table("recommendations").select("*").eq("status", "active").order("created_at", desc=True).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching active recommendations: {e}")
            return []

    @staticmethod
    def get_by_id(rec_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Fetches a single recommendation by UUID, including its evidence.
        """
        supabase = get_supabase()
        try:
            # Get recommendation
            rec_resp = supabase.table("recommendations").select("*").eq("id", str(rec_id)).execute()
            if not rec_resp.data or len(rec_resp.data) == 0:
                return None
            
            recommendation = rec_resp.data[0]
            
            # Get evidence
            ev_resp = supabase.table("recommendation_evidence").select("*").eq("recommendation_id", str(rec_id)).execute()
            recommendation["evidence"] = ev_resp.data or []
            
            return recommendation
        except Exception as e:
            logger.error(f"Error fetching recommendation {rec_id}: {e}")
            return None

    @staticmethod
    def update_resolution(rec_id: UUID, status: StatusEnum, result: ResultEnum, resolved_at: datetime) -> Optional[Dict[str, Any]]:
        """
        Updates the resolution status and outcome of a recommendation.
        """
        supabase = get_supabase()
        data = {
            "status": status.value,
            "result": result.value,
            "resolved_at": resolved_at.isoformat()
        }
        try:
            response = supabase.table("recommendations").update(data).eq("id", str(rec_id)).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating resolution for recommendation {rec_id}: {e}")
            raise e
