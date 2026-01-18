# Oracle Cloud Free Tier デプロイガイド

## 概要

このガイドでは、Discord Communication AssistantをOracle Cloud Free Tierにデプロイする手順を説明します。

> **変更履歴**: 2026-01-17 Fly.ioが無料で使えないため、Oracle Cloud Free Tierに変更

## Oracle Cloud Free Tier スペック

| リソース | 無料枠 |
|----------|--------|
| Compute | ARM A1（最大4 OCPU、24GB RAM） |
| Block Volume | 200GB |
| Object Storage | 10GB |
| Network | 10TB/月 |

**注意**: 無料枠は「Always Free」として提供されていますが、内容変更や終了の可能性があるため定期確認を推奨します。

---

## 前提条件

- Oracle Cloudアカウント（クレジットカード登録は必要だが課金されない）
- SSH鍵ペア（ed25519推奨）
- Dockerfileが存在すること

---

## Step 1: Oracle Cloud Free Tier登録

### 1.1 アカウント作成

1. [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) にアクセス
2. 「Start for free」をクリック
3. 以下の情報を入力：
   - Country/Region: Japan
   - Email
   - Name
4. Home Regionを選択（**Tokyo** または **Osaka** 推奨）
5. クレジットカード情報を入力（本人確認用、課金されない）

### 1.2 アカウント確認

- 登録完了後、Oracle Cloud Consoleにログイン
- 「Compute」→「Instances」が表示されることを確認

---

## Step 2: ARM A1インスタンス作成

### 2.1 インスタンス作成

1. Oracle Cloud Console → Compute → Instances → 「Create instance」

2. 以下を設定：

| 項目 | 設定値 |
|------|--------|
| Name | discord-bot |
| Compartment | (root) |
| Placement | AD-1 (どれでもOK) |

3. **Image and shape** セクション：
   - Image: **Ubuntu 22.04 Minimal (aarch64)**
   - Shape: **VM.Standard.A1.Flex**
   - OCPU: 2（または4）
   - Memory: 12GB（または24GB）

4. **Networking** セクション：
   - Create new VCN（デフォルト）
   - Public IPv4 address: **Assign a public IPv4 address**

5. **Add SSH keys** セクション：
   - 「Paste public keys」を選択
   - SSH公開鍵を貼り付け

6. **Boot volume** セクション：
   - サイズ: 50GB（デフォルト）

7. 「Create」をクリック

### 2.2 インスタンス起動確認

- Status: **RUNNING** になるまで待機（数分）
- Public IP addressをメモ

---

## Step 3: SSH接続＆初期設定

### 3.1 SSH接続

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<PUBLIC_IP>
```

**セキュリティ推奨**: Oracle CloudのSecurity ListでTCP 22（SSH）を自分のIPに制限してください。

### 3.2 システム更新

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.3 Docker インストール

```bash
# Docker公式リポジトリ追加
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# ubuntuユーザーをdockerグループに追加
sudo usermod -aG docker ubuntu

# 再ログイン
exit
ssh -i ~/.ssh/id_ed25519 ubuntu@<PUBLIC_IP>

# 確認
docker --version
```

### 3.4 Docker Compose インストール

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Step 4: アプリケーションデプロイ

### 4.1 リポジトリクローン

```bash
git clone https://github.com/<your-username>/discord-communication-assistant.git
cd discord-communication-assistant
```

### 4.2 環境変数設定

```bash
cp .env.example .env
nano .env
```

必須項目を設定：

```env
DISCORD_TOKEN=<your-discord-bot-token>
OPENAI_API_KEY=<your-openai-api-key>
# 他のAPIキー...
```

### 4.3 Dockerビルド＆起動

```bash
docker build -t discord-bot .
docker run -d \
  --name discord-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  discord-bot
```

### 4.4 動作確認

```bash
# ログ確認
docker logs -f discord-bot

# コンテナ状態確認
docker ps
```

---

## Step 5: 永続化（OCI Block Volume）

### 5.1 Block Volume作成（オプション）

1. Oracle Cloud Console → Block Storage → Block Volumes → 「Create Block Volume」
2. 設定：
   - Name: discord-bot-data
   - Size: 50GB
   - Availability Domain: インスタンスと同じAD

3. 「Create Block Volume」をクリック

### 5.2 インスタンスにアタッチ

1. 作成したBlock Volume → 「Attached Instances」→ 「Attach to Instance」
2. インスタンスを選択
3. Attachment type: **Paravirtualized**
4. 「Attach」をクリック

### 5.3 マウント

```bash
# デバイス確認（例: /dev/sdb, /dev/oracleoci/oraclevdb など）
lsblk

# フォーマット（初回のみ）
sudo mkfs.ext4 /dev/<device>

# マウントポイント作成
sudo mkdir -p /mnt/data

# マウント
sudo mount /dev/<device> /mnt/data

# 自動マウント設定（UUIDで固定）
sudo blkid /dev/<device>
echo 'UUID=<uuid> /mnt/data ext4 defaults,_netdev 0 2' | sudo tee -a /etc/fstab

# Dockerコンテナ再起動（新しいパスで）
docker stop discord-bot
docker rm discord-bot
docker run -d \
  --name discord-bot \
  --restart unless-stopped \
  -v /mnt/data:/app/data \
  --env-file .env \
  discord-bot
```

---

## Step 6: 監視＆自動復旧

### 6.1 systemdサービス化

```bash
sudo nano /etc/systemd/system/discord-bot.service
```

内容：

```ini
[Unit]
Description=Discord Bot Container
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/discord-communication-assistant
ExecStart=/usr/bin/docker start discord-bot
ExecStop=/usr/bin/docker stop discord-bot

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
```

### 6.2 ヘルスチェック（オプション）

```bash
# crontabでヘルスチェック
crontab -e
```

追加：

```
*/5 * * * * docker ps | grep discord-bot || docker start discord-bot
```

---

## トラブルシューティング

### インスタンスが作成できない

**原因**: ARM A1の無料枠が人気で、リソースが不足している可能性

**対策**:
1. 別のAvailability Domain（AD）を試す
2. 別のリージョン（Osaka）を試す
3. 少し時間をおいて再試行

### SSHが接続できない

**原因**: ファイアウォール設定

**対策**:
1. Security List → Ingress Rules で TCP 22 が許可されているか確認
2. インスタンスの Public IP が正しいか確認

### Dockerコンテナが起動しない

**確認コマンド**:

```bash
docker logs discord-bot
```

よくある原因：
- `.env`ファイルの設定ミス
- Discord Tokenが無効
- APIキーが無効

---

## 参考リンク

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Oracle Cloud Documentation](https://docs.oracle.com/en-us/iaas/Content/home.htm)
- [Docker on ARM](https://www.docker.com/blog/getting-started-with-docker-for-arm-on-linux/)
