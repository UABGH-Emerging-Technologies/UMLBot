import pytest
from UMLBot.llm_interface import LangchainLLMAdapter, LLMInterface
from UMLBot.exceptions import LLMError

def test_adapter_invokes_callable():
    def mock_llm(prompt: str) -> str:
        return f"response for: {prompt}"
    adapter = LangchainLLMAdapter({"llm_callable": mock_llm})
    result = adapter.invoke("test prompt")
    assert result == "response for: test prompt"

def test_adapter_raises_on_exception():
    def mock_llm(prompt: str) -> str:
        raise RuntimeError("fail")
    adapter = LangchainLLMAdapter({"llm_callable": mock_llm})
    with pytest.raises(LLMError):
        adapter.invoke("test prompt")

@pytest.mark.asyncio
async def test_adapter_invoke_async():
    def mock_llm(prompt: str) -> str:
        return f"async response for: {prompt}"
    adapter = LangchainLLMAdapter({"llm_callable": mock_llm})
    result = await adapter.invoke_async("async prompt")
    assert result == "async response for: async prompt"

def test_adapter_invalid_config():
    with pytest.raises(ValueError):
        LangchainLLMAdapter({"llm_callable": None})
