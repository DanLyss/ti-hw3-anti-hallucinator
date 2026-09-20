import httpx

from src.llm_clients.base import LLMClient
from src.llm_clients.http_utils import post_with_retry


class OpenAICompatibleClient(LLMClient):
    """Общая реализация для любого провайдера с OpenAI-совместимым /chat/completions."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self._transport = transport  # только для тестов (подмена сети)

    def generate(self, prompt: str) -> str:
        with httpx.Client(timeout=60.0, transport=self._transport) as client:
            response = post_with_retry(
                client,
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                },
            )
        return response.json()["choices"][0]["message"]["content"]
