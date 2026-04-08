from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


OUTPUT_FILE = "output.md"
DEFAULT_COMMIT_FALLBACK = [
    "GitHub連携なしの手入力フローを確認",
    "日報テンプレートを生成するCLIを実装",
]


@dataclass
class GitHubMaterials:
    commit_messages: list[str]
    source: str


def prompt_text(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_with_preview(label: str, preview: str, default: str = "") -> str:
    if preview:
        print(f"{label}候補:")
        print(preview)
    value = input(f"{label}: ").strip()
    return value or default


def prompt_attendance() -> dict[str, str]:
    print("出欠を入力してください。")
    result = {}
    for period in ("3限", "4限", "5限", "6限"):
        result[period] = prompt_text(period, "出席")
    return result


def normalize_items(items: Iterable[str]) -> list[str]:
    result = []
    for item in items:
        text = item.strip()
        if text and text not in result:
            result.append(text)
    return result


def bullet_block(items: list[str], empty_text: str = "未入力") -> str:
    if not items:
        return empty_text
    return "\n".join(f"- {item}" for item in items)


def iso_day_bounds(target_day: date) -> tuple[str, str]:
    start_local = datetime.combine(target_day, datetime.min.time(), tzinfo=timezone.utc)
    end_local = start_local + timedelta(days=1)
    return start_local.isoformat().replace("+00:00", "Z"), end_local.isoformat().replace("+00:00", "Z")


def github_headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "nippou-cli"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def http_get_json(url: str, headers: dict[str, str]) -> dict:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_materials(target_day: date, owner: str, repo: str, token: str | None) -> GitHubMaterials:
    start, end = iso_day_bounds(target_day)
    headers = github_headers(token)

    commits_url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits"
        f"?since={start}&until={end}&per_page=100"
    )

    commit_messages: list[str] = []

    try:
        commit_data = http_get_json(commits_url, headers)
        if isinstance(commit_data, list):
            commit_messages = normalize_items(
                item.get("commit", {}).get("message", "").splitlines()[0]
                for item in commit_data
                if isinstance(item, dict)
            )
    except (URLError, HTTPError, TimeoutError, ValueError, KeyError, IndexError):
        commit_messages = []

    source = "github"
    if not commit_messages:
        source = "fallback"
        commit_messages = DEFAULT_COMMIT_FALLBACK[:]

    return GitHubMaterials(commit_messages=commit_messages, source=source)


def build_suggestions(materials: GitHubMaterials) -> tuple[str, str]:
    todo = bullet_block(materials.commit_messages)
    done = bullet_block(materials.commit_messages)
    return todo, done


def build_report(data: dict[str, str], attendance: dict[str, str]) -> str:
    lines = [
        f"日付：{data['date']}",
        f"今回の目標：{data['goal']}",
        "",
        f"やること：",
        data["todo"],
        f"出来たこと：",
        data["done"],
        f"出来なかったこと：{data['not_done']}",
        f"その理由：{data['reason']}",
        f"達成度：{data['progress']}",
        "",
        "出欠：",
        f"3限：{attendance['3限']}",
        f"4限：{attendance['4限']}",
        f"5限：{attendance['5限']}",
        f"6限：{attendance['6限']}",
        "",
        f"気づき・反省・次回やること：",
        data["reflection"],
    ]
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="日報（マネジメントシート）入力支援ツール")
    parser.add_argument("--date", help="日報の日付 YYYY-MM-DD")
    parser.add_argument("--owner", help="GitHub owner")
    parser.add_argument("--repo", help="GitHub repository")
    parser.add_argument("--output", default=OUTPUT_FILE, help="出力先ファイル")
    return parser.parse_args()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    args = parse_args()
    today = date.today()
    target_date = date.fromisoformat(args.date) if args.date else today

    token = os.getenv("GITHUB_TOKEN")
    owner = args.owner or os.getenv("GITHUB_OWNER") or ""
    repo = args.repo or os.getenv("GITHUB_REPO") or ""
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if (not owner or not repo) and repository:
        parts = repository.split("/", 1)
        if len(parts) == 2:
            owner = owner or parts[0]
            repo = repo or parts[1]

    materials = GitHubMaterials(commit_messages=[], source="manual")
    if owner and repo and token:
        materials = fetch_github_materials(target_date, owner, repo, token)
    else:
        materials = GitHubMaterials(
            commit_messages=DEFAULT_COMMIT_FALLBACK[:],
            source="fallback",
        )

    todo_suggestion, done_suggestion = build_suggestions(materials)

    print("GitHub候補:")
    print(f"- 取得元: {materials.source}")
    print("- commit message:")
    print(bullet_block(materials.commit_messages))
    print("")

    data = {
        "date": prompt_text("日付", target_date.isoformat()),
        "goal": prompt_text("今回の目標"),
        "todo": prompt_with_preview("やること", todo_suggestion, todo_suggestion),
        "done": prompt_with_preview("出来たこと", done_suggestion, done_suggestion),
        "not_done": prompt_text("出来なかったこと"),
        "reason": prompt_text("その理由"),
        "progress": prompt_text("達成度"),
        "reflection": prompt_text("気づき・反省・次回やること"),
    }
    attendance = prompt_attendance()

    report = build_report(data, attendance)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8-sig")

    print("")
    print(report, end="")
    print(f"保存先: {output_path.resolve()}")


if __name__ == "__main__":
    main()
