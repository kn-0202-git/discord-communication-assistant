---
name: fix-issue
description: GitHub Issueの修正を依頼する。Issue番号を引数として渡す。
---

# Issue修正

Issue: $ARGUMENTS

## 修正手順

1. **Issue内容の取得**
   - `gh issue view $ARGUMENTS` でIssue詳細を取得
   - 問題の内容と期待される動作を確認

2. **原因分析**
   - 関連ファイルを検索
   - 問題の根本原因を特定

3. **テスト作成（再現確認）**
   - 問題を再現するテストを作成
   - テストが失敗することを確認

4. **修正実装**
   - 最小限の変更で修正
   - 副作用がないことを確認

5. **テスト通過確認**
   - 作成したテストが通過
   - 既存テストも全て通過

6. **コミット・PR作成**
   - `git commit -m "fix: #{Issue番号} {修正内容}"`
   - `gh pr create --title "fix: #{Issue番号} {修正内容}"`
