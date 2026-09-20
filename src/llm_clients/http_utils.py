import time

import httpx

MAX_RETRIES = 6
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def _backoff_seconds(attempt: int, response: httpx.Response | None) -> float:
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return min(60.0, 5.0 * (2**attempt))  # 429 обычно требует более долгого охлаждения, чем 5xx
    return min(30.0, 2.0**attempt)


def post_with_retry(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """POST с ретраями на 429/5xx и сетевые обрывы. 429 ждёт дольше (уважает Retry-After,
    если провайдер его прислал), 5xx/обрывы сети — короткий экспоненциальный бэкофф."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        response: httpx.Response | None = None
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
            time.sleep(_backoff_seconds(attempt, response))
    assert last_error is not None
    raise last_error
