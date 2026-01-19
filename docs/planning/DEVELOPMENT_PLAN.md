# 開発計画

## 目次

1. [概要](#1-概要) - 開発方針・最終ゴール
2. [Phase 1: 基盤構築](#2-phase-1-基盤構築完了) - DB・Bot・AI基盤
3. [Phase 2: 機能拡張](#3-phase-2-機能拡張進行中) - リマインダー・通話録音・クラウド
4. [Phase 3: RAG実装](#4-phase-3-rag実装未着手) - 資料AI質問
5. [Phase 4: スケール](#5-phase-4-スケール将来) - 50社対応
6. [運用ルール](#6-運用ルール) - GitHub・進捗確認・クラウド移行
7. [テンプレート](#7-テンプレート) - Issue・PR

---

## 1. 概要

### 1.1 開発方針

- テスト駆動開発（TDD）
- GitHub Issue駆動
- 1 Issue = 1 PR = 1 機能
- Claude Codeで実装補助
- 9つの専門家視点でレビュー

### 1.2 最終ゴール対応表

docs/specs/VISION.mdで定義した最終ゴールと、各Phaseでの対応状況:

| 最終ゴール | Phase 1 | Phase 2 | Phase 3 |
|------------|---------|---------|---------|
| G1: 全データ保存 | ✅ テキスト・添付 | 通話録音 | - |
| G2: 検索 | ✅ キーワード | - | ベクトル検索 |
| G3: 資料AI質問 | - | - | RAG |
| G4: リマインド | - | リマインダー | - |
| G5: 分離管理 | ✅ Workspace | - | - |
| G6: AI切替 | ✅ AIRouter | - | - |
| 可用性（24h稼働） | - | Oracle Cloud移行 | - |
| ファイルクラウド化 | - | Google Drive | - |

**結論**: Phase 2で24h稼働+クラウドファイル保存を実現。Phase 3でRAG追加し最終ゴール達成。

---

## 2. Phase 1: 基盤構築【完了】

### Week 1: 基盤構築

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #1 | DB設計・実装 | models.py、テスト通過 | ✅完了 |
| #2 | Discord Bot基盤 | 接続確認、イベント受信 | ✅完了 |
| #3 | メッセージ＋添付ファイル保存 | テスト通過、手動テスト成功 | ✅完了（#4統合） |

### Week 2: Bot機能

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #4 | 添付ファイル保存 | 写真・動画保存成功 | ✅完了（#3に統合） |
| #5 | Workspace/Room分離 | 構造通りに分離確認 | ✅完了（※1） |
| #6 | ローカルストレージ | ファイル保存・取得 | ✅完了（#3に統合） |

> **※1 Issue #5 注記**: ユニットテストで分離は確認済み。実機テスト（複数Discordサーバー）は Issue #14（試験運用準備）で実施予定。手戻りリスクは低いと評価（分離ロジックが単純、DBで強制分離）。

### Week 3: AI連携

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #7 | AI基盤（base, router） | 抽象化レイヤー完成 | ✅完了 |
| #8 | OpenAIプロバイダー | 接続・テスト通過 | ✅完了 |
| #9 | /summary実装 | 要約生成確認 | ✅完了 |
| #10 | /search実装 | 検索結果返却確認 | ✅完了 |

### Week 4: 統合・テスト

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #11 | 統合Room通知 | 通知送信成功 | ✅完了 |
| #12 | 他AIプロバイダー追加 | Anthropic, Google, Groq | ✅完了 |
| #13 | 統合テスト | 全機能連携確認 | ✅完了 |
| #14 | 試験運用準備 | 1社分のWorkspace構築、複数サーバー実機テスト（#5確認含む） | ✅完了 |

---

## 3. Phase 2: 機能拡張【進行中】

### 方針

1. 技術課題を先に解消（安定性確保）
2. リマインダー実装
3. 通話録音・文字起こし（ローカル機能を先に完成）
4. Google Drive連携（クラウドストレージ）
5. クラウド移行（Oracle Cloud Free Tier）

**順序の理由**: ローカルで全機能を確認してからクラウド移行する方が自然なフロー

**変更履歴**: 2026-01-17 Fly.ioが無料で使えないため、Oracle Cloud Free Tierに変更

### Step 1: 技術課題解消【完了】

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #15 | datetime.utcnow()修正 | datetime.now(UTC)に置換 | ✅完了 |
| #16 | GuildListenerテスト追加 | on_guild_join/removeテスト | ✅完了 |
| #17 | レート制限対策 | asyncio.Semaphore/クールダウン実装 | ✅完了 |

### Step 2: リマインダー機能【完了】

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #18 | Reminderテーブル | モデル・CRUD完了 | ✅完了 |
| #19 | /remind実装 | リマインダー登録 | ✅完了 |
| #20 | /reminders実装 | 一覧表示 | ✅完了 |
| #21 | 期限通知機能 | 統合Room自動通知 | ✅完了 |

### Step 3: 通話録音・文字起こし【完了】

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #30 | VoiceSession実装 | テーブル・CRUD完了 | ✅完了 |
| #31 | 通話録音機能 | /record on/off実装 | ✅完了 |
| #32 | Whisperプロバイダー | 文字起こしAPI連携 | ✅完了 |
| #33 | /transcribe実装 | 文字起こし結果表示 | ✅完了 |

### Step 4: Google Drive連携【完了】

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #26 | GoogleDriveStorage実装 | StorageProviderインターフェース準拠 | ✅完了 |
| #27 | OAuth設定 | 認証フロー完了 | ✅完了 |
| #28 | /saveコマンド | 手動アップロード成功 | ✅完了 |
| #29 | 自動アップロード | config設定で制御 | ✅完了 |

### Step 5: クラウド移行（Oracle Cloud Free Tier）【未着手】

> **変更履歴**: 2026-01-17 Fly.ioが無料で使えないため、Oracle Cloud Free Tierに変更

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #22 | Dockerfile作成 | ローカルでビルド成功 | ✅完了 |
| #23 | Oracle Cloud環境構築 | ARM A1インスタンス作成、Docker/Python設定 | 未着手 |
| #24 | OCI Block Volume対応 | SQLiteデータ永続化確認 | 未着手 |
| #25 | Oracle Cloudデプロイ | 本番稼働確認 | 未着手 |

### Step 5.5: Geminiレビュー対応（並行）

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| G1 | MAX_ATTACHMENT_SIZEのconfig化 | config.yaml反映 + テスト更新 | ✅完了 |
| G4 | 共有aiohttpセッション導入 | セッション再利用の確認 | ✅完了 |
| G2 | TokenCounter導入 | docs/specs/TOKEN_COUNTER.md作成 + 長文トリム確認 | ✅完了 |
| G3 | MagicMock autospec化 | 主要テストのautospec化完了 | ✅完了 |
| G8 | AIRouterテスト分割 | 選択ロジックの単体テスト追加 | ✅完了 |
| G6 | main.py初期化のファクトリ化 | エントリ分離とテスト容易性 | ✅完了 |
| G7 | MessageService抽出 | Handlerの責務分離 | ✅完了 |
| G5 | gitleaks導入方針決定 | 運用ルールに反映 | ✅完了 |

### Step 5.6: R-issue12-14レビュー対応（/search・/record・E2E）

| Issue | タスク | 完了条件 | 状態 |
|------|-------|--------|------|
| R-issue12 | /set_room_type追加 | 管理者コマンド追加、DB更新ヘルパー実装 | ✅完了 |
| R-issue12 | 統合Room運用ドキュメント | DISCORD_SETUPに手順追記 | ✅完了 |
| R-issue12 | /search検索範囲テスト | 通常/統合Roomの範囲テスト追加 | ✅完了 |
| R-issue13 | /recordメッセージ明確化 | プレースホルダー録音の注記を明記 | 未着手 |
| R-issue13 | voice_recording.enabled導入 | config.yaml追加、無効時は/record未登録 | 未着手 |
| R-issue13 | /recordフローのテスト追加 | VC未接続/開始/停止のケース追加 | 未着手 |
| R-issue14 | 最小E2Eスクリプト | tests/e2eに追加、環境変数で実行 | 未着手 |
| R-issue14 | E2E運用ドキュメント | テスト用Bot/Guild分離手順 | 未着手 |

### Step 5.7: R-issue17-19 Room管理改善

| Issue | タスク | 完了条件 | 状態 |
|------|-------|--------|------|
| R-issue17 | DBセッションエラーリカバリー | 全write操作にrollback追加 | ✅完了 |
| R-issue17 | Room名修正（channel_name） | MessageData/message_service更新 | ✅完了 |
| R-issue17 | Room名変更追従 | on_guild_channel_updateイベント | ✅完了 |
| R-issue17 | Room削除記録 | deleted_atフィールド追加 | ✅完了 |
| R-issue18 | テスト補完/リファクタ | テスト追加、型修正 | 未着手 |
| R-issue19 | Room名変更履歴マスタ | RoomNameHistoryテーブル追加 | 未着手 |
| R-issue19 | 削除済みRoom表示 | `#room名（削除済み）`形式 | 未着手 |

### Step 6: 統合・テスト【一部完了】

| Issue | タスク | 完了条件 | 状態 |
|-------|--------|----------|------|
| #34 | Phase 2統合テスト | 全機能連携確認 | ✅完了 |
| #35 | 本番運用テスト | 複数社で動作確認 | 未着手 |
| #40 | テスト実行環境整備 | uv/pytest実行確認 | 未着手 |

---

## 4. Phase 3: RAG実装【未着手】

### 目標

「資料にAI質問」(G3) - 自然言語検索と回答生成

### タスク一覧

| Issue | タスク | 内容 | 状態 |
|-------|--------|------|------|
| #36 | Documentテーブル | 資料メタデータ保存 | 未着手 |
| #37 | ベクトル化 | Embeddings保存・検索 | 未着手 |
| #38 | /ask実装 | RAG回答生成 | 未着手 |
| #39 | Phase 3統合テスト | 全機能確認 | 未着手 |

---

## 5. Phase 4: スケール【将来】

### 目標

50社対応、スケールアウト

### タスク一覧

| 機能 | 内容 | トリガー |
|------|------|----------|
| Bot分割 | 10サーバー/Bot制限対応 | 10社到達時 |
| PostgreSQL移行 | SQLite→本番DB | クラウド移行時 |
| シャーディング | 2,500サーバー対応 | 将来 |

---

## 6. 運用ルール

### 6.1 GitHub運用

#### ブランチ戦略

```
main              ← 本番（保護）
└── feature/issue-{n}  ← 機能開発
```

#### マージルール

- PRは全テスト通過必須
- ruff check通過必須
- セルフマージOK（1人開発のため）

### 6.2 進捗の確認方法

#### テスト結果で判断

```bash
uv run pytest tests/ -v
```

- `PASSED` が増えている → 順調
- `FAILED` がある → 修正必要

#### カバレッジで判断

```bash
uv run pytest tests/ --cov=src
```

- 70%以上 → OK
- 70%未満 → テスト追加

#### リントチェック

```bash
uv run ruff check src/
```

- エラー0 → OK
- エラーあり → 修正必要

### 6.3 クラウド移行計画

#### 結論

**Oracle Cloud Free Tier**（2026-01-17 変更）

> **変更履歴**: 2026-01-17 Fly.ioが無料で使えないことが判明。Oracle Cloud Free Tierに変更。

#### 選定理由

| 理由 | 詳細 |
|------|------|
| Discord Botと相性◎ | WebSocket常時接続OK、スリープしない |
| 永久無料 | 4 OCPU ARM、24GB RAM、200GB Storageが無料 |
| コード変更なし | 既存Dockerfileがそのまま動作 |
| 全機能維持 | スラッシュコマンド、音声録音、リアルタイム通知すべて対応 |

#### Oracle Cloud Free Tier スペック

| リソース | 無料枠 |
|----------|--------|
| Compute | ARM A1（4 OCPU、24GB RAM） |
| Block Volume | 200GB |
| Object Storage | 10GB |
| Network | 10TB/月 |

#### 代替案（フォールバック）

Oracle Cloudが使えない場合の代替：

| 選択肢 | 特徴 |
|--------|------|
| Railway | 月$5クレジット、使い切ると停止 |
| Render.com | 無料枠あるがスリープあり（15分） |
| GitHub Actions | バッチモードのみ（コマンド不可） |

#### Lambda構成案（常時接続なしの場合・検討メモ）

前提: 常時接続は不要、半日/日/週などの定期実行で十分。

**構成**

- EventBridge（cron）で定期起動
- LambdaでDiscord APIを呼び出し（Webhook/メッセージ送信/バッチ処理）
- 状態保存はDynamoDB or S3
- シークレットはSSM or Secrets Manager

**理由**

| 理由 | 詳細 |
|------|------|
| 常時接続不要に最適 | WebSocket/Gateway接続が不要なら、Lambdaが最小構成 |
| コスト最適化 | 実行時のみ課金され、アイドルコストを避けられる |
| 運用が軽い | サーバー管理不要、スケールも自動 |

**注意点**

- リアルタイム性が必要な機能（常時接続）には不向き
- Slash Commandの即時応答が必要ならAPI Gateway/Lambda構成を追加検討

**現在の方針**: いまは実装しない。要件が「定期実行で十分」と確定したら移行候補として検討する。

#### 実施タイミング

Phase 2 Step 4（Google Drive連携）完了後、Step 6（統合テスト）の前。Step 5と並行して「Geminiレビュー対応（Step 5.5）」を進める。

**変更履歴**:
- 2025-01-06 順序変更。ローカル機能を先に完成させてからクラウド移行する方針に変更。
- 2026-01-17 Fly.io → Oracle Cloud Free Tierに変更。

#### 実施内容

1. Oracle Cloud Free Tier登録
2. ARM A1インスタンス作成（Ubuntu 22.04）
3. Docker、Python 3.11インストール
4. Dockerコンテナビルド・起動
5. OCI Block Volumeでデータ永続化
6. systemdサービス設定（自動再起動）

---

## 7. テンプレート

### 7.1 Issueテンプレート

```markdown
## 概要
何を実装するか

## 完了条件
- [ ] テストが書かれている
- [ ] 実装が完了している
- [ ] 全テスト通過
- [ ] ruff check 通過
- [ ] ドキュメント更新（必要なら）

## 関連ドキュメント
- docs/specs/REQUIREMENTS.md: #{セクション番号}
- docs/specs/ARCHITECTURE.md: #{セクション番号}

## テストケース
- TEST_PLAN.md: {テストID}

## 専門家チェック
- [ ] ソフトウェアエンジニア視点
- [ ] Python視点
- [ ] セキュリティ視点
- [ ] QA視点
```

### 7.2 PRテンプレート

```markdown
## 対応Issue
closes #XX

## 変更内容
-

## テスト結果
uv run pytest tests/ -v の出力

## 確認事項
- [ ] 全テスト通過
- [ ] ruff check 通過
- [ ] pyright 通過（警告のみ許容）
- [ ] ドキュメント更新（必要なら）
```
