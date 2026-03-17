from unittest.mock import AsyncMock, patch

from app.agent.nodes.answerer import _chunk_label, build_answerer_prompt, answerer_node


def test_build_answerer_prompt_default():
    prompt = build_answerer_prompt("")
    assert "You are a document analyst." in prompt
    assert "Rules:" in prompt


def test_build_answerer_prompt_with_skill():
    prompt = build_answerer_prompt("You are a legal expert.")
    assert "You are a legal expert." in prompt
    assert "Rules:" in prompt
    assert "You are a document analyst." not in prompt


def test_chunk_label_with_filename_and_pages():
    chunk = {"metadata": {"filename": "Report.pdf", "page_numbers": [1, 2]}}
    label = _chunk_label(chunk, 0)
    assert label == "[Report.pdf, p.1, p.2]"


def test_chunk_label_filename_only():
    chunk = {"metadata": {"filename": "Report.pdf", "page_numbers": []}}
    label = _chunk_label(chunk, 0)
    assert label == "[Report.pdf]"


def test_chunk_label_no_filename():
    chunk = {"metadata": {}}
    label = _chunk_label(chunk, 3)
    assert label == "[3]"


def test_chunk_label_no_filename_with_chunk_index():
    chunk = {"metadata": {"chunk_index": 7}}
    label = _chunk_label(chunk, 0)
    assert label == "[7]"


@patch("app.agent.nodes.answerer.answerer_llm")
async def test_answerer_node(mock_llm):
    mock_response = AsyncMock()
    mock_response.content = "The revenue was $1M according to [Report.pdf, p.1]."
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "query": "What is the revenue?",
        "messages": [],
        "retrieved_chunks": [
            {"content": "Revenue is $1M", "metadata": {"filename": "Report.pdf", "page_numbers": [1]}}
        ],
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
    result = await answerer_node(state)
    assert result["answer"] == "The revenue was $1M according to [Report.pdf, p.1]."
