from src.llm_clients.base import LLMClient


class GigaChatClient(LLMClient):
    """GigaChat: OAuth2-токен (client_id/secret) + self-signed сертификат Минцифры. Реализация — Этап 4 (PLAN.md)."""

    def __init__(self, client_id: str, client_secret: str, model_name: str, temperature: float = 0.7):
        self.client_id = client_id
        self.client_secret = client_secret
        self.model_name = model_name
        self.temperature = temperature
        self._token: str | None = None

    def _refresh_token(self) -> None:
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        raise NotImplementedError
