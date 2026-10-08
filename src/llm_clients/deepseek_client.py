from src.llm_clients.openai_compatible import OpenAICompatibleClient

# Проверить актуальный base_url в документации DeepSeek перед первым реальным запуском
# (https://api-docs.deepseek.com/) — на момент написания это OpenAI-совместимый эндпоинт.
DEFAULT_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient(OpenAICompatibleClient):
    """DeepSeek (OpenAI-совместимый REST). base_url подтверждён реальным запросом
    (сервер ответил 402 Insufficient Balance, а не 404 — значит, путь верный)."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        base_url: str = DEFAULT_BASE_URL,
    ):
        super().__init__(
            base_url=base_url, api_key=api_key, model_name=model_name, temperature=temperature, max_tokens=max_tokens
        )
