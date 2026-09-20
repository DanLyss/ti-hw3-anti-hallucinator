from src.llm_clients.openai_compatible import OpenAICompatibleClient

# DashScope (Alibaba Cloud) compatible-mode эндпоинт — OpenAI-совместимый REST.
# Проверить актуальный base_url в документации перед первым реальным запуском:
# https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenClient(OpenAICompatibleClient):
    """Qwen (Alibaba Cloud DashScope, OpenAI-совместимый REST)."""

    def __init__(self, api_key: str, model_name: str, temperature: float = 0.7, base_url: str = DEFAULT_BASE_URL):
        super().__init__(base_url=base_url, api_key=api_key, model_name=model_name, temperature=temperature)
