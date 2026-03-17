import logging

from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


async def eval_answer_node(state: AgentState) -> dict:
    if not settings.RAGAS_ENABLED:
        return {
            "ragas_faithfulness": 1.0,
            "ragas_answer_relevancy": 1.0,
            "ragas_context_precision": 1.0,
            "ragas_feedback": "",
        }

    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import Faithfulness, LLMContextPrecisionWithoutReference, ResponseRelevancy
        from ragas import SingleTurnSample

        llm_kwargs = {
            "model": settings.RAGAS_LLM_MODEL,
            "api_key": settings.OPENAI_API_KEY,
        }
        emb_kwargs = {
            "model": settings.EMBEDDING_MODEL,
            "api_key": settings.OPENAI_API_KEY,
        }
        if settings.OPENAI_BASE_URL:
            llm_kwargs["base_url"] = settings.OPENAI_BASE_URL
            emb_kwargs["base_url"] = settings.OPENAI_BASE_URL
        ragas_llm = LangchainLLMWrapper(ChatOpenAI(**llm_kwargs))
        ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(**emb_kwargs))

        sample = SingleTurnSample(
            user_input=state["query"],
            response=state["answer"],
            retrieved_contexts=[c["content"] for c in state.get("retrieved_chunks", [])],
        )

        faithfulness = Faithfulness(llm=ragas_llm)
        relevancy = ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
        precision = LLMContextPrecisionWithoutReference(llm=ragas_llm)

        faithfulness_score = await faithfulness.single_turn_ascore(sample)
        relevancy_score = await relevancy.single_turn_ascore(sample)
        precision_score = await precision.single_turn_ascore(sample)

        feedback_parts = []
        if faithfulness_score < 0.8:
            feedback_parts.append(
                f"Faithfulness: {faithfulness_score:.2f} — answer may contain claims not supported by context"
            )
        if precision_score < 0.6:
            feedback_parts.append(
                f"Context Precision: {precision_score:.2f} — retrieved chunks may not be relevant"
            )
        if relevancy_score < 0.7:
            feedback_parts.append(
                f"Answer Relevancy: {relevancy_score:.2f} — answer may not fully address the question"
            )

        ragas_feedback = "; ".join(feedback_parts)

        logger.info(
            f"Ragas scores — faithfulness: {faithfulness_score:.2f}, "
            f"relevancy: {relevancy_score:.2f}, precision: {precision_score:.2f}"
        )

        return {
            "ragas_faithfulness": float(faithfulness_score),
            "ragas_answer_relevancy": float(relevancy_score),
            "ragas_context_precision": float(precision_score),
            "ragas_feedback": ragas_feedback,
        }
    except Exception as e:
        logger.warning(f"Ragas evaluation failed, defaulting to low scores for safety: {e}")
        return {
            "ragas_faithfulness": 0.0,
            "ragas_answer_relevancy": 0.0,
            "ragas_context_precision": 0.0,
            "ragas_feedback": f"Ragas evaluation failed: {e}",
        }
