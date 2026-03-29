from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import yaml


def normalize_competition_slug(value: str) -> str:
    value = str(value).strip().strip('/')
    m = re.search(r"kaggle\.com/competitions/([^/?#]+)", value)
    if m:
        return m.group(1)
    return value


@dataclass
class LLMConfig:
    enabled: bool = False
    base_url: str = "https://api.openai.com/v1/chat/completions"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    max_items_for_summary: int = 8
    existing_code_path: str = ""


@dataclass
class AppConfig:
    competition_slug: str
    outputs_dir: Path
    meta_kaggle_dir: Path
    state_db_path: Path
    request_timeout_sec: int
    user_agent: str
    use_kaggle_cli_for_meta_download: bool
    llm: LLMConfig


def load_config(path: str | Path) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    comp = raw.get("competition") or raw.get("competition_slug")
    if not comp:
        raise ValueError("config に competition または competition_slug が必要です。")

    llm = LLMConfig(**raw.get("llm", {}))
    return AppConfig(
        competition_slug=normalize_competition_slug(comp),
        outputs_dir=Path(raw.get("outputs_dir", "outputs")),
        meta_kaggle_dir=Path(raw.get("meta_kaggle_dir", "outputs/meta_kaggle")),
        state_db_path=Path(raw.get("state_db_path", "outputs/state/monitor.db")),
        request_timeout_sec=int(raw.get("request_timeout_sec", 40)),
        user_agent=raw.get(
            "user_agent", "Mozilla/5.0 (compatible; KaggleCompetitionDailyMonitor/1.1)"
        ),
        use_kaggle_cli_for_meta_download=bool(raw.get("use_kaggle_cli_for_meta_download", False)),
        llm=llm,
    )
