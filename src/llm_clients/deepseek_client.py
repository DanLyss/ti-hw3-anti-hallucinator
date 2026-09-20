from src.llm_clients.openai_compatible import OpenAICompatibleClient

# Проверить актуальный base_url в документации DeepSeek перед первым реальным запуском
# (https://api-docs.deepseek.com/) — на момент написания это OpenAI-совместимый эндпоинт.
DEFAULT_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient(OpenAICompatibleClient):
    """DeepSeek (OpenAI-совместимый REST)."""

    def __init__(self, api_key: str, model_name: str, temperature: float = 0.7, base_url: str = DEFAULT_BASE_URL):
        super().__init__(base_url=base_url, api_key=api_key, model_name=model_name, temperature=temperature)
