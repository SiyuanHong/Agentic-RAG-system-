from unittest.mock import AsyncMock, patch

from app.agent.nodes.checker import build_checker_prompt, checker_node


def test_build_checker_prompt_no_skill():
    prompt = build_checker_prompt("")
    assert "quality auditor" in prompt
    assert "Skill compliance" not in prompt


def test_build_checker_prompt_with_skill():
    prompt = build_checker_prompt("You must cite legal statutes.")
    assert "Skill compliance" in prompt
    assert "You must cite legal statutes." in prompt


@patch("app.agent.nodes.checker.checker_llm")
async def test_checker_node_pass(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = '{"result": "pass", "feedback": ""}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "What is the revenue?",
        "messages": [],
        "retrieved_chunks": [{"content": "Revenue is $1M", "metadata": {}}],
        "answer": "The revenue is $1M.",
        "checker_feedback": "",
        "checker_result": "",
        "iteration_count": 0,
        "kb_id": "kb1",
        "user_id": "user1",
        "skill_content": "",
        "ragas_faithfulness": 0.0,
        "ragas_answer_relevancy": 0.0,
        "ragas_context_precision": 0.0,
        "ragas_feedback": "",
    }
    result = await checker_node(state)
    assert result["checker_result"] == "pass"
    assert result["checker_feedback"] == ""
    assert result["iteration_count"] == 1


@patch("app.agent.nodes.checker.checker_llm")
async def test_checker_node_hallucination(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = '{"result": "hallucination", "feedback": "Claim X not in sources"}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "What is the revenue?",
        "messages": [],
        "retrieved_chunks": [{"content": "Revenue is $1M", "metadata": {}}],
        "answer": "Revenue is $5M and growing.",
        "checker_feedback": "",
        "checker_result": "",
        "iteration_count": 1,
        "kb_id": "kb1",
        "user_id": "user1",
        "skill_content": "",
        "ragas_faithfulness": 0.0,
        "ragas_answer_relevancy": 0.0,
        "ragas_context_precision": 0.0,
        "ragas_feedback": "",
    }
    result = await checker_node(state)
    assert result["checker_result"] == "hallucination"
    assert "Claim X" in result["checker_feedback"]
    assert result["iteration_count"] == 2


@patch("app.agent.nodes.checker.checker_llm")
async def test_checker_node_invalid_json(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = "Not valid JSON"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "q",
        "messages": [],
        "retrieved_chunks": [],
        "answer": "a",
        "checker_feedback": "",
        "checker_result": "",
        "iteration_count": 0,
        "kb_id": "kb1",
        "user_id": "user1",
        "skill_content": "",
        "ragas_faithfulness": 0.0,
        "ragas_answer_relevancy": 0.0,
        "ragas_context_precision": 0.0,
        "ragas_feedback": "",
    }
    result = await checker_node(state)
    assert result["checker_result"] == "insufficient_data"
    assert "not valid JSON" in result["checker_feedback"]
    assert result["iteration_count"] == 1


@patch("app.agent.nodes.checker.checker_llm")
async def test_checker_increments_iteration(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = '{"result": "pass", "feedback": ""}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "q",
        "messages": [],
        "retrieved_chunks": [],
        "answer": "a",
        "checker_feedback": "",
        "checker_result": "",
        "iteration_count": 2,
        "kb_id": "kb1",
        "user_id": "user1",
        "skill_content": "",
        "ragas_faithfulness": 0.0,
        "ragas_answer_relevancy": 0.0,
        "ragas_context_precision": 0.0,
        "ragas_feedback": "",
    }
    result = await checker_node(state)
    assert result["iteration_count"] == 3
