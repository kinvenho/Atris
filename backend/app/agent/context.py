import logging
from typing import Dict, Any
from app.integrations.xai import XAIClient

logger = logging.getLogger(__name__)

def gather_context(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 2 in Pipeline: ContextGatherer
    Fetches web search context for a candidate market using Grok.
    """
    question = candidate.get("question", "")
    description = candidate.get("raw_data", {}).get("description", "")
    
    logger.info(f"Pipeline Step 2: ContextGatherer gathering info for market: '{question}'")
    xai_client = XAIClient()
    context = xai_client.gather_context_with_search(question, description)
    logger.info(f"Context gathered successfully for '{question}'. Citations found: {len(context['citations'])}")
    
    return context
