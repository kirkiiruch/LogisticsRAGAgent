"""Multilingual translations (SK / RU / EN) for LogisticsRAGAgent desktop app."""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES: tuple[str, ...] = ("SK", "RU", "EN")
DEFAULT_LANGUAGE: str = "SK"

CATEGORY_KEYS: tuple[str, ...] = (
    "faktura",
    "pokladnicny_doklad",
    "zmluva",
    "smernica",
)

CATEGORY_TO_DOC_TYPE: dict[str, str] = {
    "faktura": "invoice",
    "pokladnicny_doklad": "receipt",
    "zmluva": "contract",
    "smernica": "guideline",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "SK": {
        "app_title": "LogisticsRAGAgent — Inteligentný asistent logistu",
        "brand_name": "LogisticsRAGAgent",
        "brand_subtitle": "n8n + Qdrant + Ollama",
        "sidebar_nav_label": "Navigácia",
        "nav_chat": "Chat s agentom",
        "nav_kb": "Znalostná báza",
        "nav_settings": "Nastavenia",
        "sidebar_lang_label": "Jazyk rozhrania",
        "sidebar_theme_label": "Téma vzhľadu",
        "theme_system": "Systém",
        "theme_dark": "Tmavá",
        "theme_light": "Svetlá",
        "sidebar_session_label": "ID relácie",
        "chat_header": "Chat s logistickým AI agentom",
        "chat_subheader": "Sémantické vyhľadávanie v Qdrant, kontrola e-mailov v Gmail a overovanie dokladov.",
        "chat_new_session": "Nová relácia",
        "chat_status_label": "Stav:",
        "status_idle": "Pripravený",
        "status_sending": "Odosiela sa požiadavka...",
        "status_done": "Hotovo",
        "status_error": "Chyba",
        "chat_presets_label": "Rýchle predvoľby:",
        "preset_gmail_label": "Gmail: doklad Google One",
        "preset_gmail_prompt": "Nájdi na Gmaili doklad o platbe za Google One a vypíš dátum, sumu a predmet správy.",
        "preset_qdrant_label": "Qdrant: interné tarify",
        "preset_qdrant_prompt": "Vyhľadaj v internej databáze Qdrant platné dopravné tarify, stojné a limity cestovných náhrad.",
        "preset_invoice_label": "Overiť faktúru / doklad",
        "preset_invoice_prompt": "Skontroluj poslednú faktúru alebo pokladničný doklad podľa interných smerníc a tarifných limitov v Qdrant.",
        "preset_cmr_label": "Návrh odpovede CMR",
        "preset_cmr_prompt": "Priprav návrh profesionálnej e-mailovej odpovede pre klienta k oneskoreniu vykládky a postupu pri CMR reklamácii.",
        "chat_welcome_title": "Vitajte v LogisticsRAGAgent",
        "chat_welcome_body": "Položte otázku ohľadom faktúr, pokladničných dokladov, interných taríf, smerníc alebo e-mailovej komunikácie.",
        "chat_input_placeholder": "Napíšte požiadavku pre logistického agenta...",
        "chat_send_btn": "Odoslať",
        "chat_clear_btn": "Vyčistiť chat",
        "chat_role_user": "Logista",
        "chat_role_agent": "AI Agent",
        "chat_role_system": "Systém",
        "chat_tools_label": "Použité nástroje:",
        "chat_sources_label": "Zdroje:",
        "chat_no_tools": "žiadne nástroje",
        "chat_session_reset_msg": "Bola spustená nová konverzačná relácia: {session_id}",
        "chat_empty_warning": "Zadajte prosím text správy pred odoslaním.",
        "kb_header": "Znalostná báza — nahrávanie do Qdrant",
        "kb_subheader": "Nahrajte interné dokumenty (PDF, TXT, DOCX, CSV) na rozdelenie a indexáciu do vektorovej databázy.",
        "kb_file_label": "Vybraný súbor:",
        "kb_no_file": "Žiadny súbor nie je vybraný",
        "kb_browse_btn": "Vybrať súbor...",
        "kb_file_dialog_title": "Vyberte dokument pre znalostnú bázu",
        "kb_file_types_label": "Podporované dokumenty",
        "kb_category_label": "Kategória dokumentu:",
        "cat_faktura": "Faktúra",
        "cat_pokladnicny_doklad": "Pokladničný doklad",
        "cat_zmluva": "Zmluva",
        "cat_smernica": "Smernica",
        "kb_upload_btn": "Nahrať do znalostnej bázy",
        "kb_uploading": "Nahrávam a indexujem dokument...",
        "kb_upload_success": "Dokument '{filename}' bol úspešne nahraný (chunkov: {chunks}).",
        "kb_select_file_first": "Najprv vyberte súbor na nahratie.",
        "kb_log_header": "Denník nahratých dokumentov",
        "kb_col_time": "Čas (UTC)",
        "kb_col_filename": "Názov súboru",
        "kb_col_category": "Kategória",
        "kb_col_status": "Stav / Chunky",
        "kb_log_empty": "Zatiaľ neboli nahraté žiadne dokumenty.",
        "settings_header": "Nastavenia pripojenia a aplikácie",
        "settings_subheader": "Konfigurácia webhookov n8n, zabezpečenia a časových limitov. Ukladá sa lokálne do AppData.",
        "settings_chat_url_label": "URL webhooku pre chat (n8n):",
        "settings_chat_url_placeholder": "http://localhost:5678/webhook/logistics-agent",
        "settings_ingest_url_label": "URL webhooku pre nahrávanie (n8n):",
        "settings_ingest_url_placeholder": "http://localhost:5678/webhook/rag-ingest",
        "settings_token_label": "Bearer token (voliteľný):",
        "settings_token_placeholder": "Zadajte prístupový token (ak je zapnutý v n8n)",
        "settings_show_token": "Zobraziť",
        "settings_hide_token": "Skryť",
        "settings_timeout_label": "Časový limit požiadavky (sekundy):",
        "settings_config_path_label": "Cesta ku konfigurácii:",
        "settings_save_btn": "Uložiť nastavenia",
        "settings_test_btn": "Otestovať pripojenie",
        "settings_testing": "Testujem pripojenie na webhook...",
        "settings_saved_ok": "Nastavenia boli úspešne uložené.",
        "settings_invalid_timeout": "Časový limit musí byť kladné celé číslo (minimálne 5 sekúnd).",
        "settings_invalid_url": "Zadajte platnú HTTP alebo HTTPS adresu webhooku.",
        "settings_test_ok": "Pripojenie úspešné (HTTP {status_code}): {detail}",
        "settings_test_fail": "Pripojenie zlyhalo: {detail}",
        "err_dialog_title": "Chyba aplikácie",
        "err_timeout": "Časový limit požiadavky vypršal ({timeout} s). Skontrolujte beh Ollama a n8n.",
        "err_connection_error": "Nepodarilo sa pripojiť k serveru n8n: {detail}",
        "err_http_error": "Server vrátil chybu HTTP {status_code}: {detail}",
        "err_invalid_json": "Server nevrátil platnú odpoveď vo formáte JSON: {detail}",
        "err_invalid_file": "Nepodporovaný formát súboru '{ext}'. Povolené sú: .pdf, .txt, .docx, .csv.",
        "err_file_not_found": "Vybraný súbor neexistuje alebo k nemu nie je prístup: {path}",
        "err_invalid_url": "Neplatná adresa URL webhooku: {url}",
        "err_empty_message": "Správa nemôže byť prázdna.",
        "err_unknown": "Nastala neočakávaná chyba: {detail}",
    },
    "RU": {
        "app_title": "LogisticsRAGAgent — Интеллектуальный помощник логиста",
        "brand_name": "LogisticsRAGAgent",
        "brand_subtitle": "n8n + Qdrant + Ollama",
        "sidebar_nav_label": "Навигация",
        "nav_chat": "Чат с агентом",
        "nav_kb": "База знаний",
        "nav_settings": "Настройки",
        "sidebar_lang_label": "Язык интерфейса",
        "sidebar_theme_label": "Тема оформления",
        "theme_system": "Системная",
        "theme_dark": "Тёмная",
        "theme_light": "Светлая",
        "sidebar_session_label": "ID сессии",
        "chat_header": "Чат с логистическим AI-агентом",
        "chat_subheader": "Семантический поиск в Qdrant, проверка писем в Gmail и сверка документов.",
        "chat_new_session": "Новая сессия",
        "chat_status_label": "Статус:",
        "status_idle": "Готов",
        "status_sending": "Отправка запроса...",
        "status_done": "Готово",
        "status_error": "Ошибка",
        "chat_presets_label": "Быстрые команды:",
        "preset_gmail_label": "Gmail: чек Google One",
        "preset_gmail_prompt": "Найди в Gmail квитанцию об оплате Google One и укажи дату, сумму и тему письма.",
        "preset_qdrant_label": "Qdrant: внутренние тарифы",
        "preset_qdrant_prompt": "Найди во внутренней базе Qdrant действующие транспортные тарифы, простой и лимиты командировочных расходов.",
        "preset_invoice_label": "Проверить счёт / чек",
        "preset_invoice_prompt": "Проверь последний счёт или кассовый чек на соответствие внутренним регламентам и тарифным лимитам в Qdrant.",
        "preset_cmr_label": "Черновик ответа CMR",
        "preset_cmr_prompt": "Подготовь черновик профессионального ответа клиенту по задержке выгрузки и порядку оформления рекламации CMR.",
        "chat_welcome_title": "Добро пожаловать в LogisticsRAGAgent",
        "chat_welcome_body": "Задайте вопрос по счетам, кассовым чекам, внутренним тарифам, регламентам или письмам.",
        "chat_input_placeholder": "Введите запрос для логистического агента...",
        "chat_send_btn": "Отправить",
        "chat_clear_btn": "Очистить чат",
        "chat_role_user": "Логист",
        "chat_role_agent": "AI-агент",
        "chat_role_system": "Система",
        "chat_tools_label": "Использованные инструменты:",
        "chat_sources_label": "Источники:",
        "chat_no_tools": "инструменты не использовались",
        "chat_session_reset_msg": "Запущена новая сессия диалога: {session_id}",
        "chat_empty_warning": "Пожалуйста, введите текст сообщения перед отправкой.",
        "kb_header": "База знаний — загрузка в Qdrant",
        "kb_subheader": "Загрузите внутренние документы (PDF, TXT, DOCX, CSV) для нарезки и индексации в векторную базу.",
        "kb_file_label": "Выбранный файл:",
        "kb_no_file": "Файл не выбран",
        "kb_browse_btn": "Выбрать файл...",
        "kb_file_dialog_title": "Выберите документ для базы знаний",
        "kb_file_types_label": "Поддерживаемые документы",
        "kb_category_label": "Категория документа:",
        "cat_faktura": "Счёт-фактура",
        "cat_pokladnicny_doklad": "Кассовый чек",
        "cat_zmluva": "Договор",
        "cat_smernica": "Инструкция",
        "kb_upload_btn": "Загрузить в базу знаний",
        "kb_uploading": "Загрузка и индексация документа...",
        "kb_upload_success": "Документ '{filename}' успешно загружен (фрагментов: {chunks}).",
        "kb_select_file_first": "Сначала выберите файл для загрузки.",
        "kb_log_header": "Журнал загруженных документов",
        "kb_col_time": "Время (UTC)",
        "kb_col_filename": "Имя файла",
        "kb_col_category": "Категория",
        "kb_col_status": "Статус / Фрагменты",
        "kb_log_empty": "Документы ещё не загружались.",
        "settings_header": "Настройки подключения и приложения",
        "settings_subheader": "Конфигурация вебхуков n8n, авторизации и таймаутов. Сохраняется локально в AppData.",
        "settings_chat_url_label": "URL вебхука чата (n8n):",
        "settings_chat_url_placeholder": "http://localhost:5678/webhook/logistics-agent",
        "settings_ingest_url_label": "URL вебхука загрузки (n8n):",
        "settings_ingest_url_placeholder": "http://localhost:5678/webhook/rag-ingest",
        "settings_token_label": "Bearer-токен (необязательно):",
        "settings_token_placeholder": "Введите токен доступа (если включён в n8n)",
        "settings_show_token": "Показать",
        "settings_hide_token": "Скрыть",
        "settings_timeout_label": "Таймаут запроса (секунды):",
        "settings_config_path_label": "Путь к файлу конфигурации:",
        "settings_save_btn": "Сохранить настройки",
        "settings_test_btn": "Проверить соединение",
        "settings_testing": "Проверка соединения с вебхуком...",
        "settings_saved_ok": "Настройки успешно сохранены.",
        "settings_invalid_timeout": "Таймаут должен быть целым положительным числом (минимум 5 секунд).",
        "settings_invalid_url": "Укажите корректный HTTP или HTTPS адрес вебхука.",
        "settings_test_ok": "Соединение успешно (HTTP {status_code}): {detail}",
        "settings_test_fail": "Ошибка соединения: {detail}",
        "err_dialog_title": "Ошибка приложения",
        "err_timeout": "Превышено время ожидания запроса ({timeout} с). Проверьте работу Ollama и n8n.",
        "err_connection_error": "Не удалось подключиться к серверу n8n: {detail}",
        "err_http_error": "Сервер вернул ошибку HTTP {status_code}: {detail}",
        "err_invalid_json": "Сервер вернул некорректный ответ JSON: {detail}",
        "err_invalid_file": "Неподдерживаемый формат файла '{ext}'. Разрешены: .pdf, .txt, .docx, .csv.",
        "err_file_not_found": "Выбранный файл не найден или недоступен: {path}",
        "err_invalid_url": "Некорректный URL вебхука: {url}",
        "err_empty_message": "Сообщение не может быть пустым.",
        "err_unknown": "Произошла непредвиденная ошибка: {detail}",
    },
    "EN": {
        "app_title": "LogisticsRAGAgent — Intelligent Logistics Assistant",
        "brand_name": "LogisticsRAGAgent",
        "brand_subtitle": "n8n + Qdrant + Ollama",
        "sidebar_nav_label": "Navigation",
        "nav_chat": "Agent Chat",
        "nav_kb": "Knowledge Base",
        "nav_settings": "Settings",
        "sidebar_lang_label": "Interface Language",
        "sidebar_theme_label": "Appearance Theme",
        "theme_system": "System",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "sidebar_session_label": "Session ID",
        "chat_header": "Logistics AI Agent Chat",
        "chat_subheader": "Semantic search in Qdrant, Gmail inbox lookup, and invoice/receipt verification.",
        "chat_new_session": "New Session",
        "chat_status_label": "Status:",
        "status_idle": "Idle",
        "status_sending": "Sending request...",
        "status_done": "Done",
        "status_error": "Error",
        "chat_presets_label": "Quick Presets:",
        "preset_gmail_label": "Gmail: Google One Receipt",
        "preset_gmail_prompt": "Search Gmail for a Google One payment receipt and list the date, amount, and email subject.",
        "preset_qdrant_label": "Qdrant: Internal Tariffs",
        "preset_qdrant_prompt": "Search the internal Qdrant knowledge base for current transport tariffs, detention fees, and travel allowance limits.",
        "preset_invoice_label": "Verify Invoice / Receipt",
        "preset_invoice_prompt": "Verify the latest supplier invoice or cash receipt against internal guidelines and tariff limits in Qdrant.",
        "preset_cmr_label": "Draft CMR Delay Reply",
        "preset_cmr_prompt": "Draft a professional email reply to a client regarding an unloading delay and the CMR claim procedure.",
        "chat_welcome_title": "Welcome to LogisticsRAGAgent",
        "chat_welcome_body": "Ask questions about invoices, cash receipts, internal tariffs, company guidelines, or email threads.",
        "chat_input_placeholder": "Enter a request for the logistics agent...",
        "chat_send_btn": "Send",
        "chat_clear_btn": "Clear Chat",
        "chat_role_user": "Dispatcher",
        "chat_role_agent": "AI Agent",
        "chat_role_system": "System",
        "chat_tools_label": "Used tools:",
        "chat_sources_label": "Sources:",
        "chat_no_tools": "no tools used",
        "chat_session_reset_msg": "Started a new conversation session: {session_id}",
        "chat_empty_warning": "Please enter a message before sending.",
        "kb_header": "Knowledge Base — Upload to Qdrant",
        "kb_subheader": "Upload internal documents (PDF, TXT, DOCX, CSV) for chunking and indexing into the vector store.",
        "kb_file_label": "Selected file:",
        "kb_no_file": "No file selected",
        "kb_browse_btn": "Browse File...",
        "kb_file_dialog_title": "Select a document for the knowledge base",
        "kb_file_types_label": "Supported documents",
        "kb_category_label": "Document category:",
        "cat_faktura": "Invoice",
        "cat_pokladnicny_doklad": "Cash Receipt",
        "cat_zmluva": "Contract",
        "cat_smernica": "Guideline",
        "kb_upload_btn": "Upload to Knowledge Base",
        "kb_uploading": "Uploading and indexing document...",
        "kb_upload_success": "Document '{filename}' uploaded successfully (chunks: {chunks}).",
        "kb_select_file_first": "Please select a file before uploading.",
        "kb_log_header": "Uploaded Documents Log",
        "kb_col_time": "Time (UTC)",
        "kb_col_filename": "Filename",
        "kb_col_category": "Category",
        "kb_col_status": "Status / Chunks",
        "kb_log_empty": "No documents uploaded yet.",
        "settings_header": "Connection & Application Settings",
        "settings_subheader": "Configure n8n webhook URLs, authentication, and timeouts. Stored locally in AppData.",
        "settings_chat_url_label": "Chat Webhook URL (n8n):",
        "settings_chat_url_placeholder": "http://localhost:5678/webhook/logistics-agent",
        "settings_ingest_url_label": "Ingestion Webhook URL (n8n):",
        "settings_ingest_url_placeholder": "http://localhost:5678/webhook/rag-ingest",
        "settings_token_label": "Bearer Token (optional):",
        "settings_token_placeholder": "Enter access token (if enabled in n8n)",
        "settings_show_token": "Show",
        "settings_hide_token": "Hide",
        "settings_timeout_label": "Request Timeout (seconds):",
        "settings_config_path_label": "Config File Path:",
        "settings_save_btn": "Save Settings",
        "settings_test_btn": "Test Connection",
        "settings_testing": "Testing webhook connection...",
        "settings_saved_ok": "Settings saved successfully.",
        "settings_invalid_timeout": "Timeout must be a positive integer (minimum 5 seconds).",
        "settings_invalid_url": "Please enter a valid HTTP or HTTPS webhook URL.",
        "settings_test_ok": "Connection successful (HTTP {status_code}): {detail}",
        "settings_test_fail": "Connection failed: {detail}",
        "err_dialog_title": "Application Error",
        "err_timeout": "Request timed out after {timeout} s. Check that Ollama and n8n are running.",
        "err_connection_error": "Could not connect to n8n server: {detail}",
        "err_http_error": "Server returned HTTP error {status_code}: {detail}",
        "err_invalid_json": "Server did not return valid JSON: {detail}",
        "err_invalid_file": "Unsupported file format '{ext}'. Allowed: .pdf, .txt, .docx, .csv.",
        "err_file_not_found": "Selected file does not exist or is inaccessible: {path}",
        "err_invalid_url": "Invalid webhook URL: {url}",
        "err_empty_message": "Message cannot be empty.",
        "err_unknown": "An unexpected error occurred: {detail}",
    },
}


def normalize_language(lang: str | None) -> str:
    """Normalize a language code to one of SUPPORTED_LANGUAGES."""
    if not lang:
        return DEFAULT_LANGUAGE
    upper = str(lang).strip().upper()
    if upper in SUPPORTED_LANGUAGES:
        return upper
    return DEFAULT_LANGUAGE


def t(lang: str | None, key: str, **kwargs: Any) -> str:
    """Translate a key into the requested language with optional format arguments."""
    resolved = normalize_language(lang)
    table = TRANSLATIONS.get(resolved, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = table.get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template


def get_category_options(lang: str | None) -> list[str]:
    """Return localized category dropdown labels in canonical order."""
    return [t(lang, f"cat_{cat_key}") for cat_key in CATEGORY_KEYS]


def get_category_key(lang: str | None, display_label: str) -> str:
    """Map a localized category label (in any supported language) back to its canonical key."""
    cleaned = str(display_label).strip()
    if cleaned in CATEGORY_KEYS:
        return cleaned
    for check_lang in (normalize_language(lang), *SUPPORTED_LANGUAGES):
        for cat_key in CATEGORY_KEYS:
            if t(check_lang, f"cat_{cat_key}") == cleaned:
                return cat_key
    return CATEGORY_KEYS[0]


def get_category_label(lang: str | None, category_key: str) -> str:
    """Return localized label for a canonical category key."""
    if category_key not in CATEGORY_KEYS:
        return category_key
    return t(lang, f"cat_{category_key}")


class Translator:
    """Stateful translator helper bound to an active language."""

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = normalize_language(language)

    def set_language(self, language: str) -> str:
        self.language = normalize_language(language)
        return self.language

    def get(self, key: str, **kwargs: Any) -> str:
        return t(self.language, key, **kwargs)

    def __call__(self, key: str, **kwargs: Any) -> str:
        return self.get(key, **kwargs)