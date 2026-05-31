import logging
from typing import Dict, Any
from app.services.market_service import MarketService
from app.services.recommendation_service import RecommendationService
from app.models.market import MarketCreate
from app.models.recommendation import RecommendationCreate, EvidenceCreate, SideEnum, StatusEnum, ResultEnum

logger = logging.getLogger(__name__)

def write_recommendation(candidate: Dict[str, Any], decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 5 in Pipeline: RecommendationWriter
    Saves the market, recommendation, and evidence source links to Supabase.
    """
    logger.info(f"Pipeline Step 5: RecommendationWriter writing prediction for: '{candidate['question']}'")
    
    # 1. Upsert market record
    market_create = MarketCreate(
        polymarket_id=candidate["polymarket_id"],
        question=candidate["question"],
        category=candidate.get("category", "General"),
        closing_time=candidate["closing_time"]
    )
    db_market = MarketService.upsert_market(market_create)
    market_uuid = db_market["id"]

    # 2. Build recommendation evidence list
    evidence_list = []
    for citation_url in context.get("citations", []):
        evidence_list.append(
            EvidenceCreate(
                source_url=citation_url,
                summary=f"Context reference gathered by Grok during evaluation."
            )
        )

    # 3. Create recommendation record
    rec_create = RecommendationCreate(
        market_id=market_uuid,
        market_question=candidate["question"],
        side=SideEnum(decision["side"]),
        market_probability=decision["market_probability"],
        atris_probability=decision["atris_probability"],
        edge=decision["edge"],
        confidence=decision["confidence"],
        reasoning=decision["reasoning"],
        evidence_summary=decision["evidence_summary"],
        status=StatusEnum.ACTIVE,
        result=ResultEnum.PENDING,
        evidence=evidence_list
    )

    db_rec = RecommendationService.create_recommendation(rec_create)
    logger.info(f"Successfully published recommendation {db_rec['id']} to database.")
    
    return db_rec
