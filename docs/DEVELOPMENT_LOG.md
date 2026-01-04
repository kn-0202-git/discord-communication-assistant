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

（今後の開発記録をここに追記）
