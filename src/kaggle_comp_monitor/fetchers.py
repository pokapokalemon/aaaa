from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class KaggleContentFetcher:
    def __init__(self, timeout_sec: int = 40, user_agent: str = "Mozilla/5.0"):
        self.timeout_sec = timeout_sec
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _fetch_html(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _clean_text_from_html(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def fetch_discussion_text(self, url: str) -> str:
        html = self._fetch_html(url)
        return self._clean_text_from_html(html)

    def fetch_code_text(self, url: str) -> str:
        html = self._fetch_html(url)

        cleaned = self._clean_text_from_html(html)

        snippets: list[str] = []
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script"):
            script_text = script.string or script.get_text() or ""
            if not script_text:
                continue
            if "__NEXT_DATA__" in script_text or '"kernel"' in script_text or '"source"' in script_text:
                snippets.extend(self._extract_code_like_strings(script_text))

        chunks = [cleaned]
        if snippets:
            uniq = []
            seen = set()
            for s in snippets:
                s2 = s.strip()
                if len(s2) < 100:
                    continue
                if s2 in seen:
                    continue
                seen.add(s2)
                uniq.append(s2)

            if uniq:
                chunks.append(
                    "\n\n=== EXTRACTED_CODE_CANDIDATES ===\n"
                    + "\n\n---\n\n".join(uniq[:5])
                )

        return "".join(chunks)

    @staticmethod
    def _extract_code_like_strings(text: str) -> list[str]:
        found: list[str] = []

        patterns = [
            r'"source"\s*:\s*"((?:\\.|[^"\\]){80,})"',
            r'"content"\s*:\s*"((?:\\.|[^"\\]){80,})"',
            r'"code"\s*:\s*"((?:\\.|[^"\\]){80,})"',
        ]

        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.DOTALL):
                raw = m.group(1)
                try:
                    decoded = json.loads('"' + raw + '"')
                except Exception:
                    decoded = raw.encode("utf-8", errors="ignore").decode(
                        "unicode_escape", errors="ignore"
                    )
                found.append(decoded)

        return found

    @staticmethod
    def write_single_text_file(out_dir: Path, filename: str, text: str) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / filename
        p.write_text(text, encoding="utf-8")
        return [p]

    @staticmethod
    def read_files_text(paths: list[Path]) -> str:
        chunks: list[str] = []
        for p in paths:
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = p.read_text(encoding="utf-8", errors="ignore")
            chunks.append(f"\n\n### FILE: {p.name}\n{text}")
        return "".join(chunks).strip()
