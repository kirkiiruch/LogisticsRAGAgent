"""Security and repository hygiene tests for LogisticsRAGAgent."""

from __future__ import annotations

import re
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    "dist",
    "build",
    "__pycache__",
    ".git",
    ".pytest_cache",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI / generic sk- key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub classic PAT", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("Google OAuth client secret", re.compile(r"\bGOCSPX-[0-9A-Za-z_-]{12,}\b")),
    ("JWT token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE" + r" KEY-----")),
    (
        "Database URI with embedded password",
        re.compile(r"postgres(?:ql)?://[^:\s/]+:([^@\s$]{4,})@(?!localhost\b|postgres\b|example\.com\b)"),
    ),
    (
        "Personal Gmail address",
        re.compile(r"[A-Za-z0-9._%+-]+@" + r"gmail\.com\b", re.IGNORECASE),
    ),
]


def _iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in MVP_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(MVP_ROOT).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        files.append(path)
    return files


class TestSecurityHygiene:
    def test_no_committed_env_or_secret_files(self) -> None:
        forbidden_env_files: list[Path] = []
        forbidden_artifact_files: list[Path] = []
        for path in _iter_repo_files():
            name = path.name
            if name.startswith(".env") and name != ".env.example":
                forbidden_env_files.append(path)
            if name in {"config.json"} or name.endswith((".pem", ".key")):
                forbidden_artifact_files.append(path)
            if ("credentials" in name.lower() or "client_secret" in name.lower()) and name.endswith(".json"):
                forbidden_artifact_files.append(path)

        assert not forbidden_env_files, f"Committed .env file(s) found: {forbidden_env_files}"
        assert not forbidden_artifact_files, f"Forbidden secret/config file(s) found: {forbidden_artifact_files}"

    def test_no_hardcoded_secrets_or_personal_gmails(self) -> None:
        findings: list[str] = []
        for path in _iter_repo_files():
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rel = path.relative_to(MVP_ROOT).as_posix()
            for label, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    snippet = match.group(0)[:40]
                    findings.append(f"{rel}: {label} ({snippet}...)")

        assert not findings, "Potential secret leaks detected:\n" + "\n".join(findings)

    def test_gitignore_covers_sensitive_and_runtime_paths(self) -> None:
        gitignore_path = MVP_ROOT / ".gitignore"
        assert gitignore_path.exists()
        lines = {
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        required_entries = {
            ".env",
            ".env.*",
            "!.env.example",
            "desktop_app/build/",
            "desktop_app/dist/",
            "*.spec",
            "*credentials*.json",
            "*client_secret*.json",
            "n8n_data/",
            "qdrant_storage/",
            "ollama_data/",
            "postgres_data/",
        }
        missing = required_entries - lines
        assert not missing, f".gitignore missing required security/build rules: {sorted(missing)}"
