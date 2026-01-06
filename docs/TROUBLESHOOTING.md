# トラブルシューティング

問題と解決策の記録。

---

## 目次

- [環境構築](#環境構築)
- [Discord Bot](#discord-bot)
- [AI連携](#ai連携)
- [データベース](#データベース)
- [開発プロセス](#開発プロセス)

---

## 環境構築

### uv: command not found

#### 症状
`uv` コマンドが見つからない

#### 原因
uvがインストールされていない、またはPATHが通っていない

#### 解決策
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# PATHを再読み込み
source ~/.zshrc
```

#### 日付
2025-01-XX

---

## Discord Bot

（今後追記）

---

## AI連携

（今後追記）

---

## データベース

（今後追記）

---

## 開発プロセス

### Issue完了時の文書作成忘れ

#### 症状
Issue完了後、DEVELOPMENT_LOG.md や CONVERSATION_LOG を作成せずにマージしてしまう

#### 原因
1. コード実装に集中すると記録作成を後回しにする
2. 「コード変更なし＝記録不要」と誤判断する
3. TodoWriteに記録タスクを含め忘れる

#### 解決策

**対策 A: Issue開始時に記録タスクをTodoに追加**
```
TodoWriteに必ず含める項目:
- 📝 DEVELOPMENT_LOG.md 更新
- 📝 CONVERSATION_LOG 作成
- 📝 DEVELOPMENT_PLAN.md / ISSUES_STATUS.md 更新
```

**対策 B: ブランチ作成時に空ファイルを作成**
```bash
# ブランチ作成後すぐに実行
touch docs/CONVERSATION_LOG_ISSUE{N}.md
```

#### 根本原因分析
- プロセスの一貫性が欠けていた
- 問題 → 記録 → 解決 → 文書化 のフローが不明確だった
- TROUBLESHOOTING.md が活用されていなかった

#### 発見日
2025-01-04（Issue #5）、2025-01-06（Issue #15-17）

#### 対応日
2025-01-06

#### 参考
- CLAUDE.md「Issue完了時の必須作業」セクション
