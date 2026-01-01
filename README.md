# Discord Business Assistant

ビジネスパートナーとのやり取りをAIがサポートするDiscord Bot。

## 特徴

- 会話履歴の自動保存・検索
- ファイル（写真・動画・音声）の管理
- 過去のやり取りを基にしたAI回答
- 通話録音・文字起こし
- Google Drive連携
- リマインダー機能
- **複数AIプロバイダー対応**（OpenAI / Anthropic / Google / Groq / ローカルLLM）

## 想定ユースケース

- 複数の取引先との連絡管理
- 過去のやり取りの振り返り
- 資料の一元管理
- 引き継ぎ資料の自動生成

## クイックスタート
```bash
# リポジトリ取得
git clone https://github.com/kn-0202-git/discord-communication-assistant.git
cd discord-communication-assistant

# 環境構築（uv使用）
uv sync

# 環境変数設定
cp .env.example .env
# .envを編集

# 起動
uv run python -m src.main
```

詳細は [docs/SETUP.md](docs/SETUP.md) を参照。

## ドキュメント

| 文書 | 内容 |
|------|------|
| [VISION.md](docs/VISION.md) | プロジェクトのゴール |
| [ROADMAP.md](docs/ROADMAP.md) | 全体計画 |
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | 機能要件 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 設計 |
| [DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) | 開発スケジュール |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | テスト計画 |
| [SETUP.md](docs/SETUP.md) | 環境構築 |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | 利用者向けガイド |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 問題と解決策 |
| [DECISIONS.md](docs/DECISIONS.md) | 設計決定記録 |

## 技術スタック

- Python 3.11+
- uv（パッケージ管理）
- discord.py
- SQLite / PostgreSQL
- 複数AI対応（OpenAI / Anthropic / Google / Groq / ローカル）
- Google Drive API
- ruff（リンター/フォーマッター）
- pytest（テスト）

## ライセンス

MIT
