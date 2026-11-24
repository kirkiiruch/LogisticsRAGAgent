# LogisticsRAGAgent

Practical MVP for the TUKE FBERG diploma thesis:
**"Návrh a implementácia RAG agenta v prostredí n8n"** *(Design and Implementation of a RAG Agent in the n8n Environment)*.

`LogisticsRAGAgent` is an autonomous logistics dispatcher assistant and document RAG system built on **n8n**, **Qdrant**, **Ollama** (`qwen2.5:3b` + `nomic-embed-text`), **Gmail OAuth2**, and a multilingual **CustomTkinter** Windows desktop client (`SK | RU | EN`).

---

## Architecture Overview

The repository supports **two deployment topologies**:

1. **Hybrid Cloud + Local AI (MVP Demo Stack)**
   - **n8n Orchestrator**: Docker Space on Hugging Face Spaces (`port 7860`, `docker/Dockerfile.hf_space`) backed by external PostgreSQL (Neon / Supabase).
   - **Vector Knowledge Base**: Qdrant Cloud (Free Tier 1 GB), collection `logistics_docs` (768 dimensions, Cosine similarity, payload metadata: `doc_type`, `category`, `filename`, `uploaded_at`).
   - **Local LLM & Embeddings**: Local Windows PC (`NVIDIA GeForce GTX 1650`, 4 GB VRAM) running Ollama (`qwen2.5:3b` for native tool calling + `nomic-embed-text` for 768-dim embeddings) exposed securely via `cloudflared` HTTPS tunnel (`docker/start_local_ollama.ps1`).
   - **Email Integration**: Gmail API (OAuth2) for searching receipts/messages, reading email details, and creating reply drafts.

2. **Full On-Premise Stack (Thesis Chapter 2.3 Reference Architecture)**
   - Complete isolated Docker Compose stack in `docker/docker-compose.onprem.yml` (`n8n`, `postgres`, `qdrant`, `ollama` / `ollama-gpu`) keeping 100% of corporate documents, emails, vectors, and LLM inference inside the internal network.

---

## Repository Structure

```text
LogisticsRAGAgent/
├── .env.example                           # Environment variable placeholders (no secrets)
├── .gitignore                             # Excludes .env, dist/, build/, local DB volumes
├── README.md                              # Project documentation
├── docker/
│   ├── Dockerfile.hf_space                # n8n image for Hugging Face Spaces (port 7860)
│   ├── docker-compose.onprem.yml          # Full on-premise stack (Thesis Ch. 2.3)
│   └── start_local_ollama.ps1             # Windows script: Ollama + Cloudflare Tunnel
├── n8n/
│   ├── 01_rag_ingestion.json              # RAG document ingestion workflow
│   ├── 02_logistics_rag_agent.json        # Supervisory AI Agent + Subagent workflow
│   └── sample_docs/
│       ├── interne_tarify_2026.txt
│       ├── smernica_cestovne_nahrad_limity.txt
│       └── sop_cmr_reklamacie.txt
├── desktop_app/
│   ├── requirements.txt
│   ├── main.py                            # CustomTkinter GUI (SK | RU | EN)
│   ├── i18n.py                            # 100% translated localization dictionaries
│   ├── api_client.py                      # HTTP client for n8n webhooks
│   ├── config_manager.py                  # Persists settings in %APPDATA%\LogisticsRAGAgent\config.json
│   └── build_exe.ps1                      # PyInstaller build -> dist/LogisticsRAGAgent.exe
└── tests/
    ├── test_n8n_workflows.py              # Validates n8n JSON schemas & AI connections
    ├── test_desktop_app.py                # Tests i18n parity, config persistence, API client
    └── test_security.py                   # Scans repository for leaked secrets or .env files
```

---

## n8n Workflows

### 1. `n8n/01_rag_ingestion.json` (`POST /webhook/rag-ingest`)
- Optional Bearer token verification via `$env.WEBHOOK_BEARER_TOKEN`.
- Accepts `multipart/form-data` binary uploads (`file` or `data` field for `.pdf`, `.txt`, `.docx`, `.csv`) and `application/json` (`text` payload).
- Splits text using `Recursive Character Text Splitter` (`chunkSize: 800`, `chunkOverlap: 120`) and `Default Data Loader`.
- Generates 768-dim vectors via `Embeddings Ollama` (`nomic-embed-text`) and inserts into Qdrant collection `logistics_docs` with payload metadata (`doc_type`, `category`, `filename`, `uploaded_at`).
- Returns JSON: `{"status": "ok", "filename", "category", "doc_type", "collection": "logistics_docs", "chunks_indexed", "uploaded_at", "message"}`.

### 2. `n8n/02_logistics_rag_agent.json` (`POST /webhook/logistics-agent`)
- Optional Bearer token verification via `$env.WEBHOOK_BEARER_TOKEN`.
- Fast-path `IF Healthcheck` (`action === "healthcheck"`) responding immediately with `{"status": "ok", "service": "LogisticsRAGAgent", "mode": "healthcheck"}`.
- Supervisory `AI Agent` (`@n8n/n8n-nodes-langchain.agent`, `Tools Agent` mode) connected to:
  - `Ollama Chat Model` (`qwen2.5:3b`) via `ai_languageModel`
  - `Simple Memory` (`memoryBufferWindow`, keyed by `sessionId`) via `ai_memory`
  - `Qdrant Vector Store` (`retrieve-as-tool`, `logistics_docs`, `Embeddings Ollama` `nomic-embed-text`) via `ai_tool`
  - `Gmail Search Tool`, `Gmail Read Message Tool`, `Gmail Create Draft Tool` (`gmailTool`) via `ai_tool`
  - `Invoice & Receipt Verification Subagent` (`@n8n/n8n-nodes-langchain.agentTool`) with its own `Ollama Chat Model` and `Qdrant Vector Store` (`retrieve-as-tool`) to cross-check carrier invoices and driver receipts against internal tariffs and travel allowance directives.
- Returns JSON: `{"status": "ok", "answer", "used_tools", "sources", "sessionId"}`.

---

## Quick Start

### A. Local Ollama + Cloudflare Tunnel (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File docker/start_local_ollama.ps1
```
Copy the printed `https://*.trycloudflare.com` URL into your Hugging Face Space `OLLAMA_BASE_URL` variable and update the Ollama credential inside n8n.

### B. Full On-Premise Docker Stack
```powershell
copy .env.example .env
# Edit .env with local passwords and encryption key
docker compose --env-file .env -f docker/docker-compose.onprem.yml up -d
```

### C. Desktop Application & `.exe` Build
```powershell
cd desktop_app
pip install -r requirements.txt
python main.py

# Or build standalone Windows executable:
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

### D. Automated Tests
```powershell
python -m pytest tests/ -v
```

---

## Slovenský prehľad (Kontext diplomovej práce TUKE FBERG)

Tento repozitár tvorí praktickú implementáciu k diplomovej práci **"Návrh a implementácia RAG agenta v prostredí n8n"** (TUKE FBERG). Projekt pokrýva všetkých 5 logistických scenárov z kapitoly 4 (príprava odpovedí na e-maily, kontrola dodávateľských faktúr, analýza pokladničných dokladov vodičov, poradenstvo pri plánovaní trás a sémantické vyhľadávanie v smerniciach a CMR manuáloch) s využitím uzlov **AI Agent (`Tools Agent`)**, **AI Agent Tool**, **Qdrant Vector Store**, **Simple Memory**, **Ollama Chat Model** (`qwen2.5:3b`) a **Embeddings Ollama** (`nomic-embed-text`).
