from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    retrieved_chunks: list[dict]
    answer: str
    checker_feedback: str
    checker_result: str  # "pass" | "hallucination" | "insufficient_data"
    iteration_count: int
    kb_id: str
    user_id: str
    skill_content: str
    ragas_faithfulness: float
    ragas_answer_relevancy: float
    ragas_context_precision: float
    ragas_feedback: str
