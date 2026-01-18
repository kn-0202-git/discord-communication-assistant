# R-issue18: 管理者コマンドの権限制御改善

## 要約

`/set_room_type` などの管理者コマンドが全ユーザーに表示されている。
Discord側の権限制御機能を使い、管理者以外にはコマンドを非表示にする。

## Agent

Claude Code (Opus 4.5)

## 日付

2026-01-18

---

## 現状

```python
# src/bot/commands.py:457-459
if not isinstance(user, discord.Member) or not user.guild_permissions.administrator:
    await interaction.followup.send("このコマンドは管理者のみ実行できます。")
    return
```

- コマンド実行時に権限チェック → 拒否メッセージ表示
- コマンド自体は全ユーザーに表示される

---

## 問題点

1. 管理者以外もコマンドを見て実行を試みることができる
2. UXが悪い（実行してからエラーになる）
3. コマンド一覧が煩雑になる

---

## 対応案

`@app_commands.default_permissions()` デコレータを使用：

```python
@self._tree.command(name="set_room_type", ...)
@app_commands.default_permissions(administrator=True)
async def set_room_type_command(...):
```

### 効果

- 管理者以外にはコマンドが表示されない
- サーバー管理者がDiscord設定で権限をカスタマイズ可能
- 実行時チェックも残す（二重チェック）

---

## 対象コマンド

| コマンド | 現状 | 対応 |
|----------|------|------|
| `/set_room_type` | 全員に表示 | 管理者のみ表示 |
| `/record` | 全員に表示 | 検討（VCメンバーのみ？） |

---

## 優先度

中 - セキュリティ上の問題はない（実行時チェックあり）が、UX改善として対応推奨

---

## 関連ファイル

- `src/bot/commands.py` - コマンド登録
