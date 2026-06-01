import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any
import httpx
from openai import OpenAI
from app.config import settings
from app.agent.prompts import CONTEXT_GATHERER_SYSTEM_PROMPT, PROBABILITY_ENGINE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class XAIAuthenticationError(RuntimeError):
    """Raised when xAI rejects the configured key, model, or endpoint access."""


class XAIClient:
    def __init__(self):
        # xAI is OpenAI-compatible
        self.client = OpenAI(
            api_key=settings.XAI_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL
        self.search_model = settings.LLM_SEARCH_MODEL
        self.base_url = settings.LLM_BASE_URL.rstrip("/")

    def _extract_response_text_and_citations(self, payload: Dict[str, Any]) -> tuple[str, list[str]]:
        text_parts: list[str] = []
        citations: list[str] = []

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            text_parts.append(output_text)

        for item in payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                content_text = content.get("text")
                if isinstance(content_text, str) and content_text.strip():
                    text_parts.append(content_text)

                for annotation in content.get("annotations", []) or []:
                    url = annotation.get("url")
                    if isinstance(url, str) and url.startswith(("http://", "https://")):
                        citations.append(url)

        content = "\n\n".join(dict.fromkeys(text_parts)).strip()
        regex_urls = re.findall(r'https?://[^\s\)\]\},"\']+', content)
        citations.extend(regex_urls)

        clean_citations = []
        for url in citations:
            clean_url = re.sub(r'[.,;\)"\']$', "", url)
            if clean_url and clean_url not in clean_citations:
                clean_citations.append(clean_url)

        return content, clean_citations[:15]

    def gather_context_with_search(self, question: str, description: str) -> Dict[str, Any]:
        """
        Uses Grok's native web search to gather context on the market question.
        Returns a dictionary with summary, citations list, and retrieved_at.
        """
        prompt = (
            f"Gather context, recent news, and current status for this prediction market question:\n"
            f"Question: {question}\n"
            f"Description: {description if description else 'No additional description provided.'}\n\n"
            f"Please search the web to retrieve the most up-to-date facts, search results, and evidence. "
            f"Provide a clear, detailed summary of your findings, and list the source URLs you used as citations."
        )

        try:
            logger.info("Gathering web search context from Grok for: '%s'...", question)

            response = None
            last_error = None
            for attempt in range(2):
                try:
                    response = httpx.post(
                        f"{self.base_url}/responses",
                        headers={
                            "Authorization": f"Bearer {settings.XAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.search_model,
                            "input": [
                                {
                                    "role": "system",
                                    "content": CONTEXT_GATHERER_SYSTEM_PROMPT,
                                },
                                {"role": "user", "content": prompt},
                            ],
                            "tools": [{"type": "web_search"}],
                            "store": False,
                        },
                        timeout=75.0,
                    )
                    if response.status_code in {401, 403}:
                        raise XAIAuthenticationError(
                            "xAI rejected the context request. Check XAI_API_KEY, model access, "
                            "and whether this account can use the Responses API with web search. "
                            f"Configured search model: {self.search_model}."
                        )
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    logger.warning(
                        "Grok context attempt %s failed for '%s': %s",
                        attempt + 1,
                        question,
                        exc,
                    )
                    if attempt == 0:
                        time.sleep(2)

            if response is None:
                raise RuntimeError(f"Grok context request failed after retries: {last_error}")
            content, clean_citations = self._extract_response_text_and_citations(response.json())

            if not content:
                raise RuntimeError("Grok web search returned no context text.")

            return {
                "summary": content,
                "citations": clean_citations,
                "retrieved_at": datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.error(f"Error in gather_context_with_search: {e}")
            raise e

    def estimate_probability(self, question: str, description: str, context: str) -> Dict[str, Any]:
        """
        Calls Grok to assess the probability of the market question resolving to YES.
        Uses structured JSON response format.
        """
        user_prompt = (
            f"Market Question: {question}\n"
            f"Description: {description if description else 'None'}\n\n"
            f"Gathered Web Search Context:\n{context}"
        )

        try:
            logger.info(f"Estimating probability from Grok for: '{question}'...")
            
            response = None
            last_error = None
            for attempt in range(2):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": PROBABILITY_ENGINE_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=75.0,
                    )
                    break
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    logger.warning(
                        "Grok probability attempt %s failed for '%s': %s",
                        attempt + 1,
                        question,
                        exc,
                    )
                    if attempt == 0:
                        time.sleep(2)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None) or getattr(
                        getattr(exc, "response", None), "status_code", None
                    )
                    if status_code in {401, 403}:
                        raise XAIAuthenticationError(
                            "xAI rejected the probability request. Check XAI_API_KEY and model access."
                        ) from exc
                    raise

            if response is None:
                raise RuntimeError(f"Grok probability request failed after retries: {last_error}")

            raw_content = response.choices[0].message.content or ""
            
            # Clean up potential markdown formatting block ```json ... ```
            json_text = raw_content.strip()
            if json_text.startswith("```"):
                # Remove starting and ending backticks
                lines = json_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                json_text = "\n".join(lines).strip()

            parsed_data = json.loads(json_text)

            # Ensure all required keys exist and have correct types
            required_keys = ["atris_probability", "confidence", "reasoning", "evidence_summary"]
            for k in required_keys:
                if k not in parsed_data:
                    raise KeyError(f"Response missing required key: {k}")

            # Normalize values
            parsed_data["atris_probability"] = max(0.0, min(1.0, float(parsed_data["atris_probability"])))
            parsed_data["confidence"] = max(0.0, min(1.0, float(parsed_data["confidence"])))
            parsed_data["reasoning"] = str(parsed_data["reasoning"])
            parsed_data["evidence_summary"] = str(parsed_data["evidence_summary"])

            return parsed_data

        except Exception as e:
            logger.error(f"Error in estimate_probability: {e}")
            raise e
