from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import answerer_llm
from app.agent.state import AgentState

_ANSWERER_RULES = """
Rules:
1. Answer ONLY based on the provided context chunks. Do not use prior knowledge.
2. Cite sources using the exact label format provided (e.g., [Report.pdf, p.5]). If no page number is available, use [filename] only.
3. If the context is insufficient, say so clearly.
4. Be precise, professional, and thorough.

If you have received checker feedback, revise your answer to address the critique while still grounding everything in the sources."""

DEFAULT_ROLE = "You are a document analyst."


def build_answerer_prompt(skill_content: str) -> str:
    if skill_content:
        return f"{skill_content}\n\nYour job is to answer questions using ONLY the provided document context.\n{_ANSWERER_RULES}"
    return f"{DEFAULT_ROLE} Your job is to answer questions using ONLY the provided document context.\n{_ANSWERER_RULES}"


def _chunk_label(chunk: dict, fallback_index: int) -> str:
    """Build a citation label like [Report.pdf, p.5] from chunk metadata."""
    meta = chunk.get("metadata", {})
    filename = meta.get("filename")
    page_numbers = meta.get("page_numbers", [])

    if not filename:
        idx = meta.get("chunk_index", fallback_index)
        return f"[{idx}]"

    if page_numbers:
        pages = ", ".join(f"p.{p}" for p in page_numbers[:3])
        return f"[{filename}, {pages}]"

    return f"[{filename}]"


async def answerer_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    context_parts = []
    for i, chunk in enumerate(chunks):
        label = _chunk_label(chunk, i)
        context_parts.append(f"{label} {chunk['content']}")
    context = "\n\n".join(context_parts)

    user_msg = f"Question: {state['query']}\n\nContext:\n{context}"

    if state.get("checker_feedback"):
        user_msg += f"\n\nPrevious feedback from checker (please revise):\n{state['checker_feedback']}"

    system_prompt = build_answerer_prompt(state.get("skill_content", ""))
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]
    response = await answerer_llm.ainvoke(messages)

    return {"answer": response.content}
