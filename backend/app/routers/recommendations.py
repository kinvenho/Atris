from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from uuid import UUID
from app.services.recommendation_service import RecommendationService
from app.services.scoring_service import ScoringService

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_active_recommendations():
    """
    GET /recommendations - Fetches all currently active recommendations.
    """
    try:
        return RecommendationService.get_active_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=Dict[str, Any])
async def get_recommendation_by_id(id: UUID):
    """
    GET /recommendations/:id - Fetches a single recommendation and its evidence.
    """
    try:
        rec = RecommendationService.get_by_id(id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
