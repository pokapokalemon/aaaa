from __future__ import annotations

from pathlib import Path
import json
import re


def first_existing_column(columns: list[str], candidates: list[str]) -> str | None:
    colset = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in colset:
            return colset[cand.lower()]
    return None



def slugify_filename(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    return text[:120].strip("-") or "item"



def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)



def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
