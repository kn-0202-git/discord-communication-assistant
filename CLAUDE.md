# CLAUDE.md - Discord Business Assistant

## このファイルの目的

Claude Codeがこのプロジェクトを理解し、一貫した開発を行うための指示書。

## プロジェクト概要

請負者とのチャット（Discord）をAIが監視・保存し、過去のやり取りを忘れない仕組みを作る。

詳細は以下を参照：
- ゴール・背景 → [docs/VISION.md](docs/VISION.md)
- 機能要件 → [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)
- 設計 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 開発者について

- コードを読むのは得意ではない
- テストで品質を担保する方針
- Claude Codeで開発を進める

## 技術スタック

| カテゴリ | ツール |
|----------|--------|
| 言語 | Python 3.11+ |
| パッケージ管理 | uv |
| フレームワーク | discord.py |
| DB | SQLite（ローカル）→ PostgreSQL（クラウド） |
| AI | OpenAI / Anthropic / Google / Groq / ローカルLLM |
| ストレージ | ローカル → Google Drive |
| リンター/フォーマッター | ruff |
| 型チェック | pyright |
| テスト | pytest |
| CI | GitHub Actions |
| コミット前チェック | pre-commit |

## 対応OS

- macOS
- Windows

両OSで動作するコードを書くこと。パス区切りは `pathlib.Path` を使用。

## コーディング規約

- 型ヒントを必ず使う
- docstringを書く（Google style）
- 関数は小さく、単一責任
- マジックナンバー禁止（定数化）
- パスは `pathlib.Path` を使用（OS互換）
- 抽象化を意識（AI/ストレージは差し替え可能に）
- ruffでフォーマット・リント

## テスト方針

- TDD（テスト先行）
- tests/ にミラー構成
- 1機能につき最低3テストケース（正常系・異常系・境界値）
- AI部分はモック化してテスト
- **テスト結果で品質がわかるようにする**

## やってはいけないこと

- Workspace AのデータをBに見せる処理
- APIキーのハードコード
- テストなしのPR
- 破壊的なDB操作（DELETE/DROP）を確認なしで実行
- OS依存のパス記述（`\` や `/` の直書き）
- AIプロバイダーの直接呼び出し（必ずrouterを経由）

## 開発フロー

1. GitHub Issueを確認
2. `feature/issue-{番号}` ブランチを作成
3. テストを先に書く
4. 実装
5. `uv run ruff check src/` でリントチェック
6. `uv run pytest tests/ -v` で全テスト通過確認
7. PRを作成

## コマンド
```bash
# 依存関係インストール
uv sync

# テスト実行
uv run pytest tests/ -v

# カバレッジ付き
uv run pytest tests/ --cov=src --cov-report=html

# リントチェック
uv run ruff check src/

# フォーマット
uv run ruff format src/

# 型チェック
uv run pyright src/

# Bot起動（ローカル）
uv run python -m src.main
```

## ファイル参照ルール

### 毎回必ず読むファイル
- CLAUDE.md（このファイル）

### 必要に応じて読むファイル

| 状況 | 参照するファイル |
|------|------------------|
| エラー・問題が起きた | docs/TROUBLESHOOTING.md |
| 設計の理由を知りたい | docs/DECISIONS.md |
| 過去の議論を確認したい | docs/DISCUSSION_SUMMARY.md |
| 機能の詳細を知りたい | docs/REQUIREMENTS.md |
| 実装方法を知りたい | docs/ARCHITECTURE.md |
| テスト方法を知りたい | docs/TEST_PLAN.md |
| 残課題を確認したい | docs/ISSUES_STATUS.md |
| 開発の経緯を知りたい | docs/DEVELOPMENT_LOG.md |
| 詳細な会話を確認したい | docs/CONVERSATION_LOG_*.md |

### ファイル更新タイミング

| ファイル | 更新タイミング |
|----------|----------------|
| TROUBLESHOOTING.md | 問題を解決した時 |
| DECISIONS.md | 重要な設計決定をした時 |
| DISCUSSION_SUMMARY.md | 大きな議論があった時 |
| REQUIREMENTS.md | 機能要件が変わった時 |
| ARCHITECTURE.md | 設計が変わった時 |
| TEST_PLAN.md | テストケースを追加した時 |
| DEVELOPMENT_PLAN.md | スケジュール・Issueが変わった時 |
| ISSUES_STATUS.md | 課題を発見・対応した時 |
| DEVELOPMENT_LOG.md | Issue完了時（試行錯誤・技術解説を記録） |
| CONVERSATION_LOG_*.md | Issue完了時（詳細な会話を記録） |

## 文書更新ルール

| 変更内容 | 更新する文書 |
|----------|--------------|
| 機能追加 | REQUIREMENTS.md → ARCHITECTURE.md → TEST_PLAN.md → DEVELOPMENT_PLAN.md |
| 技術スタック変更 | ARCHITECTURE.md → CLAUDE.md |
| AI設定変更 | config.yaml、必要ならARCHITECTURE.md |
| スケジュール変更 | DEVELOPMENT_PLAN.md |
| テスト追加 | TEST_PLAN.md |
| コーディング規約変更 | CLAUDE.md |

## 専門家視点

開発時は以下の9つの専門家視点で検討すること。

### 1. ソフトウェアエンジニア
- 設計の一貫性
- 保守性・拡張性
- 技術的負債の回避

### 2. Python開発者
- Pythonicなコード
- 適切なライブラリ選定
- パフォーマンス

### 3. コードレビュアー
- 可読性（変数名、関数名、コメント）
- コーディング規約の遵守
- バグ・エッジケースの発見
- パフォーマンスの問題
- 重複コードの排除
- リファクタリング提案

### 4. UI/UXデザイナー
- ユーザー体験
- コマンドの分かりやすさ
- エラーメッセージの親切さ

### 5. 化学系エンジニア（ドメインエキスパート）
- 業務要件との整合性
- 実務での使いやすさ
- 専門用語・ワークフロー

### 6. 教育者
- ドキュメントの分かりやすさ
- 学習コストの低減
- 段階的な説明

### 7. セキュリティエンジニア
- 権限分離の徹底
- シークレット管理
- データ保護

### 8. QAエンジニア
- テストカバレッジ
- エッジケースの考慮
- 品質基準の維持

### 9. AIエンジニア
- LLM選定・比較
- プロンプト設計
- コスト最適化
- プロバイダー切り替えの設計

## Claude Code運用ルール

### カスタムスラッシュコマンド

`.claude/commands/` にカスタムコマンドを定義。`/project:{コマンド名}` で呼び出す。

| コマンド | 用途 |
|----------|------|
| `/project:implement` | 機能実装を依頼 |
| `/project:review` | コードレビューを依頼（サブエージェント並列実行） |
| `/project:test` | テスト作成を依頼 |
| `/project:fix-issue` | GitHub Issue修正を依頼 |
| `/project:refactor` | リファクタリングを依頼 |

### サブエージェント

`.claude/agents/` に専門エージェントを定義。レビュー時に並列実行される。

| エージェント | 観点 |
|--------------|------|
| python-expert | Pythonのベストプラクティス、パフォーマンス |
| security-reviewer | セキュリティ、権限分離、データ保護 |
| code-reviewer | 可読性、保守性、コーディング規約 |
| qa-reviewer | テストカバレッジ、エッジケース、品質 |
| discord-expert | Discord API、Bot設計、レート制限 |

### プロンプト管理

- 重要なプロンプトは `docs/prompts/` に保存
- 再利用可能なテンプレートとして管理
- プロンプトは知的財産として扱う

### 運用のポイント

1. **目標設計に集中**：「What（何を）」を明確にする。「How（どのように）」はClaudeに任せる
2. **CLAUDE.mdを育てる**：`#` キーで情報を追加し、継続的に改善
3. **レビューを標準化**：カスタムコマンドでレビュー品質を一定に保つ
4. **トークン消費に注意**：サブエージェント並列実行はSonnetモード推奨
