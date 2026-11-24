"""HTTP API client for communicating with n8n webhooks (chat, ingestion, healthcheck)."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlparse

import requests

from i18n import CATEGORY_TO_DOC_TYPE

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".txt", ".docx", ".csv")
DEFAULT_HEALTHCHECK_TIMEOUT: int = 10


class ApiError(Exception):
    """Structured error carrying an i18n-mappable error_code and details."""

    def __init__(
        self,
        error_code: str,
        detail: str = "",
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(detail or error_code)


@dataclass
class ChatResponse:
    """Parsed response from the n8n logistics agent webhook."""

    answer: str
    used_tools: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    status: str = "ok"
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestResponse:
    """Parsed response from the n8n document ingestion webhook."""

    status: str
    filename: str
    category: str
    doc_type: str
    collection: str = "logistics_docs"
    chunks_indexed: int = 0
    uploaded_at: str = ""
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class ConnectionCheckResult(NamedTuple):
    """Structured result returned by test_connection()."""

    ok: bool
    detail: str
    status_code: int | None


def is_valid_http_url(url: str) -> bool:
    """Validate that a string is a well-formed http/https URL."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _normalize_used_tools(raw_tools: Any) -> list[str]:
    """Normalize used_tools from list[str], list[dict], or None into unique strings."""
    if not raw_tools:
        return []
    if isinstance(raw_tools, str):
        items: list[Any] = [raw_tools]
    elif isinstance(raw_tools, list):
        items = raw_tools
    else:
        return []

    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = str(
                item.get("name")
                or item.get("tool")
                or item.get("id")
                or ""
            ).strip()
        else:
            name = str(item).strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _normalize_sources(raw_sources: Any) -> list[dict[str, str]]:
    """Normalize sources from list[dict] or list[str] into uniform dicts."""
    if not raw_sources:
        return []
    if isinstance(raw_sources, str):
        items: list[Any] = [raw_sources]
    elif isinstance(raw_sources, list):
        items = raw_sources
    else:
        return []

    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "filename": str(
                        item.get("filename")
                        or item.get("source")
                        or item.get("title")
                        or ""
                    ).strip(),
                    "category": str(item.get("category") or "").strip(),
                    "doc_type": str(item.get("doc_type") or "").strip(),
                    "snippet": str(
                        item.get("snippet") or item.get("text") or ""
                    ).strip(),
                }
            )
        else:
            text = str(item).strip()
            if text:
                normalized.append(
                    {
                        "filename": text,
                        "category": "",
                        "doc_type": "",
                        "snippet": "",
                    }
                )
    return normalized


def _extract_http_error_detail(response: requests.Response) -> str:
    """Extract a concise human-readable error detail from an HTTP error response."""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            for key in ("message", "error", "detail"):
                val = payload.get(key)
                if val:
                    return str(val)
    except (ValueError, json.JSONDecodeError):
        pass
    text = (response.text or "").strip()
    if text:
        return text[:300]
    return response.reason or f"HTTP {response.status_code}"


def _parse_json_dict(response: requests.Response) -> dict[str, Any]:
    """Parse response body as a JSON object (handles single-element n8n list wrappers)."""
    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise ApiError("invalid_json", detail=str(exc), status_code=response.status_code) from exc

    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        raise ApiError(
            "invalid_json",
            detail="Expected JSON object from webhook",
            status_code=response.status_code,
        )
    if not isinstance(data, dict):
        raise ApiError(
            "invalid_json",
            detail=f"Unexpected JSON type: {type(data).__name__}",
            status_code=response.status_code,
        )
    return data


class LogisticsApiClient:
    """Client for n8n LogisticsRAGAgent webhooks."""

    def __init__(
        self,
        chat_webhook_url: str,
        ingest_webhook_url: str,
        bearer_token: str = "",
        timeout_seconds: int = 90,
        session: requests.Session | None = None,
    ) -> None:
        self.chat_webhook_url = chat_webhook_url.strip()
        self.ingest_webhook_url = ingest_webhook_url.strip()
        self.bearer_token = (bearer_token or "").strip()
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.session = session or requests.Session()

    def update_settings(
        self,
        chat_webhook_url: str,
        ingest_webhook_url: str,
        bearer_token: str = "",
        timeout_seconds: int = 90,
    ) -> None:
        """Update endpoint URLs, optional bearer token, and request timeout."""
        self.chat_webhook_url = chat_webhook_url.strip()
        self.ingest_webhook_url = ingest_webhook_url.strip()
        self.bearer_token = (bearer_token or "").strip()
        self.timeout_seconds = max(5, int(timeout_seconds))

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def send_chat(
        self,
        message: str,
        session_id: str,
        language: str = "sk",
    ) -> ChatResponse:
        """Send a chat query to the n8n AI Agent webhook."""
        cleaned_message = (message or "").strip()
        if not cleaned_message:
            raise ApiError("empty_message", detail="Message cannot be empty")
        if not is_valid_http_url(self.chat_webhook_url):
            raise ApiError(
                "invalid_url",
                detail=self.chat_webhook_url,
                extra={"url": self.chat_webhook_url},
            )

        payload = {
            "message": cleaned_message,
            "sessionId": session_id,
            "language": (language or "sk").strip().lower(),
            "action": "chat",
        }

        try:
            response = self.session.post(
                self.chat_webhook_url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ApiError(
                "timeout",
                detail=str(exc),
                extra={"timeout": self.timeout_seconds},
            ) from exc
        except requests.ConnectionError as exc:
            raise ApiError("connection_error", detail=str(exc)) from exc
        except requests.RequestException as exc:
            raise ApiError("connection_error", detail=str(exc)) from exc

        if response.status_code >= 400:
            raise ApiError(
                "http_error",
                detail=_extract_http_error_detail(response),
                status_code=response.status_code,
            )

        data = _parse_json_dict(response)
        status = str(data.get("status") or "ok").strip()
        if status.lower() == "error":
            raise ApiError(
                "http_error",
                detail=str(data.get("message") or data.get("error") or "Agent error"),
                status_code=response.status_code,
            )

        answer = str(
            data.get("answer")
            or data.get("output")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

        return ChatResponse(
            answer=answer,
            used_tools=_normalize_used_tools(data.get("used_tools")),
            sources=_normalize_sources(data.get("sources")),
            status=status,
            session_id=str(data.get("sessionId") or session_id),
            raw=data,
        )

    def upload_document(
        self,
        file_path: str | Path,
        category: str,
        doc_type: str | None = None,
    ) -> IngestResponse:
        """Upload a local document (PDF/TXT/DOCX/CSV) to the n8n RAG ingestion webhook."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise ApiError(
                "file_not_found",
                detail=str(path),
                extra={"path": str(path)},
            )

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ApiError(
                "invalid_file",
                detail=f"Unsupported extension: {ext}",
                extra={"ext": ext or "(none)"},
            )

        if not is_valid_http_url(self.ingest_webhook_url):
            raise ApiError(
                "invalid_url",
                detail=self.ingest_webhook_url,
                extra={"url": self.ingest_webhook_url},
            )

        resolved_category = (category or "smernica").strip()
        resolved_doc_type = (
            doc_type.strip()
            if doc_type
            else CATEGORY_TO_DOC_TYPE.get(resolved_category, resolved_category)
        )
        uploaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "application/octet-stream"

        form_data = {
            "category": resolved_category,
            "doc_type": resolved_doc_type,
            "filename": path.name,
            "uploaded_at": uploaded_at,
        }

        try:
            with path.open("rb") as fh:
                files = {"file": (path.name, fh, mime_type)}
                response = self.session.post(
                    self.ingest_webhook_url,
                    files=files,
                    data=form_data,
                    headers=self._build_headers(),
                    timeout=self.timeout_seconds,
                )
        except OSError as exc:
            raise ApiError(
                "file_not_found",
                detail=str(exc),
                extra={"path": str(path)},
            ) from exc
        except requests.Timeout as exc:
            raise ApiError(
                "timeout",
                detail=str(exc),
                extra={"timeout": self.timeout_seconds},
            ) from exc
        except requests.ConnectionError as exc:
            raise ApiError("connection_error", detail=str(exc)) from exc
        except requests.RequestException as exc:
            raise ApiError("connection_error", detail=str(exc)) from exc

        if response.status_code >= 400:
            raise ApiError(
                "http_error",
                detail=_extract_http_error_detail(response),
                status_code=response.status_code,
            )

        data = _parse_json_dict(response)
        status = str(data.get("status") or "ok").strip()
        if status.lower() == "error":
            raise ApiError(
                "http_error",
                detail=str(data.get("message") or data.get("error") or "Ingestion error"),
                status_code=response.status_code,
            )

        try:
            chunks_indexed = int(data.get("chunks_indexed") or 0)
        except (TypeError, ValueError):
            chunks_indexed = 0

        return IngestResponse(
            status=status,
            filename=str(data.get("filename") or path.name),
            category=str(data.get("category") or resolved_category),
            doc_type=str(data.get("doc_type") or resolved_doc_type),
            collection=str(data.get("collection") or "logistics_docs"),
            chunks_indexed=chunks_indexed,
            uploaded_at=str(data.get("uploaded_at") or uploaded_at),
            message=str(data.get("message") or ""),
            raw=data,
        )

    def test_connection(self, timeout: int = DEFAULT_HEALTHCHECK_TIMEOUT) -> ConnectionCheckResult:
        """Ping the n8n chat webhook using the fast non-LLM healthcheck action."""
        if not is_valid_http_url(self.chat_webhook_url):
            return ConnectionCheckResult(
                ok=False,
                detail=f"Invalid URL: {self.chat_webhook_url}",
                status_code=None,
            )

        payload = {
            "action": "healthcheck",
            "message": "ping",
            "sessionId": "healthcheck",
        }

        try:
            response = self.session.post(
                self.chat_webhook_url,
                json=payload,
                headers=self._build_headers(),
                timeout=max(2, int(timeout)),
            )
        except requests.Timeout as exc:
            return ConnectionCheckResult(
                ok=False,
                detail=f"Timeout ({timeout}s): {exc}",
                status_code=None,
            )
        except requests.RequestException as exc:
            return ConnectionCheckResult(
                ok=False,
                detail=str(exc),
                status_code=None,
            )

        if response.status_code >= 400:
            return ConnectionCheckResult(
                ok=False,
                detail=_extract_http_error_detail(response),
                status_code=response.status_code,
            )

        try:
            data = _parse_json_dict(response)
            service = str(data.get("service") or "LogisticsRAGAgent")
            mode = str(data.get("mode") or data.get("status") or "ok")
            return ConnectionCheckResult(
                ok=True,
                detail=f"{service} ({mode})",
                status_code=response.status_code,
            )
        except ApiError as exc:
            return ConnectionCheckResult(
                ok=False,
                detail=exc.detail,
                status_code=response.status_code,
            )