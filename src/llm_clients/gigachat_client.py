import base64
import time
import uuid

import httpx

from src.llm_clients.base import LLMClient
from src.llm_clients.http_utils import post_with_retry

# Проверить актуальные OAuth-URL/scope/base_url в документации перед первым реальным запуском:
# https://developers.sber.ru/portal/products/gigachat-api
DEFAULT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
DEFAULT_BASE_URL = "https://gigachat.devices.sberbank.ru/api/v1"
DEFAULT_SCOPE = "GIGACHAT_API_PERS"
_TOKEN_SAFETY_MARGIN_SECONDS = 30


class GigaChatClient(LLMClient):
    """GigaChat: OAuth2 client-credentials (client_id/secret) + self-signed сертификат
    Минцифры. Без сертификата (ca_bundle_path) TLS-верификация по умолчанию не пройдёт —
    сознательно не выключаем verify по умолчанию, чтобы не ослаблять проверку молча."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        model_name: str,
        temperature: float = 0.7,
        oauth_url: str = DEFAULT_OAUTH_URL,
        base_url: str = DEFAULT_BASE_URL,
        scope: str = DEFAULT_SCOPE,
        ca_bundle_path: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.model_name = model_name
        self.temperature = temperature
        self.oauth_url = oauth_url
        self.base_url = base_url
        self.scope = scope
        self.ca_bundle_path = ca_bundle_path
        self._transport = transport  # только для тестов (подмена сети)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _verify(self):
        return self.ca_bundle_path if self.ca_bundle_path else True

    def _auth_header(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}".encode()
        return base64.b64encode(credentials).decode()

    def _refresh_token(self) -> None:
        with httpx.Client(timeout=30.0, verify=self._verify(), transport=self._transport) as client:
            response = post_with_retry(
                client,
                self.oauth_url,
                headers={
                    "Authorization": f"Basic {self._auth_header()}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": self.scope},
            )
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = payload["expires_at"] / 1000  # приходит в мс с эпохи

    def _ensure_token(self) -> str:
        if self._token is None or time.time() >= self._token_expires_at - _TOKEN_SAFETY_MARGIN_SECONDS:
            self._refresh_token()
        assert self._token is not None
        return self._token

    def generate(self, prompt: str) -> str:
        token = self._ensure_token()
        with httpx.Client(timeout=60.0, verify=self._verify(), transport=self._transport) as client:
            response = post_with_retry(
                client,
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                },
            )
        return response.json()["choices"][0]["message"]["content"]
