import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import asdict

from langgraph.graph import END, StateGraph

from app.agent.nodes.answerer import answerer_node
from app.agent.nodes.checker import checker_node
from app.agent.nodes.router import router_node
from app.agent.state import AgentState
from app.agent.tools.hybrid_search import hybrid_search

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


async def retrieve_node(state: AgentState) -> dict:
    results = await hybrid_search(
        query=state["query"],
        kb_id=state["kb_id"],
        user_id=state["user_id"],
    )
    return {
        "retrieved_chunks": [asdict(r) for r in results],
    }


def route_after_router(state: AgentState) -> str:
    if state.get("answer"):
        return END
    return "retrieve"


def route_after_checker(state: AgentState) -> str:
    result = state.get("checker_result", "pass")
    iteration = state.get("iteration_count", 0)

    if result == "pass" or iteration >= MAX_ITERATIONS:
        return END
    if result == "hallucination":
        return "answerer"
    if result == "insufficient_data":
        return "router"
    return END


# Build graph
workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("answerer", answerer_node)
workflow.add_node("checker", checker_node)

workflow.set_entry_point("router")
workflow.add_conditional_edges("router", route_after_router, {END: END, "retrieve": "retrieve"})
workflow.add_edge("retrieve", "answerer")
workflow.add_edge("answerer", "checker")
workflow.add_conditional_edges(
    "checker",
    route_after_checker,
    {END: END, "answerer": "answerer", "router": "router"},
)

graph = workflow.compile()


async def run_agent(
    query: str, kb_id: str, user_id: str
) -> AsyncGenerator[dict, None]:
    initial_state: AgentState = {
        "messages": [],
        "query": query,
        "retrieved_chunks": [],
        "answer": "",
        "checker_feedback": "",
        "checker_result": "",
        "iteration_count": 0,
        "kb_id": kb_id,
        "user_id": user_id,
    }

    final_answer = ""
    sources_emitted = False
    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            # Capture the latest answer
            if "answer" in node_output and node_output["answer"]:
                final_answer = node_output["answer"]

            # Emit sources after retrieve node
            if node_name == "retrieve" and not sources_emitted:
                chunks = node_output.get("retrieved_chunks", [])
                sources = []
                for chunk in chunks:
                    meta = chunk.get("metadata", {})
                    sources.append({
                        "chunk_id": chunk.get("id", ""),
                        "document_id": meta.get("document_id", ""),
                        "filename": meta.get("filename", ""),
                        "page_numbers": meta.get("page_numbers", []),
                    })
                if sources:
                    yield {
                        "event": "sources",
                        "data": json.dumps(sources),
                    }
                sources_emitted = True

            yield {
                "event": "thinking",
                "node": node_name,
                "data": json.dumps(
                    {k: v for k, v in node_output.items() if k != "messages"},
                    default=str,
                ),
            }

    yield {
        "event": "answer",
        "data": final_answer or "I couldn't generate an answer.",
    }
