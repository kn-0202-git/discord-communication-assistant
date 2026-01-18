# 開発記録 - Phase 3（現行）

**期間**: 2026-01-11 ～
**Issue**: #32-
**テスト**: 180 → 281

このファイルはPhase 3の開発記録です。
過去の記録は以下のアーカイブを参照してください：
- [Phase 1（Issue #1-14）](../archive/logs/DEVELOPMENT_LOG_PHASE1.md)
- [Phase 2（Issue #15-31）](../archive/logs/DEVELOPMENT_LOG_PHASE2.md)

要約は [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md) を参照してください。

---

## 2026-01-17: Step 5.5 Geminiレビュー対応（G8, G6, G7）

### Agent

Claude Opus 4.5

### 目標

Geminiレビュー指摘（G8: AIRouterテスト分割、G6: main.py初期化ファクトリ化、G7: MessageService抽出）を実装し、コード品質を向上させる。

### 実施内容

#### G8: AIRouterテスト分割（16テスト追加）

tests/test_ai_router.pyに3つのテストクラスを追加：
- `TestAIRouterSelectionLogic`（8テスト）: Room > Workspace > グローバルの優先順位を段階的にテスト
- `TestAIRouterEdgeCases`（5テスト）: 空のID、特殊文字、purpose間の独立性
- `TestAIRouterFallbackLogic`（3テスト）: フォールバック順序、未設定時の空リスト

#### G6: main.py初期化ファクトリ化（172行→67行）

新規作成：
- `src/config.py`: AppConfig - YAML設定の一元管理クラス
- `src/factory.py`: AppComponents dataclass + create_app_components関数
- `src/bot/initializer.py`: BotInitializer - Bot初期化ロジック

効果：
- config.yamlの二重読み込み解消
- DI対応でテスト容易性向上
- main.pyが簡潔なエントリポイントに

#### G7: MessageService抽出（344行→186行）

新規作成：
- `src/bot/services/message_service.py`: メッセージ保存のビジネスロジック

MessageHandlerの責務を分離：
- Handler: DM判定、オーケストレーション
- Service: Workspace/Room確保、メッセージタイプ判定、添付ファイル保存

後方互換性を維持（既存テストが変更なしで通過）

### 発生したエラーと解決

1. **モックパスエラー**: `src.bot.handlers.aiohttp` → `src.bot.services.message_service.aiohttp`に変更
2. **AsyncMock問題**: `session.get()`が非同期コンテキストマネージャを返さない → `MagicMock`に変更、`mock_response.headers`を辞書で設定

### テスト結果

- コマンド: `uv run pytest tests/ -v`
- 結果: 281 passed, 2 failed（既存のGoogle Drive Storage問題）
- G8/G6/G7関連テスト: 87 passed（全て通過）
- pyright: 0 errors（変更ファイルのみ）
- ruff: All checks passed

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| src/config.py | 新規作成 - AppConfig |
| src/factory.py | 新規作成 - create_app_components |
| src/bot/initializer.py | 新規作成 - BotInitializer |
| src/main.py | ファクトリ化（172→67行） |
| src/bot/services/__init__.py | 新規作成 |
| src/bot/services/message_service.py | 新規作成 - MessageService |
| src/bot/handlers.py | オーケストレーターに変更（344→186行） |
| tests/test_ai_router.py | G8テスト追加（18→34テスト） |
| tests/test_config.py | 新規作成（11テスト） |
| tests/test_factory.py | 新規作成（10テスト） |
| tests/test_message_service.py | 新規作成（16テスト） |
| tests/test_handler.py | モックパス修正 |
| docs/planning/DEVELOPMENT_PLAN.md | G8/G6/G7を完了に更新 |

### 次のステップ

- Step 5: Oracle Cloud移行（#23, #24, #25）
- 既存のGoogle Drive Storageテスト問題の修正（別Issue）

---

## 2026-01-17: R-issue11 レビュー指摘対応

### Agent

Codex (GPT-5)

### 目標

レビュー指摘に基づき、計画・デプロイ手順・運用ルールの不整合と安全性を改善する。

### 実施内容

1. **計画の整合性修正**
   - Step 4（Google Drive連携）を「完了」に更新

2. **デプロイガイドの安全性強化**
   - Always Freeの注意書きを追加（変更/終了リスク）
   - SSHのSecurity List制限を明記
   - Block Volumeのマウント手順をデバイス確認/UUID固定に変更

3. **運用ルール追記**
   - 無料枠の四半期確認と変更時の再評価ルールを追加

### テスト結果

- コマンド: 未実施（ドキュメント更新のみ）
- 結果: -

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| docs/planning/DEVELOPMENT_PLAN.md | Step 4の完了表記に修正 |
| docs/guides/DEPLOY_ORACLE.md | Always Free注意書き/SSH制限/Block Volume手順を更新 |
| docs/rules/CORE_RULES.md | 無料枠の運用ルールを追記 |

---

## 2026-01-17: R-issue11 クラウド移行設計変更（Fly.io → Oracle Cloud）

### Agent

Claude Opus 4.5

### 目標

Fly.ioが無料で使えないことが判明したため、Phase 2 Step 5のクラウド移行先を再検討し、設計を変更する。

### 実施内容

1. **選択肢の調査**
   - Oracle Cloud Free Tier、GitHub Actions Batch、Railway、Render.comを比較
   - 9つの専門家視点（ソフトウェアエンジニア、Python開発者、コードレビュアー、UI/UX、ドメインエキスパート、教育者、セキュリティ、QA、AI）で評価

2. **ユーザー要件の確認**
   - リアルタイムが望ましいが1時間おきでもOK
   - クラウド必須（ローカル常時稼働は不可）
   - DB設計はSQLite/SQLAlchemy維持（NDJSON変更なし）

3. **決定事項**
   - Oracle Cloud Free Tierを採用（4 OCPU ARM、24GB RAM、200GB Storage永久無料）
   - 既存コードの変更なし（Dockerfileそのまま使用）
   - 全機能維持（スラッシュコマンド、音声録音、リアルタイム通知）

4. **ドキュメント更新**
   - DEVELOPMENT_PLAN.md: Phase 2 Step 5をOracle Cloudに変更
   - ARCHITECTURE.md: セクション5.2をOracle Cloud構成に更新
   - CORE_RULES.md: クラウド移行設計原則セクション追加
   - DEPLOY_ORACLE.md: 新規作成（デプロイ手順）
   - fly.toml: 参考用コメント追加

### テスト結果

- コマンド: 設計変更のためテスト実行なし
- 結果: ドキュメント更新のみ

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| docs/planning/DEVELOPMENT_PLAN.md | Phase 2 Step 5をOracle Cloudに変更 |
| docs/specs/ARCHITECTURE.md | セクション5.2, 5.3更新 |
| docs/rules/CORE_RULES.md | クラウド移行設計原則追加 |
| docs/guides/DEPLOY_ORACLE.md | 新規作成 |
| fly.toml | 参考用コメント追加 |
| docs/r-issues/R-issue11.md | 新規作成 |

### 次のステップ

1. Oracle Cloud Free Tier登録
2. Issue #23-25の実施（DEPLOY_ORACLE.md参照）
3. 本番稼働確認

---

## 2026-01-13: Issue #22-24 Fly.io移行準備（Dockerfile/fly.toml/Volume）

### 目標

Fly.io移行の準備として、Dockerfile・fly.toml・SQLite永続化の設定を整備する。

### 実施内容

- Dockerfileを追加し、uv.lockベースで依存関係をインストールする構成を作成
- Fly.io向けにfly.tomlを追加し、/app/dataへのVolumeマウントを設定
- Dockerビルド対象を最小化するために.dockerignoreを追加

### テスト結果

- コマンド: 未実施（Dockerビルド/Fly CLI未検証）
- 結果: -

### 変更ファイル

- Dockerfile
- .dockerignore
- fly.toml
- docs/planning/DEVELOPMENT_PLAN.md
- docs/planning/ISSUES_STATUS.md

### 次のステップ

- Dockerビルドの確認とFly CLIでのデプロイ検証（Issue #22-25）

## 2026-01-12: G1 MAX_ATTACHMENT_SIZEのconfig化

### 目標

添付ファイル上限をconfig.yamlに移し、テストで確認できるようにする。

### 実施内容

- config.yamlにattachments.max_size_bytesを追加
- MessageHandlerで設定値を読み込み、上限値を可変化
- 上限超過時の挙動をテスト追加

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- G4（aiohttp共有）に着手

## 2026-01-12: G4 共有aiohttpセッション導入

### 目標

添付ファイル取得のHTTPセッションを共有化し、コネクション再利用と安定性を向上する。

### 実施内容

- MessageHandlerに共有セッションの確保/クローズを追加
- _save_attachmentsで共有セッションを使用するように変更
- 終了時にセッションを閉じる処理を追加

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- G2（TokenCounter導入）に着手

## 2026-01-12: G2 TokenCounter導入

### 目標

コンテキストの長文化による失敗を避けるため、簡易トリムを導入する。

### 実施内容

- TokenCounterユーティリティを追加（概算トークン/トリム）
- generate_with_contextにトリムを追加（base/各プロバイダー）
- config.yamlにai.token_budgetを追加
- ユニットテストを追加

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- G3（autospec化）に着手

## 2026-01-12: G3 MagicMock autospec化

### 目標

モックの型安全性を高め、API変更時にテストが失敗するようにする。

### 実施内容

- AsyncOpenAI/AsyncAnthropic/AsyncGroq などの patch に autospec を追加
- aiohttp.ClientSession の patch に autospec を追加

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- #33（/transcribe）またはG1/G4以降の残タスクに着手

## 2026-01-12: Issues #27-29 Google Drive連携（OAuth・/save・自動アップロード）

### 目標

Google Drive連携の残タスク（OAuth設定、/saveコマンド、自動アップロード）を実装する。

### 実施内容

- GoogleDriveStorageにOAuthリフレッシュ対応と任意フォルダ保存を追加
- config.yamlにDrive設定を追加し、起動時にDrive設定を読み込み
- /saveコマンドで最新添付をDriveへ保存し、drive_pathを更新
- 自動アップロード時にDriveへ保存し、DBにdrive_pathを記録
- セットアップガイド（Google Drive OAuth）を追加
- ハンドラとコマンドのテストを追加
- **Note**: 外部ツール（Claude Code）による集中的な実装のため、詳細な `CONVERSATION_LOG` は欠損。変更内容はGit履歴参照（`a23fe14`）。

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- Step 5（クラウド移行）に着手

## 2026-01-12: Issue #26 GoogleDriveStorage実装

### 目標

StorageProviderに準拠したGoogle Driveストレージ実装を追加する。

### 実施内容

- GoogleDriveStorageを実装（保存/取得/削除、フォルダ階層作成）
- 共有セッション管理とトークン認証ヘッダを追加
- ストレージのexportを更新
- ユニットテストを追加

### テスト結果

- コマンド: 未実施
- 結果: -

### 次のステップ

- #27 OAuth設定に着手

## 2026-01-11: Issue #32 Whisperプロバイダー実装

### 目標

OpenAI Whisper APIを使用した音声文字起こし機能（TranscriptionProvider基底クラスとWhisperProvider実装）を実装する。

### 実施内容

#### Step 1: ブランチ作成
- **コマンド**: `git checkout -b feature/issue-32`
- **結果**: ✅ 成功

#### Step 2: 設計方針の決定
- **判断**: AIProviderとは独立したTranscriptionProvider基底クラスを新規作成
- **理由**:
  - 既存のAIProviderは`generate(prompt: str)`と`embed(text: str)`用
  - 文字起こしは`transcribe(audio: bytes)`で音声バイナリを入力
  - 入力の型が根本的に異なるため、別の抽象化が適切

#### Step 3: ディレクトリ構成
```
src/ai/transcription/
├── __init__.py        # エクスポート
├── base.py            # TranscriptionProvider 基底クラス
└── whisper.py         # WhisperProvider 実装
```

#### Step 4: TranscriptionProvider基底クラス作成
- **ファイル**: `src/ai/transcription/base.py`
- **内容**:
  - 抽象プロパティ: `name`, `model`
  - 抽象メソッド: `transcribe(audio: bytes, language: str | None, **kwargs) -> str`
  - 既存のAIProviderErrorクラス階層を再利用

#### Step 5: WhisperProvider実装
- **ファイル**: `src/ai/transcription/whisper.py`
- **内容**:
  - OpenAI AsyncOpenAIクライアントを使用
  - `audio.transcriptions.create()` APIをラップ
  - 対応フォーマット: WAV, MP3, M4A, WebM等
  - オプション: language, prompt, temperature, response_format

#### Step 6: テスト作成・実行
- **ファイル**: `tests/test_whisper_provider.py`
- **テストケース**: 11件
  | ID | テスト | 説明 |
  |----|--------|------|
  | WHP-01 | test_transcribe_success | 正常な文字起こし |
  | WHP-02 | test_transcribe_with_language | 言語指定付き |
  | WHP-03 | test_connection_error | 接続エラー処理 |
  | WHP-04 | test_quota_exceeded | レート制限エラー |
  | WHP-05 | test_invalid_api_key | 認証エラー |
  | WHP-06 | test_empty_audio | 空の音声データ |
  | WHP-07 | test_name_property | プロバイダー名 |
  | WHP-08 | test_model_property | モデル名 |
  | WHP-09 | test_repr | __repr__動作確認 |
  | WHP-10 | test_transcribe_with_options | オプション付き |
  | WHP-11 | test_transcribe_json_format | JSON形式出力 |

- **結果**: ✅ 11 passed

#### Step 7: 品質チェック
- **ruff**: ✅ All checks passed
- **全テスト**: ✅ 191 passed

### 技術解説

#### TranscriptionProviderの設計

```python
class TranscriptionProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
        **kwargs: Any,
    ) -> str: ...
```

**なぜAIProviderと分離したか:**
1. 入力の型が異なる（str vs bytes）
2. 責務が異なる（テキスト生成 vs 音声認識）
3. 単一責任原則（SRP）に従う

#### OpenAI Whisper API

```python
# 使用例
response = await client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    language="ja",      # 言語指定（自動検出も可）
    prompt="会議の議事録",  # ヒント
    response_format="text",  # text, json, srt, vtt
)
```

**対応形式**: mp3, mp4, mpeg, mpga, m4a, wav, webm

### 学んだこと

1. **抽象化の境界**: 入力/出力の型が異なる場合は別の基底クラスを作る
2. **BytesIOの活用**: バイナリデータをファイルライクオブジェクトに変換
3. **既存コードの再利用**: エラークラス（AIProviderError等）は共通で使用可能
4. **テストパターン**: AsyncMockで非同期APIをモック化

### 作成ファイル

| ファイル | 行数 | 内容 |
|----------|------|------|
| src/ai/transcription/__init__.py | 13 | エクスポート |
| src/ai/transcription/base.py | 99 | 基底クラス |
| src/ai/transcription/whisper.py | 150 | Whisper実装 |
| tests/test_whisper_provider.py | 215 | テスト |

### 次のステップ

- Issue #33: /transcribe コマンド実装
  - 録音ファイルの文字起こし
  - VoiceSession.transcription への保存

---

## 2026-01-12: Issue #33 /transcribe コマンド実装

### 目標

`/transcribe {session_id}` コマンドを実装し、録音セッションの音声ファイルをWhisper APIで文字起こしする。

### 実施内容

#### Step 1: テスト作成（TDD）

**ファイル**: `tests/test_commands.py`

4つのテストケースを追加（CMD-15 ~ CMD-18）:
- CMD-15: 正常系 - 文字起こし成功
- CMD-16: セッションID未検出
- CMD-17: 音声ファイル未存在
- CMD-18: サーバー外での実行

#### Step 2: コマンド実装

**ファイル**: `src/bot/commands.py`

**追加メソッド**:
- `_register_transcribe_command()`: コマンド登録
- `_handle_transcribe()`: コマンドハンドラ

**処理フロー**:
1. `defer(thinking=True)` で即座応答
2. Guild/Workspace検証
3. `get_voice_session_by_id()` でセッション取得
4. `file_path` の存在確認
5. 音声ファイル読み込み（`Path.read_bytes()`）
6. `WhisperProvider.transcribe()` で文字起こし
7. `update_voice_session_transcription()` でDB保存
8. Discord Embedで結果表示

#### Step 3: テスト実行

```
195 passed in 1.09s
```

全テストパス。

#### Step 4: 品質チェック

```
ruff check src/ → All checks passed!
pyright src/ → 0 errors, 0 warnings
```

### 技術ポイント

**WhisperProviderの使用**:
```python
provider = WhisperProvider(api_key=api_key, model="whisper-1")
transcription = await provider.transcribe(audio_bytes, language="ja")
```

**既存パターンの活用**:
- `/record` コマンドと同様のvalidationフロー
- Discord Embedでの結果表示
- 長い結果は2000文字で切り詰め

### 学んだこと

1. **TDDの効果**: テストを先に書くことで仕様が明確になった
2. **モックパターン**: `monkeypatch.setenv()` と `unittest.mock.patch` の併用
3. **既存コードの再利用**: 既存のコマンドパターンに沿った実装で一貫性を保てた

### 作成/変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| src/bot/commands.py | /transcribe コマンド追加（約90行） |
| tests/test_commands.py | TestTranscribeCommandクラス追加（4テスト） |

### 次のステップ

- Issue #34: Phase 2統合テスト

---

## 2026-01-12: Issue #34 Phase 2統合テスト

### 目標

Phase 2で実装した機能（リマインダー、通話録音・文字起こし）の統合テストを作成する。

### 実施内容

#### Step 1: 計画策定

Plan Modeで統合テスト設計を実施：
- 正常系10テスト（test_integration_phase2.py）
- エラー系10テスト（test_integration_phase2_errors.py）

#### Step 2: テストファイル作成

**test_integration_phase2.py（正常系）**:
- P2-INT-01: リマインダー作成→通知フロー
- P2-INT-02: 期限内/期限外フィルタリング
- P2-INT-03: ReminderNotifier統合
- P2-INT-04: 録音ライフサイクル
- P2-INT-05: 録音→文字起こしフロー
- P2-INT-06: WhisperProvider統合
- P2-INT-07: 両機能の同時動作
- P2-INT-08: ステータス遷移
- P2-INT-09: 複数Room録音管理
- P2-INT-10: 正しいRoomへの通知

**test_integration_phase2_errors.py（エラー系）**:
- P2-ERR-01 ~ P2-ERR-10: 各種エラーケース
- DB関連エラー5件追加

#### Step 3: 問題修正

1. **discord_channel_idの型変換エラー**
   - 非数値文字列→数値文字列に変更

2. **pyrightエラー（mock_storageの型）**
   - MagicMock→LocalStorageに型ヒント修正
   - TYPE_CHECKINGでimport追加

#### Step 4: テスト実行

```
220 passed, 12 warnings in 1.14s
```

- 新規追加: 25テスト
- 既存テスト: 195テスト
- 合計: 220テスト全パス

#### Step 5: 品質チェック

```
ruff check tests/ → All checks passed!
pyright tests/ → 0 errors
```

### 技術ポイント

**統合テストの設計パターン**:
- エンドツーエンドのワークフロー検証
- 複数モジュール間の連携確認
- エラー伝播とリカバリの検証

**モック設計**:
```python
# DiscordチャンネルIDは数値文字列を使用
discord_channel_id="222222222"  # int変換できる形式

# LocalStorageは実際のインスタンスを使用
@pytest.fixture
def mock_storage(self, tmp_path: Path) -> "LocalStorage":
    return LocalStorage(base_path=tmp_path)
```

### 学んだこと

1. 統合テストでは実装の詳細（int変換等）に合わせたテストデータが必要
2. TYPE_CHECKINGブロックでの条件付きインポートが型チェックに有効
3. 正常系とエラー系を別ファイルに分離すると管理しやすい

### 作成/変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| tests/test_integration_phase2.py | 正常系統合テスト（10テスト） |
| tests/test_integration_phase2_errors.py | エラー系統合テスト（15テスト） |
| docs/planning/DEVELOPMENT_PLAN.md | Issue #34を完了に更新 |
| docs/archive/conversations/CONVERSATION_LOG_ISSUE34.md | 会話ログ作成 |

### 次のステップ

- Issue #35: 本番運用テスト（複数社で動作確認）

---

## 2026-01-13: G5 gitleaks導入

### Agent
- Claude Opus 4.5

### 目標
gitleaksを導入し、シークレットの誤コミットを防止する。

### 実施内容

#### Step 1: 現状調査
- pre-commit設定: ruff + 基本フックのみ
- GitHub Actions: テスト・リント・カバレッジのみ
- .env: gitで追跡されていない（安全）

#### Step 2: pre-commit設定追加
- `.pre-commit-config.yaml` にgitleaks v8.21.2を追加

#### Step 3: .gitleaksignore作成
- テストファイル、ドキュメント、.env.exampleを除外

#### Step 4: GitHub Actions更新
- gitleaksジョブを追加（fetch-depth: 0で全履歴スキャン）

#### Step 5: ドキュメント更新
- `docs/rules/CORE_RULES.md` のセキュリティセクションを更新

#### Step 6: 既存履歴スキャン
- `pre-commit run gitleaks --all-files` でスキャン実行
- 結果: **Passed**（シークレット漏洩なし）

### テスト結果

- コマンド: `uv run pytest tests/ -v`
- 結果: 225 passed, 2 failed（既存問題）

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| .pre-commit-config.yaml | gitleaks hook追加 |
| .gitleaksignore | 新規作成（誤検知除外設定） |
| .github/workflows/test.yml | gitleaksジョブ追加 |
| docs/rules/CORE_RULES.md | セキュリティセクション更新 |

### 次のステップ

- G8: AIRouterテスト分割に着手
