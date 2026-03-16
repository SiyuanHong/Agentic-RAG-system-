import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import router_llm
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are an intent classifier. Classify the user message into exactly one intent.

Intents:
- "greeting": The message is a greeting, farewell, thanks, or small talk with NO information need. Examples: "hi", "hello", "hey", "thanks", "good morning", "what's up", "bye".
- "factual_query": The message asks a question or requests information that requires searching documents.

If in doubt, choose "factual_query".

Respond with ONLY a raw JSON object (no markdown, no code fences):
{"intent": "greeting", "response": "your friendly response"}
or
{"intent": "factual_query"}
"""

# Regex to extract a JSON object from LLM output that may contain extra text
_JSON_RE = re.compile(r"\{[^{}]*\}")


def _parse_router_response(raw: str) -> dict:
    """Extract a JSON object from the router LLM output, handling common formats."""
    text = raw.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting the first JSON object from the text
    match = _JSON_RE.search(text)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return {}


async def router_node(state: AgentState) -> dict:
    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=state["query"]),
    ]
    response = await router_llm.ainvoke(messages)

    raw = response.content.strip()
    logger.info("Router raw LLM output: %s", raw)

    parsed = _parse_router_response(raw)
    intent = parsed.get("intent", "")
    logger.info("Router parsed intent: %s", intent)

    if not intent:
        # Parsing failed completely — default to factual_query
        logger.warning("Router could not parse intent, defaulting to factual_query")
        intent = "factual_query"

    if intent == "greeting":
        return {
            "answer": parsed.get("response", "Hello! How can I help you today?"),
            "checker_result": "pass",
        }

    return {"answer": "", "checker_result": ""}
