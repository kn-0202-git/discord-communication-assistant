# R-issue17: Room名表示とエラーハンドリングの改善

## 要約

手動テスト中に発見した2つの問題：
1. Room名がDiscordチャンネル名ではなく「Room-{ID}」で表示される
2. DBセッションエラー時のリカバリーが不十分

## Agent

Claude Code (Opus 4.5)

## 日付

2026-01-18

---

## 問題1: Room名がIDで表示される

### 現象

`/search` の結果に表示されるRoom名が `#Room-1457257672784089120` のようなID形式になる。
期待されるのは `#room1` のようなDiscordチャンネル名。

### 原因

`src/bot/services/message_service.py:112` でRoom作成時にチャンネル名を取得していない：

```python
room = self.db.create_room(
    workspace_id=workspace.id,
    name=f"Room-{channel_id}",  # ← IDを使用
    ...
)
```

### 対応案

1. `MessageData` にチャンネル名を含める
2. Room作成時に `channel_name` を使用する

---

## 問題2: DBセッションエラーのリカバリー

### 現象

メッセージ重複（UNIQUE constraint failed）エラー発生後、セッションが `PendingRollbackError` 状態になり、以降のすべてのDB操作が失敗する。

### 原因

SQLAlchemyセッションでエラー発生後に `session.rollback()` が呼ばれていない。

### 対応案

1. 各DB操作で例外発生時に `session.rollback()` を呼ぶ
2. または、操作ごとに新しいセッションを使用する設計に変更

---

## 優先度

| 問題 | 優先度 | 理由 |
|------|--------|------|
| Room名表示 | 中 | UX改善、機能には影響なし |
| セッションリカバリー | 高 | エラー時にBotが機能停止する |

---

---

## 未テスト項目: TC-3 権限チェック

### 内容

`/set_room_type` コマンドの管理者権限チェックが正しく動作するかのテスト。

### テスト手順

1. 管理者以外のユーザーで `/set_room_type topic` 実行
2. 期待結果: `このコマンドは管理者のみ実行できます。`

### スキップ理由

テスト用の別アカウント（管理者権限なし）がないため。

### 対応案

- テスト用Discordアカウントを作成する
- または、ユニットテストで権限チェックをカバーする

---

## 関連ファイル

- `src/bot/services/message_service.py` - Room作成ロジック
- `src/db/database.py` - セッション管理
- `src/bot/handlers.py` - エラーハンドリング
- `src/bot/commands.py:457-459` - 権限チェック実装
