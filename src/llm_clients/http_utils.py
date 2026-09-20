import time

import httpx

MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def post_with_retry(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """POST с ретраями на 429/5xx и сетевые обрывы (экспоненциальная пауза)."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.post(url, **kwargs)
        except httpx.TransportError as exc:
            last_error = exc
        else:
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
                return response
            last_error = httpx.HTTPStatusError(
                f"повторяемая ошибка, статус {response.status_code}",
                request=response.request,
                response=response,
            )
        if attempt < MAX_RETRIES - 1:
            time.sleep(2**attempt)
    assert last_error is not None
    raise last_error
