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

（今後の開発記録をここに追記）
