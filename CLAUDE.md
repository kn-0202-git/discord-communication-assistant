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
| 開発の経緯を知りたい | docs/DEVELOPMENT_LOG.md（Phase 2まで）、docs/DEVELOPMENT_LOG_PHASE{N}.md（Phase 3以降） |
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
| DEVELOPMENT_LOG.md / DEVELOPMENT_LOG_PHASE{N}.md | Issue完了時（試行錯誤・技術解説を記録）。Phase 2まではDEVELOPMENT_LOG.md、Phase 3以降はDEVELOPMENT_LOG_PHASE3.md等に記録 |
| CONVERSATION_LOG_*.md | Issue完了時（詳細な会話を記録） |

### 問題解決フロー

開発プロセス上の問題（文書作成忘れ、手順の曖昧さなど）が発生した場合：

```
問題発生
    ↓
① ISSUES_STATUS.md「プロセス改善」セクションに記録
   - 問題内容、発見日、優先度
    ↓
② 対応中は status を 🟡 に
    ↓
③ 解決したら:
   - TROUBLESHOOTING.md「開発プロセス」セクションに詳細を追加
   - DEVELOPMENT_LOG.md に記録
   - ISSUES_STATUS.md を 🟢 完了 に
```

## 文書更新ルール

| 変更内容 | 更新する文書 |
|----------|--------------|
| 機能追加 | REQUIREMENTS.md → ARCHITECTURE.md → TEST_PLAN.md → DEVELOPMENT_PLAN.md |
| 技術スタック変更 | ARCHITECTURE.md → CLAUDE.md |
| AI設定変更 | config.yaml、必要ならARCHITECTURE.md |
| スケジュール変更 | DEVELOPMENT_PLAN.md |
| テスト追加 | TEST_PLAN.md |
| コーディング規約変更 | CLAUDE.md |

## Issue完了時の必須作業

**⚠️ 重要: これらの作業は「mainにマージする前」に必ず実行すること！**

### 実行タイミング
```
コード実装完了
    ↓
全テスト通過
    ↓
ruff/pyright チェック通過
    ↓
ブランチにコミット・プッシュ
    ↓
✅ ここで必ず以下の作業を実行 ← 【忘れやすいポイント】
    ↓
mainにマージ
```

### 必須チェックリスト

**Claude Codeへの指示: Issue完了時は以下を必ず実行してください。ユーザーに指摘される前に自発的に実施すること。**

#### ステップ1: 開発記録を残す（必須）
- [ ] 開発記録ファイルに今回のIssueの記録を追記
  - **Phase 2まで**: `docs/DEVELOPMENT_LOG.md`
  - **Phase 3以降**: `docs/DEVELOPMENT_LOG_PHASE3.md`（新規Phaseごとにファイル作成）
- [ ] 含めるべき内容:
  - 開始時刻、目標
  - Step-by-Stepの実施内容（コマンド、結果、解説）
  - **発生したエラーと解決方法**（重要！）
  - 技術解説（初心者が理解できるレベル）
  - 学んだこと（3〜5点）
  - 次のステップ

#### ステップ2: 会話ログを残す（必須）
- [ ] `docs/CONVERSATION_LOG_ISSUE{番号}.md` を作成
- [ ] 含めるべき内容:
  - ユーザーとClaudeの会話を時系列で記録
  - 実装の流れと技術的なポイント
  - まとめ（実装の流れ、技術的なポイント、学んだこと、今後の改善）
- [ ] 会話ログの運用ルール:
  - 先頭に「要約」セクションを置く（結論を先に）
  - 「要約 + 詳細」の二層構成にする
  - 作成日/作成時点（後追い作成含む）を明記
  - 統合Issueは1ファイルあたり最大3〜4件を目安にする
  - 統合Issueの冒頭にクイックインデックスを付ける

#### ステップ3: 状態ファイルを更新（必須）
- [ ] `docs/DEVELOPMENT_PLAN.md`: Issueの状態を「未着手」→「✅完了」に変更
- [ ] `docs/ISSUES_STATUS.md`: 完了した課題に追加

#### ステップ4: 関連文書を更新（必要に応じて）
- [ ] 新しいファイルタイプを作成した場合 → CLAUDE.md参照テーブルに追加
- [ ] 設計決定があった場合 → DECISIONS.md
- [ ] 議論があった場合 → DISCUSSION_SUMMARY.md

#### ステップ5: 最終確認
- [ ] `git status` で作業が全てコミットされているか確認
- [ ] 上記のドキュメントファイルをコミット・プッシュ
- [ ] mainにマージ

### 再発防止のルール

**Claude Codeは以下を厳守すること:**

1. **マージ前に必ず確認**: 「Issue完了時の必須作業を実施しましたか？」とセルフチェック
2. **TodoListの活用**: Issue実装時のTodoに「DEVELOPMENT_LOG.md更新」「CONVERSATION_LOG作成」を必ず含める
3. **ユーザーに指摘される前に**: 自発的にこれらの作業を実施する
4. **判断に迷う場合のみユーザーに確認**: 基本は自動で実行
5. **コード変更がなくても記録は必須**: 議論・設計判断・リスク評価のみの場合も記録する
6. **Issue開始時に空ファイル作成**: `touch docs/CONVERSATION_LOG_ISSUE{N}.md` で先に作成しておく（忘れ防止）
7. **各Issue完了直後に記録**: 複数Issueをまとめて記録せず、1つ完了したらすぐ記録
8. **セッション終了前チェック**: 「記録ファイルは全て作成・更新したか？」を最終確認

### トークン節約ガイド

- 参照文書の固定セットを優先: CLAUDE.md / docs/DEVELOPMENT_PLAN.md / docs/ISSUES_STATUS.md
- 出力は原則5〜7項目以内に制限（詳細は要求時のみ拡張）
- 変更は差分だけ記載（全文再掲を避ける）
- テスト結果は合格件数のみ記載（失敗時のみ詳細）

### 過去の失敗事例

| 日付 | Issue | 失敗内容 | 原因 | 対策 |
|------|-------|----------|------|------|
| 2025-01-04 | #5 | 記録（DEVELOPMENT_LOG/CONVERSATION_LOG）を作成せずにコミット | 「コード変更なし=記録不要」と誤判断、TodoWriteを使わなかった | ルール5追加、TodoWrite必須化 |
| 2025-01-06 | #15-17 | Issue完了後にCONVERSATION_LOGを作成忘れ、DEVELOPMENT_LOGも遅延 | 実装に集中しTodoに記録作成を含めなかった、セッション終了前の確認を怠った | ルール6-8追加、Issue開始時の空ファイル作成を義務化 |

### テンプレート: Issueのチェックリスト

各Issue開始時に以下のTodoを設定すること:

```
1. ブランチ作成
2. 📝 空のCONVERSATION_LOG_ISSUE{N}.md を先に作成 ← 【新規】忘れ防止
3. テスト作成
4. 実装
5. テスト実行・修正
6. ruff/pyright チェック
7. コミット・プッシュ
8. 📝 開発記録ファイル更新（Phase 2: DEVELOPMENT_LOG.md / Phase 3以降: DEVELOPMENT_LOG_PHASE{N}.md） ← 必須（Issue完了直後に！）
9. 📝 CONVERSATION_LOG_ISSUE{N}.md 記入 ← 必須（Issue完了直後に！）
10. 📝 DEVELOPMENT_PLAN.md / ISSUES_STATUS.md 更新 ← 必須
11. mainにマージ
```

**重要**: ステップ8-10は「マージ前」に必ず実施。後回しにしない。

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

## Codexレビュー対応プロセス

Codex（または他のAIレビューツール）からのレビュー結果を受け取った際の対応プロセス。

### ファイル構成

| ファイル | 役割 |
|----------|------|
| `codex_review_md` | Codexとのコミュニケーション用ファイル |
| `codex_process.md` | Codexへの指示・プロセス定義（オプション） |

### 対応フロー

```
1. レビュー結果を受け取る
    ↓
2. codex_review_md を読み、指摘内容を理解
    ↓
3. 優先度順に対応
   - 高: 即座に対応
   - 中: 今回のセッションで対応
   - 低: ISSUES_STATUS.md に記録、後日対応
    ↓
4. 各指摘に対して:
   - コード修正
   - テスト実行（128テスト全パス確認）
   - pyright/ruff チェック
    ↓
5. codex_review_md に「対応結果」セクションを追記
    ↓
6. DEVELOPMENT_LOG.md に記録
    ↓
7. コミット・プッシュ
```

### codex_review_md 対応結果テンプレート

```markdown
---

## 対応結果

### 対応日: YYYY-MM-DD

### 対応者: Claude Code (Model名)

### 対応状況

| # | 問題 | 優先度 | 状態 | 対応内容 |
|---|------|--------|------|----------|
| 1 | 問題概要 | 高/中/低 | ✅ 完了 / 🟡 対応中 / ⏸️ 保留 | 具体的な対応内容 |

### Open Questions への回答

（質問への回答）

### Testing Gaps への対応

（テスト追加・修正内容）

### テスト結果

```
✅ XXX tests passed
✅ pyright: X errors
✅ ruff: All checks passed
```

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|

### コミット

- `ハッシュ`: コミットメッセージ
```

## セッション引き継ぎプロセス

長いチャットセッションを終了し、新しいセッションで継続する際のプロセス。

### 引き継ぎファイル

| ファイル | 役割 |
|----------|------|
| `docs/HANDOVER_YYYY-MM-DD.md` | その日の引き継ぎ文書 |

### 引き継ぎフロー

```
セッション終了時
    ↓
1. docs/HANDOVER_YYYY-MM-DD.md を作成
    ↓
2. 以下の内容を記載:
   - 今回のセッションでやったこと
   - 現在の状態（テスト結果、ブランチ状況）
   - 次にやるべきこと
   - 注意事項・コンテキスト
    ↓
3. コミット・プッシュ
    ↓
新しいセッション開始時
    ↓
4. 最新の HANDOVER_*.md を読む
    ↓
5. 必要に応じて DEVELOPMENT_LOG.md, ISSUES_STATUS.md も参照
    ↓
6. 作業を継続
```

### HANDOVER テンプレート

```markdown
# 引き継ぎ文書 - YYYY-MM-DD

## 今回のセッションでやったこと

- [ ] 実施内容1
- [ ] 実施内容2

## 現在の状態

### テスト結果
- テスト: XXX passed
- pyright: X errors
- ruff: X errors

### ブランチ状況
- 現在のブランチ: XXX
- main との差分: X commits ahead

### 未コミットの変更
- なし / あり（内容）

## 次にやるべきこと

1. タスク1
2. タスク2

## 注意事項・コンテキスト

- 特記事項
- 前提知識

## 関連ファイル

- docs/DEVELOPMENT_LOG.md の「YYYY-MM-DD: XXX」セクション
- docs/ISSUES_STATUS.md
```

### 引き継ぎの頻度

- **推奨**: 大きなタスク完了時、または1-2時間ごと
- **必須**: セッション終了時、コンテキストが長くなった時
