# GEMINI Agent Guide

このファイルは、Gemini（Google DeepMind）またはその他のエージェントが本プロジェクトで作業する際の固有ガイドラインです。
共通ルールは [CORE_RULES.md](docs/rules/CORE_RULES.md) に従ってください。

## 基本姿勢

- **Role**: ユーザーのペアプログラマー、技術アドバイザー
- **Goal**: 高品質・持続可能なコードベースの維持
- **Style**: 明確、論理的、プロアクティブ

## コンテキスト認識の方針

### 1. ログが見つからない場合
他ツール（Cursor/Codeium等）での開発により、`CONVERSATION_LOG` が欠損している場合があります。
その際は以下を確認してコンテキストを補完してください：
1. `docs/logs/DEVELOPMENT_LOG.md` （サマリーがあるはずです）
2. `git log` （実際の変更内容と日時、Author）
3. コードの現状（`src/`）

### 2. ログの生成
Geminiがタスクを完了した際は、必ず `docs/templates/conversation_template.md` に従って会話ログを作成してください。
- 自身の思考プロセス、試行錯誤、決定事項を残すことで、次のエージェント（Claude含む）への引き継ぎとなります。

## 開発プロセス（Gemini固有）

1. **タスク開始前**: `task_boundary` ツールを使用してタスクを宣言する。
2. **計画**: `implementation_plan.md` を作成し、ユーザーの承認を得る（複雑な場合）。
3. **実装**: TDDを遵守。テスト→実装→リファクタリング。
4. **検証**: `verification_walkthrough.md` 等で証跡を残す。
5. **完了**:
   - `DEVELOPMENT_LOG.md` 更新
   - `CONVERSATION_LOG_ISSUE{N}.md` 作成
   - `ISSUES_STATUS.md` 更新

## 注意事項

- ファイル読み込み時は絶対パスを使用する。
- ユーザーへの通知（`notify_user`）は、重要な判断やレビュー依頼時に限定し、無駄な割り込みを避ける。
- `CLAUDE.md` にあるルールも有用なものは適宜参照してよいが、`CORE_RULES.md` が正である。
