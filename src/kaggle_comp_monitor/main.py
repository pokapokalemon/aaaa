from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .fetchers import KaggleContentFetcher
from .llm import LLMAnalyzer
from .meta_kaggle import MetaKaggleClient
from .models import CodeItem, DiscussionItem, RunResult, now_iso
from .reporting import save_run_outputs
from .state import StateDB
from .utils import slugify_filename, write_json, write_text


def run(config_path: str) -> RunResult:
    cfg = load_config(config_path)
    started_at = now_iso()

    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    raw_disc_dir = cfg.outputs_dir / "raw" / "discussions"
    raw_code_dir = cfg.outputs_dir / "raw" / "code"
    snapshot_dir = cfg.outputs_dir / "snapshots"
    raw_disc_dir.mkdir(parents=True, exist_ok=True)
    raw_code_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    state = StateDB(cfg.state_db_path)
    meta = MetaKaggleClient(cfg.meta_kaggle_dir, cfg.use_kaggle_cli_for_meta_download)
    fetcher = KaggleContentFetcher(cfg.request_timeout_sec, cfg.user_agent)

    meta.download_needed_files()

    disc_df = meta.get_discussions(cfg.competition_slug)
    code_df = meta.get_code(cfg.competition_slug)

    write_json(
        snapshot_dir / "discussions_latest.json",
        disc_df.to_dict(orient="records"),
    )
    write_json(
        snapshot_dir / "code_latest.json",
        code_df.to_dict(orient="records"),
    )

    seen_discussion_ids = state.get_seen_ids("discussion")
    seen_code_ids = state.get_seen_ids("code")

    new_disc_rows = [row for row in disc_df.to_dict(orient="records") if str(row["topic_id"]) not in seen_discussion_ids]
    new_code_rows = [row for row in code_df.to_dict(orient="records") if str(row["kernel_version_id"]) not in seen_code_ids]

    new_discussions: list[DiscussionItem] = []
    new_code: list[CodeItem] = []

    for row in new_disc_rows:
        item_id = str(row["topic_id"])
        text = fetcher.fetch_discussion_text(row["url"])
        item = DiscussionItem(
            item_id=item_id,
            competition_slug=cfg.competition_slug,
            title=str(row["title"]),
            author=str(row["author"]),
            created_at=str(row["created_at"]),
            url=str(row["url"]),
            score=None if row.get("score") is None else int(row.get("score") or 0),
            raw_text=text,
        )
        fname = slugify_filename(f"{item_id}_{item.title}.txt")
        write_text(raw_disc_dir / fname, text)
        new_discussions.append(item)

    for row in new_code_rows:
        item_id = str(row["kernel_version_id"])
        text = fetcher.fetch_code_text(str(row["url"]))
        item_dir = raw_code_dir / slugify_filename(f"{item_id}_{row['author']}_{row['title']}")
        source_paths = fetcher.write_single_text_file(item_dir, "page_text.txt", text)
        item = CodeItem(
            item_id=item_id,
            competition_slug=cfg.competition_slug,
            title=str(row["title"]),
            author=str(row["author"]),
            created_at=str(row["created_at"]),
            url=str(row["url"]),
            kernel_ref=str(row["kernel_ref"]),
            source_files=[str(p) for p in source_paths],
            raw_text=text,
        )
        new_code.append(item)

    state.mark_many_seen(
        "discussion",
        [(x.item_id, x.created_at, x.url) for x in new_discussions],
    )
    state.mark_many_seen(
        "code",
        [(x.item_id, x.created_at, x.url) for x in new_code],
    )

    llm_summary = ""
    llm_patch_suggestions = ""
    if cfg.llm.enabled and (new_discussions or new_code):
        existing_code = ""
        if cfg.llm.existing_code_path:
            p = Path(cfg.llm.existing_code_path)
            if p.exists():
                existing_code = p.read_text(encoding="utf-8", errors="ignore")
        analyzer = LLMAnalyzer(cfg.llm)
        llm_summary, llm_patch_suggestions = analyzer.summarize(
            discussions=new_discussions,
            code_items=new_code,
            existing_code=existing_code,
        )
        write_text(cfg.outputs_dir / "llm_summary.md", llm_summary)
        write_text(cfg.outputs_dir / "llm_patch_suggestions.md", llm_patch_suggestions)

    finished_at = now_iso()
    result = RunResult(
        started_at=started_at,
        finished_at=finished_at,
        competition_slug=cfg.competition_slug,
        new_discussions=new_discussions,
        new_code=new_code,
        llm_summary=llm_summary,
        llm_patch_suggestions=llm_patch_suggestions,
    )
    save_run_outputs(cfg.outputs_dir, result)
    state.log_run(started_at, cfg.competition_slug, len(new_discussions), len(new_code))
    state.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    run(args.config)
