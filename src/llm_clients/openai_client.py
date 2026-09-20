from src.llm_clients.openai_compatible import OpenAICompatibleClient

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIClient(OpenAICompatibleClient):
    """ChatGPT."""

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
