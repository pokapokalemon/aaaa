from __future__ import annotations

from pathlib import Path
import subprocess
import pandas as pd

from .utils import first_existing_column


META_DATASET = "kaggle/meta-kaggle"
NEEDED_FILES = [
    "Competitions.csv",
    "ForumTopics.csv",
    "Kernels.csv",
    "KernelVersions.csv",
    "KernelVersionCompetitionSources.csv",
    "Users.csv",
]


class MetaKaggleClient:
    def __init__(self, base_dir: Path, use_kaggle_cli_for_meta_download: bool = True):
        self.base_dir = base_dir
        self.use_kaggle_cli_for_meta_download = use_kaggle_cli_for_meta_download
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def download_needed_files(self) -> None:
        missing = [x for x in NEEDED_FILES if not (self.base_dir / x).exists()]
        if not missing:
            return
        if not self.use_kaggle_cli_for_meta_download:
            raise RuntimeError(
                "Meta Kaggle CSV が不足しています。use_kaggle_cli_for_meta_download=false のため自動取得できません。"
            )
        for filename in missing:
            self._download_single_file(filename)

    def _download_single_file(self, filename: str) -> None:
        cmd = [
            "kaggle",
            "datasets",
            "download",
            "-d",
            META_DATASET,
            "-f",
            filename,
            "-p",
            str(self.base_dir),
            "--unzip",
            "-o",
        ]
        subprocess.run(cmd, check=True)

    def load_csv(self, filename: str) -> pd.DataFrame:
        path = self.base_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Meta Kaggle file not found: {path}")
        return pd.read_csv(path, low_memory=False)

    def get_competition_row(self, competition_slug: str) -> pd.Series:
        comps = self.load_csv("Competitions.csv")
        slug_col = first_existing_column(list(comps.columns), ["Slug", "TitleSlug", "UrlSlug"])
        if slug_col is None:
            raise RuntimeError("Competitions.csv に slug 列が見つかりません。")
        match = comps[comps[slug_col].astype(str) == competition_slug]
        if match.empty:
            raise RuntimeError(f"Competition slug not found in Meta Kaggle: {competition_slug}")
        return match.iloc[0]

    def get_competition_ids(self, competition_slug: str) -> tuple[int, int | None]:
        row = self.get_competition_row(competition_slug)
        comp_id_col = first_existing_column(list(row.index), ["Id", "CompetitionId"])
        forum_id_col = first_existing_column(list(row.index), ["ForumId"])
        comp_id = int(row[comp_id_col])
        forum_id = None if forum_id_col is None or pd.isna(row[forum_id_col]) else int(row[forum_id_col])
        return comp_id, forum_id

    def get_discussions(self, competition_slug: str) -> pd.DataFrame:
        _, forum_id = self.get_competition_ids(competition_slug)
        if forum_id is None:
            return pd.DataFrame(columns=["topic_id", "title", "author", "created_at", "score", "url"])

        topics = self.load_csv("ForumTopics.csv")
        users = self.load_csv("Users.csv")

        topic_forum_col = first_existing_column(list(topics.columns), ["ForumId"])
        topic_id_col = first_existing_column(list(topics.columns), ["Id", "ForumTopicId"])
        title_col = first_existing_column(list(topics.columns), ["Title"])
        author_col = first_existing_column(list(topics.columns), ["AuthorUserId", "UserId", "CreatorUserId"])
        created_col = first_existing_column(list(topics.columns), ["DateCreated", "CreationDate", "CreateDate", "CreateTime"])
        score_col = first_existing_column(list(topics.columns), ["Score", "TotalVotes", "VoteCount"])

        user_id_col = first_existing_column(list(users.columns), ["Id", "UserId"])
        username_col = first_existing_column(list(users.columns), ["UserName", "Username", "DisplayName"])

        if None in [topic_forum_col, topic_id_col, title_col, author_col, created_col, user_id_col, username_col]:
            raise RuntimeError("ForumTopics / Users の必要列が見つかりません。")

        filtered = topics[topics[topic_forum_col].fillna(-1).astype(int) == int(forum_id)].copy()
        if filtered.empty:
            return pd.DataFrame(columns=["topic_id", "title", "author", "created_at", "score", "url"])

        merged = filtered.merge(
            users[[user_id_col, username_col]],
            left_on=author_col,
            right_on=user_id_col,
            how="left",
        )
        merged = merged.sort_values([created_col, topic_id_col], ascending=[False, False])
        keep_cols = [topic_id_col, title_col, username_col, created_col]
        if score_col:
            keep_cols.append(score_col)
        out = merged[keep_cols].copy()
        out.columns = [
            "topic_id",
            "title",
            "author",
            "created_at",
            *([] if not score_col else ["score"]),
        ]
        if "score" not in out.columns:
            out["score"] = None
        out["topic_id"] = out["topic_id"].astype(str)
        out["url"] = out["topic_id"].map(
            lambda x: f"https://www.kaggle.com/competitions/{competition_slug}/discussion/{int(x)}"
        )
        return out[["topic_id", "title", "author", "created_at", "score", "url"]]

    def get_code(self, competition_slug: str) -> pd.DataFrame:
        comp_id, _ = self.get_competition_ids(competition_slug)
        kernels = self.load_csv("Kernels.csv")
        versions = self.load_csv("KernelVersions.csv")
        kvcs = self.load_csv("KernelVersionCompetitionSources.csv")
        users = self.load_csv("Users.csv")

        kvcs_version_col = first_existing_column(list(kvcs.columns), ["KernelVersionId"])
        kvcs_comp_col = first_existing_column(list(kvcs.columns), ["CompetitionSourceId", "CompetitionId", "SourceCompetitionId"])
        if None in [kvcs_version_col, kvcs_comp_col]:
            raise RuntimeError("KernelVersionCompetitionSources.csv の必要列が見つかりません。")

        version_id_col = first_existing_column(list(versions.columns), ["Id", "KernelVersionId"])
        version_kernel_id_col = first_existing_column(list(versions.columns), ["KernelId"])
        version_title_col = first_existing_column(list(versions.columns), ["Title"])
        version_created_col = first_existing_column(list(versions.columns), ["ScriptVersionDateCreated", "DateCreated", "CreateDate"])

        kernel_id_col = first_existing_column(list(kernels.columns), ["Id", "KernelId"])
        kernel_author_col = first_existing_column(list(kernels.columns), ["AuthorUserId", "UserId"])
        kernel_slug_col = first_existing_column(list(kernels.columns), ["CurrentUrlSlug", "UrlSlug", "CurrentSlug"])

        user_id_col = first_existing_column(list(users.columns), ["Id", "UserId"])
        username_col = first_existing_column(list(users.columns), ["UserName", "Username", "DisplayName"])

        if None in [
            version_id_col,
            version_kernel_id_col,
            version_title_col,
            version_created_col,
            kernel_id_col,
            kernel_author_col,
            kernel_slug_col,
            user_id_col,
            username_col,
        ]:
            raise RuntimeError("KernelVersions / Kernels / Users の必要列が見つかりません。")

        kvcs_filtered = kvcs[kvcs[kvcs_comp_col].fillna(-1).astype(int) == int(comp_id)].copy()
        if kvcs_filtered.empty:
            return pd.DataFrame(columns=["kernel_version_id", "kernel_id", "title", "author", "created_at", "slug", "kernel_ref", "url"])

        merged = kvcs_filtered.merge(
            versions[[version_id_col, version_kernel_id_col, version_title_col, version_created_col]],
            left_on=kvcs_version_col,
            right_on=version_id_col,
            how="inner",
        ).merge(
            kernels[[kernel_id_col, kernel_author_col, kernel_slug_col]],
            left_on=version_kernel_id_col,
            right_on=kernel_id_col,
            how="inner",
        ).merge(
            users[[user_id_col, username_col]],
            left_on=kernel_author_col,
            right_on=user_id_col,
            how="left",
        )

        merged = merged.sort_values([version_created_col, version_id_col], ascending=[False, False])
        out = pd.DataFrame(
            {
                "kernel_version_id": merged[version_id_col].astype(str),
                "kernel_id": merged[version_kernel_id_col].astype(str),
                "title": merged[version_title_col].astype(str),
                "author": merged[username_col].astype(str),
                "created_at": merged[version_created_col].astype(str),
                "slug": merged[kernel_slug_col].astype(str),
            }
        )
        out["kernel_ref"] = out["author"] + "/" + out["slug"]
        out["url"] = out["kernel_ref"].map(lambda x: f"https://www.kaggle.com/code/{x}")
        return out[["kernel_version_id", "kernel_id", "title", "author", "created_at", "slug", "kernel_ref", "url"]]
