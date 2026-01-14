# Google Drive Setup

Google Drive 連携（Step 4）で使うOAuth設定と環境変数の手順をまとめる。

## 1. 前提
- Google Cloud Project を作成
- Google Drive API を有効化
- OAuth 同意画面を設定

## 2. OAuthクライアント作成
1. Google Cloud Console → APIs & Services → Credentials
2. Create Credentials → OAuth client ID
3. Application type: Web application
4. Authorized redirect URI に `http://localhost:8080` を追加
5. Client ID と Client Secret を控える

## 3. 認可コード取得
以下のURLにアクセスして認可し、`code` を取得する。

```
https://accounts.google.com/o/oauth2/v2/auth?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:8080&
  response_type=code&
  scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file&
  access_type=offline&
  prompt=consent
```

## 4. トークン発行（refresh token取得）

```
curl -X POST https://oauth2.googleapis.com/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=AUTH_CODE \
  -d grant_type=authorization_code \
  -d redirect_uri=http://localhost:8080
```

レスポンスの `refresh_token` を控える。

## 5. 環境変数

```
GOOGLE_DRIVE_CLIENT_ID=...
GOOGLE_DRIVE_CLIENT_SECRET=...
GOOGLE_DRIVE_REFRESH_TOKEN=...
GOOGLE_DRIVE_ACCESS_TOKEN=... # 任意: 手動で短期トークンを指定したい場合
GOOGLE_DRIVE_ROOT_FOLDER_ID=... # 任意: Drive上の保存先ルートフォルダID
```

`GOOGLE_DRIVE_REFRESH_TOKEN` が設定されていれば、アクセストークンは自動更新される。

## 6. config.yamlの設定

```
google_drive:
  enabled: true
  auto_upload: false
  root_folder_id: ${GOOGLE_DRIVE_ROOT_FOLDER_ID}
```

- `enabled`: /save を有効化
- `auto_upload`: 添付ファイル受信時の自動アップロード
