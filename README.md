# 日報（マネジメントシート）自動生成ツール

GitHub の当日 `commit message` と `PR タイトル` を取得し、日報を自動生成して `output.md` に保存する CLI ツールです。対話入力はありません。

## 構成

```text
.
├── code.py
├── run.ps1
├── requirements.txt
├── README.md
└── output.md
```

## 動作概要

- `--date` があればその日付を対象にする
- 未指定なら実行日のローカル日付を使う
- GitHub から当日分の commit と PR を取得する
- 取得できない場合は fallback 文で日報を自動生成する
- 実行後に `output.md` を保存して終了する

## 必要な環境変数

- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`

補助的に `GITHUB_REPOSITORY=owner/repo` も利用できます。

## 実行方法

PowerShell:

```powershell
.\run.ps1
```

日付指定:

```powershell
python code.py --date 2026-04-10
```

環境変数設定例:

```powershell
$env:GITHUB_TOKEN="your-token"
$env:GITHUB_OWNER="your-owner"
$env:GITHUB_REPO="your-repo"
python code.py --date 2026-04-10
```

## 出力フォーマット

以下の形式で `output.md` に保存します。

```text
日付：
今回の目標：

やること：
出来たこと：
出来なかったこと：
その理由：
達成度：

出欠：
3限：
4限：
5限：
6限：

気づき・反省・次回やること：
```

## 自動生成ルール

- 今回の目標:
  PR タイトル優先。なければ commit message。両方なければ fallback 文。
- やること:
  PR タイトル優先。なければ commit message。両方なければ fallback 文。
- 出来たこと:
  commit message を箇条書き。なければ fallback 文。
- 出来なかったこと:
  固定文を出力。
- その理由:
  固定文を出力。
- 達成度:
  commit 件数から `0-10` の整数で自動算出。
- 出欠:
  `3限` から `6限` まで固定で `出` を出力。
- 気づき・反省・次回やること:
  PR タイトル優先。なければ最新 commit message。両方なければ fallback 文。

## フォールバック

以下のケースでもクラッシュせずに `output.md` を生成します。

- `GITHUB_TOKEN` 未設定
- `GITHUB_OWNER` / `GITHUB_REPO` 未設定
- GitHub API エラー
- 対象日に commit / PR がない

## 非対応

- issue 連携
- Web UI
- DB
- 手動入力画面
- 高度な自然言語要約
