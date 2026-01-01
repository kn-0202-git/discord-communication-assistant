# 議論の要約

このプロジェクトの設計に至った議論の要点を記録する。

---

## 2025-01-01: 初期要件定義

### 参加者
- 依頼者（ユーザー）
- Claude（9つの専門家視点）

### 議論の要点

#### 1. 背景・課題
- 現在WhatsAppで請負者とやり取りしている
- 過去のやり取りを忘れる
- 引き継ぎが大変
- 写真・動画が埋もれる
- 提出物管理が記憶頼み

#### 2. プラットフォーム選定
- WhatsApp → Bot不可で却下
- Telegram → 「怪しい」イメージで却下
- Slack → 履歴90日制限が懸念
- Discord → 採用（履歴無制限、Bot自由）

#### 3. 部屋構造の設計
- Workspace（最上位）= Discordサーバー = 請負者ごと
- Room（中の部屋）= Discordチャンネル = トピック/メンバーごと
- Workspace間は完全分離
- Room間は情報共有可能

#### 4. AI設計
- 複数プロバイダー対応（OpenAI, Anthropic, Google, Groq, ローカル）
- 機能ごとにAIを設定可能
- Workspace/Roomごとに上書き可能

#### 5. 開発環境
- Python + uv（パッケージ管理）
- ruff（リンター/フォーマッター）
- pre-commit（コミット前チェック）
- TDD（テスト駆動開発）
- macOS / Windows 両対応

#### 6. Phase分け
- Phase 1: MVP（メッセージ保存、要約、検索）
- Phase 2: 通話録音、Google Drive連携
- Phase 3: RAG、クラウド移行
- Phase 4: スケール対応

### 決定事項
- Discordを使用
- 複数AIプロバイダー対応
- uv + ruff + pre-commit
- 9つの専門家視点で開発

---

## 2025-01-01: Discord API調査

### 調査内容
- Discord APIの料金・制限・ポリシーを確認

### 結果

| 項目 | 結果 |
|------|------|
| API料金 | 無料 |
| Bot作成 | 無料 |
| メッセージ取得 | 可能 |
| 通話録音 | 可能（要告知） |
| データのAI学習利用 | 禁止 |

### 決定事項
- Discord APIを使った開発を進める
- データのAI学習利用は禁止（RAGは使用可）
- 録音は請負者に事前告知必須

---

## 2025-01-01: Claude Code運用設計

### 議論内容
- Claude Codeの効果的な運用方法を検討
- 参考記事を基に5つの型を取り入れ

### 採用した運用方法

1. カスタムスラッシュコマンド
   - /project:implement
   - /project:review
   - /project:test
   - /project:fix-issue
   - /project:refactor

2. サブエージェント
   - python-expert
   - security-reviewer
   - code-reviewer
   - qa-reviewer
   - discord-expert

3. プロンプト管理
   - docs/prompts/ に保存
   - 再利用可能なテンプレートとして管理

### 決定事項
- .claude/commands/ にカスタムコマンド配置
- .claude/agents/ にサブエージェント配置
- レビュー時は並列実行

---

## 2025-01-01: 専門家体制の確定

### 議論内容
- 当初8つの専門家視点で開発予定
- コードレビュアーの役割が不足していることを指摘

### 決定事項
- 9つの専門家体制に変更
  1. ソフトウェアエンジニア
  2. Python開発者
  3. コードレビュアー（追加）
  4. UI/UXデザイナー
  5. 化学系エンジニア（ドメインエキスパート）
  6. 教育者
  7. セキュリティエンジニア
  8. QAエンジニア
  9. AIエンジニア

---

（今後の議論を追記）
