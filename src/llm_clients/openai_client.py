from src.llm_clients.base import LLMClient


class OpenAIClient(LLMClient):
    """ChatGPT / GPT-6. Реализация — Этап 4 (PLAN.md)."""

    def __init__(self, api_key: str, model_name: str, temperature: float = 0.7):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        raise NotImplementedError
