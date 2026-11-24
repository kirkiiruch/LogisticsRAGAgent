"""Unit tests for LogisticsRAGAgent desktop_app (i18n, config_manager, api_client)."""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

MVP_ROOT = Path(__file__).resolve().parent.parent
DESKTOP_APP_DIR = MVP_ROOT / "desktop_app"
if str(DESKTOP_APP_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_APP_DIR))

import api_client  # noqa: E402
import config_manager  # noqa: E402
import i18n  # noqa: E402


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        reason: str = "OK",
        json_exc: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.reason = reason
        self._json_exc = json_exc

    def json(self) -> Any:
        if self._json_exc is not None:
            raise self._json_exc
        return self._json_data


class TestI18n:
    def test_defaults_and_full_key_parity(self) -> None:
        assert i18n.DEFAULT_LANGUAGE == "SK"
        assert i18n.SUPPORTED_LANGUAGES == ("SK", "RU", "EN")
        sk_keys = set(i18n.TRANSLATIONS["SK"].keys())
        ru_keys = set(i18n.TRANSLATIONS["RU"].keys())
        en_keys = set(i18n.TRANSLATIONS["EN"].keys())
        assert sk_keys == ru_keys
        assert sk_keys == en_keys
        assert len(sk_keys) >= 90

    def test_non_empty_values_and_placeholder_parity(self) -> None:
        placeholder_re = re.compile(r"\{[a-zA-Z0-9_]+\}")
        base_table = i18n.TRANSLATIONS["SK"]
        for key, sk_val in base_table.items():
            expected_ph = sorted(placeholder_re.findall(sk_val))
            for lang in i18n.SUPPORTED_LANGUAGES:
                val = i18n.TRANSLATIONS[lang][key]
                assert isinstance(val, str) and val.strip() != "", f"Empty {lang}.{key}"
                assert sorted(placeholder_re.findall(val)) == expected_ph, (
                    f"Placeholder mismatch in {lang}.{key}"
                )

    def test_zero_language_mixing_across_ui_presets_and_categories(self) -> None:
        cyrillic_re = re.compile(r"[\u0400-\u04FF]")
        # Keys that are intentionally identical brand/technical strings
        brand_or_url_keys = {
            "brand_name",
            "brand_subtitle",
            "settings_chat_url_placeholder",
            "settings_ingest_url_placeholder",
        }
        # Keys whose translations must be distinct across SK, RU, EN
        must_differ_keys = [
            "nav_chat",
            "nav_kb",
            "nav_settings",
            "preset_gmail_label",
            "preset_gmail_prompt",
            "preset_qdrant_label",
            "preset_qdrant_prompt",
            "preset_invoice_label",
            "preset_invoice_prompt",
            "preset_cmr_label",
            "preset_cmr_prompt",
            "cat_faktura",
            "cat_pokladnicny_doklad",
            "cat_zmluva",
            "cat_smernica",
            "kb_upload_btn",
            "settings_save_btn",
            "settings_test_btn",
        ]
        for key in must_differ_keys:
            sk_val = i18n.TRANSLATIONS["SK"][key]
            ru_val = i18n.TRANSLATIONS["RU"][key]
            en_val = i18n.TRANSLATIONS["EN"][key]
            assert len({sk_val, ru_val, en_val}) == 3, f"Unlocalized duplicate in {key}"
            assert cyrillic_re.search(ru_val), f"RU.{key} missing Cyrillic"
            assert not cyrillic_re.search(sk_val), f"SK.{key} unexpectedly contains Cyrillic"
            assert not cyrillic_re.search(en_val), f"EN.{key} unexpectedly contains Cyrillic"

        for key, sk_val in i18n.TRANSLATIONS["SK"].items():
            if key in brand_or_url_keys:
                continue
            assert not cyrillic_re.search(sk_val), f"Cyrillic leaked into SK.{key}"
            assert not cyrillic_re.search(i18n.TRANSLATIONS["EN"][key]), f"Cyrillic leaked into EN.{key}"

    def test_category_roundtrip_and_translator_helpers(self) -> None:
        assert i18n.normalize_language("ru") == "RU"
        assert i18n.normalize_language("unknown") == "SK"

        for lang in i18n.SUPPORTED_LANGUAGES:
            options = i18n.get_category_options(lang)
            assert len(options) == len(i18n.CATEGORY_KEYS)
            for key, label in zip(i18n.CATEGORY_KEYS, options):
                assert i18n.get_category_key(lang, label) == key
                assert i18n.get_category_label(lang, key) == label

        tr = i18n.Translator("EN")
        assert tr("nav_chat") == i18n.TRANSLATIONS["EN"]["nav_chat"]
        tr.set_language("SK")
        assert tr("nav_chat") == i18n.TRANSLATIONS["SK"]["nav_chat"]


class TestConfigManager:
    def test_default_path_resolves_under_appdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        fake_appdata = tmp_path / "Roaming"
        monkeypatch.setenv("APPDATA", str(fake_appdata))
        resolved = config_manager.get_default_config_path()
        assert resolved == fake_appdata / "LogisticsRAGAgent" / "config.json"

    def test_persistence_defaults_and_session_reset(self, tmp_path: Path) -> None:
        fake_appdata = tmp_path / "AppDataRoaming"
        mgr = config_manager.ConfigManager(appdata_dir=fake_appdata)

        expected_path = fake_appdata / "LogisticsRAGAgent" / "config.json"
        assert mgr.config_path == expected_path
        assert expected_path.exists()
        assert mgr.config.language == "SK"
        assert mgr.config.timeout_seconds == 90
        assert uuid.UUID(mgr.config.session_id).version == 4

        old_session = mgr.config.session_id
        mgr.update(
            language="EN",
            chat_webhook_url="https://example.hf.space/webhook/logistics-agent",
            bearer_token="test-token-123",
            timeout_seconds=120,
        )

        reloaded = config_manager.ConfigManager(appdata_dir=fake_appdata)
        assert reloaded.config.language == "EN"
        assert reloaded.config.chat_webhook_url == "https://example.hf.space/webhook/logistics-agent"
        assert reloaded.config.bearer_token == "test-token-123"
        assert reloaded.config.timeout_seconds == 120
        assert reloaded.config.session_id == old_session

        new_session = reloaded.reset_session_id()
        assert new_session != old_session
        assert uuid.UUID(new_session).version == 4

        raw = json.loads(expected_path.read_text(encoding="utf-8"))
        assert raw["session_id"] == new_session
        assert not list(MVP_ROOT.rglob("config.json")), "config.json must never be written inside mvp/"

    def test_corrupted_json_and_timeout_floor(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "LogisticsRAGAgent" / "config.json"
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text("{corrupt json", encoding="utf-8")

        mgr = config_manager.ConfigManager(config_path=cfg_file)
        assert mgr.config.language == "SK"
        assert mgr.config.timeout_seconds == 90

        mgr.update(timeout_seconds=1)
        assert mgr.config.timeout_seconds == config_manager.MIN_TIMEOUT_SECONDS


class TestApiClient:
    def _make_client(self, session: MagicMock, token: str = "secret-bearer") -> api_client.LogisticsApiClient:
        return api_client.LogisticsApiClient(
            chat_webhook_url="https://demo.example.com/webhook/logistics-agent",
            ingest_webhook_url="https://demo.example.com/webhook/rag-ingest",
            bearer_token=token,
            timeout_seconds=45,
            session=session,
        )

    def test_send_chat_success_with_dict_and_str_sources(self) -> None:
        session = MagicMock()
        session.post.return_value = _FakeResponse(
            200,
            json_data={
                "status": "ok",
                "answer": "Stojné po 2 hodinách je 35 EUR/hod.",
                "used_tools": [
                    {"name": "qdrant_logistics_knowledge_base"},
                    "qdrant_logistics_knowledge_base",
                    "invoice_receipt_verifier",
                ],
                "sources": [
                    {
                        "filename": "interne_tarify_2026.txt",
                        "category": "smernica",
                        "doc_type": "guideline",
                        "snippet": "FTL súprava: 35,00 EUR",
                    },
                    "sop_cmr_reklamacie.txt",
                ],
                "sessionId": "sess-1",
            },
        )
        client = self._make_client(session, token="my-bearer-token")
        resp = client.send_chat("Aké je stojné?", session_id="sess-1", language="SK")

        assert resp.status == "ok"
        assert "35 EUR" in resp.answer
        assert resp.used_tools == ["qdrant_logistics_knowledge_base", "invoice_receipt_verifier"]
        assert len(resp.sources) == 2
        assert resp.sources[0]["filename"] == "interne_tarify_2026.txt"
        assert resp.sources[1]["filename"] == "sop_cmr_reklamacie.txt"

        call_kwargs = session.post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer my-bearer-token"
        assert call_kwargs["json"] == {
            "message": "Aké je stojné?",
            "sessionId": "sess-1",
            "language": "sk",
            "action": "chat",
        }
        assert call_kwargs["timeout"] == 45

    def test_upload_document_multipart_and_metadata(self, tmp_path: Path) -> None:
        doc_path = tmp_path / "faktura_01.txt"
        doc_path.write_text("Faktúra za prepravu KE-BA 1.28 EUR/km", encoding="utf-8")

        session = MagicMock()
        session.post.return_value = _FakeResponse(
            200,
            json_data=[
                {
                    "status": "ok",
                    "filename": "faktura_01.txt",
                    "category": "faktura",
                    "doc_type": "invoice",
                    "collection": "logistics_docs",
                    "chunks_indexed": 2,
                    "uploaded_at": "2026-11-24T20:50:00Z",
                    "message": "Indexed",
                }
            ],
        )
        client = self._make_client(session, token="tok-abc")
        res = client.upload_document(doc_path, category="faktura")

        assert res.status == "ok"
        assert res.filename == "faktura_01.txt"
        assert res.category == "faktura"
        assert res.doc_type == "invoice"
        assert res.chunks_indexed == 2
        assert res.collection == "logistics_docs"

        call_kwargs = session.post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer tok-abc"
        assert "file" in call_kwargs["files"]
        assert call_kwargs["files"]["file"][0] == "faktura_01.txt"
        form_data = call_kwargs["data"]
        assert form_data["category"] == "faktura"
        assert form_data["doc_type"] == "invoice"
        assert form_data["filename"] == "faktura_01.txt"
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", form_data["uploaded_at"])

    def test_test_connection_success_and_failures(self) -> None:
        session = MagicMock()
        session.post.return_value = _FakeResponse(
            200,
            json_data={"status": "ok", "service": "LogisticsRAGAgent", "mode": "healthcheck"},
        )
        client = self._make_client(session)
        ok_res = client.test_connection(timeout=8)
        assert ok_res.ok is True
        assert ok_res.status_code == 200
        assert "LogisticsRAGAgent" in ok_res.detail
        assert session.post.call_args.kwargs["json"]["action"] == "healthcheck"

        session.post.return_value = _FakeResponse(401, json_data={"message": "Unauthorized"})
        unauth_res = client.test_connection()
        assert unauth_res.ok is False
        assert unauth_res.status_code == 401
        assert "Unauthorized" in unauth_res.detail

        session.post.side_effect = requests.Timeout("timed out")
        timeout_res = client.test_connection()
        assert timeout_res.ok is False
        assert timeout_res.status_code is None
        assert "Timeout" in timeout_res.detail

    def test_send_chat_and_upload_error_paths(self, tmp_path: Path) -> None:
        session = MagicMock()
        client = self._make_client(session)

        with pytest.raises(api_client.ApiError) as exc_empty:
            client.send_chat("   ", session_id="s1")
        assert exc_empty.value.error_code == "empty_message"

        session.post.return_value = _FakeResponse(500, json_data={"message": "Internal error"})
        with pytest.raises(api_client.ApiError) as exc_http:
            client.send_chat("Ahoj", session_id="s1")
        assert exc_http.value.error_code == "http_error"
        assert exc_http.value.status_code == 500

        session.post.return_value = _FakeResponse(200, json_exc=ValueError("bad json"), text="not-json")
        with pytest.raises(api_client.ApiError) as exc_json:
            client.send_chat("Ahoj", session_id="s1")
        assert exc_json.value.error_code == "invalid_json"

        session.post.side_effect = requests.Timeout("read timeout")
        with pytest.raises(api_client.ApiError) as exc_to:
            client.send_chat("Ahoj", session_id="s1")
        assert exc_to.value.error_code == "timeout"

        session.post.side_effect = requests.ConnectionError("refused")
        with pytest.raises(api_client.ApiError) as exc_conn:
            client.send_chat("Ahoj", session_id="s1")
        assert exc_conn.value.error_code == "connection_error"

        with pytest.raises(api_client.ApiError) as exc_missing:
            client.upload_document(tmp_path / "missing.pdf", category="faktura")
        assert exc_missing.value.error_code == "file_not_found"

        bad_ext = tmp_path / "malware.exe"
        bad_ext.write_text("x", encoding="utf-8")
        with pytest.raises(api_client.ApiError) as exc_ext:
            client.upload_document(bad_ext, category="faktura")
        assert exc_ext.value.error_code == "invalid_file"

        bad_url_client = api_client.LogisticsApiClient("ftp://invalid", "ftp://invalid", session=session)
        with pytest.raises(api_client.ApiError) as exc_url:
            bad_url_client.send_chat("Hello", session_id="s1")
        assert exc_url.value.error_code == "invalid_url"
