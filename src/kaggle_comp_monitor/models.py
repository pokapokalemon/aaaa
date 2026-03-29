from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class DiscussionItem:
    item_id: str
    competition_slug: str
    title: str
    author: str
    created_at: str
    url: str
    score: int | None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeItem:
    item_id: str
    competition_slug: str
    title: str
    author: str
    created_at: str
    url: str
    kernel_ref: str
    source_files: list[str]
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunResult:
    started_at: str
    finished_at: str
    competition_slug: str
    new_discussions: list[DiscussionItem]
    new_code: list[CodeItem]
    llm_summary: str = ""
    llm_patch_suggestions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "competition_slug": self.competition_slug,
            "new_discussions": [x.to_dict() for x in self.new_discussions],
            "new_code": [x.to_dict() for x in self.new_code],
            "llm_summary": self.llm_summary,
            "llm_patch_suggestions": self.llm_patch_suggestions,
        }


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
