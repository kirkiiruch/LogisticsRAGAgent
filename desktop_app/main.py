"""LogisticsRAGAgent — Multilingual CustomTkinter Desktop Application."""

from __future__ import annotations

import argparse
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog
from typing import Any

# Ensure sibling modules resolve cleanly when launched directly, via pytest, or PyInstaller.
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import customtkinter as ctk

from api_client import (
    ApiError,
    ChatResponse,
    ConnectionCheckResult,
    IngestResponse,
    LogisticsApiClient,
    is_valid_http_url,
)
from config_manager import ConfigManager
from i18n import (
    CATEGORY_KEYS,
    SUPPORTED_LANGUAGES,
    get_category_key,
    get_category_label,
    get_category_options,
    normalize_language,
    t,
)

APPEARANCE_KEYS: tuple[str, ...] = ("System", "Dark", "Light")


class LogisticsRAGApp(ctk.CTk):
    """Main desktop GUI window for LogisticsRAGAgent."""

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        api_client: LogisticsApiClient | None = None,
    ) -> None:
        super().__init__()

        self.config_manager = config_manager or ConfigManager()
        cfg = self.config_manager.config

        self.active_lang: str = normalize_language(cfg.language)
        self.active_tab: str = "chat"
        self.selected_category_key: str = CATEGORY_KEYS[0]
        self.selected_file_path: Path | None = None
        self.token_visible: bool = False
        self.is_busy: bool = False
        self._closing: bool = False

        # Dynamic state records so all visible messages/logs re-translate on language switch.
        self.chat_messages: list[dict[str, Any]] = []
        self.upload_logs: list[dict[str, Any]] = []
        self._chat_status_key: str = "status_idle"
        self._kb_status_state: tuple[str, dict[str, Any]] | None = None
        self._settings_status_state: tuple[str, dict[str, Any], str] | None = None

        self.api_client = api_client or LogisticsApiClient(
            chat_webhook_url=cfg.chat_webhook_url,
            ingest_webhook_url=cfg.ingest_webhook_url,
            bearer_token=cfg.bearer_token,
            timeout_seconds=cfg.timeout_seconds,
        )

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode(cfg.appearance_mode)

        self.geometry("1140x760")
        self.minsize(940, 620)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_container()
        self._build_chat_tab()
        self._build_kb_tab()
        self._build_settings_tab()

        self._select_tab("chat")
        self.apply_language()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        brand_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_box.grid(row=0, column=0, padx=18, pady=(22, 16), sticky="ew")

        self.brand_title_lbl = ctk.CTkLabel(
            brand_box,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.brand_title_lbl.pack(fill="x")

        self.brand_subtitle_lbl = ctk.CTkLabel(
            brand_box,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65"),
            anchor="w",
        )
        self.brand_subtitle_lbl.pack(fill="x", pady=(2, 0))

        self.nav_section_lbl = ctk.CTkLabel(
            self.sidebar_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray45", "gray60"),
            anchor="w",
        )
        self.nav_section_lbl.grid(row=1, column=0, padx=20, pady=(6, 6), sticky="ew")

        self.nav_chat_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            height=40,
            anchor="w",
            corner_radius=8,
            command=lambda: self._select_tab("chat"),
        )
        self.nav_chat_btn.grid(row=2, column=0, padx=16, pady=4, sticky="ew")

        self.nav_kb_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            height=40,
            anchor="w",
            corner_radius=8,
            command=lambda: self._select_tab("kb"),
        )
        self.nav_kb_btn.grid(row=3, column=0, padx=16, pady=4, sticky="ew")

        self.nav_settings_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="",
            height=40,
            anchor="w",
            corner_radius=8,
            command=lambda: self._select_tab("settings"),
        )
        self.nav_settings_btn.grid(row=4, column=0, padx=16, pady=4, sticky="ew")

        bottom_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_box.grid(row=6, column=0, padx=16, pady=(12, 18), sticky="sew")

        self.lang_label = ctk.CTkLabel(
            bottom_box,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.lang_label.pack(fill="x", pady=(0, 4))

        self.lang_selector = ctk.CTkSegmentedButton(
            bottom_box,
            values=list(SUPPORTED_LANGUAGES),
            command=self._on_language_selected,
        )
        self.lang_selector.set(self.active_lang)
        self.lang_selector.pack(fill="x", pady=(0, 12))

        self.theme_label = ctk.CTkLabel(
            bottom_box,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.theme_label.pack(fill="x", pady=(0, 4))

        self.theme_menu = ctk.CTkOptionMenu(
            bottom_box,
            values=list(APPEARANCE_KEYS),
            command=self._on_theme_selected,
        )
        self.theme_menu.pack(fill="x", pady=(0, 12))

        self.session_title_lbl = ctk.CTkLabel(
            bottom_box,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray45", "gray60"),
            anchor="w",
        )
        self.session_title_lbl.pack(fill="x")

        self.session_id_lbl = ctk.CTkLabel(
            bottom_box,
            text=self._short_session_id(),
            font=ctk.CTkFont(size=11),
            text_color=("gray35", "gray70"),
            anchor="w",
        )
        self.session_id_lbl.pack(fill="x")

    def _build_main_container(self) -> None:
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=18, pady=16)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

    def _build_chat_tab(self) -> None:
        self.chat_tab = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.chat_tab.grid_rowconfigure(2, weight=1)
        self.chat_tab.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.chat_tab)
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_row.grid_columnconfigure(0, weight=1)

        title_col = ctk.CTkFrame(header_row, fg_color="transparent")
        title_col.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self.chat_header_lbl = ctk.CTkLabel(
            title_col,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.chat_header_lbl.pack(fill="x")

        self.chat_subheader_lbl = ctk.CTkLabel(
            title_col,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray68"),
            anchor="w",
        )
        self.chat_subheader_lbl.pack(fill="x", pady=(2, 0))

        controls_col = ctk.CTkFrame(header_row, fg_color="transparent")
        controls_col.grid(row=0, column=1, padx=14, pady=10, sticky="e")

        self.chat_status_title_lbl = ctk.CTkLabel(
            controls_col,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.chat_status_title_lbl.pack(side="left", padx=(0, 6))

        self.chat_status_badge = ctk.CTkLabel(
            controls_col,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            padx=10,
            pady=4,
            fg_color=("gray82", "gray28"),
        )
        self.chat_status_badge.pack(side="left", padx=(0, 12))

        self.new_session_btn = ctk.CTkButton(
            controls_col,
            text="",
            width=120,
            height=32,
            command=self._on_new_session,
        )
        self.new_session_btn.pack(side="left")

        presets_frame = ctk.CTkFrame(self.chat_tab)
        presets_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        presets_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.presets_title_lbl = ctk.CTkLabel(
            presets_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.presets_title_lbl.grid(
            row=0, column=0, columnspan=4, padx=12, pady=(8, 4), sticky="w"
        )

        self.preset_buttons: list[tuple[ctk.CTkButton, str, str]] = []
        preset_specs = [
            ("preset_gmail_label", "preset_gmail_prompt"),
            ("preset_qdrant_label", "preset_qdrant_prompt"),
            ("preset_invoice_label", "preset_invoice_prompt"),
            ("preset_cmr_label", "preset_cmr_prompt"),
        ]
        for idx, (label_key, prompt_key) in enumerate(preset_specs):
            btn = ctk.CTkButton(
                presets_frame,
                text="",
                height=34,
                fg_color=("gray86", "gray26"),
                text_color=("gray10", "gray92"),
                hover_color=("gray78", "gray34"),
                command=lambda pk=prompt_key: self._trigger_preset(pk),
            )
            btn.grid(row=1, column=idx, padx=8, pady=(2, 10), sticky="ew")
            self.preset_buttons.append((btn, label_key, prompt_key))

        self.chat_scroll = ctk.CTkScrollableFrame(self.chat_tab)
        self.chat_scroll.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        input_frame = ctk.CTkFrame(self.chat_tab)
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(
            input_frame,
            height=42,
            placeholder_text="",
        )
        self.chat_input.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="ew")
        self.chat_input.bind("<Return>", self._on_chat_enter)

        self.chat_send_btn = ctk.CTkButton(
            input_frame,
            text="",
            width=120,
            height=42,
            command=self._on_send_chat,
        )
        self.chat_send_btn.grid(row=0, column=1, padx=(0, 8), pady=10)

        self.chat_clear_btn = ctk.CTkButton(
            input_frame,
            text="",
            width=120,
            height=42,
            fg_color=("gray75", "gray30"),
            text_color=("gray10", "gray95"),
            hover_color=("gray65", "gray38"),
            command=self._on_clear_chat,
        )
        self.chat_clear_btn.grid(row=0, column=2, padx=(0, 12), pady=10)

    def _build_kb_tab(self) -> None:
        self.kb_tab = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.kb_tab.grid_rowconfigure(2, weight=1)
        self.kb_tab.grid_columnconfigure(0, weight=1)

        kb_header_card = ctk.CTkFrame(self.kb_tab)
        kb_header_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.kb_header_lbl = ctk.CTkLabel(
            kb_header_card,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.kb_header_lbl.pack(fill="x", padx=14, pady=(12, 2))

        self.kb_subheader_lbl = ctk.CTkLabel(
            kb_header_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray68"),
            anchor="w",
        )
        self.kb_subheader_lbl.pack(fill="x", padx=14, pady=(0, 12))

        upload_card = ctk.CTkFrame(self.kb_tab)
        upload_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        upload_card.grid_columnconfigure(1, weight=1)

        self.kb_file_title_lbl = ctk.CTkLabel(
            upload_card,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.kb_file_title_lbl.grid(row=0, column=0, padx=(14, 10), pady=(14, 8), sticky="w")

        self.kb_selected_file_lbl = ctk.CTkLabel(
            upload_card,
            text="",
            anchor="w",
            text_color=("gray30", "gray78"),
        )
        self.kb_selected_file_lbl.grid(row=0, column=1, padx=6, pady=(14, 8), sticky="ew")

        self.kb_browse_btn = ctk.CTkButton(
            upload_card,
            text="",
            width=150,
            height=34,
            command=self._on_browse_file,
        )
        self.kb_browse_btn.grid(row=0, column=2, padx=(8, 14), pady=(14, 8))

        self.kb_category_title_lbl = ctk.CTkLabel(
            upload_card,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.kb_category_title_lbl.grid(row=1, column=0, padx=(14, 10), pady=8, sticky="w")

        self.kb_category_menu = ctk.CTkOptionMenu(
            upload_card,
            values=get_category_options(self.active_lang),
            command=self._on_category_selected,
        )
        self.kb_category_menu.grid(row=1, column=1, padx=6, pady=8, sticky="w")

        self.kb_upload_btn = ctk.CTkButton(
            upload_card,
            text="",
            width=210,
            height=38,
            command=self._on_upload_document,
        )
        self.kb_upload_btn.grid(row=2, column=0, padx=(14, 10), pady=(8, 14), sticky="w")

        self.kb_status_lbl = ctk.CTkLabel(
            upload_card,
            text="",
            anchor="w",
            wraplength=540,
        )
        self.kb_status_lbl.grid(row=2, column=1, columnspan=2, padx=(6, 14), pady=(8, 14), sticky="ew")

        log_card = ctk.CTkFrame(self.kb_tab)
        log_card.grid(row=2, column=0, sticky="nsew")
        log_card.grid_rowconfigure(2, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        self.kb_log_header_lbl = ctk.CTkLabel(
            log_card,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.kb_log_header_lbl.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="w")

        cols_header = ctk.CTkFrame(log_card, fg_color=("gray86", "gray22"))
        cols_header.grid(row=1, column=0, padx=14, pady=(0, 4), sticky="ew")
        cols_header.grid_columnconfigure(0, weight=1)
        cols_header.grid_columnconfigure(1, weight=2)
        cols_header.grid_columnconfigure(2, weight=1)
        cols_header.grid_columnconfigure(3, weight=2)

        self.kb_col_time_lbl = ctk.CTkLabel(cols_header, text="", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.kb_col_time_lbl.grid(row=0, column=0, padx=8, pady=6, sticky="w")

        self.kb_col_file_lbl = ctk.CTkLabel(cols_header, text="", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.kb_col_file_lbl.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        self.kb_col_cat_lbl = ctk.CTkLabel(cols_header, text="", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.kb_col_cat_lbl.grid(row=0, column=2, padx=8, pady=6, sticky="w")

        self.kb_col_status_lbl = ctk.CTkLabel(cols_header, text="", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.kb_col_status_lbl.grid(row=0, column=3, padx=8, pady=6, sticky="w")

        self.kb_log_scroll = ctk.CTkScrollableFrame(log_card)
        self.kb_log_scroll.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self.kb_log_scroll.grid_columnconfigure(0, weight=1)

    def _build_settings_tab(self) -> None:
        cfg = self.config_manager.config
        self.settings_tab = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.settings_tab.grid_columnconfigure(0, weight=1)

        header_card = ctk.CTkFrame(self.settings_tab)
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.settings_header_lbl = ctk.CTkLabel(
            header_card,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.settings_header_lbl.pack(fill="x", padx=14, pady=(12, 2))

        self.settings_subheader_lbl = ctk.CTkLabel(
            header_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray68"),
            anchor="w",
        )
        self.settings_subheader_lbl.pack(fill="x", padx=14, pady=(0, 12))

        form_card = ctk.CTkFrame(self.settings_tab)
        form_card.grid(row=1, column=0, sticky="ew")
        form_card.grid_columnconfigure(1, weight=1)

        self.settings_chat_url_lbl = ctk.CTkLabel(
            form_card, text="", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.settings_chat_url_lbl.grid(row=0, column=0, padx=14, pady=(16, 8), sticky="w")

        self.chat_url_entry = ctk.CTkEntry(form_card, height=36)
        self.chat_url_entry.insert(0, cfg.chat_webhook_url)
        self.chat_url_entry.grid(row=0, column=1, columnspan=2, padx=14, pady=(16, 8), sticky="ew")

        self.settings_ingest_url_lbl = ctk.CTkLabel(
            form_card, text="", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.settings_ingest_url_lbl.grid(row=1, column=0, padx=14, pady=8, sticky="w")

        self.ingest_url_entry = ctk.CTkEntry(form_card, height=36)
        self.ingest_url_entry.insert(0, cfg.ingest_webhook_url)
        self.ingest_url_entry.grid(row=1, column=1, columnspan=2, padx=14, pady=8, sticky="ew")

        self.settings_token_lbl = ctk.CTkLabel(
            form_card, text="", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.settings_token_lbl.grid(row=2, column=0, padx=14, pady=8, sticky="w")

        self.token_entry = ctk.CTkEntry(form_card, height=36, show="*")
        if cfg.bearer_token:
            self.token_entry.insert(0, cfg.bearer_token)
        self.token_entry.grid(row=2, column=1, padx=(14, 8), pady=8, sticky="ew")

        self.token_toggle_btn = ctk.CTkButton(
            form_card,
            text="",
            width=96,
            height=36,
            fg_color=("gray76", "gray30"),
            text_color=("gray10", "gray95"),
            hover_color=("gray66", "gray38"),
            command=self._toggle_token_visibility,
        )
        self.token_toggle_btn.grid(row=2, column=2, padx=(0, 14), pady=8)

        self.settings_timeout_lbl = ctk.CTkLabel(
            form_card, text="", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.settings_timeout_lbl.grid(row=3, column=0, padx=14, pady=8, sticky="w")

        self.timeout_entry = ctk.CTkEntry(form_card, height=36, width=140)
        self.timeout_entry.insert(0, str(cfg.timeout_seconds))
        self.timeout_entry.grid(row=3, column=1, padx=14, pady=8, sticky="w")

        self.settings_cfg_path_title_lbl = ctk.CTkLabel(
            form_card, text="", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.settings_cfg_path_title_lbl.grid(row=4, column=0, padx=14, pady=8, sticky="w")

        self.settings_cfg_path_val_lbl = ctk.CTkLabel(
            form_card,
            text=str(self.config_manager.config_path),
            text_color=("gray38", "gray68"),
            anchor="w",
            wraplength=560,
        )
        self.settings_cfg_path_val_lbl.grid(row=4, column=1, columnspan=2, padx=14, pady=8, sticky="w")

        btn_row = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_row.grid(row=5, column=0, columnspan=3, padx=14, pady=(12, 8), sticky="w")

        self.settings_save_btn = ctk.CTkButton(
            btn_row,
            text="",
            width=170,
            height=38,
            command=self._on_save_settings,
        )
        self.settings_save_btn.pack(side="left", padx=(0, 10))

        self.settings_test_btn = ctk.CTkButton(
            btn_row,
            text="",
            width=190,
            height=38,
            fg_color=("gray75", "gray30"),
            text_color=("gray10", "gray95"),
            hover_color=("gray65", "gray38"),
            command=self._on_test_connection,
        )
        self.settings_test_btn.pack(side="left")

        self.settings_status_lbl = ctk.CTkLabel(
            form_card,
            text="",
            anchor="w",
            wraplength=760,
        )
        self.settings_status_lbl.grid(row=6, column=0, columnspan=3, padx=14, pady=(4, 16), sticky="ew")
    # ------------------------------------------------------------------
    # Language & Tab Switching
    # ------------------------------------------------------------------
    def _tr(self, key: str, **kwargs: Any) -> str:
        return t(self.active_lang, key, **kwargs)

    def _short_session_id(self) -> str:
        sid = self.config_manager.config.session_id
        return sid[:18] + "..." if len(sid) > 21 else sid

    def _select_tab(self, tab_name: str) -> None:
        self.active_tab = tab_name
        for frame in (self.chat_tab, self.kb_tab, self.settings_tab):
            frame.grid_forget()

        if tab_name == "chat":
            self.chat_tab.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "kb":
            self.kb_tab.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "settings":
            self.settings_tab.grid(row=0, column=0, sticky="nsew")

        self._update_nav_styles()

    def _update_nav_styles(self) -> None:
        buttons = {
            "chat": self.nav_chat_btn,
            "kb": self.nav_kb_btn,
            "settings": self.nav_settings_btn,
        }
        for key, btn in buttons.items():
            if key == self.active_tab:
                btn.configure(
                    fg_color=("#1f6aa5", "#1f6aa5"),
                    text_color=("white", "white"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray15", "gray90"),
                )

    def _on_language_selected(self, lang_value: str) -> None:
        self.set_language(lang_value)

    def set_language(self, lang: str) -> None:
        """Switch the active UI language immediately and persist to config."""
        self.active_lang = normalize_language(lang)
        self.lang_selector.set(self.active_lang)
        self.config_manager.update(language=self.active_lang)
        self.apply_language()

    def _on_theme_selected(self, localized_mode: str) -> None:
        mode = self._theme_label_to_mode(localized_mode)
        ctk.set_appearance_mode(mode)
        self.config_manager.update(appearance_mode=mode)

    def _theme_mode_to_label(self, mode: str) -> str:
        mapping = {
            "System": self._tr("theme_system"),
            "Dark": self._tr("theme_dark"),
            "Light": self._tr("theme_light"),
        }
        return mapping.get(mode, self._tr("theme_system"))

    def _theme_label_to_mode(self, label: str) -> str:
        cleaned = str(label).strip()
        for lang in SUPPORTED_LANGUAGES:
            if cleaned == t(lang, "theme_system"):
                return "System"
            if cleaned == t(lang, "theme_dark"):
                return "Dark"
            if cleaned == t(lang, "theme_light"):
                return "Light"
        if cleaned in APPEARANCE_KEYS:
            return cleaned
        return "System"

    def apply_language(self) -> None:
        """Re-translate 100% of visible UI widgets without restarting."""
        self.title(self._tr("app_title"))

        # Sidebar
        self.brand_title_lbl.configure(text=self._tr("brand_name"))
        self.brand_subtitle_lbl.configure(text=self._tr("brand_subtitle"))
        self.nav_section_lbl.configure(text=self._tr("sidebar_nav_label"))
        self.nav_chat_btn.configure(text=self._tr("nav_chat"))
        self.nav_kb_btn.configure(text=self._tr("nav_kb"))
        self.nav_settings_btn.configure(text=self._tr("nav_settings"))
        self.lang_label.configure(text=self._tr("sidebar_lang_label"))
        self.theme_label.configure(text=self._tr("sidebar_theme_label"))
        self.session_title_lbl.configure(text=self._tr("sidebar_session_label"))
        self.session_id_lbl.configure(text=self._short_session_id())

        theme_options = [
            self._tr("theme_system"),
            self._tr("theme_dark"),
            self._tr("theme_light"),
        ]
        self.theme_menu.configure(values=theme_options)
        self.theme_menu.set(self._theme_mode_to_label(self.config_manager.config.appearance_mode))

        # Chat tab
        self.chat_header_lbl.configure(text=self._tr("chat_header"))
        self.chat_subheader_lbl.configure(text=self._tr("chat_subheader"))
        self.chat_status_title_lbl.configure(text=self._tr("chat_status_label"))
        self._refresh_chat_status_badge()
        self.new_session_btn.configure(text=self._tr("chat_new_session"))
        self.presets_title_lbl.configure(text=self._tr("chat_presets_label"))
        for btn, label_key, _ in self.preset_buttons:
            btn.configure(text=self._tr(label_key))

        self.chat_input.configure(placeholder_text=self._tr("chat_input_placeholder"))
        self.chat_send_btn.configure(text=self._tr("chat_send_btn"))
        self.chat_clear_btn.configure(text=self._tr("chat_clear_btn"))
        self._render_chat_messages()

        # Knowledge Base tab
        self.kb_header_lbl.configure(text=self._tr("kb_header"))
        self.kb_subheader_lbl.configure(text=self._tr("kb_subheader"))
        self.kb_file_title_lbl.configure(text=self._tr("kb_file_label"))
        if self.selected_file_path is None:
            self.kb_selected_file_lbl.configure(text=self._tr("kb_no_file"))
        else:
            self.kb_selected_file_lbl.configure(text=self.selected_file_path.name)
        self.kb_browse_btn.configure(text=self._tr("kb_browse_btn"))
        self.kb_category_title_lbl.configure(text=self._tr("kb_category_label"))
        self.kb_category_menu.configure(values=get_category_options(self.active_lang))
        self.kb_category_menu.set(get_category_label(self.active_lang, self.selected_category_key))
        self.kb_upload_btn.configure(text=self._tr("kb_upload_btn"))
        if self._kb_status_state is not None:
            key, kwargs = self._kb_status_state
            self.kb_status_lbl.configure(text=self._tr(key, **kwargs))

        self.kb_log_header_lbl.configure(text=self._tr("kb_log_header"))
        self.kb_col_time_lbl.configure(text=self._tr("kb_col_time"))
        self.kb_col_file_lbl.configure(text=self._tr("kb_col_filename"))
        self.kb_col_cat_lbl.configure(text=self._tr("kb_col_category"))
        self.kb_col_status_lbl.configure(text=self._tr("kb_col_status"))
        self._render_upload_logs()

        # Settings tab
        self.settings_header_lbl.configure(text=self._tr("settings_header"))
        self.settings_subheader_lbl.configure(text=self._tr("settings_subheader"))
        self.settings_chat_url_lbl.configure(text=self._tr("settings_chat_url_label"))
        self.settings_ingest_url_lbl.configure(text=self._tr("settings_ingest_url_label"))
        self.settings_token_lbl.configure(text=self._tr("settings_token_label"))
        self.settings_timeout_lbl.configure(text=self._tr("settings_timeout_label"))
        self.settings_cfg_path_title_lbl.configure(text=self._tr("settings_config_path_label"))
        self.settings_save_btn.configure(text=self._tr("settings_save_btn"))
        self.settings_test_btn.configure(text=self._tr("settings_test_btn"))
        self.chat_url_entry.configure(placeholder_text=self._tr("settings_chat_url_placeholder"))
        self.ingest_url_entry.configure(placeholder_text=self._tr("settings_ingest_url_placeholder"))
        self.token_entry.configure(placeholder_text=self._tr("settings_token_placeholder"))
        self.token_toggle_btn.configure(
            text=self._tr("settings_hide_token") if self.token_visible else self._tr("settings_show_token")
        )
        if self._settings_status_state is not None:
            key, kwargs, color = self._settings_status_state
            self.settings_status_lbl.configure(text=self._tr(key, **kwargs), text_color=color)

    # ------------------------------------------------------------------
    # Chat Tab Logic
    # ------------------------------------------------------------------
    def _set_chat_status(self, status_key: str) -> None:
        self._chat_status_key = status_key
        self._refresh_chat_status_badge()

    def _refresh_chat_status_badge(self) -> None:
        colors = {
            "status_idle": ("gray82", "gray28"),
            "status_sending": ("#d97706", "#b45309"),
            "status_done": ("#15803d", "#166534"),
            "status_error": ("#b91c1c", "#991b1b"),
        }
        text_colors = {
            "status_idle": ("gray15", "gray92"),
            "status_sending": ("white", "white"),
            "status_done": ("white", "white"),
            "status_error": ("white", "white"),
        }
        self.chat_status_badge.configure(
            text=self._tr(self._chat_status_key),
            fg_color=colors.get(self._chat_status_key, ("gray82", "gray28")),
            text_color=text_colors.get(self._chat_status_key, ("gray15", "gray92")),
        )

    def _set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        self.chat_send_btn.configure(state=state)
        self.kb_upload_btn.configure(state=state)
        self.settings_test_btn.configure(state=state)
        for btn, _, _ in self.preset_buttons:
            btn.configure(state=state)

    def _on_chat_enter(self, _event: Any) -> None:
        if not self.is_busy:
            self._on_send_chat()

    def _trigger_preset(self, prompt_key: str) -> None:
        if self.is_busy:
            return
        prompt_text = self._tr(prompt_key)
        self.chat_input.delete(0, "end")
        self.chat_input.insert(0, prompt_text)
        self._on_send_chat()

    def _on_new_session(self) -> None:
        if self.is_busy:
            return
        new_sid = self.config_manager.reset_session_id()
        self.session_id_lbl.configure(text=self._short_session_id())
        self.chat_messages.append(
            {
                "role": "system",
                "i18n_key": "chat_session_reset_msg",
                "i18n_kwargs": {"session_id": new_sid},
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }
        )
        self._set_chat_status("status_idle")
        self._render_chat_messages()

    def _on_clear_chat(self) -> None:
        self.chat_messages.clear()
        self._set_chat_status("status_idle")
        self._render_chat_messages()

    def _on_send_chat(self) -> None:
        if self.is_busy:
            return
        message = self.chat_input.get().strip()
        if not message:
            self.chat_messages.append(
                {
                    "role": "error",
                    "i18n_key": "chat_empty_warning",
                    "i18n_kwargs": {},
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                }
            )
            self._set_chat_status("status_error")
            self._render_chat_messages()
            return

        self.chat_input.delete(0, "end")
        self.chat_messages.append(
            {
                "role": "user",
                "text": message,
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }
        )
        self._set_chat_status("status_sending")
        self._set_busy(True)
        self._render_chat_messages()

        session_id = self.config_manager.config.session_id
        lang_code = self.active_lang.lower()

        def worker() -> None:
            try:
                result = self.api_client.send_chat(
                    message=message,
                    session_id=session_id,
                    language=lang_code,
                )
                self._schedule_ui(lambda r=result: self._handle_chat_success(r))
            except ApiError as exc:
                self._schedule_ui(lambda e=exc: self._handle_chat_error(e))
            except Exception as exc:  # noqa: BLE001
                err = ApiError("unknown", detail=str(exc))
                self._schedule_ui(lambda e=err: self._handle_chat_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_chat_success(self, result: ChatResponse) -> None:
        self._set_busy(False)
        self._set_chat_status("status_done")
        self.chat_messages.append(
            {
                "role": "agent",
                "text": result.answer,
                "used_tools": result.used_tools,
                "sources": result.sources,
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }
        )
        self._render_chat_messages()

    def _handle_chat_error(self, error: ApiError) -> None:
        self._set_busy(False)
        self._set_chat_status("status_error")
        self.chat_messages.append(
            {
                "role": "error",
                "text": self._format_api_error(error),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }
        )
        self._render_chat_messages()

    def _render_chat_messages(self) -> None:
        for child in self.chat_scroll.winfo_children():
            child.destroy()

        if not self.chat_messages:
            welcome = ctk.CTkFrame(self.chat_scroll, corner_radius=10)
            welcome.grid(row=0, column=0, padx=8, pady=12, sticky="ew")
            ctk.CTkLabel(
                welcome,
                text=self._tr("chat_welcome_title"),
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(14, 4))
            ctk.CTkLabel(
                welcome,
                text=self._tr("chat_welcome_body"),
                font=ctk.CTkFont(size=13),
                text_color=("gray35", "gray72"),
                anchor="w",
                justify="left",
                wraplength=680,
            ).pack(fill="x", padx=16, pady=(0, 14))
            return

        for idx, msg in enumerate(self.chat_messages):
            role = msg.get("role", "agent")
            if role == "user":
                bg = ("#dbeafe", "#1e3a5f")
                role_label = self._tr("chat_role_user")
            elif role == "error":
                bg = ("#fee2e2", "#4c1d1d")
                role_label = self._tr("status_error")
            elif role == "system":
                bg = ("#e5e7eb", "#2b2d31")
                role_label = self._tr("chat_role_system")
            else:
                bg = ("#f3f4f6", "#252830")
                role_label = self._tr("chat_role_agent")

            card = ctk.CTkFrame(self.chat_scroll, fg_color=bg, corner_radius=10)
            card.grid(row=idx, column=0, padx=8, pady=6, sticky="ew")

            meta_text = f"{role_label}  •  {msg.get('timestamp', '')}"
            ctk.CTkLabel(
                card,
                text=meta_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray30", "gray75"),
                anchor="w",
            ).pack(fill="x", padx=14, pady=(10, 2))

            if "i18n_key" in msg:
                body_text = self._tr(msg["i18n_key"], **msg.get("i18n_kwargs", {}))
            else:
                body_text = str(msg.get("text", ""))

            ctk.CTkLabel(
                card,
                text=body_text,
                font=ctk.CTkFont(size=13),
                anchor="w",
                justify="left",
                wraplength=680,
            ).pack(fill="x", padx=14, pady=(2, 8))

            if role == "agent":
                used_tools = msg.get("used_tools") or []
                tools_text = (
                    ", ".join(used_tools) if used_tools else self._tr("chat_no_tools")
                )
                ctk.CTkLabel(
                    card,
                    text=f"{self._tr('chat_tools_label')} {tools_text}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("#1d4ed8", "#93c5fd"),
                    anchor="w",
                    justify="left",
                    wraplength=680,
                ).pack(fill="x", padx=14, pady=(0, 6))

                sources = msg.get("sources") or []
                if sources:
                    source_lines: list[str] = []
                    for src in sources:
                        fname = src.get("filename") or "?"
                        cat = src.get("category") or ""
                        snippet = src.get("snippet") or ""
                        line = f"• {fname}"
                        if cat:
                            line += f" [{cat}]"
                        if snippet:
                            line += f": {snippet[:140]}"
                        source_lines.append(line)
                    ctk.CTkLabel(
                        card,
                        text=f"{self._tr('chat_sources_label')}\n" + "\n".join(source_lines),
                        font=ctk.CTkFont(size=11),
                        text_color=("gray30", "gray72"),
                        anchor="w",
                        justify="left",
                        wraplength=680,
                    ).pack(fill="x", padx=14, pady=(0, 10))

    # ------------------------------------------------------------------
    # Knowledge Base Tab Logic
    # ------------------------------------------------------------------
    def _on_browse_file(self) -> None:
        filetypes = [
            (self._tr("kb_file_types_label"), "*.pdf *.txt *.docx *.csv"),
            ("PDF", "*.pdf"),
            ("TXT", "*.txt"),
            ("DOCX", "*.docx"),
            ("CSV", "*.csv"),
        ]
        chosen = filedialog.askopenfilename(
            title=self._tr("kb_file_dialog_title"),
            filetypes=filetypes,
        )
        if chosen:
            self.selected_file_path = Path(chosen)
            self.kb_selected_file_lbl.configure(text=self.selected_file_path.name)
            self._kb_status_state = None
            self.kb_status_lbl.configure(text="")

    def _on_category_selected(self, label: str) -> None:
        self.selected_category_key = get_category_key(self.active_lang, label)

    def _on_upload_document(self) -> None:
        if self.is_busy:
            return
        if self.selected_file_path is None:
            self._kb_status_state = ("kb_select_file_first", {})
            self.kb_status_lbl.configure(
                text=self._tr("kb_select_file_first"),
                text_color=("#b91c1c", "#f87171"),
            )
            return

        target_path = self.selected_file_path
        cat_key = self.selected_category_key
        self._kb_status_state = ("kb_uploading", {})
        self.kb_status_lbl.configure(
            text=self._tr("kb_uploading"),
            text_color=("gray20", "gray85"),
        )
        self._set_busy(True)

        def worker() -> None:
            try:
                res = self.api_client.upload_document(
                    file_path=target_path,
                    category=cat_key,
                )
                self._schedule_ui(lambda r=res: self._handle_upload_success(r))
            except ApiError as exc:
                self._schedule_ui(lambda e=exc: self._handle_upload_error(target_path.name, cat_key, e))
            except Exception as exc:  # noqa: BLE001
                err = ApiError("unknown", detail=str(exc))
                self._schedule_ui(lambda e=err: self._handle_upload_error(target_path.name, cat_key, e))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_upload_success(self, res: IngestResponse) -> None:
        self._set_busy(False)
        self._kb_status_state = (
            "kb_upload_success",
            {"filename": res.filename, "chunks": res.chunks_indexed},
        )
        self.kb_status_lbl.configure(
            text=self._tr(
                "kb_upload_success",
                filename=res.filename,
                chunks=res.chunks_indexed,
            ),
            text_color=("#15803d", "#4ade80"),
        )
        self.upload_logs.insert(
            0,
            {
                "timestamp": res.uploaded_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "filename": res.filename,
                "category_key": res.category if res.category in CATEGORY_KEYS else self.selected_category_key,
                "status": f"OK ({res.chunks_indexed})",
                "ok": True,
            },
        )
        self._render_upload_logs()

    def _handle_upload_error(self, filename: str, cat_key: str, error: ApiError) -> None:
        self._set_busy(False)
        msg = self._format_api_error(error)
        self._kb_status_state = None
        self.kb_status_lbl.configure(text=msg, text_color=("#b91c1c", "#f87171"))
        self.upload_logs.insert(
            0,
            {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "filename": filename,
                "category_key": cat_key,
                "status": f"{self._tr('status_error')}: {error.error_code}",
                "ok": False,
            },
        )
        self._render_upload_logs()

    def _render_upload_logs(self) -> None:
        for child in self.kb_log_scroll.winfo_children():
            child.destroy()

        if not self.upload_logs:
            ctk.CTkLabel(
                self.kb_log_scroll,
                text=self._tr("kb_log_empty"),
                text_color=("gray45", "gray65"),
                anchor="w",
            ).grid(row=0, column=0, padx=8, pady=12, sticky="w")
            return

        for idx, entry in enumerate(self.upload_logs):
            row = ctk.CTkFrame(self.kb_log_scroll, fg_color=("gray90", "gray20"))
            row.grid(row=idx, column=0, padx=2, pady=3, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=2)
            row.grid_columnconfigure(2, weight=1)
            row.grid_columnconfigure(3, weight=2)

            ctk.CTkLabel(row, text=entry["timestamp"], anchor="w").grid(
                row=0, column=0, padx=8, pady=6, sticky="w"
            )
            ctk.CTkLabel(row, text=entry["filename"], anchor="w").grid(
                row=0, column=1, padx=8, pady=6, sticky="w"
            )
            ctk.CTkLabel(
                row,
                text=get_category_label(self.active_lang, entry["category_key"]),
                anchor="w",
            ).grid(row=0, column=2, padx=8, pady=6, sticky="w")
            ctk.CTkLabel(
                row,
                text=entry["status"],
                text_color=("#15803d", "#4ade80") if entry["ok"] else ("#b91c1c", "#f87171"),
                anchor="w",
            ).grid(row=0, column=3, padx=8, pady=6, sticky="w")

    # ------------------------------------------------------------------
    # Settings Tab Logic
    # ------------------------------------------------------------------
    def _toggle_token_visibility(self) -> None:
        self.token_visible = not self.token_visible
        self.token_entry.configure(show="" if self.token_visible else "*")
        self.token_toggle_btn.configure(
            text=self._tr("settings_hide_token") if self.token_visible else self._tr("settings_show_token")
        )

    def _read_settings_form(self) -> tuple[str, str, str, int] | None:
        chat_url = self.chat_url_entry.get().strip()
        ingest_url = self.ingest_url_entry.get().strip()
        bearer = self.token_entry.get().strip()
        timeout_raw = self.timeout_entry.get().strip()

        if not is_valid_http_url(chat_url) or not is_valid_http_url(ingest_url):
            self._settings_status_state = ("settings_invalid_url", {}, ("#b91c1c", "#f87171"))
            self.settings_status_lbl.configure(
                text=self._tr("settings_invalid_url"),
                text_color=("#b91c1c", "#f87171"),
            )
            return None

        try:
            timeout_val = int(timeout_raw)
            if timeout_val < 5:
                raise ValueError("timeout < 5")
        except ValueError:
            self._settings_status_state = ("settings_invalid_timeout", {}, ("#b91c1c", "#f87171"))
            self.settings_status_lbl.configure(
                text=self._tr("settings_invalid_timeout"),
                text_color=("#b91c1c", "#f87171"),
            )
            return None

        return chat_url, ingest_url, bearer, timeout_val

    def _on_save_settings(self) -> None:
        parsed = self._read_settings_form()
        if parsed is None:
            return
        chat_url, ingest_url, bearer, timeout_val = parsed
        self.config_manager.update(
            chat_webhook_url=chat_url,
            ingest_webhook_url=ingest_url,
            bearer_token=bearer,
            timeout_seconds=timeout_val,
        )
        self.api_client.update_settings(
            chat_webhook_url=chat_url,
            ingest_webhook_url=ingest_url,
            bearer_token=bearer,
            timeout_seconds=timeout_val,
        )
        self._settings_status_state = ("settings_saved_ok", {}, ("#15803d", "#4ade80"))
        self.settings_status_lbl.configure(
            text=self._tr("settings_saved_ok"),
            text_color=("#15803d", "#4ade80"),
        )

    def _on_test_connection(self) -> None:
        if self.is_busy:
            return
        parsed = self._read_settings_form()
        if parsed is None:
            return
        chat_url, ingest_url, bearer, timeout_val = parsed
        self.api_client.update_settings(
            chat_webhook_url=chat_url,
            ingest_webhook_url=ingest_url,
            bearer_token=bearer,
            timeout_seconds=timeout_val,
        )
        self._settings_status_state = ("settings_testing", {}, ("gray20", "gray85"))
        self.settings_status_lbl.configure(
            text=self._tr("settings_testing"),
            text_color=("gray20", "gray85"),
        )
        self._set_busy(True)

        def worker() -> None:
            result = self.api_client.test_connection()
            self._schedule_ui(lambda r=result: self._handle_test_connection_result(r))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_test_connection_result(self, result: ConnectionCheckResult) -> None:
        self._set_busy(False)
        if result.ok:
            code_str = str(result.status_code or 200)
            self._settings_status_state = (
                "settings_test_ok",
                {"status_code": code_str, "detail": result.detail},
                ("#15803d", "#4ade80"),
            )
            self.settings_status_lbl.configure(
                text=self._tr("settings_test_ok", status_code=code_str, detail=result.detail),
                text_color=("#15803d", "#4ade80"),
            )
        else:
            self._settings_status_state = (
                "settings_test_fail",
                {"detail": result.detail},
                ("#b91c1c", "#f87171"),
            )
            self.settings_status_lbl.configure(
                text=self._tr("settings_test_fail", detail=result.detail),
                text_color=("#b91c1c", "#f87171"),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _format_api_error(self, error: ApiError) -> str:
        kwargs = dict(error.extra)
        kwargs.setdefault("detail", error.detail)
        if error.status_code is not None:
            kwargs.setdefault("status_code", error.status_code)
        key = f"err_{error.error_code}"
        return self._tr(key, **kwargs)

    def _schedule_ui(self, callback: Any) -> None:
        if not self._closing:
            try:
                self.after(0, callback)
            except Exception:  # noqa: BLE001
                pass

    def _on_close(self) -> None:
        self._closing = True
        self.destroy()


def run_smoke_test() -> int:
    """Instantiate the GUI briefly, test live SK/RU/EN switching, and exit cleanly."""
    app = LogisticsRAGApp()
    app.update()
    for lang in ("RU", "EN", "SK"):
        app.set_language(lang)
        app.update()
    app._select_tab("kb")
    app.update()
    app._select_tab("settings")
    app.update()
    app._select_tab("chat")
    app.update()
    app._on_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LogisticsRAGAgent Desktop Application")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify GUI initialization and live language switching, then exit.",
    )
    args = parser.parse_args(argv)
    if args.smoke_test:
        return run_smoke_test()

    app = LogisticsRAGApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())