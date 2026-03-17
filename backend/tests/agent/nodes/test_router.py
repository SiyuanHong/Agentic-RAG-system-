from unittest.mock import AsyncMock, patch

from app.agent.nodes.router import _parse_router_response, router_node


def test_parse_valid_json():
    result = _parse_router_response('{"intent": "greeting", "response": "Hi"}')
    assert result == {"intent": "greeting", "response": "Hi"}


def test_parse_json_in_code_fence():
    raw = '```json\n{"intent": "factual_query"}\n```'
    result = _parse_router_response(raw)
    assert result == {"intent": "factual_query"}


def test_parse_json_with_extra_text():
    raw = 'Here is my response: {"intent": "greeting", "response": "Hello!"} end.'
    result = _parse_router_response(raw)
    assert result["intent"] == "greeting"
    assert result["response"] == "Hello!"


def test_parse_invalid_json():
    result = _parse_router_response("this is not json at all")
    assert result == {}


@patch("app.agent.nodes.router.router_llm")
async def test_router_node_greeting(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = '{"intent": "greeting", "response": "Hello there!"}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "hi",
        "messages": [],
        "retrieved_chunks": [],
        "answer": "",
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
    result = await router_node(state)
    assert result["answer"] == "Hello there!"
    assert result["checker_result"] == "pass"


@patch("app.agent.nodes.router.router_llm")
async def test_router_node_factual(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = '{"intent": "factual_query"}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "What is the revenue?",
        "messages": [],
        "retrieved_chunks": [],
        "answer": "",
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
    result = await router_node(state)
    assert result["answer"] == ""
    assert result["checker_result"] == ""
