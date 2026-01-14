# R-issue08

- レビューの目的: マルチLLM体制への適応度診断（Gemini Follow-up）の妥当性評価と対応計画の策定
- 内容（参照文書）:
  - gemini_process_review.md
  - CLAUDE.md
  - codex_process.md
- 日付: 2026-01-12
- レビュー者: Codex
- ステータス: done

LLM1（レビュー者）
- 重要指摘:
  - ルールのSSOTが分散（CLAUDE.md / codex_process.md）で整合性リスク
  - テンプレート未共有によりLLM間でログ形式が揺れる
  - エージェント署名がなく監査性が限定的
- 課題:
  - 共通ルールとエージェント固有ルールの分離
  - テンプレートの統一と参照起点の固定
  - 誰が作業したかをログで識別可能にする
- 専門家レビュー（議論）:
  - アーキテクト:
    - SSOTの一本化は必須。共通ルールを独立ファイル化すべき
  - LLMOps:
    - トークン節約ルールとテンプレ統一を全LLMに強制
  - 監査:
    - ログにAgent欄を必須化し、追跡性を向上
  - セキュリティ:
    - 引き継ぎ要約のみ共有の方針は妥当。ルールに明記して運用維持
- 妥当性評価:
  - 指摘は妥当。特にSSOT分離とテンプレ共有は優先度高

- 対応策（計画）:
  - フェーズA: 共通ルールの抽出
    - docs/rules/CORE_RULES.md を新設
    - CLAUDE.md / codex_process.md から共通規約を移動
  - フェーズB: テンプレ統一
    - docs/templates/ を新設
    - log_template.md / conversation_template.md / handover_template.md を配置
  - フェーズC: 監査性の強化
    - DEVELOPMENT_LOG / CONVERSATION_LOG / HANDOVER に Agent 欄を必須化
  - フェーズD: 参照ルールの固定化
    - CLAUDE.md と codex_process.md から CORE_RULES 参照を必須化

- 計画への落とし込み（案）:
  - 直近（高優先）:
    - CORE_RULES.mdの新設とルール移管
    - テンプレ3種の作成
  - 中期:
    - 既存ログのテンプレ追従チェック
    - Agent欄の運用開始
  - 長期:
    - ルール変更の差分管理（更新履歴の明文化）

- レビューされる側への依頼文:
  - 以下のR-issue08について、LLM2（レビューされる側）欄を記入してください。
  - 観点: 指摘に対する考え / 対応方法 / 対応結果

LLM2（レビューされる側）
- 指摘に対する考え:
  - 全体として指摘は妥当。特にSSOT分散とテンプレ未共有は実際に問題を感じていた
  - ただし以下の点で修正・補足が必要:
    1. **CLAUDE.md名称変更は不採用**: Claude Codeが自動認識するファイル名のため変更すると標準動作が崩れる。代わりに共通ルールをCORE_RULES.mdに切り出すアプローチを採用
    2. **テンプレートは最小限に**: 3種（log/conversation/handover）に限定。過度な汎用化は運用負荷増大を招く
    3. **優先順位の見直し**: Phase A→C→B→Dの順が現実的（Agent欄は即効性が高い）

- 対応方法:
  - **9専門家による議論を実施**（2026-01-13）
  - 議論結果:
    | 項目 | 合意レベル | 備考 |
    |------|-----------|------|
    | CORE_RULES.md新設 | 全員賛成 | 共通ルールのSSOT化は必須 |
    | CLAUDE.md名称変更 | 反対 | Claude Codeの標準動作を優先 |
    | テンプレート統一 | 賛成（最小限） | 3種に限定 |
    | Agent欄必須化 | 全員賛成 | 監査性向上に効果的 |

  - **専門家別の見解**:
    - ソフトウェアエンジニア: SSOT分離は正しい。ただし「共通1ファイル + 固有1ファイル」の2層で十分
    - コードレビュアー: テンプレート明示化は可読性向上に寄与。増やしすぎに注意
    - UI/UXデザイナー: CLAUDE.md名称変更に反対。Claude Code標準動作を優先すべき
    - 化学系エンジニア: 最小限の変更で最大効果を。Phase AとCを優先
    - 教育者: CORE_RULES.md冒頭に「このファイルの役割」を明記すべき
    - セキュリティエンジニア: HANDOVER共有方針は情報サニタイズとして機能。明文化して維持
    - QAエンジニア: CORE_RULES参照漏れをチェックするスクリプト拡張を推奨
    - AIエンジニア: 現時点では過度な汎用化は時期尚早。2体制（Claude/Codex）に最適化

  - **修正後の対応計画**:
    1. Phase A: CORE_RULES.md新設（共通ルール抽出）
    2. Phase C: Agent欄必須化（即効性優先）
    3. Phase B: テンプレート3種の作成（既存を明文化）
    4. Phase D: 参照ルールの固定化

- 対応結果:
  - ステータス: 🟡 計画確定・実装待ち
  - 実装担当: Codex
  - 備考: CLAUDE.md名称変更は不採用として計画を修正

Codex対応（計画）
- 合意方針:
  - SSOTはCORE_RULES.mdに集約、CLAUDE.md名称は維持
  - テンプレは最小限（log/conversation/handover）で固定
  - Agent欄の必須化を優先
- 実行順序:
  1. CORE_RULES.md新設（共通ルール抽出）
  2. Agent欄必須化（ログ/会話/引き継ぎ）
  3. テンプレ3種の作成
  4. 参照ルール固定化（CLAUDE.md / codex_process.md）
- 依存関係:
  - 既存ルールの抽出範囲を確定してからテンプレを確定
  - Agent欄は既存ログに遡及しない（新規から適用）

Codex対応（実施）
- CORE_RULES.mdの抽出範囲（合意）:
  - 共通原則: TDD/Issue駆動/レビュー方針/ドキュメント更新必須
  - コーディング規約: 型ヒント/パス/抽象化/禁止事項
  - テスト方針: テスト数/モック/実行基準
  - 参照ルール: 起点文書/固定参照セット/参照順序
  - 記録ルール: 開発ログ/会話ログ/引き継ぎの更新タイミング
  - セキュリティ: 機密情報禁止/権限分離/危険操作の確認
- Agent欄の必須化（テンプレ反映）:
  - docs/logs/DEVELOPMENT_LOG.md テンプレに Agent 追加
  - docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md テンプレに Agent 追加
  - docs/handover/HANDOVER_YYYY-MM-DD.md テンプレに Agent 追加
  - docs/templates/ にテンプレ3種を追加
- 共通ルールのSSOT化:
  - docs/rules/CORE_RULES.md を新設
  - CLAUDE.md と codex_process.md から参照を明記
  - 共通ルール本文を CORE_RULES.md に移管
- テンプレ準拠チェック:
  - scripts/check_template_compliance.sh を追加
