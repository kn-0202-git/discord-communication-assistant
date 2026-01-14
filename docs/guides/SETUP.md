# 環境構築手順

## 1. 前提条件

- Python 3.11以上
- Git
- Discordアカウント
- AIプロバイダーのAPIキー（少なくとも1つ）

## 2. リポジトリ取得
```bash
git clone https://github.com/kn-0202-git/discord-communication-assistant.git
cd discord-communication-assistant
```

## 3. uv インストール

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 確認
```bash
uv --version
```

## 4. 依存関係インストール
```bash
uv sync --all-extras
```

## 5. pre-commit 設定
```bash
uv run pre-commit install
```

## 6. Discord Bot作成

### 6.1 Developer Portalでアプリ作成

1. https://discord.com/developers/applications にアクセス
2. 「New Application」をクリック
3. アプリ名を入力（例：Business Assistant）
4. 「Create」をクリック

### 6.2 Botユーザー作成

1. 左メニュー「Bot」をクリック
2. 「Add Bot」をクリック
3. 「Reset Token」でトークン取得（コピーして保存）

### 6.3 権限設定

1. 左メニュー「OAuth2」→「URL Generator」
2. Scopes:
   - bot
   - applications.commands
3. Bot Permissions:
   - Read Messages/View Channels
   - Send Messages
   - Read Message History
   - Attach Files
   - Connect（通話用、Phase 2）
   - Speak（通話用、Phase 2）
4. 生成されたURLをコピー

### 6.4 サーバーに招待

1. 生成されたURLをブラウザで開く
2. 招待先サーバーを選択
3. 「認証」をクリック

## 7. 環境変数設定

### .env作成
```bash
cp .env.example .env
```

### .env編集
```
# 必須
DISCORD_TOKEN=your_discord_bot_token

# DB（デフォルトでOK）
DATABASE_URL=sqlite:///data/app.db

# Storage（デフォルトでOK）
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=data/files

# AI（使うものだけ設定）
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
GROQ_API_KEY=your_groq_key
LOCAL_LLM_BASE_URL=http://localhost:11434
```

## 8. 動作確認

### リントチェック
```bash
uv run ruff check src/
```

### テスト実行
```bash
uv run pytest tests/ -v
```

### Bot起動
```bash
uv run python -m src.main
```

## 9. トラブルシューティング

### uv: command not found

uvのインストールを再度実行。パスが通っているか確認。
```bash
source ~/.zshrc
```

### ModuleNotFoundError
```bash
uv sync --all-extras
```

### discord.errors.LoginFailure

- DISCORD_TOKENが正しいか確認
- トークンをリセットして再取得

### openai.error.AuthenticationError

- OPENAI_API_KEYが正しいか確認
- OpenAIアカウントの支払い設定を確認
