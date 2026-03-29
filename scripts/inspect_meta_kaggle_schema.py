from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

FILES = [
    "Competitions.csv",
    "Forums.csv",
    "ForumTopics.csv",
    "ForumMessages.csv",
    "Kernels.csv",
    "KernelVersions.csv",
    "KernelVersionCompetitionSources.csv",
    "Users.csv",
]


def main(base_dir: str) -> None:
    base = Path(base_dir)
    for name in FILES:
        path = base / name
        print(f"\n=== {name} ===")
        if not path.exists():
            print("missing")
            continue
        df = pd.read_csv(path, low_memory=False, nrows=5)
        print(f"sample_rows={len(df)}")
        print("columns:")
        for c in df.columns:
            print(f"  - {c}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="outputs/meta_kaggle")
    args = parser.parse_args()
    main(args.base_dir)
