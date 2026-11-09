import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class WorkerAPIError(RuntimeError):
    """Ошибка обращения бота к центральному Worker API."""


def _request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    base_url = os.getenv("WORKER_API_URL", "").rstrip("/")
    secret = os.getenv("BOT_API_SECRET", "")
    if not base_url or not secret:
        raise WorkerAPIError("WORKER_API_URL и BOT_API_SECRET должны быть заданы в .env.")
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base_url}{path}", data=body, method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "X-Bot-Api-Key": secret},
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise WorkerAPIError(f"Worker API вернул HTTP {exc.code}: {details}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WorkerAPIError(f"Не удалось подключиться к Worker API: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkerAPIError("Worker API вернул некорректный JSON.") from exc
    if not isinstance(result, dict):
        raise WorkerAPIError("Worker API вернул неожиданный формат ответа.")
    return result


def get(path: str) -> dict:
    return _request(path)


def post(path: str, payload: dict) -> dict:
    return _request(path, "POST", payload)
