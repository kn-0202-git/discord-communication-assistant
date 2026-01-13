# 要件定義書

## 1. 概要

### 1.1 目的
請負者とのチャット履歴をAIが監視・保存し、過去のやり取りを忘れない仕組みを構築する。

### 1.2 スコープ
| Phase | 内容 |
|-------|------|
| Phase 1 | MVP（メッセージ保存・検索・要約・AI切替） |
| Phase 2 | 通話録音・文字起こし・Google Drive連携 |
| Phase 3 | RAG（資料を読んでAI回答）・クラウド移行 |
| Phase 4 | スケール対応 |

## 2. ユーザーと役割

| ユーザー | 役割 |
|----------|------|
| 依頼者 | やり取りの主体、システム管理者 |
| 請負者 | 複数社、各社数人 |
| AI Bot | 監視・保存・通知・回答 |

## 3. 部屋構造

### 3.1 概念
```
Workspace（最上位の部屋）
├── 請負者ごと or プロジェクトごとに作成
├── Workspace間は完全分離（相互に見えない）
│
└── Room（中の部屋）
    ├── トピック別 or メンバー別
    ├── 同一Workspace内では情報共有可能
    └── room_type:
        ├── "topic" - トピック別の会話
        ├── "member" - メンバー限定
        └── "aggregation" - 統合・AI用
```

### 3.2 情報共有ルール

| 関係 | 共有 | 例 |
|------|------|-----|
| Workspace A ↔ Workspace B | ❌ 不可 | A社の情報はB社に見えない |
| Room 1 ↔ Room 2（同一Workspace） | ⚪ 可能 | 設定次第で相互参照 |
| Room 6（統合）← Room 1, 2 | ⚪ 集約 | AIが情報をまとめる |

### 3.3 Discordとの対応

| 概念 | Discord |
|------|---------|
| Workspace | サーバー |
| Room | チャンネル |
| 統合Room | 依頼者専用チャンネル or 別サーバー |

## 4. 機能要件

### Phase 1: MVP

#### 4.1 メッセージ保存
- すべてのテキストメッセージをDBに保存
- 発言者、タイムスタンプ、Room情報を記録
- Workspaceごとに完全分離

#### 4.2 ファイル保存（ローカル）
- 写真・動画・ボイスメッセージを保存
- ファイルパスをDBに記録
- ディレクトリ構成：`{workspace_id}/{room_id}/{date}/`

#### 4.3 要約コマンド
- `/summary` で直近N日の会話を要約
- Room単位 or Workspace単位で指定可能

#### 4.4 検索コマンド
- `/search {キーワード}` で過去メッセージ検索
- Workspace内のみ検索（他Workspaceは検索不可）

#### 4.5 通知機能
- 依頼者専用のRoom（統合Room）へ通知
- 類似過去案件があれば自動通知

#### 4.6 AI設定
- 機能ごとにAIプロバイダー・モデルを設定可能
- Workspace/Roomごとに上書き可能
- 設定変更はconfig.yamlで管理

### Phase 2: 拡張

#### 4.7 通話録音
- 通話を自動録音（デフォルトon）
- `/record off` で一時停止可能
- 録音ファイルを保存

#### 4.8 文字起こし
- 音声ファイルをテキスト化（Whisper API）
- ボイスメッセージも対象
- 文字起こし結果をDBに保存・検索可能

#### 4.9 Google Drive連携
- ファイルをGoogle Driveに保存
- 自動保存：受信時に自動アップロード
- 手動保存：`/save {folder}` でフォルダ指定
- フォルダ構成：`{workspace_name}/{date}/` + 任意指定

#### 4.10 リマインダー
- `/remind {title} {date}` で登録
- 期限前に統合Roomへ通知

### Phase 3: RAG

#### 4.11 資料検索・AI回答
- 保存済み資料（PDF・Word等）をベクトル化
- `/ask {質問}` で関連資料を検索
- AIが資料を基に回答生成
- 回答には出典（ファイル名・ページ）を含める

## 5. AI要件

### 5.1 対応プロバイダー

| プロバイダー | モデル例 | 用途 |
|--------------|----------|------|
| OpenAI | GPT-4o, GPT-4o-mini, Whisper, Embeddings | 汎用、音声 |
| Anthropic | Claude 3.5 Sonnet, Haiku | 長文、精度重視 |
| Google | Gemini 1.5 Pro, Flash | 安価、長文 |
| Groq | Llama 3.1, Mixtral | 高速、安価 |
| ローカル | Ollama（Llama等） | 無料、オフライン |

### 5.2 機能別デフォルト設定

| 機能 | プロバイダー | モデル | 理由 |
|------|--------------|--------|------|
| 要約 | OpenAI | gpt-4o-mini | バランス良い |
| 類似検索 | OpenAI | text-embedding-3-small | 標準的 |
| RAG回答 | Anthropic | claude-3-5-sonnet | 精度重視 |
| 文字起こし | OpenAI | whisper-1 | 音声専用 |
| 通知文生成 | Groq | llama-3.1-70b | 高速・安価 |

### 5.3 設定の上書き
```yaml
# Workspace別の上書き例
workspace_overrides:
  workspace_a:
    summary:
      provider: google
      model: gemini-1.5-flash
```

## 6. 非機能要件

| 項目 | 要件 |
|------|------|
| データ保持 | 削除しない（履歴が価値） |
| 権限分離 | Workspace Aは Workspace Bのデータを見れない |
| 可用性 | Botが落ちても会話は継続可能 |
| 拡張性 | 50 Workspaceまで対応できる設計 |
| OS互換 | macOS / Windows両対応 |
| テスト | コードが読めなくても品質担保 |
| AI柔軟性 | プロバイダー・モデルを自由に切替可能 |

## 7. データモデル

### Workspace（最上位の部屋）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| name | TEXT | Workspace名 |
| discord_server_id | TEXT | DiscordサーバーID |
| ai_config | JSON | AI設定の上書き（オプション） |
| created_at | DATETIME | 作成日時 |

### Room（中の部屋）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| workspace_id | INTEGER | FK |
| name | TEXT | Room名 |
| discord_channel_id | TEXT | DiscordチャンネルID |
| room_type | TEXT | topic / member / aggregation |
| ai_config | JSON | AI設定の上書き（オプション） |
| created_at | DATETIME | 作成日時 |

### RoomLink（Room間の情報共有設定）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| source_room_id | INTEGER | FK（情報元） |
| target_room_id | INTEGER | FK（情報先） |
| link_type | TEXT | bidirectional / one_way |

### Message（メッセージ）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| room_id | INTEGER | FK |
| sender_name | TEXT | 発言者 |
| sender_id | TEXT | Discord User ID |
| content | TEXT | 本文 |
| message_type | TEXT | text / image / video / voice |
| discord_message_id | TEXT | DiscordメッセージID |
| timestamp | DATETIME | 発言日時 |

### Attachment（添付ファイル）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| message_id | INTEGER | FK |
| file_name | TEXT | 元ファイル名 |
| file_path | TEXT | ローカル保存パス |
| drive_path | TEXT | Google Driveパス |
| file_type | TEXT | image / video / voice / document |
| file_size | INTEGER | サイズ（bytes） |
| transcription | TEXT | 文字起こし（音声用） |

### Document（資料 - Phase 3）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| workspace_id | INTEGER | FK |
| attachment_id | INTEGER | FK |
| content_text | TEXT | 抽出テキスト |
| embedding | BLOB | ベクトル |

### Reminder（リマインダー）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| workspace_id | INTEGER | FK |
| title | TEXT | 件名 |
| description | TEXT | 詳細 |
| due_date | DATETIME | 期限 |
| status | TEXT | pending / done / cancelled |
| notified | BOOLEAN | 通知済みか |

### VoiceSession（通話録音 - Phase 2）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PK |
| room_id | INTEGER | FK |
| start_time | DATETIME | 開始時刻 |
| end_time | DATETIME | 終了時刻 |
| file_path | TEXT | 録音ファイルパス |
| transcription | TEXT | 文字起こし |
| participants | TEXT | 参加者（JSON） |

## 8. コマンド一覧

| コマンド | 機能 | Phase |
|----------|------|-------|
| `/summary [days]` | 直近の会話を要約 | 1 |
| `/search {keyword}` | 過去メッセージ検索 | 1 |
| `/ai-config` | 現在のAI設定を表示 | 1 |
| `/remind {title} {date}` | リマインダー登録 | 2 |
| `/reminders` | リマインダー一覧 | 2 |
| `/record on/off` | 通話録音の切替 | 2 |
| `/transcribe` | 直近音声を文字起こし | 2 |
| `/save [folder]` | 指定フォルダにDrive保存 | 2 |
| `/docs` | Workspaceの資料一覧 | 2 |
| `/ask {question}` | 資料を基にAI回答 | 3 |

## 9. 外部連携

| サービス | 用途 | Phase |
|----------|------|-------|
| Discord API | Bot、メッセージ取得、通話 | 1 |
| OpenAI API | 要約、Embeddings、Whisper | 1-3 |
| Anthropic API | RAG回答等 | 1-3 |
| Google AI API | 要約等（安価版） | 1-3 |
| Groq API | 高速推論 | 1-3 |
| ローカルLLM | オフライン対応 | 1-3 |
| Google Drive API | ファイル保存 | 2 |
| Fly.io | クラウドホスティング | 3 |

## 10. 制約・前提

- Discord無料プランで運用
- ファイル上限25MB/件
- AIは判断しない（ドラフト生成のみ）
- ローカル実行からスタート（macOS / Windows）
- 録音は請負者に事前告知が必要
- AIプロバイダーは必要なもののみ設定すればよい

## 11. Discord API制約

### 11.1 料金
- Discord API：無料
- Bot作成：無料
- Discord Nitro：不要（無料プランで十分）

### 11.2 制限

| 項目 | 制限 | 影響 |
|------|------|------|
| Bot作成サーバー | 10個/Bot | 5社はOK、50社で要検討 |
| レート制限 | 50リクエスト/秒 | 小規模なら問題なし |
| シャーディング必須 | 2,500サーバー以上 | 当面不要 |

### 11.3 禁止事項（開発者ポリシー）

| 禁止事項 | 今回の対応 |
|----------|-----------|
| データのAI学習利用 | ❌ しない（RAGは使用可） |
| データの商業化・販売 | ❌ しない（自社利用のみ） |
| スクレイピング | ❌ しない（参加サーバーのみ） |
| 13歳未満の利用 | ❌ 業務用なので該当なし |

### 11.4 推奨事項

- **プライベートサーバーを使用**（公開サーバーはリスクあり）
- **録音は請負者に事前告知**（法的・信頼関係上必須）
- **レート制限を考慮したコード実装**
