# R-issue19: Room名変更履歴マスタ + 削除済みRoom表示

## 要約

R-issue17で延期した2つの機能を実装する:
1. Room名変更履歴マスタ（RoomNameHistoryテーブル）
2. 削除済みRoom表示（`#room名（削除済み）`形式）

## Agent

Claude Code (Opus 4.5)

## 日付

2026-01-19

---

## 背景

R-issue17でRoom管理改善を実施した際、YAGNIの原則に従い以下を延期:
- Room名変更履歴の保存（いつ、どの名前だったかを追跡）
- 削除済みRoomの表示形式変更

現状:
- Room名変更時は最新の名前のみ保持
- 削除済みRoomは`deleted_at`フィールドがセットされるが、表示は通常と同じ

---

## タスク1: Room名変更履歴マスタ

### 目的

Room名の変更履歴を保存し、「いつの時点で何という名前だったか」を追跡可能にする。

### 設計案

```python
class RoomNameHistory(Base):
    __tablename__ = "room_name_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"))
    name: Mapped[str] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
```

### 変更箇所

- `src/db/models.py`: RoomNameHistoryモデル追加
- `src/db/database.py`: 履歴保存メソッド追加
- `src/bot/initializer.py`: `on_guild_channel_update`で履歴保存

---

## タスク2: 削除済みRoom表示

### 目的

削除されたRoomを検索結果などで識別しやすくする。

### 設計案

`/search`結果のRoom名表示を変更:
- 通常: `#channel-name`
- 削除済み: `#channel-name（削除済み）`

### 変更箇所

- `src/bot/commands.py`: `/search`のRoom名表示ロジック

---

## 優先度

低 - 現状でも機能上の問題はない。必要になったら実装する。

---

## 関連Issue

- R-issue17: Room管理改善（完了）

---

## 関連ファイル

- `src/db/models.py` - モデル定義
- `src/db/database.py` - CRUD操作
- `src/bot/initializer.py` - イベントリスナー
- `src/bot/commands.py` - コマンド表示
