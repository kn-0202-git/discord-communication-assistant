# 開発記録 - Phase 2（アーカイブ）

**期間**: 2025-01-06 ～ 2025-01-09
**Issue**: #15-31
**テスト**: 120 → 180

このファイルはPhase 2の開発記録アーカイブです。
最新の開発記録は [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md) を参照してください。

---

## 2025-01-06: Phase 2 Step 1 技術課題解消 (#15-17)

### 開始時刻: セッション開始時

### 目標

Phase 2の最初のステップとして、Phase 1で発見された技術課題を解消する:
- Issue #15: datetime.utcnow() を datetime.now(UTC) に修正
- Issue #16: GuildListener のテスト追加
- Issue #17: レート制限対策

### 背景

Phase 1完了時点で以下の課題が保留されていた:
1. `datetime.utcnow()` はPython 3.12で非推奨
2. GuildListenerクラスのテストカバレッジが不足
3. 統合Room通知がDiscordのレート制限に引っかかる可能性

### 実施内容

#### Issue #15: datetime.utcnow() 修正

**ファイル**: `src/db/models.py`

**変更内容**:
```python
# Before
from datetime import datetime
created_at = mapped_column(DateTime, default=datetime.utcnow)

# After
from datetime import UTC, datetime

def _utc_now() -> datetime:
    """現在のUTC時刻を返す（Python 3.12対応）."""
    return datetime.now(UTC)

created_at = mapped_column(DateTime, default=_utc_now)
```

**技術解説**:
- Python 3.12で `datetime.utcnow()` が非推奨になった
- `datetime.now(UTC)` が推奨される新しい書き方
- `datetime.UTC` は Python 3.11+ で使用可能なエイリアス
- SQLAlchemyの `default` には呼び出し可能オブジェクトを渡す必要があるため、ヘルパー関数 `_utc_now()` を作成

**影響箇所**: 3箇所（Workspace.created_at, Room.created_at, Message.timestamp）

---

#### Issue #16: GuildListener テスト追加

**ファイル**: `tests/test_bot.py`

**追加テスト**: 4件
1. `test_create_guild_listener`: GuildListener作成テスト
2. `test_on_guild_join`: サーバー参加イベント処理テスト
3. `test_on_guild_remove`: サーバー退出イベント処理テスト
4. `test_on_guild_join_with_zero_members`: 境界値テスト（メンバー数0）

**技術解説**:
- `MagicMock(spec=discord.Guild)` で型安全なモックを作成
- `on_guild_join` は guild_id, guild_name, member_count, owner_id を返す
- `on_guild_remove` は guild_id, guild_name のみ返す（退出時は詳細情報不要）

---

#### Issue #17: レート制限対策

**ファイル**: `src/bot/notifier.py`

**追加機能**:
1. `asyncio.Semaphore` で同時リクエスト数を制限（最大5）
2. チャンネルごとのクールダウン（1秒）

**実装詳細**:
```python
class AggregationNotifier:
    MAX_CONCURRENT_REQUESTS = 5
    CHANNEL_COOLDOWN_SECONDS = 1.0

    def __init__(self, ...):
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        self._channel_last_sent: dict[str, float] = {}

    async def _send_notification(self, ...):
        async with self._semaphore:
            await self._wait_for_cooldown(channel_id)
            # 送信処理
            self._channel_last_sent[channel_id] = time.monotonic()

    async def _wait_for_cooldown(self, channel_id: str):
        if channel_id in self._channel_last_sent:
            elapsed = time.monotonic() - self._channel_last_sent[channel_id]
            remaining = self.CHANNEL_COOLDOWN_SECONDS - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
```

**技術解説**:
- `asyncio.Semaphore`: 同時実行数を制限する同期プリミティブ
- `time.monotonic()`: 単調増加する時刻（システム時刻変更の影響を受けない）
- `async with self._semaphore`: セマフォを取得し、ブロック終了時に自動解放

**テスト**: 4件追加
1. `test_rate_limit_semaphore_initialized`: セマフォ初期化確認
2. `test_rate_limit_cooldown_tracking`: クールダウン追跡確認
3. `test_wait_for_cooldown_no_previous_send`: 初回送信時の即時返却
4. `test_wait_for_cooldown_after_cooldown_period`: クールダウン経過後の即時返却

### 最終テスト結果

```
tests/test_bot.py: 14 passed (10 → 14, +4)
tests/test_notifier.py: 13 passed (9 → 13, +4)
Total: 128 passed (120 → 128, +8)
```

### 成果物

| ファイル | 変更内容 |
|----------|----------|
| src/db/models.py | _utc_now() ヘルパー追加、3箇所修正 |
| src/bot/notifier.py | レート制限機能追加 |
| tests/test_bot.py | GuildListenerテスト4件追加 |
| tests/test_notifier.py | レート制限テスト4件追加 |

### 学んだこと

1. **Python非推奨機能の追跡**: Python 3.12でdatetime.utcnow()が非推奨になるなど、バージョンアップで変わる機能に注意
2. **レート制限の設計**: Semaphore + チャンネルごとクールダウンの組み合わせが効果的
3. **time.monotonic()の活用**: システム時刻変更の影響を受けない時間計測

### 次のステップ

- Phase 2 Step 2: リマインダー機能 (#18-21)
- /remind, /reminders コマンド実装
- 期限通知機能

---

## 2025-01-06: プロセス改善

### 目標

繰り返し発生している「文書作成忘れ」問題を解決し、問題解決プロセスを明確化する。

### 背景

Issue #5（2025-01-04）およびIssue #15-17（2025-01-06）で、以下の問題が発生した：
- DEVELOPMENT_LOG.mdへの記録を忘れた
- CONVERSATION_LOGを作成しなかった
- ユーザーに指摘されるまで気づかなかった

### 専門家視点での分析

| 専門家 | 分析 |
|--------|------|
| ソフトウェアエンジニア | プロセスの一貫性が欠けている |
| コードレビュアー | 問題の発見・記録・解決の可視化が重要 |
| QAエンジニア | 根本原因分析（Why）が必要 |
| 教育者 | 問題解決フローを明確に文書化すべき |

### 根本原因

1. 問題解決プロセスが曖昧だった
2. TROUBLESHOOTING.mdが活用されていなかった
3. TodoWriteに記録タスクを含め忘れていた

### 対策

#### 対策 A: TodoWrite必須項目化

Issue開始時に以下をTodoに含める：
- DEVELOPMENT_LOG.md 更新
- CONVERSATION_LOG 作成
- DEVELOPMENT_PLAN.md / ISSUES_STATUS.md 更新

#### 対策 B: 空ファイル事前作成

ブランチ作成直後に `docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md` を作成しておく。

### 問題解決フロー（新規定義）

```
問題発生
    ↓
① ISSUES_STATUS.md「プロセス改善」セクションに記録
    ↓
② 対応中は status を 🟡 に
    ↓
③ 解決したら:
   - TROUBLESHOOTING.md「開発プロセス」セクションに詳細を追加
   - DEVELOPMENT_LOG.md に記録
   - ISSUES_STATUS.md を 🟢 完了 に
```

### Phase 2 順序変更

ユーザーからの提案により、Phase 2のStep順序を変更：

| 変更前 | 変更後 | 理由 |
|--------|--------|------|
| Step 2: リマインダー | Step 2: リマインダー | 変更なし |
| Step 3: クラウド移行 | Step 3: 通話録音 | ローカル機能を先に |
| Step 4: Google Drive | Step 4: Google Drive | 変更なし |
| Step 5: 通話録音 | Step 5: クラウド移行 | 最後にデプロイ |
| Step 6: 統合テスト | Step 6: 統合テスト | 変更なし |

**理由**: ローカルで全機能を確認してからクラウド移行する方が自然なフロー。

### 更新したファイル

| ファイル | 変更内容 |
|----------|----------|
| docs/reference/TROUBLESHOOTING.md | 「開発プロセス」セクション追加 |
| docs/planning/ISSUES_STATUS.md | 「プロセス改善」セクション追加 |
| CLAUDE.md | 問題解決フロー追記 |
| docs/planning/DEVELOPMENT_PLAN.md | Phase 2 Step順序変更 |
| docs/logs/DEVELOPMENT_LOG.md | この記録 |

### 学んだこと

1. **プロセスの明文化が重要**: 暗黙のルールは忘れやすい
2. **TROUBLESHOOTINGは技術問題だけでなくプロセス問題も記録**: 活用範囲を広げる
3. **問題→記録→解決→文書化のフローを定着させる**: 同じ失敗を繰り返さない

### 次のステップ

- Phase 2 Step 2: リマインダー機能 (#18-21) の実装開始

---

## 2025-01-08: Codexレビュー対応（セキュリティ・品質改善）

### 目標

Phase 2実装開始前に、Codexレビューで指摘されたセキュリティ・品質問題を解決する。

### 背景

ユーザーから `codex_review_md` ファイルのレビュー結果を確認し、必要な対応を行うよう依頼があった。
以下の4つの問題が特定された：

| # | 問題 | 優先度 | 影響 |
|---|------|--------|------|
| 1 | naive/aware datetime比較 | 高 | 日付フィルタリングが不正確になる可能性 |
| 2 | summarizer が OpenAI 固定 | 中 | config.yaml の設定が無視される |
| 3 | パストラバーサル脆弱性 | 中 | 悪意あるファイル名で任意パスに書き込み可能 |
| 4 | 添付ファイルサイズ無制限 | 中 | DoS攻撃のリスク |

### 実施内容

#### Issue 1 (HIGH): naive/aware datetime比較問題

**ファイル**: `src/ai/summarizer.py`

**問題**:
```python
# 修正前: naive datetime と aware datetime の比較でエラー
cutoff = datetime.now() - timedelta(days=days)
```

**解決**:
```python
# 修正後: UTC aware datetime を使用
from datetime import UTC
cutoff = datetime.now(UTC) - timedelta(days=days)
default_timestamp = datetime.min.replace(tzinfo=UTC)
```

**技術解説**:
- Python の datetime には「naive」（タイムゾーン情報なし）と「aware」（タイムゾーン情報あり）がある
- 両者を比較すると `TypeError: can't compare offset-naive and offset-aware datetimes`
- メッセージの timestamp は aware なので、比較対象も aware にする必要がある

#### Issue 2 (MED): マルチプロバイダー対応

**ファイル**: `src/ai/summarizer.py`

**問題**:
- `_get_provider()` が OpenAI 固定でハードコードされていた
- config.yaml で Anthropic/Google/Groq を設定しても無視される

**解決**:
```python
# プロバイダー名とクラスのマッピング
_PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "groq": GroqProvider,
}

def _get_provider(self, workspace_id, room_id):
    provider_info = self._router.get_provider_info("summary", ...)
    provider_name = provider_info["provider"]
    provider_class = self._PROVIDER_CLASSES.get(provider_name)
    return cast(Any, provider_class)(
        api_key=provider_config["api_key"],
        model=provider_info["model"],
    )
```

**技術解説**:
- `cast(Any, provider_class)` で型チェックを回避
- 各プロバイダーは同一シグネチャ `(api_key, model)` を持つ
- pyright エラーを回避しつつ、実行時の柔軟性を確保

#### Issue 3 (MED): パストラバーサル対策

**ファイル**: `src/storage/local.py`

**問題**:
```python
# 修正前: ユーザー入力のファイル名をそのまま使用
target_path = target_dir / filename  # "../../../etc/passwd" が可能
```

**解決**:
```python
def _sanitize_filename(self, filename: str) -> str:
    """ファイル名をサニタイズしてパストラバーサルを防止"""
    safe_name = Path(filename).name  # ベース名のみ取得
    if not safe_name or safe_name in (".", ".."):
        safe_name = "unnamed_file"
    return safe_name
```

**技術解説**:
- `Path(filename).name` でディレクトリ部分を除去
- `../../../etc/passwd` → `passwd` に変換される
- OWASP Top 10: パストラバーサル（A01:2021 - Broken Access Control）対策

#### Issue 4 (MED): 添付ファイルサイズ上限

**ファイル**: `src/bot/handlers.py`

**問題**:
- 添付ファイルのサイズ制限がなかった
- 大きなファイルでメモリ枯渇やDoS攻撃のリスク

**解決**:
```python
# Discord無料プランの上限に合わせる
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB

# サイズチェック（2箇所）
file_size = att.get("size", 0)
if file_size > self.MAX_ATTACHMENT_SIZE:
    logger.warning(f"Skipping {att['filename']}: size exceeds limit")
    continue

# Content-Lengthでも再チェック
content_length = response.headers.get("Content-Length")
if content_length and int(content_length) > self.MAX_ATTACHMENT_SIZE:
    continue
```

### テスト修正

**問題**: テストが失敗
- `_PROVIDER_CLASSES` がクラス定義時に参照をキャプチャするため、`patch("src.ai.summarizer.OpenAIProvider")` が効かない

**解決**: `patch.object()` パターンに変更
```python
# 修正前
with patch("src.ai.summarizer.OpenAIProvider"):
    result = await summarizer.summarize(messages)

# 修正後
with patch.object(summarizer, "_get_provider", return_value=mock_provider):
    result = await summarizer.summarize(messages)
```

### 最終結果

```
✅ 128 tests passed
✅ pyright: 0 errors
✅ ruff: All checks passed
```

### 学んだこと

1. **datetime は常に UTC aware を使う**: `datetime.now(UTC)` を標準に
2. **ユーザー入力は必ずサニタイズ**: ファイル名、パス、URLなど
3. **リソース制限を設ける**: サイズ、件数、時間など
4. **モッキングは対象の特性を理解**: クラス変数 vs インスタンスメソッド

### 次のステップ

- Phase 2 Step 2: リマインダー機能 (#18-21) の実装開始

---

## 2025-01-09: Phase 2 Step 2 リマインダー機能実装

### 目標

リマインダー機能の完全実装（Issue #18-21）

### 実施内容

#### Issue #18: ReminderテーブルCRUD（8テスト）

1. `src/db/database.py` にReminder CRUD操作を追加:
   - `create_reminder`: リマインダー作成
   - `get_reminders_by_workspace`: Workspace内リマインダー一覧
   - `get_pending_reminders`: 期限が近いリマインダー取得
   - `get_reminder_by_id`: IDで取得
   - `update_reminder_status`: ステータス更新（pending/done/cancelled）
   - `update_reminder_notified`: 通知済みフラグ更新
   - `delete_reminder`: 削除

2. テストケース: DB-09 ~ DB-15

#### Issue #19: /remindコマンド（11テスト）

1. `src/bot/commands.py` に追加:
   - `parse_due_date`: 日時パーサー
     - 相対日時: 1d, 2h, 30m（日/時間/分）
     - 絶対日時: 2025-01-15, 2025-01-15 14:30
   - `/remind` コマンド: タイトル、期限、説明を受け取り登録

2. テストケース: CMD-01 ~ CMD-10

#### Issue #20: /remindersコマンド（4テスト）

1. `/reminders` コマンド:
   - 未完了リマインダーを一覧表示
   - 期限順にソート
   - 最大10件表示

2. テストケース: CMD-11 ~ CMD-14

#### Issue #21: 期限通知機能（5テスト）

1. `src/bot/notifier.py` に `ReminderNotifier` クラス追加:
   - `check_and_notify`: 期限が近いリマインダーをチェック
   - 統合Roomに自動通知
   - 通知済みフラグを更新
   - バックグラウンドタスク（start/stop制御）

2. テストケース: RN-01 ~ RN-05

### テスト結果

```
156 passed, 12 warnings
pyright: 0 errors
ruff: All checks passed
```

### 技術的なポイント

1. **日時パーサーの設計**:
   - 正規表現で相対日時（`^(\d+)([dhm])$`）をパース
   - `datetime.strptime` で絶対日時をパース
   - UTC タイムゾーンを統一

2. **CommandTree のモック**:
   - `CommandTree(MagicMock(spec=discord.Client))` は `client.http` を参照するため失敗
   - CommandTree 自体をモックして `_handle_*` メソッドを直接テスト

3. **バックグラウンドタスクの制御**:
   - `asyncio.create_task` でループを開始
   - `contextlib.suppress` で `CancelledError` を抑制（ruff SIM105）

### 学んだこと

1. Discord スラッシュコマンドのテストは CommandTree をモックする
2. 日時パーサーは相対と絶対の両方をサポートすると使いやすい
3. SQLite はタイムゾーン情報を保存しないため、テストで注意が必要
4. バックグラウンドタスクは start/stop で制御できる設計が良い
5. ruff の推奨に従い `contextlib.suppress` を使う

### 次のステップ

- Phase 2 Step 3: 通話録音・文字起こし (#30-33)

---

## 2025-01-09: Issue #30-31 VoiceSession & /record コマンド実装

### 目標

通話録音機能の基盤実装（Issue #30: VoiceSessionテーブル、Issue #31: /record on/off）

### 実施内容

#### Issue #30: VoiceSessionテーブル（7テスト）

1. `src/db/models.py` に VoiceSession モデル追加:
   - `id`, `room_id`, `start_time`, `end_time`
   - `file_path`, `transcription`, `participants`

2. `src/db/database.py` に CRUD 操作追加:
   - `create_voice_session`: セッション作成
   - `get_voice_session_by_id`: IDで取得
   - `get_voice_sessions_by_room`: Room別取得
   - `get_active_voice_sessions`: 録音中セッション取得
   - `update_voice_session_end`: 終了時刻とファイルパス更新
   - `update_voice_session_transcription`: 文字起こし更新
   - `delete_voice_session`: 削除

3. テストケース: DB-16 ~ DB-22

#### Issue #31: /record on/off コマンド（17テスト）

1. `src/bot/voice_recorder.py` 新規作成:
   - `VoiceRecorder` クラス: 録音セッション管理
   - `VoiceRecorderError`: カスタム例外
   - セッション状態管理（`_active_recordings`）
   - 参加者追跡（`add_participant`, `remove_participant`）

2. `src/bot/commands.py` に `/record` コマンド追加:
   - `/record on`: 録音開始（ボイスチャンネル接続、VoiceSession作成）
   - `/record off`: 録音停止（ファイル保存、セッション更新、切断）

3. 依存関係更新:
   - `discord.py[voice]>=2.3.0`（音声機能）
   - `pynacl>=1.5.0`（音声暗号化）

### 技術的なポイント

#### 1. discord.py の音声録音について

**課題**: 標準の discord.py には音声録音機能（`sinks` モジュール）がない

**選択肢**:
1. py-cord（discord.py フォーク）に移行
2. ffmpeg + VoiceRecvClient を使用
3. セッション管理のみ先行実装

**決定**: 選択肢3を採用
- 理由: py-cord への移行は破壊的、ffmpeg は追加依存関係が複雑
- 現在はプレースホルダーWAVファイルを生成
- 実際の音声キャプチャは Issue #32（Whisperプロバイダー）で対応

#### 2. BotCommands への VoiceRecorder 注入

```python
# コンストラクタでオプショナル引数として受け取り
def __init__(
    self,
    tree: app_commands.CommandTree,
    db: "Database",
    router: "AIRouter",
    voice_recorder: "VoiceRecorder | None" = None,  # 追加
) -> None:
```

- VoiceRecorder が None の場合は「利用できません」メッセージを表示
- 後方互換性を維持

#### 3. コマンドの選択肢（Choices）

```python
@app_commands.choices(
    action=[
        app_commands.Choice(name="on - 録音開始", value="on"),
        app_commands.Choice(name="off - 録音停止", value="off"),
    ]
)
```

- ユーザーが選択式で操作できる
- 入力ミスを防止

#### 4. テストのモック構成

```python
@pytest.fixture
def mock_voice_recorder(self):
    recorder = MagicMock()
    recorder.is_recording.return_value = False
    recorder.start_recording = AsyncMock(return_value=1)
    recorder.stop_recording = AsyncMock(return_value=Path("/test/recording.wav"))
    return recorder
```

- VoiceRecorder 全体をモック
- 非同期メソッドは `AsyncMock` を使用

### テスト結果

```
180 passed, 12 warnings
pyright: 0 errors
ruff: All checks passed
```

### 学んだこと

1. **discord.py の音声機能は限定的**: 標準版には録音機能がない（py-cord との違い）
2. **段階的実装が有効**: 完全な機能を待たずに、セッション管理を先に実装
3. **プレースホルダーの活用**: 実装が未完でもテスト可能な状態を維持
4. **依存関係の互換性**: `discord.py[voice]` でオプショナル依存を追加
5. **コマンド引数の設計**: `app_commands.choices` でユーザー入力を制限

### 次のステップ

- Issue #32: Whisperプロバイダー実装（音声→テキスト変換）
- Issue #33: /transcribe コマンド実装
- 実際の音声キャプチャ機能の検討（py-cord 移行 or ffmpeg 連携）

---

## 2026-01-09: Codexによる追記（記録整合性の確認結果）

※本追記は整合性確認の結果をまとめたものであり、過去の記録内容は修正していません。

### 確認結果（Issue #1〜#21）

- Issue #1: 部分的に不足
  - 実施内容は整合
  - 必須ドキュメント更新の記録が薄い

- Issue #2: 部分的に不足
  - 実装内容は整合
  - CLAUDE.md強化や警告情報の記録が不足

- Issue #3: 部分的に不足
  - 実施内容は整合
  - ドキュメント更新・Issue状態更新の記録がない

- Issue #4: Issue #3に統合（単独評価対象外）

- Issue #5: 一部あいまい
  - 会話ログは更新済み
  - Development_log内で完了/次ステップの境界が不明瞭

- Issue #7: 一部あいまい
  - 会話ログは完了まで記録
  - Development_logでは「次のステップ」扱いで実施有無が不明

- Issue #8-14: 一部あいまい
  - 実装〜テストは整合
  - ドキュメント更新の裏付けが薄い

- Issue #15-17: ほぼ正しい
  - 会話ログと整合
  - 「会話ログ未作成」との記述は作成済みと矛盾するため、作成時期の注記が必要

- Issue #18-21: 概ね正しい
  - 会話ログと整合
  - 12 warningsの記録が会話ログ側にない（軽微）

### 総評

- 実装内容の事実は概ね正確。
- 記録作成やドキュメント更新の実施タイミングが曖昧な箇所が複数あり、プロセス面の信頼性は中程度。
