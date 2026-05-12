from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class CrawlLimits(BaseModel):
    max_pages: int = 50
    max_states: int = 200
    max_replay_requests: int = 200
    max_runtime_seconds: int = 1800
    concurrency: int = 2
    delay_ms: int = 500


class AuthConfig(BaseModel):
    required: bool = False
    persist_state: bool = False
    storage_state_path: str | None = None


class Guardrails(BaseModel):
    allowed_actions: list[str] = Field(default_factory=lambda: [
        "navigate", "filter", "sort", "paginate", "tab", "expand", "scroll", "download"
    ])
    blocked_label_patterns: list[str] = Field(default_factory=lambda: [
        "save", "submit", "delete", "remove", "archive", "purchase", "checkout", "invite",
        "upload", "send", "post", "publish", "approve", "reject", "cancel subscription",
        "change password", "create", "update", "edit", "import", "sync", "run job",
    ])
    allowed_selectors: list[str] = Field(default_factory=list)
    blocked_selectors: list[str] = Field(default_factory=list)


class SiteConfig(BaseModel):
    name: str
    url: HttpUrl
    auth: AuthConfig = Field(default_factory=AuthConfig)
    guardrails: Guardrails = Field(default_factory=Guardrails)
    limits: CrawlLimits = Field(default_factory=CrawlLimits)
    rebuild_mode: Literal["ask", "clone", "redesign", "skip"] = "ask"
    notes: str = ""


class CrawlEvent(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    url: str
    method: Literal["ui", "network", "system"]
    state_hash: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RunPaths(BaseModel):
    site: str
    run_id: str
    root: Path

    @property
    def duckdb_path(self) -> Path:
        return self.root / "catalog.duckdb"

    @property
    def parquet_root(self) -> Path:
        return self.root / "parquet"

    @property
    def json_root(self) -> Path:
        return self.root / "json"

    @property
    def screenshot_root(self) -> Path:
        return self.root / "screenshots"

    @property
    def design_root(self) -> Path:
        return self.root / "design"
