# CORE_RULES

このファイルは、全LLM共通のルール（SSOT）です。

## 共通原則

- TDDを基本とする
- Issue駆動で進める（1 Issue = 1 PR = 1 機能）
- 9つの専門家視点でレビュー
- ドキュメント更新は必須（コード変更がなくても記録する）

## コーディング規約

- 型ヒントを必ず使う
- docstringを書く（Google style）
- 関数は小さく、単一責任
- マジックナンバー禁止（定数化）
- パスは `pathlib.Path` を使用（OS互換）
- 抽象化を意識（AI/ストレージは差し替え可能に）
- ruffでフォーマット・リント

## テスト方針

- TDD（テスト先行）
- tests/ にミラー構成
- 1機能につき最低3テスト（正常/異常/境界）
- AI部分はモック化してテスト
- テスト結果で品質がわかるようにする

## やってはいけないこと

- Workspace AのデータをBに見せる処理
- APIキーのハードコード
- テストなしのPR
- 破壊的なDB操作（DELETE/DROP）を確認なしで実行
- OS依存のパス記述（`\\` や `/` の直書き）
- AIプロバイダーの直接呼び出し（必ずrouterを経由）

## 開発フロー（最小）

1. GitHub Issueを確認
2. `feature/issue-{番号}` ブランチを作成
3. テストを先に書く
4. 実装
5. `uv run ruff check src/` でリントチェック
6. `uv run pytest tests/ -v` で全テスト通過確認
7. PRを作成

## 参照ルール

- 起点: docs/INDEX.md
- 固定参照セット: CLAUDE.md / docs/planning/DEVELOPMENT_PLAN.md / docs/planning/ISSUES_STATUS.md / docs/handover/HANDOVER_*.md（最新）
- 詳細は必要時のみ参照する

## 記録ルール

- Issue完了時は記録を必ず更新
- 開発記録: docs/logs/DEVELOPMENT_LOG.md
- 会話ログ: docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md
  - ※ 外部ツール（Cursor/Codeium等）利用でログ出力が困難な場合は、DEVELOPMENT_LOGへの詳細な要約で代替可とする
  - ※ その場合、Gitコミットハッシュや変更内容をDEVELOPMENT_LOGに明記すること
- 状態更新: docs/planning/DEVELOPMENT_PLAN.md / docs/planning/ISSUES_STATUS.md
- テンプレート: docs/templates/log_template.md / docs/templates/conversation_template.md / docs/templates/handover_template.md
- Agent欄は必須（誰が作業したかを明記）

## セキュリティ

- 機密情報の記載禁止（APIキー/PII）
- 破壊的操作は必ず確認する
- gitleaksによるシークレット検出
  - pre-commit hookでコミット時に自動チェック
  - GitHub ActionsでPR時にも二重チェック
  - 誤検知は `.gitleaksignore` で除外設定
