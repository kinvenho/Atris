import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.services.supabase_client import get_supabase
from app.agent.scanner import scan_markets
from app.agent.context import gather_context
from app.agent.probability import estimate_probability
from app.agent.decision import evaluate_decision
from app.agent.writer import write_recommendation
from app.integrations.xai import XAIAuthenticationError, XAIClient
from app.config import settings

logger = logging.getLogger(__name__)


def _run_error(
    step: str,
    message: str,
    *,
    kind: str = "runtime_error",
    market_question: str | None = None,
    polymarket_id: str | None = None,
    include_trace: bool = True,
) -> Dict[str, Any]:
    error: Dict[str, Any] = {
        "kind": kind,
        "step": step,
        "message": message,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    if market_question:
        error["market_question"] = market_question
    if polymarket_id:
        error["polymarket_id"] = polymarket_id
    if include_trace:
        error["trace"] = traceback.format_exc()
    return error


def _final_status(
    errors: List[Dict[str, Any]],
    markets_scanned: int,
    candidates_evaluated: int,
    recommendations_published: int,
) -> str:
    if not errors:
        return "success"

    blocking_error_kinds = {"llm_auth", "scanner_error", "pipeline_error"}
    if recommendations_published == 0 and any(e.get("kind") in blocking_error_kinds for e in errors):
        return "failed"

    if markets_scanned == 0 or candidates_evaluated == 0:
        return "failed"

    return "partial"

def run_pipeline(dry_run: bool = False) -> Dict[str, Any]:
    """
    Orchestrates the entire Atris market scanner and evaluation pipeline.
    Chains: Scanner -> ContextGatherer -> ProbabilityEngine -> DecisionEngine -> Writer.
    Records stats and errors in Supabase under `agent_runs`.
    """
    supabase = None if dry_run else get_supabase()
    started_at = datetime.now(timezone.utc)
    
    # 1. Create initial agent run record
    run_record = {
        "started_at": started_at.isoformat(),
        "markets_scanned": 0,
        "candidates_evaluated": 0,
        "recommendations_published": 0,
        "errors": [],
        "status": "failed" # Default to failed in case of catastrophic crash
    }

    try:
        if dry_run:
            run_id = None
            logger.info("Initialized dry-run pipeline execution. Database writes are disabled.")
        else:
            response = supabase.table("agent_runs").insert(run_record).execute()
            if not response.data or len(response.data) == 0:
                raise RuntimeError("Could not initialize agent run log in database.")
            run_db_record = response.data[0]
            run_id = run_db_record["id"]
            logger.info(f"Initialized agent pipeline run with ID: {run_id}")
    except Exception as e:
        logger.critical(f"Failed to start pipeline: cannot log to agent_runs. Error: {e}")
        raise e

    markets_scanned_count = 0
    candidates_evaluated_count = 0
    recommendations_published_count = 0
    errors_list = []

    try:
        try:
            XAIClient().validate_access()
        except XAIAuthenticationError as preflight_err:
            error_msg = str(preflight_err)
            logger.error("Stopping run before market scan: %s", error_msg)
            errors_list.append(
                _run_error(
                    "XAIPreflight",
                    error_msg,
                    kind="llm_auth",
                    include_trace=False,
                )
            )
            completed_at = datetime.now(timezone.utc)
            update_data = {
                "completed_at": completed_at.isoformat(),
                "markets_scanned": 0,
                "candidates_evaluated": 0,
                "recommendations_published": 0,
                "errors": errors_list,
                "status": "failed",
            }
            if not dry_run:
                supabase.table("agent_runs").update(update_data).eq("id", run_id).execute()
            return {**update_data, "dry_run": dry_run}

        # Step 1: Scan
        candidates = []
        try:
            candidates = scan_markets()
            markets_scanned_count = len(candidates)
        except Exception as scan_err:
            error_msg = f"Scanner failed: {str(scan_err)}"
            logger.error(error_msg)
            errors_list.append(_run_error("MarketScanner", error_msg, kind="scanner_error"))

        # Process each candidate
        for cand in candidates[: settings.MAX_LLM_CANDIDATES_PER_RUN]:
            question = cand.get("question", "Unknown")
            polymarket_id = cand.get("polymarket_id")
            
            logger.info(f"Processing candidate: '{question}' (ID: {polymarket_id})")
            candidates_evaluated_count += 1
            
            try:
                # Step 2: Gather context
                context = gather_context(cand)
                
                # Step 3: Estimate Probability
                assessment = estimate_probability(cand, context)
                
                # Step 4: Decision Engine
                decision = evaluate_decision(cand, assessment)
                
                # Step 5: Publish if approved
                if decision and dry_run:
                    logger.info("Dry run approved recommendation but skipped database write.")
                    recommendations_published_count += 1
                elif decision:
                    write_recommendation(cand, decision, context)
                    recommendations_published_count += 1

            except XAIAuthenticationError as item_err:
                error_msg = str(item_err)
                logger.error("Stopping run after xAI authentication/access failure: %s", error_msg)
                errors_list.append(
                    _run_error(
                        "ContextGatherer",
                        error_msg,
                        kind="llm_auth",
                        market_question=question,
                        polymarket_id=polymarket_id,
                        include_trace=False,
                    )
                )
                break
            except Exception as item_err:
                error_msg = f"Failed evaluating candidate '{question}': {str(item_err)}"
                logger.error(error_msg)
                errors_list.append(
                    _run_error(
                        "CandidateEvaluation",
                        error_msg,
                        market_question=question,
                        polymarket_id=polymarket_id,
                    )
                )

        # Calculate final status
        final_status = _final_status(
            errors_list,
            markets_scanned_count,
            candidates_evaluated_count,
            recommendations_published_count,
        )

        # Update run record on completion
        completed_at = datetime.now(timezone.utc)
        update_data = {
            "completed_at": completed_at.isoformat(),
            "markets_scanned": markets_scanned_count,
            "candidates_evaluated": candidates_evaluated_count,
            "recommendations_published": recommendations_published_count,
            "errors": errors_list,
            "status": final_status
        }
        if not dry_run:
            supabase.table("agent_runs").update(update_data).eq("id", run_id).execute()
        logger.info(f"Pipeline run completed with status '{final_status}'. Published: {recommendations_published_count}")
        return {**update_data, "dry_run": dry_run}

    except Exception as fatal_err:
        # Catch any catastrophic error outside of scan/candidates
        error_msg = f"Catastrophic failure in pipeline runner: {str(fatal_err)}"
        logger.critical(error_msg)
        errors_list.append(_run_error("PipelineRunner", error_msg, kind="pipeline_error"))
        
        try:
            completed_at = datetime.now(timezone.utc)
            update_data = {
                "completed_at": completed_at.isoformat(),
                "markets_scanned": markets_scanned_count,
                "candidates_evaluated": candidates_evaluated_count,
                "recommendations_published": recommendations_published_count,
                "errors": errors_list,
                "status": "failed"
            }
            if not dry_run:
                supabase.table("agent_runs").update(update_data).eq("id", run_id).execute()
        except Exception as db_err:
            logger.critical(f"Could not write catastrophic failure status to database: {db_err}")

        raise fatal_err
if __name__ == "__main__":
    # Basic script usage for testing or direct trigger
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
