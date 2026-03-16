"""Centralized LLM client factory — supports Anthropic direct or OpenRouter."""
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_llm(model: str, max_tokens: int) -> ChatAnthropic | ChatOpenAI:
    """Create an LLM client.

    If ANTHROPIC_BASE_URL is set (e.g. OpenRouter), uses ChatOpenAI
    with the OpenAI-compatible endpoint. Otherwise uses ChatAnthropic directly.
    """
    if settings.ANTHROPIC_BASE_URL:
        # OpenRouter / OpenAI-compatible proxy
        return ChatOpenAI(
            model=model,
            max_tokens=max_tokens,
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
        )
    else:
        # Direct Anthropic API
        return ChatAnthropic(
            model=settings.ANTHROPIC_ROUTER_MODEL if model == settings.ANTHROPIC_ROUTER_MODEL else model,
            max_tokens=max_tokens,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
        )


router_llm = create_llm(settings.ANTHROPIC_ROUTER_MODEL, max_tokens=256)
answerer_llm = create_llm(settings.ANTHROPIC_ANSWERER_MODEL, max_tokens=2048)
checker_llm = create_llm(settings.ANTHROPIC_CHECKER_MODEL, max_tokens=512)
