# 日報（マネジメントシート）入力支援ツール

最小構成の CLI ツールです。手入力を中心に、GitHub の commit message と PR タイトルを補助材料として取り込み、日報テキストを生成します。

## 最小ディレクトリ構成

```text
.
├── code.py
├── requirements.txt
├── README.md
└── output.md  # 実行時に生成
```

## 実装方針

- CLI で動作させる
- UI は作らない
- 外部依存は使わない
- GitHub 連携が未設定でも動くようにする
- まずは `output.md` に保存する

## 実行方法

### PowerShell から起動

```powershell
.\run.ps1
```

### 1. Python を起動

```bash
python code.py
```

### 2. 日付を指定して実行

```bash
python code.py --date 2026-04-08
```

### 3. GitHub 連携を使う場合

環境変数を設定します。

- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`

または、GitHub Actions 環境であれば `GITHUB_REPOSITORY` から `owner/repo` を読み取ります。

例:

```bash
$env:GITHUB_TOKEN="xxxxx"
$env:GITHUB_OWNER="your-name"
$env:GITHUB_REPO="your-repo"
python code.py --date 2026-04-08
```

## フォールバック動作

以下のどれかが未設定でも実行できます。

- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`

その場合はダミーの commit message と PR タイトルを使って入力を補助します。

## 出力

- 標準出力に日報テキストを表示
- `output.md` に保存

## できること

- 手入力で日報を埋める
- GitHub の commit message を候補として使う
- GitHub の PR タイトルを候補として使う
- GitHub 未設定時も動く

## 未実装

- 達成度の自動計算
- issue 連携
- DB 保存
- Web UI
