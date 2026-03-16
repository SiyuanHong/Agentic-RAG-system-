import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import router_llm
from app.agent.state import AgentState

ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a Finance/Legal document Q&A system.

Given the user's message, classify the intent as one of:
- "factual_query": The user is asking a question that requires retrieving information from documents.
- "greeting": The user is greeting, saying hello, or making small talk.

Respond with ONLY a JSON object: {"intent": "factual_query"} or {"intent": "greeting", "response": "your friendly response"}
"""


async def router_node(state: AgentState) -> dict:
    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=state["query"]),
    ]
    response = await router_llm.ainvoke(messages)

    try:
        parsed = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        # Default to factual_query if parsing fails
        parsed = {"intent": "factual_query"}

    if parsed.get("intent") == "greeting":
        return {
            "answer": parsed.get("response", "Hello! How can I help you today?"),
            "checker_result": "pass",
        }

    return {"answer": "", "checker_result": ""}
