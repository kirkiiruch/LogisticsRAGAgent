"""Automated structural, contract, and infra tests for LogisticsRAGAgent n8n workflows and Docker configs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

MVP_ROOT = Path(__file__).resolve().parent.parent
N8N_DIR = MVP_ROOT / "n8n"
SAMPLE_DOCS_DIR = N8N_DIR / "sample_docs"
DOCKER_DIR = MVP_ROOT / "docker"

INGESTION_WORKFLOW_PATH = N8N_DIR / "01_rag_ingestion.json"
AGENT_WORKFLOW_PATH = N8N_DIR / "02_logistics_rag_agent.json"

ALLOWED_PLACEHOLDER_CRED_IDS = {
    "QDRANT_CREDENTIAL_ID",
    "OLLAMA_CREDENTIAL_ID",
    "GMAIL_OAUTH2_CREDENTIAL_ID",
}


def _load_workflow(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing workflow file: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert isinstance(data.get("nodes"), list) and len(data["nodes"]) > 0
    assert isinstance(data.get("connections"), dict) and len(data["connections"]) > 0
    return data


def _nodes_by_name(wf: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["name"]: node for node in wf["nodes"]}


def _collect_connection_types(wf: dict[str, Any]) -> set[str]:
    types: set[str] = set()
    for conn_map in wf["connections"].values():
        types.update(conn_map.keys())
    return types


class TestIngestionWorkflow:
    @pytest.fixture(scope="class")
    @classmethod
    def wf(cls) -> dict[str, Any]:
        return _load_workflow(INGESTION_WORKFLOW_PATH)

    def test_webhook_and_response_mode(self, wf: dict[str, Any]) -> None:
        webhooks = [n for n in wf["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
        assert len(webhooks) == 1
        params = webhooks[0]["parameters"]
        assert params["httpMethod"] == "POST"
        assert params["path"] == "rag-ingest"
        assert params["responseMode"] == "responseNode"

    def test_connections_integrity_and_langchain_types(self, wf: dict[str, Any]) -> None:
        node_names = set(_nodes_by_name(wf).keys())
        for src_name, conn_map in wf["connections"].items():
            assert src_name in node_names, f"Unknown source node: {src_name}"
            for conn_type, branches in conn_map.items():
                for branch in branches:
                    for edge in branch:
                        assert edge["node"] in node_names, f"Unknown target node: {edge['node']}"
                        assert edge["type"] == conn_type

        conn_types = _collect_connection_types(wf)
        assert {"main", "ai_embedding", "ai_document", "ai_textSplitter"}.issubset(conn_types)

    def test_chunking_embedding_qdrant_and_metadata(self, wf: dict[str, Any]) -> None:
        splitters = [
            n
            for n in wf["nodes"]
            if n.get("type") == "@n8n/n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter"
        ]
        assert len(splitters) == 1
        assert splitters[0]["parameters"]["chunkSize"] == 800
        assert splitters[0]["parameters"]["chunkOverlap"] == 120

        embeddings = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.embeddingsOllama"
        ]
        assert len(embeddings) == 1
        assert embeddings[0]["parameters"]["model"] == "nomic-embed-text"

        qdrants = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.vectorStoreQdrant"
        ]
        assert len(qdrants) == 1
        assert qdrants[0]["parameters"]["mode"] == "insert"
        assert qdrants[0]["parameters"]["qdrantCollection"]["value"] == "logistics_docs"

        loaders = [
            n
            for n in wf["nodes"]
            if n.get("type") == "@n8n/n8n-nodes-langchain.documentDefaultDataLoader"
        ]
        assert len(loaders) == 1
        meta_values = loaders[0]["parameters"]["options"]["metadata"]["metadataValues"]
        meta_keys = {item["name"] for item in meta_values}
        assert meta_keys == {"doc_type", "category", "filename", "uploaded_at"}

    def test_supported_formats_and_bearer_guard(self, wf: dict[str, Any]) -> None:
        nodes = _nodes_by_name(wf)
        assert "Check Bearer Auth" in nodes
        assert "$env.WEBHOOK_BEARER_TOKEN" in nodes["Check Bearer Auth"]["parameters"]["jsCode"]
        assert "Prepare Input" in nodes
        prepare_code = nodes["Prepare Input"]["parameters"]["jsCode"]
        for ext in (".pdf", ".csv", ".docx", ".txt"):
            assert ext in prepare_code

        switch_node = nodes["Route Input Format"]
        output_keys = {r["outputKey"] for r in switch_node["parameters"]["rules"]["values"]}
        assert {"json", "pdf", "csv", "txt", "docx"}.issubset(output_keys)

    def test_no_hardcoded_credentials(self, wf: dict[str, Any]) -> None:
        for node in wf["nodes"]:
            for cred in node.get("credentials", {}).values():
                assert cred.get("id") in ALLOWED_PLACEHOLDER_CRED_IDS, (
                    f"Non-placeholder credential id in {node['name']}: {cred}"
                )


class TestAgentWorkflow:
    @pytest.fixture(scope="class")
    @classmethod
    def wf(cls) -> dict[str, Any]:
        return _load_workflow(AGENT_WORKFLOW_PATH)

    def test_webhook_and_healthcheck_fast_path(self, wf: dict[str, Any]) -> None:
        webhooks = [n for n in wf["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
        assert len(webhooks) == 1
        params = webhooks[0]["parameters"]
        assert params["httpMethod"] == "POST"
        assert params["path"] == "logistics-agent"
        assert params["responseMode"] == "responseNode"

        nodes = _nodes_by_name(wf)
        assert "IF Healthcheck" in nodes
        assert "Respond Healthcheck" in nodes
        hc_conds = nodes["IF Healthcheck"]["parameters"]["conditions"]["conditions"]
        assert any(c.get("rightValue") == "healthcheck" for c in hc_conds)

        hc_branches = wf["connections"]["IF Healthcheck"]["main"]
        assert hc_branches[0][0]["node"] == "Respond Healthcheck"
        assert hc_branches[1][0]["node"] == "Prepare Date & Context"
        assert wf["connections"]["Prepare Date & Context"]["main"][0][0]["node"] == "AI Agent"

        hc_body = nodes["Respond Healthcheck"]["parameters"]["responseBody"]
        assert "LogisticsRAGAgent" in hc_body
        assert "healthcheck" in hc_body

    def test_connections_integrity_and_langchain_types(self, wf: dict[str, Any]) -> None:
        node_names = set(_nodes_by_name(wf).keys())
        for src_name, conn_map in wf["connections"].items():
            assert src_name in node_names, f"Unknown source node: {src_name}"
            for conn_type, branches in conn_map.items():
                for branch in branches:
                    for edge in branch:
                        assert edge["node"] in node_names, f"Unknown target node: {edge['node']}"
                        assert edge["type"] == conn_type

        conn_types = _collect_connection_types(wf)
        assert {"main", "ai_languageModel", "ai_memory", "ai_tool", "ai_embedding"}.issubset(
            conn_types
        )

    def test_tools_agent_memory_models_and_tools(self, wf: dict[str, Any]) -> None:
        nodes = _nodes_by_name(wf)

        agent = nodes["AI Agent"]
        assert agent["type"] == "@n8n/n8n-nodes-langchain.agent"
        assert agent["parameters"]["agent"] == "toolsAgent"
        assert agent["parameters"]["options"]["returnIntermediateSteps"] is True

        llms = [n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.lmChatOllama"]
        assert len(llms) == 2
        for llm in llms:
            assert llm["parameters"]["model"] == "qwen2.5:3b"

        embeds = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.embeddingsOllama"
        ]
        assert len(embeds) == 2
        for embed in embeds:
            assert embed["parameters"]["model"] == "nomic-embed-text"

        memories = [
            n
            for n in wf["nodes"]
            if n.get("type") == "@n8n/n8n-nodes-langchain.memoryBufferWindow"
        ]
        assert len(memories) == 1
        assert memories[0]["parameters"]["sessionIdType"] == "customKey"
        assert "sessionId" in memories[0]["parameters"]["sessionKey"]

        qdrants = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.vectorStoreQdrant"
        ]
        assert len(qdrants) == 2
        for q in qdrants:
            assert q["parameters"]["mode"] == "retrieve-as-tool"
            assert q["parameters"]["qdrantCollection"]["value"] == "logistics_docs"

        gmail_tools = [n for n in wf["nodes"] if n.get("type") == "n8n-nodes-base.gmailTool"]
        assert len(gmail_tools) == 3
        gmail_ops = {(g["parameters"]["resource"], g["parameters"]["operation"]) for g in gmail_tools}
        assert gmail_ops == {("message", "getAll"), ("message", "get"), ("draft", "create")}

        subagents = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.agentTool"
        ]
        assert len(subagents) == 1
        sub_name = subagents[0]["name"]
        assert wf["connections"][sub_name]["ai_tool"][0][0]["node"] == "AI Agent"
        assert (
            wf["connections"]["Ollama Chat Model (Subagent)"]["ai_languageModel"][0][0]["node"]
            == sub_name
        )
        assert (
            wf["connections"]["Qdrant Vector Store (Subagent)"]["ai_tool"][0][0]["node"] == sub_name
        )
        assert wf["connections"]["Calculator (Subagent)"]["ai_tool"][0][0]["node"] == sub_name

    def test_context_optimization_time_awareness_and_math_tools(self, wf: dict[str, Any]) -> None:
        nodes = _nodes_by_name(wf)

        # Higher limits with compact context protections
        gmail_search = nodes["Gmail Search Tool"]
        assert gmail_search["parameters"]["limit"] >= 20
        assert gmail_search["parameters"]["simple"] is True

        for q_name in ("Qdrant Vector Store", "Qdrant Vector Store (Subagent)"):
            assert nodes[q_name]["parameters"]["topK"] >= 8

        assert nodes["Simple Memory"]["parameters"]["contextWindowLength"] <= 6
        assert nodes["AI Agent"]["parameters"]["options"]["maxIterations"] >= 10

        # Calendar / time context node & prompt injection
        date_node = nodes["Prepare Date & Context"]
        assert "Europe/Bratislava" in date_node["parameters"]["jsCode"]
        assert "calendar_context" in date_node["parameters"]["jsCode"]
        assert "calendar_context" in nodes["AI Agent"]["parameters"]["options"]["systemMessage"]
        assert (
            "calendar_context"
            in nodes["Invoice & Receipt Verification Subagent"]["parameters"]["options"]["systemMessage"]
        )

        # Calculator & Custom Code Tools wired to AI Agent / Subagent
        calcs = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.toolCalculator"
        ]
        assert len(calcs) == 2
        assert wf["connections"]["Calculator"]["ai_tool"][0][0]["node"] == "AI Agent"

        code_tools = [
            n for n in wf["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.toolCode"
        ]
        assert len(code_tools) == 2
        for ct in code_tools:
            assert ct["parameters"]["language"] == "jsCode"
            assert "query" in ct["parameters"]["jsCode"]
            assert "JSON.stringify" in ct["parameters"]["jsCode"]
            assert wf["connections"][ct["name"]]["ai_tool"][0][0]["node"] == "AI Agent"

    def test_no_hardcoded_credentials_or_instance_ids(self, wf: dict[str, Any]) -> None:
        raw_text = AGENT_WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "trycloudflare.com" not in raw_text
        assert "hf.space" not in raw_text
        for node in wf["nodes"]:
            for cred in node.get("credentials", {}).values():
                assert cred.get("id") in ALLOWED_PLACEHOLDER_CRED_IDS, (
                    f"Non-placeholder credential id in {node['name']}: {cred}"
                )


class TestSampleDocsAndInfra:
    def test_sample_documents_exist_and_cover_logistics_domains(self) -> None:
        expected_docs = {
            "interne_tarify_2026.txt": ["EUR/km", "stojné", "palet", "mýto", "ADR"],
            "smernica_cestovne_nahrad_limity.txt": ["DPH", "pohonné hmoty", "parkovné", "stravné"],
            "sop_cmr_reklamacie.txt": ["CMR", "vykládk", "reklamáci", "e-mail"],
        }
        for filename, keywords in expected_docs.items():
            path = SAMPLE_DOCS_DIR / filename
            assert path.exists(), f"Missing sample doc: {path}"
            content = path.read_text(encoding="utf-8")
            assert len(content.strip()) > 300
            lowered = content.lower()
            for kw in keywords:
                assert kw.lower() in lowered, f"Keyword '{kw}' missing in {filename}"

    def test_dockerfile_hf_space_static_config(self) -> None:
        dockerfile = DOCKER_DIR / "Dockerfile.hf_space"
        assert dockerfile.exists()
        content = dockerfile.read_text(encoding="utf-8")
        assert "FROM docker.n8n.io/n8nio/n8n:" in content
        assert "EXPOSE 7860" in content
        assert "N8N_PORT=7860" in content
        assert "DB_TYPE=postgresdb" in content
        assert "USER node" in content

    def test_docker_compose_onprem_yaml_and_services(self) -> None:
        compose_path = DOCKER_DIR / "docker-compose.onprem.yml"
        assert compose_path.exists()
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        services = data.get("services", {})
        for required_service in ("postgres", "qdrant", "ollama", "n8n"):
            assert required_service in services, f"Missing service: {required_service}"

        n8n_env = services["n8n"]["environment"]
        assert n8n_env["DB_TYPE"] == "postgresdb"
        assert n8n_env["OLLAMA_BASE_URL"] == "http://ollama:11434"
        assert n8n_env["QDRANT_URL"] == "http://qdrant:6333"
        assert "${DB_POSTGRESDB_PASSWORD" in str(n8n_env["DB_POSTGRESDB_PASSWORD"])
        assert "${N8N_ENCRYPTION_KEY" in str(n8n_env["N8N_ENCRYPTION_KEY"])
        assert str(services["ollama"]["environment"]["OLLAMA_CONTEXT_LENGTH"]).endswith("8192}")
        assert str(services["ollama-gpu"]["environment"]["OLLAMA_CONTEXT_LENGTH"]).endswith("8192}")

    def test_start_local_ollama_ps1_contents(self) -> None:
        script_path = DOCKER_DIR / "start_local_ollama.ps1"
        assert script_path.exists()
        content = script_path.read_text(encoding="utf-8")
        assert "qwen2.5:3b" in content
        assert "nomic-embed-text" in content
        assert "11434" in content
        assert "OLLAMA_CONTEXT_LENGTH" in content
        assert "8192" in content
        assert "cloudflared" in content
        assert "trycloudflare.com" in content

    def test_root_env_example_gitignore_and_readme(self) -> None:
        env_example = MVP_ROOT / ".env.example"
        assert env_example.exists()
        env_text = env_example.read_text(encoding="utf-8")
        for key in (
            "N8N_ENCRYPTION_KEY",
            "DB_POSTGRESDB_PASSWORD",
            "QDRANT_URL",
            "QDRANT_API_KEY",
            "OLLAMA_BASE_URL",
            "WEBHOOK_BEARER_TOKEN",
        ):
            assert re.search(rf"^{key}=", env_text, re.MULTILINE), f"Missing {key} in .env.example"

        gitignore = MVP_ROOT / ".gitignore"
        assert gitignore.exists()
        gi_lines = {
            line.strip()
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        for required_pattern in (".env", "desktop_app/build/", "desktop_app/dist/", "*.spec"):
            assert required_pattern in gi_lines, f"Missing {required_pattern} in .gitignore"

        readme = MVP_ROOT / "README.md"
        assert readme.exists()
        readme_text = readme.read_text(encoding="utf-8")
        assert "LogisticsRAGAgent" in readme_text
        assert "01_rag_ingestion.json" in readme_text
        assert "02_logistics_rag_agent.json" in readme_text
