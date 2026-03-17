from unittest.mock import patch

from langgraph.graph import END

from app.agent.graph import route_after_checker, route_after_eval, route_after_router


def test_route_after_router_with_answer():
    state = {"answer": "Hello!", "checker_result": "pass"}
    assert route_after_router(state) == END


def test_route_after_router_no_answer():
    state = {"answer": "", "checker_result": ""}
    assert route_after_router(state) == "retrieve"


def test_route_after_eval_high_faithfulness():
    with patch("app.agent.graph.settings") as mock_settings:
        mock_settings.RAGAS_FAITHFULNESS_BYPASS_THRESHOLD = 0.9
        state = {"ragas_faithfulness": 0.95}
        assert route_after_eval(state) == END


def test_route_after_eval_low_faithfulness():
    with patch("app.agent.graph.settings") as mock_settings:
        mock_settings.RAGAS_FAITHFULNESS_BYPASS_THRESHOLD = 0.9
        state = {"ragas_faithfulness": 0.5}
        assert route_after_eval(state) == "checker"


def test_route_after_checker_pass():
    state = {"checker_result": "pass", "iteration_count": 1}
    assert route_after_checker(state) == END


def test_route_after_checker_hallucination():
    state = {"checker_result": "hallucination", "iteration_count": 1}
    assert route_after_checker(state) == "answerer"


def test_route_after_checker_insufficient():
    state = {"checker_result": "insufficient_data", "iteration_count": 1}
    assert route_after_checker(state) == "router"


def test_route_after_checker_max_iterations():
    state = {"checker_result": "hallucination", "iteration_count": 3}
    assert route_after_checker(state) == END
