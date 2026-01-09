# 開発記録

このファイルは、開発の全工程・試行錯誤・技術的な背景を詳細に記録したものです。
初心者にも分かるよう、なぜその選択をしたか、何が失敗したかも含めて記録します。

---

## 2025-01-01: Issue #1 DB設計・実装

### 開始時刻: 約 XX:XX

### 目標
DEVELOPMENT_PLAN.mdに従い、データベースモデルとCRUD操作を実装する。

### 実施内容

#### Step 1: ブランチ作成
- **コマンド**: `git checkout -b feature/issue-1`
- **結果**: ✅ 成功
- **解説**: Git Flow に従い、機能ごとにブランチを切る。`feature/issue-{番号}` という命名規則はCLAUDE.mdで定義済み。

#### Step 2: テストを先に書く（TDD）
- **ファイル**: `tests/test_db.py`
- **テストケース**: TEST_PLAN.md の DB-01〜DB-08 に対応
  - DB-01: Workspace作成
  - DB-02: Room作成
  - DB-03: メッセージ保存
  - DB-04: 添付ファイル付き保存
  - DB-05: Room別メッセージ取得
  - DB-06: Workspace内検索
  - DB-07: Workspace分離（セキュリティ要件）
  - DB-08: Room間リンク

- **技術解説（TDD）**:
  - TDD = Test Driven Development（テスト駆動開発）
  - 「テストを先に書く → 失敗する → 実装する → 成功する」のサイクル
  - メリット：仕様が明確になる、実装漏れを防げる、リファクタリングしやすい

#### Step 3: モデル実装
- **ファイル**: `src/db/models.py`
- **使用ライブラリ**: SQLAlchemy 2.0（ORM）

- **技術解説（ORM）**:
  - ORM = Object-Relational Mapping
  - Pythonのクラスをデータベースのテーブルに対応させる
  - 生SQLを書かなくても、Pythonオブジェクトとして操作できる
  - 例: `workspace = Workspace(name="A社")` → INSERT文が自動生成される

- **実装したモデル**:
  | モデル | 役割 |
  |--------|------|
  | Workspace | 最上位の部屋（請負者ごと） |
  | Room | 中の部屋（チャンネル） |
  | RoomLink | Room間の情報共有設定 |
  | Message | チャットメッセージ |
  | Attachment | 添付ファイル |
  | Reminder | リマインダー（Phase 2用に先行定義） |

#### Step 4: Database操作クラス実装
- **ファイル**: `src/db/database.py`
- **実装したメソッド**:
  - `create_workspace()`, `create_room()`, `create_room_link()`
  - `save_message()`, `save_attachment()`
  - `get_messages_by_room()`, `search_messages()`

- **設計判断**:
  - `search_messages()` は Workspace ID を必須引数にした
  - **理由**: セキュリティ要件「Workspace AのデータをBに見せない」を強制するため
  - これにより、うっかり他Workspaceのデータを返すバグを防げる

#### Step 5: テスト実行（1回目）
- **コマンド**: `uv run pytest tests/test_db.py -v`
- **結果**: ❌ **エラー発生**
  ```
  (eval):1: command not found: uv
  ```

- **原因**: uvがインストールされていなかった
- **解決策**: uvをインストール
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **技術解説（uv）**:
  - uv = 高速なPythonパッケージマネージャー
  - pipの10〜100倍速い（Rust製）
  - `uv sync` で依存関係をインストール、`uv run` で仮想環境内で実行

#### Step 6: 依存関係インストール
- **コマンド**: `uv sync --all-extras`
- **結果**: ✅ 成功（73パッケージ）

#### Step 7: テスト実行（2回目）
- **コマンド**: `uv run pytest tests/test_db.py -v`
- **結果**: ✅ **成功** (10 passed in 2.28s)
- 全テストケースがパス

#### Step 8: リントチェック（1回目）
- **コマンド**: `uv run ruff check src/`
- **結果**: ❌ **エラー発生**
  ```
  E501 Line too long (102 > 100)
  ```
  3箇所で行が100文字を超えていた。

- **原因**: インラインコメントが長すぎた
  ```python
  # 問題のコード
  room_type: Mapped[str] = mapped_column(String(50), nullable=False)  # topic / member / aggregation
  ```

- **技術解説（ruff）**:
  - ruff = 高速なPythonリンター/フォーマッター
  - E501 = 行が長すぎる（PEP 8違反）
  - pyproject.toml で `line-length = 100` に設定済み

- **解決策**: コメントを別行に移動
  ```python
  # 修正後
  # Room type: topic / member / aggregation
  room_type: Mapped[str] = mapped_column(String(50), nullable=False)
  ```

#### Step 9: リントチェック（2回目）
- **コマンド**: `uv run ruff check src/`
- **結果**: ✅ **成功** (All checks passed!)

#### Step 10: コミット（1回目）
- **コマンド**: `git add ... && git commit -m "..."`
- **結果**: ❌ **エラー発生**（pre-commitフック）
  ```
  F841 Local variable `link2` is assigned to but never used
  ```

- **原因**: テストコードで `link2` を作成したが、assertで使っていなかった
  ```python
  # 問題のコード
  link2 = db.create_room_link(...)  # 作成したのに使ってない
  ```

- **技術解説（pre-commit）**:
  - pre-commit = コミット前に自動でチェックを実行するツール
  - ruff、フォーマッター、末尾空白チェックなどを自動実行
  - 問題があるとコミットを中断してくれる
  - `.pre-commit-config.yaml` で設定

- **解決策**: `link2` にもassertを追加
  ```python
  # 修正後
  assert link1.id is not None
  assert link2.id is not None  # ← 追加
  ```

#### Step 11: コミット（2回目）
- **コマンド**: `git add ... && git commit -m "feat: add database models and operations"`
- **結果**: ✅ **成功**
  ```
  [feature/issue-1 41e9ae4] feat: add database models and operations
   4 files changed, 827 insertions(+)
  ```
- pre-commitフックも全てパス

#### Step 12: Push
- **コマンド**: `git push -u origin feature/issue-1`
- **結果**: ✅ **成功**
- GitHubにブランチがプッシュされた

#### Step 13: PR作成を試みる
- **コマンド**: `gh issue create ...`
- **結果**: ❌ **エラー発生**
  ```
  command not found: gh
  ```

- **原因**: GitHub CLI（gh）がインストールされていない
- **追加で試みた**: `brew install gh`
- **結果**: ❌ `command not found: brew`
- Homebrewもインストールされていなかった

- **技術解説（GitHub CLI）**:
  - gh = GitHubの公式CLI
  - Issue作成、PR作成、レビューなどをコマンドラインから実行できる
  - 今回は手動でPR作成するか、ローカルでmainにマージする方針に変更

### 発見した課題（ISSUES_STATUS.md に追加すべき）
| 課題 | 優先度 | 対応 |
|------|--------|------|
| ghコマンドがない | 低 | 手動でインストールするか、PR作成はWeb UIで |

### 成果物
| ファイル | 内容 |
|----------|------|
| src/db/models.py | 6モデル定義（172行） |
| src/db/database.py | CRUD操作（260行） |
| src/db/__init__.py | エクスポート設定 |
| tests/test_db.py | 10テストケース（329行） |

### テスト結果
```
tests/test_db.py::TestWorkspace::test_create_workspace PASSED
tests/test_db.py::TestWorkspace::test_create_workspace_with_ai_config PASSED
tests/test_db.py::TestRoom::test_create_room PASSED
tests/test_db.py::TestRoom::test_create_aggregation_room PASSED
tests/test_db.py::TestMessage::test_save_message PASSED
tests/test_db.py::TestMessage::test_save_message_with_attachment PASSED
tests/test_db.py::TestMessage::test_get_messages_by_room PASSED
tests/test_db.py::TestMessage::test_search_messages_in_workspace PASSED
tests/test_db.py::TestWorkspaceIsolation::test_workspace_isolation PASSED
tests/test_db.py::TestRoomLink::test_room_link PASSED

============================== 10 passed ==============================
```

### 学んだこと
1. **uvのインストールが必要**: 新しい環境では最初にuvをインストールする
2. **ruffの行長制限**: コメントも含めて100文字以内に収める
3. **pre-commitは強力**: 未使用変数も検出してくれる
4. **セキュリティ設計**: Workspace分離はAPI設計時点で強制する

### 次のステップ
- mainにマージする
- Issue #2（Discord Bot基盤）に進む

---

## 2025-01-04: Issue #2 Discord Bot基盤

### 開始時刻: 約 13:48

### 目標
Discord Botの基盤を実装し、メッセージイベントを受信できるようにする。

### 実施内容

#### Step 1: ブランチ作成
- **コマンド**: `git checkout -b feature/issue-2`
- **結果**: ✅ 成功
- **解説**: Issue #1と同じく、feature/issue-{番号} の命名規則に従う。

#### Step 2: テストを先に書く（TDD）
- **ファイル**: `tests/test_bot.py`
- **テストケース**: 10ケース
  - BotClient作成
  - Intents設定確認
  - カスタムIntents
  - MessageListener作成
  - Botメッセージの無視
  - ユーザーメッセージの処理
  - DMメッセージ処理（guild=None）
  - on_readyコールバック
  - コールバックなしでの動作
  - メッセージコールバック

- **技術解説（discord.py）**:
  - discord.py = Discord Bot開発用の公式Pythonライブラリ
  - Intents = Botが受信できるイベントの種類を指定する仕組み
  - messages: メッセージイベントを受信
  - message_content: メッセージの内容を取得（2022年以降は明示的に有効化が必要）
  - guilds: サーバー情報を取得

- **技術解説（TypedDict）**:
  - TypedDict = 辞書の型を厳密に定義できる
  - 例: `MessageData` で返り値の型を明確にする
  - エディタの補完が効くようになり、typoを防げる

#### Step 3: BotClient実装
- **ファイル**: `src/bot/client.py`
- **実装内容**:
  - `discord.Client` を継承
  - デフォルトIntentsを自動設定（messages, message_content, guilds）
  - on_readyコールバック対応
  - 型ヒント完備、docstring完備（Google style）

- **設計判断**:
  - IntentsをNoneにできるようにした
  - **理由**: カスタムIntentsを渡せるようにして、テスト時や将来の拡張に対応
  - デフォルトはメッセージ監視に必要な最小限のIntentsを設定

- **技術解説（継承）**:
  - `class BotClient(discord.Client)` = discord.Clientを継承
  - discord.Clientの機能を全て使える + 独自機能を追加できる
  - `super().__init__(...)` で親クラスの初期化を呼び出す

#### Step 4: MessageListener実装
- **ファイル**: `src/bot/listeners.py`
- **実装内容**:
  - `on_message()` メソッド: メッセージイベントを処理
  - Botからのメッセージは無視（無限ループ防止）
  - メッセージ情報を抽出（sender, content, guild_id, channel_id, attachments）
  - DMメッセージ対応（guild=None）
  - `GuildListener` も実装（サーバー参加/退出イベント）

- **設計判断**:
  - `on_message()` の戻り値を `MessageData | None` にした
  - **理由**: Botメッセージの場合はNoneを返し、ユーザーメッセージのみデータを返す
  - これにより、呼び出し側で `if data:` と簡潔に書ける

- **技術解説（添付ファイル抽出）**:
  - `message.attachments` は discord.Attachment のリスト
  - 必要な情報（id, filename, url, size, content_type）を辞書に変換
  - Phase 2でファイル保存に使う

#### Step 5: テスト実行（1回目）
- **コマンド**: `source .venv/bin/activate && python -m pytest tests/test_bot.py -v`
- **結果**: ✅ **成功** (10 passed in 1.43s)
- **解説**: 今回は `uv run` が使えなかったので、venv経由で実行
  - `.venv/bin/activate` で仮想環境を有効化
  - `python -m pytest` でpytestを実行

- **技術解説（モック）**:
  - `MagicMock` = テスト用の偽物オブジェクト
  - 例: `mock_message.author.bot = True` で、Botからのメッセージを模擬
  - discord.pyの実際のMessageオブジェクトを使わずにテストできる

#### Step 6: リントチェック
- **コマンド**: `source .venv/bin/activate && ruff check src/`
- **結果**: ✅ **成功** (All checks passed!)
- **コマンド**: `source .venv/bin/activate && ruff format src/ --check`
- **結果**: ✅ **成功** (10 files already formatted)
- **コマンド**: `source .venv/bin/activate && pyright src/`
- **結果**: ✅ **成功** (0 errors, 0 warnings)

- **学んだこと**: 型ヒントを最初から書くと、pyrightチェックが一発で通る

#### Step 7: 全テスト実行
- **コマンド**: `source .venv/bin/activate && python -m pytest tests/ -v`
- **結果**: ✅ **成功** (20 passed in 0.29s)
  - Botテスト: 10ケース
  - DBテスト: 10ケース（既存）
- **解説**: 既存のテストにも影響なし

#### Step 8: コミット（1回目）
- **コマンド**: `git add ... && git commit -m "..."`
- **結果**: ❌ **エラー発生**（pre-commitフック）
  ```
  ruff.....................................................................Failed
  - hook id: ruff
  - files were modified by this hook
  Found 1 error (1 fixed, 0 remaining).
  ```

- **原因**: ruffが自動でimport文を修正した
  - `from unittest.mock import AsyncMock, MagicMock, patch` → `patch` が未使用だった
  - ruffが `from unittest.mock import AsyncMock, MagicMock` に自動修正

- **解決策**: 修正されたファイルを再度add
  ```bash
  git add -u && git commit -m "..."
  ```

- **技術解説（pre-commitの自動修正）**:
  - ruffは未使用importを自動削除する
  - pre-commitフックが修正した場合、コミットは失敗する
  - 修正後のファイルを再度addして、再コミットすればOK

#### Step 9: コミット（2回目）
- **コマンド**: `git add -u && git commit -m "feat: implement Discord Bot foundation"`
- **結果**: ✅ **成功**
  ```
  [feature/issue-2 3d529a4] feat: implement Discord Bot foundation (Issue #2)
   4 files changed, 410 insertions(+)
  ```
- pre-commitフックも全てパス

#### Step 10: Push & Merge
- **コマンド**: `git push -u origin feature/issue-2`
- **結果**: ✅ **成功**
- **コマンド**: `git checkout main && git merge feature/issue-2 --no-ff`
- **結果**: ✅ **成功**
- **コマンド**: `git push origin main`
- **結果**: ✅ **成功**

#### Step 11: ドキュメント更新
- **更新ファイル**:
  - `docs/DEVELOPMENT_PLAN.md`: Issue #2を完了に変更
  - `docs/ISSUES_STATUS.md`: Issue #2を完了課題に追加、課題#2を完了に移動

- **コマンド**: `git add docs/ && git commit -m "docs: update status for Issue #2 completion"`
- **結果**: ✅ **成功**

### 発見した課題
- **課題**: Issue完了時の必須作業（DEVELOPMENT_LOG.md、CONVERSATION_LOG_*.md）を忘れていた
- **優先度**: 高
- **対応**: CLAUDE.mdの「Issue完了時の必須作業」を再確認、今回から徹底する

### 成果物
| ファイル | 内容 |
|----------|------|
| src/bot/client.py | BotClient実装（77行） |
| src/bot/listeners.py | MessageListener、GuildListener実装（157行） |
| src/bot/__init__.py | エクスポート設定（18行） |
| tests/test_bot.py | 10テストケース（155行） |

### テスト結果
```
tests/test_bot.py::TestBotClient::test_create_bot_client PASSED
tests/test_bot.py::TestBotClient::test_bot_client_has_correct_intents PASSED
tests/test_bot.py::TestBotClient::test_bot_client_with_custom_intents PASSED
tests/test_bot.py::TestMessageListener::test_create_message_listener PASSED
tests/test_bot.py::TestMessageListener::test_on_message_ignores_bot_messages PASSED
tests/test_bot.py::TestMessageListener::test_on_message_processes_user_messages PASSED
tests/test_bot.py::TestMessageListener::test_on_message_handles_dm PASSED
tests/test_bot.py::TestBotReady::test_on_ready_callback_is_called PASSED
tests/test_bot.py::TestBotReady::test_on_ready_without_callback PASSED
tests/test_bot.py::TestMessageListenerCallback::test_message_callback_is_called PASSED

============================== 20 passed (including DB tests) ==============================
```

### 学んだこと
1. **TypedDict活用**: 辞書の型定義で可読性・安全性が向上
2. **継承の設計**: discord.Clientを継承して必要な機能だけ追加
3. **pre-commitの自動修正**: 修正後は再addが必要
4. **venv経由の実行**: `uv run` が使えない環境でも `source .venv/bin/activate` で対応可能
5. **Issue完了時の必須作業**: DEVELOPMENT_LOG.md と CONVERSATION_LOG_*.md は忘れずに記録する

### 次のステップ
- CONVERSATION_LOG_ISSUE2.md を作成
- Issue #3（メッセージ保存）に進む

---

## 2025-01-04: Issue #3 メッセージ＋添付ファイル保存（統合版）

### 開始時刻: 約 19:00

### 目標
- Discord環境を構築し、実際に動作確認できるようにする
- メッセージ受信時にDBに自動保存する機能を実装
- 添付ファイル（画像など）をローカルに保存する機能を実装
- Issue #3と#4を統合して効率化

### 背景
ユーザーからの重要な指摘:
- 「ずっとバックエンド作っているよね？実際に動かして試せる環境を作った方がよくない？」
- Issue #3と#4（メッセージ保存と添付ファイル保存）は密結合しているので統合することに決定
- 先にDiscord環境を構築し、手動テストできるようにする方針

### 実施内容

#### Step 1: 計画作成
- ユーザーと議論し、以下を決定:
  - Issue #3と#4を統合
  - Discord構成: 1サーバー（WorkspaceA）、3チャンネル（room1, room2, room3-aggregation）
  - テスト方法: 自分のアカウントで手動テスト

#### Step 2: ブランチ作成
- **コマンド**: `git checkout -b feature/issue-3`
- **結果**: ✅ 成功

#### Step 3: Discord環境セットアップ手順書作成
- **ファイル**: `docs/DISCORD_SETUP.md`
- **内容**:
  - Discord Developer PortalでBot作成手順
  - MESSAGE CONTENT INTENT有効化（重要）
  - Bot権限設定
  - テスト用サーバー作成手順
  - 動作確認方法

#### Step 4: 依存パッケージ追加
- **ファイル**: `pyproject.toml`
- **追加**:
  - `aiohttp>=3.9.0` - HTTPクライアント（添付ファイルダウンロード用）
  - `python-dotenv>=1.0.0` - 環境変数読み込み
- **コマンド**: `uv sync --extra dev`
- **結果**: ✅ 成功

#### Step 5: ストレージ層実装
- **ファイル**:
  - `src/storage/base.py` - 抽象基底クラス（将来Google Drive等に差し替え可能）
  - `src/storage/local.py` - ローカルファイルシステム実装
  - `src/storage/__init__.py` - エクスポート設定

- **設計判断**:
  - ディレクトリ構成: `{base_path}/{workspace_id}/{room_id}/{date}/`
  - ファイル名重複時は連番を付与（`photo.jpg` → `photo_1.jpg`）
  - 非同期I/O（aiofiles）でパフォーマンス確保

- **技術解説（抽象化）**:
  - `StorageProvider` 抽象クラスを定義
  - `LocalStorage` はローカル実装
  - 将来 `GoogleDriveStorage` を追加しても、同じインターフェースで使える
  - CLAUDE.mdの「抽象化を意識」に従った設計

#### Step 6: ストレージテスト
- **ファイル**: `tests/test_storage.py`
- **テストケース**: 9件
  - ファイル保存
  - ディレクトリ構成確認
  - ファイル名重複処理
  - 複数回の重複
  - ファイル取得
  - 存在しないファイルでエラー
  - ファイル削除
  - 存在しないファイル削除
  - バイナリファイル（画像）保存

- **コマンド**: `uv run pytest tests/test_storage.py -v`
- **結果**: ✅ **成功** (9 passed)

#### Step 7: メッセージハンドラー実装
- **ファイル**: `src/bot/handlers.py`
- **実装内容**:
  - `MessageHandler` クラス
  - メッセージ受信時にWorkspace/Room自動作成
  - メッセージをDBに保存
  - 添付ファイルをダウンロードしてローカル保存
  - メッセージタイプ判定（text/image/video/voice）

- **設計判断**:
  - DMはスキップ（guild_id=Noneの場合）
  - Workspace/Roomが存在しない場合は自動作成
  - ファイルタイプはcontent_typeから判定

- **技術解説（aiohttp）**:
  - `aiohttp.ClientSession()` で非同期HTTPリクエスト
  - Discordの添付ファイルURLからファイルをダウンロード
  - `async with session.get(url)` でストリーミング取得

#### Step 8: ハンドラーテスト
- **ファイル**: `tests/test_handler.py`
- **テストケース**: 13件
  - Workspace/Room自動作成
  - メッセージDB保存
  - DMスキップ
  - Room分離（Room1とRoom2のデータが混ざらない）
  - 画像添付ファイル処理
  - メッセージタイプ判定（text/image/video/voice）
  - ファイルタイプ判定
  - 既存Workspace/Room再利用
  - Room3からRoom1のデータが見える（RoomLink経由）
  - Room2からRoom1のデータが見えない

- **コマンド**: `uv run pytest tests/test_handler.py -v`
- **結果**: ❌ 1件失敗（discord_message_idのUNIQUE制約違反）
- **原因**: テストで同じmessage_idを使っていた
- **解決**: テストで異なるmessage_idを使用
- **再実行**: ✅ **成功** (13 passed)

#### Step 9: エントリーポイント作成
- **ファイル**: `src/main.py`
- **実装内容**:
  - 環境変数からDISCORD_TOKEN読み込み
  - DB初期化
  - ストレージ初期化
  - MessageHandler初期化
  - Bot起動

- **技術解説（dotenv）**:
  - `load_dotenv()` で `.env` ファイルを読み込み
  - `os.getenv("DISCORD_TOKEN")` で環境変数取得
  - `.env` は `.gitignore` に含まれているので、シークレットが漏れない

#### Step 10: 全テスト・リント確認
- **コマンド**: `uv run pytest tests/ -v`
- **結果**: ✅ **成功** (42 passed)
- **コマンド**: `uv run ruff check src/`
- **結果**: ✅ **成功** (All checks passed!)
- **コマンド**: `uv run pyright src/`
- **結果**: ✅ **成功** (0 errors, 0 warnings)

#### Step 11: 手動テスト

**Discord環境構築（ユーザー作業）:**
1. Discord Developer PortalでBot作成
2. MESSAGE CONTENT INTENT有効化
3. テストサーバー作成（room1, room2, room3-aggregation）
4. Bot招待
5. `.env` ファイル作成

**トラブルシューティング:**
- 最初、メッセージが保存されなかった
- 原因: MESSAGE CONTENT INTENT が無効だった
- 解決: Developer Portalで有効化 → Bot再起動

**テスト結果:**
| テスト | 結果 |
|--------|------|
| Room1にテキストメッセージ | ✅ message_id=1として保存 |
| Room2にテキストメッセージ | ✅ 別のRoom（id=2）として保存 |
| Room1に画像送信 | ✅ `data/files/1/1/2026-01-04/IMG_4106.jpg` に保存 |

**DB確認:**
```sql
-- Rooms
1|Room-1457257672784089120|1457257672784089120  -- room1
2|Room-1457257846654767145|1457257846654767145  -- room2

-- Messages
1|1|kn_0303|test|text
2|2|kn_0303|test2|text
3|1|kn_0303||image
```

### 成果物
| ファイル | 内容 |
|----------|------|
| docs/DISCORD_SETUP.md | Discordセットアップ手順書 |
| src/storage/base.py | ストレージ抽象クラス（63行） |
| src/storage/local.py | ローカルストレージ実装（103行） |
| src/storage/__init__.py | エクスポート設定 |
| src/bot/handlers.py | メッセージハンドラー（210行） |
| src/main.py | Botエントリーポイント（81行） |
| tests/test_storage.py | ストレージテスト（9件） |
| tests/test_handler.py | ハンドラーテスト（13件） |

### テスト結果
```
tests/test_bot.py: 10 passed
tests/test_db.py: 10 passed
tests/test_handler.py: 13 passed
tests/test_storage.py: 9 passed

============================== 42 passed ==============================
```

### 学んだこと
1. **実環境テストの重要性**: ユニットテストだけでなく、実際のDiscord環境でテストすることでMESSAGE CONTENT INTENTの問題を発見できた
2. **抽象化の設計**: StorageProviderを抽象化したことで、将来Google Driveに移行しやすくなった
3. **Issue統合の判断**: 密結合した機能（メッセージ保存と添付ファイル保存）は統合して実装する方が効率的
4. **環境変数管理**: `.env` + `python-dotenv` でシークレット管理が簡単
5. **非同期処理**: aiofiles + aiohttpで非同期I/Oを実現

### 次のステップ
- コミット・プッシュ
- mainにマージ
- Issue #5（Workspace/Room分離の強化）に進む

---

## 2025-01-04: Issue #5 Workspace/Room分離

### 開始時刻: 約 21:00

### 目標
Workspace/Room分離が正しく動作していることを確認する。

### 背景
ユーザーからの重要な質問:
- 「リアルタイムにメッセージを取り込む方式ではなく、定期的（n時間に一回）や命令時に差分を取り込む方式が良いのでは？」
- 「後から変更が難しくなると嫌」
- 「サーバーコストも踏まえて専門家で議論して」

### 実施内容

#### Step 1: 専門家視点での議論

**9人の専門家で「リアルタイム vs バッチ処理」を分析:**

| 専門家 | 意見 |
|--------|------|
| ソフトウェアエンジニア | 現在の`MessageHandler`は抽象化されており、どちらの方式にも対応可能 |
| Python/Discord Expert | 両方併用可能。`on_message`（リアルタイム）+ `/sync`コマンド（バッチ）|
| セキュリティエンジニア | 両方式ともセキュリティ上の差はなし |
| ドメインエキスパート | リアルタイム通知も必要、まとめて確認したいケースも。両方あると便利 |
| コスト観点 | Phase 1（ローカル）ではコスト差なし。Phase 3（クラウド）ではバッチのみなら$5程度削減可能だがリアルタイム通知が使えなくなる |

**結論:**
- 今すぐ変更は不要
- 後からの変更も容易（`MessageHandler`が抽象化されているため）
- 推奨: 両方併用（リアルタイム + 差分取り込みコマンド）
- 実装タイミング: Phase 1完了後でOK

#### Step 2: Issue #5 の範囲確認

**DEVELOPMENT_PLAN.md の確認:**
- Issue #5: Workspace/Room分離
- 完了条件: 構造通りに分離確認

**現状の確認:**
- DBレベルでの分離: ✅ テスト済み（`test_workspace_isolation`）
- Handlerレベルでの分離: ✅ テスト済み（`test_room_isolation`）
- RoomLinkモデル: ✅ テスト済み（`test_room_link`）
- RoomLink経由の参照: ✅ テスト済み（`test_room3_can_see_room1_via_link`）

**ユーザーからの指摘:**
「今はサーバーがAしかない状態で、Bがないから検証しようとしてもできない状態なんじゃない？」

**分析:**
- ユニットテスト: ✅ 分離は確認済み（モックで検証）
- 実際のDiscord: サーバーAしかない → Bとの分離を実機で確認できない

#### Step 3: リスク評価

**手戻りリスク分析:**

| レイヤー | 実装 | リスク |
|----------|------|--------|
| DB | `workspace_id` を WHERE 条件に必ず含める | **低** - SQLで強制 |
| Handler | `guild_id` → `workspace_id` マッピング | **低** - シンプルな1:1対応 |
| Storage | `{workspace_id}/{room_id}/` でディレクトリ分離 | **低** - パスで物理分離 |

**なぜ低リスクか:**
1. ロジックが単純: `guild_id`（DiscordサーバーID）をそのまま Workspace に対応させるだけ
2. DBで強制分離: クエリに `workspace_id` がないと動かない設計
3. Issue #3 で手動テスト済み: `guild_id` が正しく取得できることは確認済み

**結論:**
- 手戻りリスク: 低
- 「コードレベルで完了」として進める
- 実機テスト（複数サーバー）は Issue #14（試験運用準備）で実施

#### Step 4: ドキュメント更新

**更新ファイル:**
- `docs/DEVELOPMENT_PLAN.md`: Issue #5 を完了に変更、注記追加
- `docs/ISSUES_STATUS.md`: Issue #5 を完了課題に追加
- Issue #14 に「複数サーバー実機テスト（#5確認含む）」を追記

#### Step 5: 記録漏れの発見（失敗）

**ユーザーからの指摘:**
「開発記録とか会話記録残していないよね？」

**原因分析:**
1. Issue #5 は「コード変更なし、ドキュメント更新のみ」だったため、「Issue完了」という認識が薄かった
2. CLAUDE.md の「Issue完了時の必須作業」セクションを確認しなかった
3. TodoWrite を使っていなかったため、必須タスクが漏れた

**根本原因:**
- 「コード変更がない = 軽いタスク = 記録不要」と無意識に判断してしまった
- CLAUDE.md を読み返す習慣がなかった

### 成果物
| ファイル | 内容 |
|----------|------|
| docs/DEVELOPMENT_PLAN.md | Issue #5 完了、注記追加、Issue #14 更新 |
| docs/ISSUES_STATUS.md | Issue #5 を完了課題に追加 |

### 学んだこと
1. **コード変更がなくても記録は必須**: Issue完了時の必須作業はコード有無に関係なく実行する
2. **TodoWriteの活用**: Issue開始時に必ずTodoリストを作成し、記録作業を含める
3. **CLAUDE.mdの再確認**: Issue完了前に「Issue完了時の必須作業」を確認する習慣をつける
4. **専門家視点の有用性**: 9人の専門家視点で議論することで、多角的な分析ができる
5. **リスク評価の重要性**: 「後から変更が難しくなる」リスクを事前に評価することで、意思決定が容易になる

### 次のステップ
- CONVERSATION_LOG_ISSUE5.md を作成
- CLAUDE.md に再発防止策を強化
- Issue #7（AI基盤）に進む

---

## 2025-01-05: Issue #7 AI基盤（base, router）

### 開始時刻: 約 00:30

### 目標
AIプロバイダーの抽象化レイヤーとルーティング機能を実装する。

### 背景
- 複数のAIプロバイダー（OpenAI, Anthropic, Google, Groq, Local）を統一的に扱いたい
- 機能（purpose）ごとに異なるプロバイダーを使い分けたい
- Workspace/Room単位で設定を上書きできるようにしたい

### 実施内容

#### Step 1: ブランチ作成
- **コマンド**: `git checkout -b feature/issue-7`
- **結果**: ✅ 成功

#### Step 2: TDDでテストを先に書く
- **ファイル**: `tests/test_ai_router.py`
- **テストケース**: 18件（TEST_PLAN.md の RTR-01〜RTR-05 に対応）

| テスト | 内容 |
|--------|------|
| RTR-01 | デフォルト設定でプロバイダー取得 |
| RTR-02 | Workspace設定で上書き |
| RTR-03 | Room設定で上書き（Workspaceより優先） |
| RTR-04 | 未設定プロバイダーでエラー |
| RTR-05 | フォールバックプロバイダー情報取得 |
| 追加 | バリデーション、設定読み込み、環境変数展開 |

- **技術解説（TDD）**:
  - まずテストを書いてから実装することで、仕様が明確になる
  - テストが「設計書」の役割を果たす
  - 実装後の動作確認が容易

#### Step 3: base.py 実装
- **ファイル**: `src/ai/base.py`
- **実装内容**:
  - `AIProvider` 抽象基底クラス
  - `generate()`: テキスト生成（抽象メソッド）
  - `embed()`: ベクトル化（抽象メソッド）
  - `generate_with_context()`: コンテキスト付き生成（デフォルト実装）
  - エラークラス: `AIProviderError`, `AIProviderNotConfiguredError`, `AIQuotaExceededError`, `AIConnectionError`, `AIResponseError`

- **技術解説（抽象基底クラス）**:
  - `ABC` (Abstract Base Class) を継承
  - `@abstractmethod` で抽象メソッドを定義
  - 実装クラス（OpenAIProvider等）は必ずこれらを実装する必要がある
  - 共通インターフェースにより、プロバイダーの差し替えが容易

- **設計判断**:
  - `name` と `model` をプロパティとして定義
  - **理由**: プロバイダー名とモデル名はインスタンス作成後に変更されないため、プロパティが適切
  - `generate_with_context()` はデフォルト実装を提供
  - **理由**: 多くのプロバイダーで同様の処理になるため、継承先での重複を避ける

#### Step 4: router.py 実装
- **ファイル**: `src/ai/router.py`
- **実装内容**:
  - `AIRouter` クラス
  - `get_provider_info()`: 機能に応じたプロバイダー情報を取得
  - `get_fallback_info()`: フォールバックプロバイダー情報のリスト取得
  - `get_provider_config()`: プロバイダーの詳細設定取得
  - `from_yaml()`: YAMLファイルから設定読み込み（環境変数展開対応）
  - `from_default_config()`: デフォルト設定ファイルから読み込み

- **技術解説（ルーティングの優先順位）**:
  ```
  1. Room設定（room_overrides）
  2. Workspace設定（workspace_overrides）
  3. グローバル設定（ai_routing）
  ```
  - 例: 特定のRoomだけローカルLLMを使いたい場合、room_overridesで上書き可能
  - 例: 特定のWorkspaceだけ安価なモデルを使いたい場合、workspace_overridesで上書き可能

- **技術解説（環境変数展開）**:
  - config.yaml で `${OPENAI_API_KEY}` のような形式で環境変数を参照可能
  - `_expand_env_vars()` メソッドで正規表現を使って展開
  - セキュリティ: APIキーをconfig.yamlに直書きせずに済む

- **設計判断**:
  - `AIRouter` はプロバイダー情報（provider名, model名）のみを返す
  - **理由**: 実際のプロバイダーインスタンス生成は Issue #8 以降で実装
  - 責務の分離: ルーティング判断と インスタンス生成を分ける

#### Step 5: __init__.py 更新
- **ファイル**: `src/ai/__init__.py`
- **実装内容**:
  - 主要クラスとエラークラスをエクスポート
  - docstringでパッケージの概要を記述

#### Step 6: テスト実行（1回目）
- **コマンド**: `source .venv/bin/activate && python -m pytest tests/test_ai_router.py -v`
- **結果**: ✅ **成功** (18 passed in 0.03s)

#### Step 7: リントチェック（1回目）
- **コマンド**: `ruff check src/ai/ tests/test_ai_router.py`
- **結果**: ❌ **エラー発生**
  ```
  F541 f-string without any placeholders
  F401 `unittest.mock.AsyncMock` imported but unused
  F401 `unittest.mock.MagicMock` imported but unused
  F401 `unittest.mock.patch` imported but unused
  ```

- **原因**:
  1. `f"provider lookup"` で `f` が不要
  2. テストで未使用のインポートがあった

- **解決策**:
  1. `f"provider lookup"` → `"provider lookup"`
  2. 未使用インポートを削除

#### Step 8: リントチェック（2回目）
- **コマンド**: `ruff check src/ai/ tests/test_ai_router.py`
- **結果**: ✅ **成功** (All checks passed!)

- **コマンド**: `pyright src/ai/`
- **結果**: ✅ **成功** (0 errors, 0 warnings, 0 informations)

#### Step 9: 全テスト実行
- **コマンド**: `python -m pytest tests/ -v`
- **結果**: ✅ **成功** (60 passed in 0.33s)
  - AI Router: 18件
  - Bot: 10件
  - DB: 10件
  - Handler: 13件
  - Storage: 9件

#### Step 10: コミット
- **コマンド**: `git add ... && git commit -m "feat: implement AI base layer and router (Issue #7)"`
- **結果**: ❌ → ✅（ruff-formatが自動修正後、再コミットで成功）
  ```
  [feature/issue-7 38a76e1] feat: implement AI base layer and router (Issue #7)
   4 files changed, 846 insertions(+)
  ```

### 成果物
| ファイル | 内容 |
|----------|------|
| src/ai/base.py | AIProvider抽象クラス、エラークラス（210行） |
| src/ai/router.py | AIRouter（255行） |
| src/ai/__init__.py | エクスポート設定（35行） |
| tests/test_ai_router.py | 18テストケース（280行） |

### テスト結果
```
tests/test_ai_router.py::TestAIRouter::test_get_default_provider PASSED
tests/test_ai_router.py::TestAIRouter::test_get_default_provider_rag PASSED
tests/test_ai_router.py::TestAIRouter::test_workspace_override PASSED
tests/test_ai_router.py::TestAIRouter::test_workspace_override_not_configured PASSED
tests/test_ai_router.py::TestAIRouter::test_room_override PASSED
tests/test_ai_router.py::TestAIRouter::test_room_override_priority PASSED
tests/test_ai_router.py::TestAIRouter::test_room_override_not_configured PASSED
tests/test_ai_router.py::TestAIRouter::test_provider_not_configured PASSED
tests/test_ai_router.py::TestAIRouter::test_provider_not_in_providers PASSED
tests/test_ai_router.py::TestAIRouter::test_get_fallback_providers PASSED
tests/test_ai_router.py::TestAIRouter::test_get_fallback_empty_if_not_configured PASSED
tests/test_ai_router.py::TestAIRouterValidation::test_empty_config PASSED
tests/test_ai_router.py::TestAIRouterValidation::test_missing_ai_providers PASSED
tests/test_ai_router.py::TestAIProviderBase::test_mock_provider_generate PASSED
tests/test_ai_router.py::TestAIProviderBase::test_mock_provider_embed PASSED
tests/test_ai_router.py::TestAIProviderBase::test_provider_properties PASSED
tests/test_ai_router.py::TestConfigLoading::test_router_from_yaml_file PASSED
tests/test_ai_router.py::TestConfigLoading::test_router_from_yaml_with_env_vars PASSED

============================== 60 passed (全テスト) ==============================
```

### 学んだこと
1. **抽象化の設計**: 抽象基底クラスで共通インターフェースを定義することで、プロバイダーの差し替えが容易になる
2. **ルーティングの優先順位**: Room > Workspace > グローバルの優先順位で設定を上書きできる設計
3. **環境変数展開**: config.yamlで `${VAR}` 形式を使うことで、シークレットをコードに含めない
4. **TDDの効果**: テストを先に書くことで、実装の方向性が明確になり、手戻りが少ない
5. **責務の分離**: ルーティング判断とインスタンス生成を分けることで、各クラスの責務が明確になる

### 次のステップ
- CONVERSATION_LOG_ISSUE7.md を作成
- DEVELOPMENT_PLAN.md / ISSUES_STATUS.md を更新
- mainにマージ
- Issue #8（OpenAIプロバイダー）に進む

---

## 2025-01-05: Issue #8-14 AI連携・統合テスト・試験運用準備

### 開始時刻: 約 01:00

### 目標
Phase 1の最終段階として、以下を完了する:
- Issue #8: OpenAIプロバイダー実装
- Issue #9: /summaryコマンド実装
- Issue #10: /searchコマンド実装
- Issue #11: 統合Room通知
- Issue #12: 他AIプロバイダー（Anthropic, Google, Groq）
- Issue #13: 統合テスト
- Issue #14: 試験運用準備

### 実施内容

#### Issue #8: OpenAIプロバイダー実装

**ファイル**: `src/ai/providers/openai.py`

**実装内容**:
- `OpenAIProvider` クラス
- `generate()`: テキスト生成（Chat Completions API）
- `embed()`: ベクトル化（Embeddings API）
- エラーハンドリング（RateLimitError, AuthenticationError等）

**技術解説**:
- `AsyncOpenAI` を使用して非同期API呼び出し
- `ChatCompletionMessageParam` で型安全なメッセージ構築
- generate_optionsで柔軟なパラメータ指定（temperature, max_tokens等）

**テスト**: `tests/test_openai_provider.py` - 9件

---

#### Issue #9: /summaryコマンド実装

**ファイル**:
- `src/ai/summarizer.py`
- `src/bot/commands.py`

**実装内容**:
- `Summarizer` クラス: メッセージを要約
- `/summary [days]` スラッシュコマンド
- 直近n日間のメッセージを取得し、AIで要約

**技術解説（スラッシュコマンド）**:
- `app_commands.CommandTree` でコマンドを登録
- `@tree.command()` デコレータでコマンド定義
- Discord UIでオートコンプリートが効く

**テスト**: `tests/test_commands.py` - 10件

---

#### Issue #10: /searchコマンド実装

**ファイル**: `src/bot/commands.py` に追加

**実装内容**:
- `/search {keyword}` スラッシュコマンド
- Workspace内のメッセージをキーワード検索
- 結果をDiscord Embedで表示

**設計判断**:
- 検索結果は最大10件に制限
- **理由**: Discord Embedの文字数制限（4096文字）を超えないため

---

#### Issue #11: 統合Room通知

**ファイル**:
- `src/bot/notifier.py`
- `src/db/database.py` に追加メソッド

**実装内容**:
- `AggregationNotifier` クラス
- `notify_new_message()`: メッセージを統合Roomに通知
- `_find_similar_messages()`: 類似過去案件を検索
- RoomLink経由で通知先を取得

**追加したDBメソッド**:
- `get_target_rooms()`: リンク先Room取得
- `get_aggregation_rooms()`: Workspace内の統合Room取得
- `get_room_by_id()`: Room ID検索

**技術解説（通知フロー）**:
```
メッセージ受信
    ↓
RoomLink確認（source → target）
    ↓
target が aggregation room なら通知
    ↓
Discord Embed作成・送信
```

**テスト**: `tests/test_notifier.py` - 9件

---

#### Issue #12: 他AIプロバイダー

**ファイル**:
- `src/ai/providers/anthropic.py`
- `src/ai/providers/google.py`
- `src/ai/providers/groq.py`
- `src/ai/providers/__init__.py`

**実装内容**:

| プロバイダー | generate | embed | 備考 |
|--------------|----------|-------|------|
| Anthropic | ✅ | ❌ | Messages API使用 |
| Google | ✅ | ✅ | Gemini API使用 |
| Groq | ✅ | ❌ | OpenAI互換API |

**技術解説（エラーハンドリング）**:
- 各プロバイダー固有のエラーを共通エラークラスにマッピング
- 例: `anthropic.BadRequestError` → `AIProviderError`
- 例: `openai.RateLimitError` → `AIQuotaExceededError`

**テスト**:
- `tests/test_anthropic_provider.py` - 9件
- `tests/test_google_provider.py` - 9件
- `tests/test_groq_provider.py` - 9件

---

#### Issue #13: 統合テスト

**ファイル**: `tests/test_integration.py`

**テストケース**: 7件

| テスト | 内容 |
|--------|------|
| INT-01 | メッセージ保存フロー（Workspace→Room→Message→検索） |
| INT-02 | Workspace/Room分離（AのデータがBに見えない） |
| INT-03 | AIルーターとプロバイダー連携 |
| INT-04 | 要約機能の統合テスト |
| INT-05 | 通知フロー（メッセージ→統合Room通知） |
| 追加 | RoomLink経由のRoom取得 |
| 追加 | Workspace内の統合Room取得 |

**発生した問題と解決**:

1. **データベースURLエラー**:
   - 問題: `Database(":memory:")` でURLパース失敗
   - 原因: SQLAlchemyは `sqlite:///:memory:` 形式を期待
   - 解決: Databaseクラスで `:memory:` を自動変換

2. **テーブル未作成エラー**:
   - 問題: `sqlalchemy.exc.OperationalError: no such table: workspaces`
   - 原因: `create_tables()` 未呼び出し
   - 解決: fixtureで `database.create_tables()` を追加

3. **isinstance チェック失敗**:
   - 問題: `isinstance(channel, discord.TextChannel)` が常にFalse
   - 原因: `MagicMock()` は型情報がない
   - 解決: `MagicMock(spec=discord.TextChannel)` でspec指定

4. **AIRouter テストのパッチ失敗**:
   - 問題: `src.ai.router.OpenAIProvider` が存在しない
   - 原因: AIRouterはプロバイダー情報のみ返し、インスタンス生成しない
   - 解決: テストを分離（ルーター情報取得 + プロバイダー生成）

---

#### Issue #14: 試験運用準備

**ファイル**: `src/main.py` 更新

**実装内容**:
- AIRouter初期化
- スラッシュコマンド登録（/summary, /search）
- 統合Room通知サービス連携
- 起動時ログ強化

**統合されたコンポーネント**:
```
main.py
  ├── Database（メッセージ保存）
  ├── LocalStorage（添付ファイル保存）
  ├── AIRouter（AI機能）
  ├── MessageHandler（メッセージ処理）
  ├── BotCommands（スラッシュコマンド）
  └── AggregationNotifier（統合Room通知）
```

### 最終テスト結果

```
tests/test_ai_router.py: 18 passed
tests/test_anthropic_provider.py: 9 passed
tests/test_bot.py: 10 passed
tests/test_commands.py: 10 passed
tests/test_db.py: 10 passed
tests/test_google_provider.py: 9 passed
tests/test_groq_provider.py: 9 passed
tests/test_handler.py: 13 passed
tests/test_integration.py: 7 passed
tests/test_notifier.py: 9 passed
tests/test_openai_provider.py: 9 passed
tests/test_storage.py: 9 passed
tests/test_summarizer.py: 8 passed

============================== 120 passed ==============================
```

### 成果物

| ファイル | 内容 |
|----------|------|
| src/ai/providers/openai.py | OpenAIプロバイダー |
| src/ai/providers/anthropic.py | Anthropicプロバイダー |
| src/ai/providers/google.py | Googleプロバイダー |
| src/ai/providers/groq.py | Groqプロバイダー |
| src/ai/summarizer.py | 要約機能 |
| src/bot/commands.py | スラッシュコマンド |
| src/bot/notifier.py | 統合Room通知 |
| src/main.py | エントリーポイント（更新） |
| tests/test_*.py | 計120テスト |

### 学んだこと

1. **統合テストの重要性**: ユニットテストだけでなく、コンポーネント間の連携を確認する統合テストが重要
2. **MagicMockのspec指定**: `spec=ClassName` で型チェックを通過できる
3. **データベースURL形式**: SQLAlchemyは厳密なURL形式を期待する
4. **責務の分離**: AIRouterはルーティング判断のみ、インスタンス生成は利用側の責務
5. **環境変数管理**: config.yamlで `${VAR}` 形式を使い、.envでシークレット管理
6. **コマンド同期**: スラッシュコマンドは `tree.sync()` でDiscordに登録が必要

### 次のステップ

- mainにマージ
- Phase 2の計画策定

### コンテキスト使用状況

**セッション情報（2025-01-05）**:
- 本セッションは前回セッションからのコンテキスト引き継ぎで継続
- Issue #8-14を連続実装（約6時間の作業）

**実施内容**:
- Issue #11-14の実装・テスト
- 統合テスト7件の作成と修正
- DEVELOPMENT_LOG.md / CONVERSATION_LOG / ISSUES_STATUS.md / DEVELOPMENT_PLAN.md の更新
- 全120テストパス確認

**コンテキスト効率化のポイント**:
1. サブエージェント（Task tool）でコード探索を委譲
2. TodoWriteで進捗管理し、コンテキスト切れ時の継続を容易に
3. DEVELOPMENT_LOG.mdに詳細記録し、次セッションでの再開を効率化

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

### 反省点（PDCA）

**Plan**: Issue #15-17を順次実装する計画だった

**Do**: 実装・テスト・マージを完了

**Check**:
- DEVELOPMENT_LOG.mdへの記録が遅れた
- CONVERSATION_LOGを作成しなかった
- Issue完了時の必須作業（CLAUDE.mdで定義）を忘れていた

**Act**:
- 今後はIssue完了直後に記録を作成する
- TodoWriteに「記録作成」タスクを必ず含める
- セッション終了前に記録の確認を行う

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
- 📝 DEVELOPMENT_LOG.md 更新
- 📝 CONVERSATION_LOG 作成
- 📝 DEVELOPMENT_PLAN.md / ISSUES_STATUS.md 更新

#### 対策 B: 空ファイル事前作成

ブランチ作成直後に `docs/CONVERSATION_LOG_ISSUE{N}.md` を作成しておく。

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
| docs/TROUBLESHOOTING.md | 「開発プロセス」セクション追加 |
| docs/ISSUES_STATUS.md | 「プロセス改善」セクション追加 |
| CLAUDE.md | 問題解決フロー追記 |
| docs/DEVELOPMENT_PLAN.md | Phase 2 Step順序変更 |
| docs/DEVELOPMENT_LOG.md | この記録 |

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

（今後の開発記録をここに追記）
