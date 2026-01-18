# R-issue15: Raspberry Piローカル実行の適合性検討と進め方

## 要約

ラズパイでローカル実行できるかの確認依頼に対し、現状ドキュメントはmacOS/Windows前提で未保証。
段階的に最小構成で起動確認し、音声/LLMなど重い機能は切り分ける計画を提示する。

## Agent

Codex

## 日付

2026-01-18

---

## 背景

- 「ローカルで動かす時、ラズパイで動かせるか？」という問い合わせ
- 仕様/設計ドキュメントはローカルPC（macOS/Windows）を前提としている
- Raspberry Pi（Linux/ARM）での検証記録は未整備
- **Oracle Cloud Free Tier (ARM A1) での運用が既にARCHITECTURE.mdに記載**されており、ARM互換性は設計上考慮済み

---

## 現状の前提（ドキュメント）

- ローカル実行の前提: macOS / Windows
- Python 3.11以上が必須
- Dockerfileは存在するが、ARM環境の検証は未実施
- `python:3.11-slim` ベースイメージはARM対応済み

---

## 依存関係のARM互換性分析

| パッケージ | ARM互換 | 備考 |
|------------|---------|------|
| `discord.py>=2.3.0` | ⚪ | Pure Python、問題なし |
| `discord.py[voice]` | ⚠️ | `pynacl` が必要、ビルド要注意 |
| `pynacl>=1.5.0` | ⚠️ | libsodiumのビルドが必要、apt install済みなら問題なし |
| `openai>=1.0.0` | ⚪ | Pure Python |
| `anthropic>=0.25.0` | ⚪ | Pure Python |
| `google-generativeai>=0.5.0` | ⚪ | Pure Python |
| `groq>=0.5.0` | ⚪ | Pure Python |
| `sqlalchemy>=2.0.0` | ⚪ | Pure Python（SQLiteドライバはPython標準） |
| `aiohttp>=3.9.0` | ⚪ | Wheel提供あり |
| `ffmpeg` (Dockerfile) | ⚠️ | apt install可能、Piのリソース消費に注意 |

### 結論

**基本的なBot機能（テキスト処理、DB保存、AI API呼び出し）はRaspberry Piで動作可能**。
音声機能（`pynacl`, `ffmpeg`）は追加パッケージが必要だが、対応可能。

---

## 機能別対応可否

| 機能 | Raspberry Pi対応 | 備考 |
|------|------------------|------|
| メッセージ保存 | ⚪ 対応可能 | SQLite、低負荷 |
| ファイル保存 | ⚪ 対応可能 | ディスクI/O依存、SDカードでも動作 |
| /summary | ⚪ 対応可能 | API呼び出しのみ |
| /search | ⚪ 対応可能 | SQLite検索、低負荷 |
| /remind | ⚪ 対応可能 | DB操作のみ |
| /record | ⚠️ 要検証 | ffmpeg/libsodiumのビルドが必要 |
| 文字起こし (Whisper) | ⚪ 対応可能 | API呼び出しのみ（ローカルWhisperは不可） |
| ローカルLLM (Ollama) | ❌ 非推奨 | Piのメモリ/CPUでは実用不可 |
| Google Drive連携 | ⚪ 対応可能 | API呼び出しのみ |

---

## 推奨Raspberry Pi構成

| 項目 | 推奨 | 最小 |
|------|------|------|
| モデル | Raspberry Pi 4/5 | Raspberry Pi 3B+ |
| RAM | 4GB以上 | 2GB |
| ストレージ | SSD (USB接続) | 32GB SD |
| OS | Raspberry Pi OS (64-bit) | 32-bit可 |
| Python | 3.11+（pyenv or docker） | - |

---

## 実装方針（Codex実装予定）

| 優先度 | タスク | ステータス |
|--------|--------|------------|
| P1 | 目標環境の確定（機種/OS/機能範囲） | 未着手 |
| P1 | 最小構成で起動確認（テキストBotのみ） | 未着手 |
| P2 | Dockerfile.arm64 作成 | 未着手 |
| P2 | 音声機能（pynacl/ffmpeg）の段階的検証 | 未着手 |
| P3 | systemdサービス化（自動起動） | 未着手 |
| P3 | 運用ドキュメント作成 | 未着手 |

---

### P1: 最小構成での起動確認

#### 手順

1. **Raspberry Pi OS (64-bit) セットアップ**
2. **Python 3.11 インストール**
   ```bash
   # オプション1: pyenv
   curl https://pyenv.run | bash
   pyenv install 3.11.7
   pyenv global 3.11.7

   # オプション2: deadsnakes PPA (Ubuntu)
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt install python3.11 python3.11-venv
   ```

3. **音声機能を無効化した依存関係でテスト**
   ```bash
   # pyproject.toml から discord.py[voice] を discord.py に変更してテスト
   uv sync
   python -m src.main
   ```

4. **確認項目**
   - [ ] Bot起動成功
   - [ ] メッセージ保存成功
   - [ ] /summary 動作確認
   - [ ] /search 動作確認

---

### P2: Dockerfile.arm64

```dockerfile
# Dockerfile.arm64
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ARM用の依存関係（libsodium for pynacl）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsodium-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-install-project

COPY config.yaml /app/config.yaml
COPY src /app/src

RUN mkdir -p /app/data/files

CMD ["python", "-m", "src.main"]
```

#### ビルドとテスト

```bash
# Raspberry Pi上で
docker build -f Dockerfile.arm64 -t discord-bot:arm64 .
docker run -d --env-file .env -v $(pwd)/data:/app/data discord-bot:arm64
```

---

### P3: systemdサービス化

```ini
# /etc/systemd/system/discord-bot.service
[Unit]
Description=Discord Business Assistant Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/discord-communication-assistant
EnvironmentFile=/home/pi/discord-communication-assistant/.env
ExecStart=/home/pi/.pyenv/shims/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
sudo journalctl -u discord-bot -f
```

---

## 検証計画

| ステップ | 確認項目 | 期待結果 |
|----------|----------|----------|
| 1 | Python 3.11 インストール | `python --version` で 3.11.x |
| 2 | 依存関係インストール | `uv sync` 成功 |
| 3 | Bot起動 | ログに「Bot is ready!」 |
| 4 | メッセージ送信 | DBに保存される |
| 5 | /summary | 要約が返信される |
| 6 | Docker起動 | `docker logs` でエラーなし |
| 7 | systemd起動 | 再起動後も自動起動 |

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| SDカードの寿命 | USB SSD推奨、SQLiteのWALモード検討 |
| メモリ不足 | swap追加、Docker制限設定 |
| pynacl ビルド失敗 | libsodium-dev 事前インストール |
| ネットワーク不安定 | 再接続ロジック確認、systemd Restart |
| ローカルLLM非対応 | API呼び出しのみ使用、ローカルLLM機能disable |

---

## 参考

- [docs/specs/REQUIREMENTS.md](file:///Users/kosukenakatani/Documents/prg/discord-communication-assistant/docs/specs/REQUIREMENTS.md)
- [docs/specs/ARCHITECTURE.md](file:///Users/kosukenakatani/Documents/prg/discord-communication-assistant/docs/specs/ARCHITECTURE.md)
- [docs/guides/SETUP.md](file:///Users/kosukenakatani/Documents/prg/discord-communication-assistant/docs/guides/SETUP.md)
- [pyproject.toml](file:///Users/kosukenakatani/Documents/prg/discord-communication-assistant/pyproject.toml)
- [Dockerfile](file:///Users/kosukenakatani/Documents/prg/discord-communication-assistant/Dockerfile)
