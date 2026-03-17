import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import checker_llm
from app.agent.state import AgentState

_CHECKER_BASE = """You are a quality auditor for a document Q&A system.

Evaluate the given answer against the source chunks. Check for:
1. **Hallucination**: Claims in the answer that are NOT supported by ANY source chunk.
2. **Insufficient data**: The source chunks do not adequately cover the user's question.
{skill_section}
Respond with ONLY a JSON object:
{{"result": "pass", "feedback": ""}}
OR
{{"result": "hallucination", "feedback": "Explain what claims are not supported by sources"}}
OR
{{"result": "insufficient_data", "feedback": "Explain what information is missing from the sources"}}
"""


def build_checker_prompt(skill_content: str) -> str:
    if skill_content:
        skill_section = f"3. **Skill compliance**: The answer should follow the skill instructions below:\n\n{skill_content}\n"
    else:
        skill_section = ""
    return _CHECKER_BASE.format(skill_section=skill_section)


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

    ragas_feedback = state.get("ragas_feedback", "")
    if ragas_feedback:
        user_msg += f"\n\nAutomated evaluation scores:\n{ragas_feedback}"
        user_msg += f"\nFaithfulness: {state.get('ragas_faithfulness', 'N/A')}"
        user_msg += f"\nAnswer relevancy: {state.get('ragas_answer_relevancy', 'N/A')}"
        user_msg += f"\nContext precision: {state.get('ragas_context_precision', 'N/A')}"

    system_prompt = build_checker_prompt(state.get("skill_content", ""))
    messages = [
        SystemMessage(content=system_prompt),
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
