# Discord Communication Assistant (Business-Grade AI Partner)

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active_Development-orange)

> **"単なるBotではありません。あなたのビジネスコンテキストを理解する、24時間365日のパートナーです。"**

Discord Communication Assistantは、複数の最先端LLM（OpenAI, Anthropic, Gemini等）の頭脳を統合し、ビジネスコミュニケーションを円滑化・自動化・資産化するために設計された高機能AIアシスタントです。

---

## 🌟 Why: なぜ作ったのか？

ビジネスチャットにおける「情報の散逸」と「文脈の断絶」を解決するために生まれました。

- **課題**: 重要な決定事項がチャットログに埋もれ、後から探せない。
- **課題**: 複数の取引先とのやり取りで、文脈を脳内でスイッチするコストが高い。
- **解決策**: このAIは、過去のやり取り、共有された資料、決定事項を「セマンティックメモリ（意味的記憶）」として保持します。単に返事をするだけでなく、**「先週のA社との会議で決まったマイルストーンに基づいて」**回答できるパートナーです。

## 🚀 Features: 主な機能

### 🧠 マルチブレイン・アーキテクチャ
状況に応じて最適な「頭脳」を使い分けます。
- **OpenAI (GPT-4o)**: 複雑な推論やコード生成に。
- **Anthropic (Claude 3.5 Sonnet)**: 自然な文章作成や長文脈の理解に。
- **Google (Gemini 1.5 Pro)**: 長大なドキュメントや動画の解析に。
- **Local LLM**: プライバシー重視の処理やコスト削減に。

### 📚 コンテキスト認識 (RAG)
Vector Databaseを活用し、過去の会話やドキュメントから関連情報を瞬時に引き出します。「あれどうなってたっけ？」に対する答えを、過去ログから見つけ出します。

### 📂 インテリジェント・アセット管理
Discordにアップロードされた画像、PDF、動画ファイルを自動でカテゴリ分けし、Google Drive等のストレージに整理して保存します。

---

## 🏗️ The "How": 独自の開発哲学

このプロジェクトは、**「人間1人 + 複数のAI専門家」** というユニークな体制で開発されています。

### 🤖 Multi-LLM Co-creation Process
開発プロセス自体が実験場です。
- **PMO**: 進行管理とタスク分解
- **アーキテクト**: 設計と技術選定
- **レビュアー**: コード品質とセキュリティチェック

これら全てのロールを、Claude, ChatGPT, GeminiなどのAIエージェントが担当し、人間の開発者と協働しています。
このプロセスの詳細は、以下のドキュメントで公開しています：

- [**codex_process.md**](codex_process.md): 開発運用の詳細なルールブック
- [**gemini_process_review.md**](gemini_process_review.md): 第三者AI（Gemini）によるプロセス監査レポート

---

## ⚡ Quick Start

### 前提条件
- Python 3.11以上
- `uv` (高速なパッケージマネージャー)

### セットアップ

```bash
# 1. リポジトリのクローン
git clone https://github.com/kn-0202-git/discord-communication-assistant.git
cd discord-communication-assistant

# 2. 依存関係のインストール (uv使用)
uv sync

# 3. 設定ファイル
cp .env.example .env
# .env を編集して各APIキーを設定してください

# 4. 起動
uv run python -m src.main
```

詳細な手順は [セットアップガイド](docs/guides/SETUP.md) を参照してください。

---

## 📖 Documentation

詳細な仕様や設計については、`docs/` 配下のドキュメントを参照してください。

| カテゴリ | ドキュメント | 内容 |
|:---|:---|:---|
| **Vision** | [VISION.md](docs/specs/VISION.md) | プロジェクトの目指す場所 |
| **Guides** | [USER_GUIDE.md](docs/guides/USER_GUIDE.md) | 利用者向けマニュアル |
| **Specs** | [ARCHITECTURE.md](docs/specs/ARCHITECTURE.md) | システムアーキテクチャ詳細 |
| | [REQUIREMENTS.md](docs/specs/REQUIREMENTS.md) | 機能要件定義 |
| **Planning** | [ROADMAP.md](docs/planning/ROADMAP.md) | 今後の開発ロードマップ |
| | [DEVELOPMENT_PLAN.md](docs/planning/DEVELOPMENT_PLAN.md) | 直近の開発計画 |
| **Rules** | [CLAUDE.md](CLAUDE.md) | AIエージェント向けガイドライン |

---

## License

[MIT License](LICENSE)
