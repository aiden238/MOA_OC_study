"""Schemas for the Week 12 self-updating wiki pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ManualWikiCandidateRequest(BaseModel):
    """Manual candidate submission for the wiki pipeline."""

    title: str
    content: str
    summary: str = ""
    category: str = "advanced"
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingWikiDocumentResponse(BaseModel):
    """Serializable pending wiki record."""

    pending_id: str
    title: str
    filename: str
    category: str
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    source_url: str | None = None
    confidence: float
    status: str
    created_at: str
    updated_at: str
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WikiStatusResponse(BaseModel):
    """Aggregate wiki update status."""

    pending_count: int = 0
    approved_count: int = 0
    last_updated: str | None = None
    latest_entries: list[dict[str, Any]] = Field(default_factory=list)
