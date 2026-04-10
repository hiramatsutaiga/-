from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


OUTPUT_FILE = "output.md"
DEFAULT_GOAL = "GitHub履歴をもとに日報を自動生成する"
DEFAULT_TODO_FALLBACK = [
    "GitHub連携なしの手入力フロー確認",
    "日報テンプレート生成CLIの確認",
]
DEFAULT_DONE_FALLBACK = [
    "実績データを取得できなかったため自動生成のみ実施",
]
DEFAULT_NOT_DONE = "GitHub履歴から未完了事項は判定できなかった"
DEFAULT_REASON = "GitHub上の履歴だけでは作業上の障害要因を特定できないため"
DEFAULT_REFLECTION = "GitHub履歴を活用した自動生成フローを継続確認する"


@dataclass
class GitHubMaterials:
    commit_messages: list[str]
    pr_titles: list[str]
    source: str


def normalize_items(items: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def bullet_block(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def local_day_bounds(target_day: date) -> tuple[str, str]:
    local_tz = datetime.now().astimezone().tzinfo or UTC
    start_local = datetime.combine(target_day, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(UTC)
    end_utc = end_local.astimezone(UTC)
    return start_utc.isoformat().replace("+00:00", "Z"), end_utc.isoformat().replace("+00:00", "Z")


def github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nippou-cli",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def http_get_json(url: str, headers: dict[str, str]) -> object:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_materials(target_day: date, owner: str, repo: str, token: str | None) -> GitHubMaterials:
    if not token or not owner or not repo:
        return GitHubMaterials(commit_messages=[], pr_titles=[], source="fallback")

    start, end = local_day_bounds(target_day)
    headers = github_headers(token)
    commits_url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits"
        f"?since={start}&until={end}&per_page=100"
    )
    prs_url = (
        "https://api.github.com/search/issues"
        f"?q={quote(f'repo:{owner}/{repo} is:pr created:{target_day.isoformat()}')}"
        "&per_page=20"
    )

    commit_messages: list[str] = []
    pr_titles: list[str] = []

    try:
        commit_data = http_get_json(commits_url, headers)
        if isinstance(commit_data, list):
            commit_messages = normalize_items(
                item.get("commit", {}).get("message", "").splitlines()[0]
                for item in commit_data
                if isinstance(item, dict) and item.get("commit")
            )
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError):
        commit_messages = []

    try:
        pr_data = http_get_json(prs_url, headers)
        if isinstance(pr_data, dict):
            pr_titles = normalize_items(
                item.get("title", "")
                for item in pr_data.get("items", [])
                if isinstance(item, dict)
            )
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        pr_titles = []

    source = "github" if commit_messages or pr_titles else "fallback"
    return GitHubMaterials(commit_messages=commit_messages, pr_titles=pr_titles, source=source)


def first_or_default(items: list[str], default: str) -> str:
    return items[0] if items else default


def build_goal(materials: GitHubMaterials) -> str:
    if materials.pr_titles:
        return f"{materials.pr_titles[0]} を進める"
    if materials.commit_messages:
        return f"{materials.commit_messages[0]} を進める"
    return DEFAULT_GOAL


def build_todo(materials: GitHubMaterials) -> str:
    if materials.pr_titles:
        return bullet_block(materials.pr_titles)
    if materials.commit_messages:
        return bullet_block(materials.commit_messages)
    return bullet_block(DEFAULT_TODO_FALLBACK)


def build_done(materials: GitHubMaterials) -> str:
    if materials.commit_messages:
        return bullet_block(materials.commit_messages)
    return bullet_block(DEFAULT_DONE_FALLBACK)


def build_progress(commit_count: int) -> int:
    if commit_count >= 3:
        return 8
    if commit_count == 2:
        return 7
    if commit_count == 1:
        return 6
    return 3


def build_reflection(materials: GitHubMaterials) -> str:
    if materials.pr_titles:
        return f"{materials.pr_titles[0]} を起点に、次回も作業のまとまりを意識して進める。"
    if materials.commit_messages:
        return f"{materials.commit_messages[0]} を踏まえて、次回も変更内容を継続して整理する。"
    return DEFAULT_REFLECTION


def build_report(target_date: date, materials: GitHubMaterials) -> str:
    lines = [
        f"日付：{target_date.isoformat()}",
        f"今回の目標：{build_goal(materials)}",
        "",
        "やること：",
        build_todo(materials),
        "出来たこと：",
        build_done(materials),
        f"出来なかったこと：{DEFAULT_NOT_DONE}",
        f"その理由：{DEFAULT_REASON}",
        f"達成度：{build_progress(len(materials.commit_messages))}",
        "",
        "出欠：",
        "3限：出",
        "4限：出",
        "5限：出",
        "6限：出",
        "",
        "気づき・反省・次回やること：",
        build_reflection(materials),
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="日報（マネジメントシート）自動生成ツール")
    parser.add_argument("--date", help="対象日 YYYY-MM-DD")
    parser.add_argument("--owner", help="GitHub owner")
    parser.add_argument("--repo", help="GitHub repository")
    parser.add_argument("--output", default=OUTPUT_FILE, help="出力先ファイル")
    return parser.parse_args()


def resolve_repository(args: argparse.Namespace) -> tuple[str, str]:
    owner = args.owner or os.getenv("GITHUB_OWNER") or ""
    repo = args.repo or os.getenv("GITHUB_REPO") or ""
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if (not owner or not repo) and repository:
        parts = repository.split("/", 1)
        if len(parts) == 2:
            owner = owner or parts[0]
            repo = repo or parts[1]
    return owner, repo


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    args = parse_args()
    target_date = date.fromisoformat(args.date) if args.date else datetime.now().astimezone().date()
    token = os.getenv("GITHUB_TOKEN")
    owner, repo = resolve_repository(args)

    materials = fetch_github_materials(target_date, owner, repo, token)
    report = build_report(target_date, materials)

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8-sig")

    print(report, end="")
    print(f"保存先: {output_path.resolve()}")


if __name__ == "__main__":
    main()
