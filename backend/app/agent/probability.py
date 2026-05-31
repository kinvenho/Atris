import logging
from typing import Dict, Any
from app.integrations.xai import XAIClient

logger = logging.getLogger(__name__)

def estimate_probability(candidate: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 3 in Pipeline: ProbabilityEngine
    Invokes Grok with question, description, and context to produce formatted probability estimation.
    """
    question = candidate.get("question", "")
    description = candidate.get("raw_data", {}).get("description", "")
    context_summary = context.get("summary", "")

    logger.info(f"Pipeline Step 3: ProbabilityEngine estimating probability for: '{question}'")
    xai_client = XAIClient()
    assessment = xai_client.estimate_probability(question, description, context_summary)
    
    logger.info(f"Probability assessment completed for '{question}': P(YES)={assessment['atris_probability']}, Conf={assessment['confidence']}")
    return assessment
