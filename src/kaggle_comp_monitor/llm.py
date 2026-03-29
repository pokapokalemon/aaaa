from __future__ import annotations

import os
import requests
from typing import Sequence

from .models import CodeItem, DiscussionItem
from .config import LLMConfig


class LLMAnalyzer:
    def __init__(self, config: LLMConfig):
        self.config = config

    def _post_chat(self, system_prompt: str, user_prompt: str) -> str:
        api_key = os.getenv(self.config.api_key_env, "")
        if not api_key:
            return "LLM は有効化されていますが、API キー環境変数が未設定です。"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(self.config.base_url, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def summarize(
        self,
        discussions: Sequence[DiscussionItem],
        code_items: Sequence[CodeItem],
        existing_code: str,
    ) -> tuple[str, str]:
        max_items = self.config.max_items_for_summary
        discussions = list(discussions)[:max_items]
        code_items = list(code_items)[:max_items]

        def pack_discussions() -> str:
            chunks = []
            for x in discussions:
                chunks.append(
                    f"[DISCUSSION] title={x.title}\nauthor={x.author}\nurl={x.url}\ntext=\n{x.raw_text[:12000]}"
                )
            return "\n\n".join(chunks)

        def pack_code() -> str:
            chunks = []
            for x in code_items:
                chunks.append(
                    f"[CODE] title={x.title}\nauthor={x.author}\nurl={x.url}\ntext=\n{x.raw_text[:16000]}"
                )
            return "\n\n".join(chunks)

        system_prompt = (
            "あなたは Kaggle コンペ支援の技術分析アシスタントです。"
            "新着 discussion / code を読み、実装知見・CV 方針・特徴量・高速化・後処理・注意点を抽出してください。"
            "誇張せず、実装反映に使える粒度で書いてください。"
        )
        user_prompt = f"""
対象の既存コード:
{existing_code[:30000]}

新着 Discussion:
{pack_discussions()}

新着 Code:
{pack_code()}

出力1: 重要ポイント要約
- 箇条書き
- 何が新しいか
- 実装価値
- リスク

出力2: 既存コードへの反映提案
- 具体的にどこを変えるか
- 追加すべき関数や特徴量
- CV / 推論 / 後処理の変更案
- 採用優先度
- パッチ案の擬似 diff
"""
        text = self._post_chat(system_prompt, user_prompt)
        parts = text.split("出力2:", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return text, ""
