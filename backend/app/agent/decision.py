import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

def evaluate_decision(candidate: Dict[str, Any], assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Step 4 in Pipeline: DecisionEngine
    Computes edge.
    edge = atris_probability - market_probability
    Publish if:
      - edge >= MIN_EDGE_TO_PUBLISH
      - confidence >= MIN_CONFIDENCE_TO_PUBLISH
    Both conditions must be met.
    """
    question = candidate.get("question", "")
    atris_yes_prob = float(assessment["atris_probability"])
    market_yes_prob = float(candidate["yes_price"])
    confidence = float(assessment["confidence"])

    # Calculate edge for YES and NO sides
    edge_yes = atris_yes_prob - market_yes_prob
    edge_no = market_yes_prob - atris_yes_prob

    # Select the side with the positive edge
    if edge_yes >= edge_no:
        side = "YES"
        edge = edge_yes
        market_prob = market_yes_prob
        atris_prob = atris_yes_prob
    else:
        side = "NO"
        edge = edge_no
        market_prob = 1.0 - market_yes_prob
        atris_prob = 1.0 - atris_yes_prob

    logger.info(f"Pipeline Step 4: DecisionEngine evaluating '{question}':")
    logger.info(f"  Side: {side}")
    logger.info(f"  Atris Probability of {side}: {atris_prob:.4f}")
    logger.info(f"  Market Probability of {side}: {market_prob:.4f}")
    logger.info(f"  Calculated Edge: {edge:.4f} (Required: {settings.MIN_EDGE_TO_PUBLISH})")
    logger.info(f"  Confidence: {confidence:.4f} (Required: {settings.MIN_CONFIDENCE_TO_PUBLISH})")

    # Both conditions must be met
    if edge >= settings.MIN_EDGE_TO_PUBLISH and confidence >= settings.MIN_CONFIDENCE_TO_PUBLISH:
        logger.info(f"  --> Decision: PUBLISH recommendation.")
        return {
            "side": side,
            "market_probability": market_prob,
            "atris_probability": atris_prob,
            "edge": edge,
            "confidence": confidence,
            "reasoning": assessment["reasoning"],
            "evidence_summary": assessment["evidence_summary"]
        }
    
    logger.info(f"  --> Decision: DISCARD (Failed thresholds).")
    return None
