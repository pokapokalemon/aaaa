from __future__ import annotations

from pathlib import Path

from .models import RunResult
from .utils import write_json, write_text



def save_run_outputs(base_dir: Path, result: RunResult) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    write_json(base_dir / "report.json", result.to_dict())
    write_text(base_dir / "report.md", build_markdown_report(result))



def build_markdown_report(result: RunResult) -> str:
    lines: list[str] = []
    lines.append(f"# Kaggle Manual Increment Monitor Report\n")
    lines.append(f"- competition: `{result.competition_slug}`")
    lines.append(f"- started_at: `{result.started_at}`")
    lines.append(f"- finished_at: `{result.finished_at}`")
    lines.append(f"- new_discussions: **{len(result.new_discussions)}**")
    lines.append(f"- new_code: **{len(result.new_code)}**\n")

    lines.append("## New Discussions\n")
    if result.new_discussions:
        for x in result.new_discussions:
            lines.append(f"### {x.title}")
            lines.append(f"- author: {x.author}")
            lines.append(f"- created_at: {x.created_at}")
            lines.append(f"- url: {x.url}")
            lines.append(f"- score: {x.score}")
            lines.append("")
    else:
        lines.append("新着なし\n")

    lines.append("## New Code\n")
    if result.new_code:
        for x in result.new_code:
            lines.append(f"### {x.title}")
            lines.append(f"- author: {x.author}")
            lines.append(f"- created_at: {x.created_at}")
            lines.append(f"- url: {x.url}")
            lines.append(f"- kernel_ref: {x.kernel_ref}")
            lines.append("")
    else:
        lines.append("新着なし\n")

    lines.append("## LLM Summary\n")
    lines.append(result.llm_summary or "未生成\n")

    lines.append("## LLM Patch Suggestions\n")
    lines.append(result.llm_patch_suggestions or "未生成\n")

    return "\n".join(lines)
