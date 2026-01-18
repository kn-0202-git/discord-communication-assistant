# Discord環境セットアップガイド

テスト用のDiscordサーバーとBotを設定する手順。

## 1. Discord Developer Portal でBot作成

### 1.1 アプリケーション作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 右上の「New Application」をクリック
3. アプリケーション名を入力（例: "Business Assistant Test"）
4. 利用規約に同意して「Create」

### 1.2 Bot追加

1. 左メニューから「Bot」を選択
2. 「Add Bot」をクリック → 確認ダイアログで「Yes, do it!」
3. 「Reset Token」をクリックしてトークンを取得
4. **重要**: トークンをコピーして安全な場所に保存（`.env`ファイルに記載）

### 1.3 Intents（権限）設定

Botセクションで以下のPrivileged Gateway Intentsを有効化:

- [x] **MESSAGE CONTENT INTENT** ← 必須（メッセージ内容を読むため）
- [ ] SERVER MEMBERS INTENT（オプション）
- [ ] PRESENCE INTENT（オプション）

**Save Changes** を忘れずに。

## 2. テスト用Discordサーバー作成

### 2.1 サーバー作成

1. Discordアプリを開く
2. 左のサーバーリスト下部「+」をクリック
3. 「Create My Own」→「For me and my friends」
4. サーバー名を入力（例: "Business Assistant Test"）

### 2.2 チャンネル作成

以下の3つのテキストチャンネルを作成:

| チャンネル名 | 用途 |
|-------------|------|
| `#room1` | 独立Room（ユーザーが書き込む） |
| `#room2` | 独立Room（Room1とは分離） |
| `#room3-aggregation` | 統合Room（Room1とRoom2のデータを集約） |

作成手順:
1. チャンネルリストの「+」をクリック
2. 「Text Channel」を選択
3. チャンネル名を入力

## 3. Bot招待

### 3.1 OAuth2 URL生成

1. Developer Portalに戻る
2. 左メニューから「OAuth2」→「URL Generator」を選択
3. SCOPES:
   - [x] `bot`
4. BOT PERMISSIONS:
   - [x] Read Messages/View Channels
   - [x] Send Messages
   - [x] Read Message History
   - [x] Attach Files
5. 生成されたURLをコピー

### 3.2 サーバーに招待

1. コピーしたURLをブラウザで開く
2. 作成したテストサーバーを選択
3. 「Authorize」をクリック

## 4. 環境変数設定

プロジェクトルートに `.env` ファイルを作成:

```bash
# .env
DISCORD_TOKEN=your_bot_token_here
```

**注意**: `.env`ファイルは`.gitignore`に含まれているため、Gitにコミットされません。

## 5. 動作確認

### 5.1 Bot起動

```bash
uv run python -m src.main
```

成功すると以下のようなログが表示される:
```
2025-01-XX XX:XX:XX - src.main - INFO - Bot is ready!
2025-01-XX XX:XX:XX - discord.client - INFO - Logged in as BotName#1234
```

### 5.2 メッセージ送信テスト

1. Discordでテストサーバーの `#room1` を開く
2. 何かメッセージを送信（例: "テストメッセージ"）
3. ターミナルにログが表示されることを確認

```
INFO - Saved message X from ユーザー名
```

### 5.3 画像送信テスト

1. `#room1` に画像を添付して送信
2. `data/files/` ディレクトリに画像が保存されることを確認

### 5.4 統合Room設定

統合Room（aggregation）として使うチャンネルで、以下を実行:

1. 対象チャンネルに一度メッセージを送信（Room登録のため）
2. `/set_room_type` を実行し、`aggregation` を選択

**注意**:
- 管理者権限が必要
- 通常Roomに戻す場合は `topic` を選択

## 6. トラブルシューティング

### Bot がオフラインのまま

- トークンが正しいか確認
- MESSAGE CONTENT INTENT が有効になっているか確認

### メッセージが保存されない

- Botがサーバーに招待されているか確認
- チャンネルの閲覧権限があるか確認

### 添付ファイルがダウンロードできない

- ネットワーク接続を確認
- `data/files/` ディレクトリの書き込み権限を確認

## 7. チャンネルIDの確認方法

デバッグ時にチャンネルIDが必要な場合:

1. Discordの設定 → 詳細設定 → 「開発者モード」を有効化
2. チャンネル名を右クリック → 「IDをコピー」

## 8. 本番環境への移行

テスト完了後、本番環境では:

1. 新しいBotを作成（本番用）
2. 本番サーバーに招待
3. 環境変数を本番用に更新
4. Workspace/Room情報をDBに登録
