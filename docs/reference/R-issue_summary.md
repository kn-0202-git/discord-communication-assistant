# R-issue Summary

R-issueの起点文書。まずここで状態と対象タスクを確認し、該当ファイルを開く。

## 運用フロー

1. このファイルでステータス/対象タスク/参照を確認
2. 該当R-issueファイルを開いて詳細を確認
3. 更新時はR-issueファイルを編集し、ここも更新

## 一覧

| ID | ステータス | 日付 | レビューの目的 | 対象タスク | 参照（主要） | ファイル |
| --- | --- | --- | --- | --- | --- | --- |
| R-issue01 | done | 2026-01-09 | 会話ログ運用の改善点整理 | 追跡性/再現性の改善 | docs/logs/DEVELOPMENT_LOG.md ほか | docs/r-issues/R-issue01.md |
| R-issue02 | done | 2026-01-09 | トークン消費削減の運用改善 | 参照/出力の圧縮 | codex_process.md ほか | docs/r-issues/R-issue02.md |
| R-issue03 | done | 2026-01-11 | 引き継ぎ運用の最小対策 | 途中停止時の復帰性 | docs/handover/HANDOVER_2026-01-11.md ほか | docs/r-issues/R-issue03.md |
| R-issue04 | done | 2026-01-12 | DEVELOPMENT_LOG肥大化の対策 | 参照コストの削減 | docs/logs/DEVELOPMENT_SUMMARY.md, docs/archive/logs/DEVELOPMENT_LOG_PHASE{N}.md | docs/r-issues/R-issue04.md |
| R-issue05 | done | 2026-01-12 | docs整理方針の策定 | 参照導線の最適化 | docs/INDEX.md ほか | docs/r-issues/R-issue05.md |
| R-issue06 | done | 2026-01-12 | LLM間の作業共有手段の整理 | 参照点の固定化 | docs/handover/HANDOVER_*.md ほか | docs/r-issues/R-issue06.md |
| R-issue07 | done | 2026-01-12 | Geminiレビューの妥当性評価 | 対応優先度の合意 | gemini_review.md | docs/r-issues/R-issue07.md |
| R-issue08 | done | 2026-01-12 | マルチLLM体制への適応度診断 | ルール/テンプレの共通化 | gemini_process_review.md | docs/r-issues/R-issue08.md |
| R-issue09 | superseded | 2026-01-13 | ~~Fly.io移行の実行検証~~ | ~~Docker/Fly CLI/Volume/デプロイ~~ | R-issue11で代替 | docs/r-issues/R-issue09.md |
| R-issue10 | done | 2026-01-14 | 常時起動/質問時起動の切替設計 | Discord運用モード分岐 | docs/planning/DEVELOPMENT_PLAN.md ほか | docs/r-issues/R-issue10.md |
| R-issue11 | done | 2026-01-17 | クラウド移行設計変更 | Fly.io→Oracle Cloud Free Tier | docs/guides/DEPLOY_ORACLE.md ほか | docs/r-issues/R-issue11.md |

## 更新ルール

- 追加/更新時はR-issueファイルとこの一覧を同時に更新する
- ステータス変更や対象タスク変更は一覧にも反映する
- 参照文書が増えた場合は「参照（主要）」を簡潔に更新する
