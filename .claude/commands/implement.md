---
name: implement
description: 機能実装を依頼する。Issue番号または機能説明を引数として渡す。
---

# 実装タスク

$ARGUMENTS

## 実装手順

1. **要件確認**
   - docs/REQUIREMENTS.md で該当機能の要件を確認
   - 不明点があれば質問

2. **設計確認**
   - docs/ARCHITECTURE.md で設計方針を確認
   - 既存コードとの整合性を確認

3. **テスト先行（TDD）**
   - tests/ に該当するテストファイルを作成または更新
   - 正常系・異常系・境界値のテストケースを作成
   - テストが失敗することを確認（Red）

4. **実装**
   - src/ に実装コードを作成
   - CLAUDE.md のコーディング規約に従う
   - 型ヒント、docstringを必ず記述

5. **テスト通過確認（Green）**
   - `uv run pytest tests/ -v` で全テスト通過を確認

6. **リファクタリング**
   - コードの重複を排除
   - 可読性を向上

7. **リント・型チェック**
   - `uv run ruff check src/`
   - `uv run pyright src/`

8. **完了報告**
   - 実装内容のサマリーを報告
   - 変更したファイル一覧を提示
