# R-issue12: /search の検索範囲と統合Room運用の改善

## 要約

/search は通常Roomでは同一Roomのみ検索、統合Roomでは同一Workspace内の全Roomを検索する仕様に修正。
ただし統合Roomの設定手段がDB手動更新のみのため、運用手順と設定コマンドの整備が必要。

## Agent

Codex

## 日付

2026-01-18

---

## 背景

- 手動テストで、通常Room内の検索は成功
- 統合Room（aggregation）扱いのチャンネルでは検索できない事象が発生
- 要件: 通常Roomは同一Roomのみ検索、統合Roomは同一Workspace内検索

---

## 現状の挙動と原因

- Roomはメッセージ保存時に `room_type="topic"` で自動作成される
- 統合Roomは自動判定されず、**DBで `room_type="aggregation"` に手動更新**が必要
- /search の検索範囲は従来 Workspace 全体だったため、Room内検索の要件に未一致

---

## 対応内容（反映済み）

- /search を **Room種別で検索範囲切り替え**
  - 通常Room: 同一Roomのみ
  - 統合Room: 同一Workspace全体
- 検索結果に **発言Room名を表示**
  - 出力: 日付 | 発言者 | #Room名 | 内容

---

## 改善点（Codex実装予定）

| 優先度 | タスク | ステータス |
|--------|--------|------------|
| P1 | `/set_room_type` 管理者コマンド追加 | 完了 |
| P2 | `DISCORD_SETUP.md` に統合Room設定手順追記 | 完了 |
| P3 | 通常Room/統合Room検索範囲のテスト追加 | 完了 |

### P1: `/set_room_type` コマンド

- 管理者権限必須
- `@app_commands.choices` で `topic` / `aggregation` を選択
- `Database.update_room_type(room_id, room_type)` を追加
- 成功時: `Room種別を {room_type} に変更しました。`

---

## 参考

- `src/bot/commands.py`（/search の検索範囲切替と表示拡張）
- `src/db/database.py`（Room指定検索ヘルパー追加）
- `docs/guides/DISCORD_SETUP.md`（統合Room作成の導線）
