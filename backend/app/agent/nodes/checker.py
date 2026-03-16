import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import checker_llm
from app.agent.state import AgentState

CHECKER_SYSTEM_PROMPT = """You are a quality auditor for a Finance/Legal document Q&A system.

Evaluate the given answer against the source chunks. Check for:
1. **Hallucination**: Claims in the answer that are NOT supported by ANY source chunk.
2. **Insufficient data**: The source chunks do not adequately cover the user's question.

Respond with ONLY a JSON object:
{"result": "pass", "feedback": ""}
OR
{"result": "hallucination", "feedback": "Explain what claims are not supported by sources"}
OR
{"result": "insufficient_data", "feedback": "Explain what information is missing from the sources"}
"""


async def checker_node(state: AgentState) -> dict:
    from app.agent.nodes.answerer import _chunk_label

    chunks = state.get("retrieved_chunks", [])
    context_parts = []
    for i, chunk in enumerate(chunks):
        label = _chunk_label(chunk, i)
        context_parts.append(f"{label} {chunk['content']}")
    context = "\n\n".join(context_parts)

    user_msg = (
        f"Question: {state['query']}\n\n"
        f"Source chunks:\n{context}\n\n"
        f"Answer to evaluate:\n{state['answer']}"
    )

    messages = [
        SystemMessage(content=CHECKER_SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]
    response = await checker_llm.ainvoke(messages)

    iteration = state.get("iteration_count", 0) + 1

    try:
        parsed = json.loads(response.content)
        return {
            "checker_result": parsed.get("result", "pass"),
            "checker_feedback": parsed.get("feedback", ""),
            "iteration_count": iteration,
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "checker_result": "pass",
            "checker_feedback": "",
            "iteration_count": iteration,
        }
