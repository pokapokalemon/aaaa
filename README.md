# Kaggle Competition Manual Increment Monitor v4

特定の Kaggle コンペについて、**ボタンを押した時だけ** Discussion / Code の増分を取得するプロジェクトです。

## 今回の修正点

前版の問題は、`created_at` や `head(max_items)` に依存していたことです。
Meta Kaggle は日次更新なので、**前回実行時刻ベース**では正しい増分判定になりません。

この版では次に変更しています。

- **時刻基準の増分判定を廃止**
- **件数上限 (`max_items`) を廃止**
- **対象コンペの Meta Kaggle スナップショット全件を毎回走査**
- **既知 ID 集合との差分だけを増分と判定**
- **今回見えた一覧を `outputs/snapshots/` に保存**

## 増分判定のしかた

増分判定は次です。

- Discussion: `topic_id`
- Code: `kernel_version_id`

毎回、対象コンペの一覧を Meta Kaggle から**全件**読みます。
その上で、SQLite の `seen_items` に存在しない ID だけを新着とみなします。

つまり判定は

- 前回実行時刻
- 投稿時刻

ではなく、

- **今回の Meta Kaggle スナップショットにある ID**
- **過去に一度でも見たことがある ID**

の差分です。

## コンペ指定のしかた

`config/config.example.yml` の `competition:` に入れます。

```yaml
competition: "map-charting-student-math-misunderstandings"
competition: "titanic"
competition: "house-prices-advanced-regression-techniques"
competition: "https://www.kaggle.com/competitions/playground-series-s5e3"
competition: "https://www.kaggle.com/competitions/map-charting-student-math-misunderstandings"
```

要するに、**Kaggle のコンペ URL の末尾部分**を入れればよいです。

## 実行方式

- GitHub Actions の **手動実行 (`workflow_dispatch`) のみ**
- 定期実行なし
- public repository なら GitHub-hosted runner は無料で使えます

## どのファイルを置けばよいか

少なくとも次を `outputs/meta_kaggle/` に置く想定です。

- `Competitions.csv`
- `ForumTopics.csv`
- `Kernels.csv`
- `KernelVersions.csv`
- `KernelVersionCompetitionSources.csv`
- `Users.csv`

## 置いた CSV の構造確認

```bash
python scripts/inspect_meta_kaggle_schema.py --base-dir outputs/meta_kaggle
```

## 実行方法

### ローカル

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m kaggle_comp_monitor.main --config config/config.example.yml
```

### GitHub Actions で手動実行

1. GitHub に push
2. Actions タブを開く
3. `manual-kaggle-monitor` を選ぶ
4. `Run workflow` を押す
5. 必要なら `competition` に slug か URL を入れる

## GitHub Secrets

既定設定 (`use_kaggle_cli_for_meta_download: false`) なら Kaggle Secrets は不要です。

必要になるのは次の場合だけです。

- `KAGGLE_USERNAME` / `KAGGLE_KEY`
  - `use_kaggle_cli_for_meta_download: true` にした時だけ
- `OPENAI_API_KEY`
  - LLM 要約を有効化した時だけ

## 出力

- `outputs/report.md`
- `outputs/report.json`
- `outputs/raw/discussions/...`
- `outputs/raw/code/...`
- `outputs/snapshots/discussions_latest.json`
- `outputs/snapshots/code_latest.json`
- `outputs/state/monitor.db`

### 保存内容

- `outputs/state/monitor.db`
  - 取得済み ID の記録
- `outputs/snapshots/*.json`
  - 今回 Meta Kaggle から見えた全件一覧
- `outputs/raw/...`
  - 実際に取得した本文

## 補足

この版でも、Meta Kaggle 自体が日次更新である以上、**Kaggle 上に投稿された瞬間**は取れません。
ただし、Meta Kaggle に反映された後は、**前回実行時刻に関係なく、初めて見えた ID は増分として拾えます。**
