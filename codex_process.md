# Codex 設計・開発プロセス

このプロセスは、理想（品質・再現性）と現実（1人開発・ドキュメント運用負荷）を両立するための実務手順です。
実際の開発履歴・運用ルール（CLAUDE.md、DEVELOPMENT_PLAN.md、ISSUES_STATUS.md、TROUBLESHOOTING.md）に合わせて整理しています。

## 基本原則

- Issue駆動で進める（1 Issue = 1 PR = 1 機能）
- 例外時は統合扱いを明記し、完了条件と更新文書を個別に記録する
- TDDを基本とし、テスト・リント・型チェックで品質担保
- 9つの専門家視点でレビュー（ソフトウェア/ Python/ コード/ UI/ 業務/ 教育/ セキュリティ/ QA/ AI）
- ドキュメント更新は必須タスク（コード変更がなくても記録する）
- 運用の現実に合わせる（gh/brewがない前提、Web UI運用も許容）
- トークン節約は「ログ削減」ではなく「運用の圧縮」で対応する

---

## 1. 要求定義フロー

### 目的
「何を解決するか」を明確にし、Phase/Issueに落とし込む。

### 入力
- 現場の課題・ユーザー要望
- 既存の運用状況（docs/logs/DEVELOPMENT_LOG.md など）

### 手順
1. VISIONを確認（docs/specs/VISION.md）
2. 現状のロードマップとPhase位置を確認（docs/planning/ROADMAP.md）
3. 要求を一言で要約し、解決対象・対象ユーザー・期待効果を明記
4. 既存Issue/課題と重複しないか確認（docs/planning/ISSUES_STATUS.md）
5. 要求をPhaseまたはIssue候補に紐付ける

### 成果物
- 要求の要約
- Phase/Issueの当たり付け

### 現実運用メモ
- 要求が曖昧な場合は「最小の受け入れ条件」を先に決める
- 既存の「試験運用」「Phase 2/3」計画に沿って優先度を付ける

---

## 2. 要件定義フロー

### 目的
要求を実装可能な仕様に変換し、テスト可能な形にする。

### 入力
- 要求定義の結果
- 既存仕様（docs/specs/REQUIREMENTS.md, docs/specs/ARCHITECTURE.md）

### 手順
1. 要件をユーザー価値と制約に分解する
2. 要件をdocs/specs/REQUIREMENTS.mdに追記（必要ならDECISIONSにも理由を残す）
3. 主要機能の設計をdocs/specs/ARCHITECTURE.mdへ反映
4. テスト観点をdocs/TEST_PLAN.mdに追加
5. Issueテンプレートに完了条件・関連ドキュメント・テストIDを設定

### 成果物
- 要件更新（REQUIREMENTS/ARCHITECTURE/TEST_PLAN）
- Issueの完了条件定義

### 現実運用メモ
- 仕様が決めきれない場合は「仮仕様 + リスク」をDECISIONS.mdに残す
- 変更履歴はDEVELOPMENT_LOG.mdに残す

---

## 3. 開発フロー

### 目的
安定してリリースできる品質で機能を実装する。

### 入力
- Issue（完了条件・テストID）
- 対応する設計/要件

### 手順
1. ブランチ作成（feature/issue-{n}）
2. テスト作成（TDD）
3. 実装
4. テスト実行・修正
5. ruff/pyright チェック
6. 手動テスト（必要時）
7. コミット・プッシュ
8. ドキュメント更新（必須）
9. マージ前チェック
10. mainにマージ

### マージ前チェックテンプレート

```
マージ前チェック
- [ ] DoDチェックリスト完了
- [ ] 重要な指摘事項はISSUES_STATUS.mdに追加済み
- [ ] 変更内容とテスト結果をDEVELOPMENT_LOG.mdに記録済み
- [ ] 未コミットが残っていない（git status確認）
```

### 成果物
- コード変更
- テスト
- 記録ドキュメント

### 必須ドキュメント更新（コード変更なしでも必須）
- docs/logs/DEVELOPMENT_LOG.md
- docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md
- docs/planning/DEVELOPMENT_PLAN.md
- docs/planning/ISSUES_STATUS.md

### 現実運用メモ
- ghがない場合はWeb UIでPR作成・マージ
- ブランチ作成直後に空のCONVERSATION_LOGを作ると忘れ防止になる
- 連続実装で複数Issueをまとめる場合は、統合理由と個別完了条件を明記する
- 統合Issueは1ファイルあたり最大3〜4件を目安にし、冒頭にクイックインデックスを付ける

---

## 4. 開発中トラブル対応フロー

### 目的
問題の再発を防ぎ、プロセスに反映する。

### 入力
- エラー・失敗事例・詰まり

### 手順
1. 問題をISSUES_STATUS.mdの「プロセス改善」へ記録
2. statusを🟡に変更
3. 詳細をTROUBLESHOOTING.mdに記録（症状/原因/解決策）
4. 対応内容をDEVELOPMENT_LOG.mdに記録
5. 解決後にISSUES_STATUS.mdを🟢に更新

### 成果物
- TROUBLESHOOTING.mdの知見
- プロセス改善の履歴

### 現実運用メモ
- 「文書作成忘れ」など運用課題は必ずプロセスに反映する
- 例: TodoWriteに記録タスクを必須化

---

## 5. レビューフロー

### 目的
多角的に品質/安全性を確認し、リスクを事前に潰す。

### 入力
- 実装済みIssue/PR
- 関連ドキュメント

### 手順
1. 9つの専門家視点でレビュー
   - ソフトウェアエンジニア
   - Python開発者
   - コードレビュアー
   - UI/UXデザイナー
   - 化学系エンジニア（ドメイン）
   - 教育者
   - セキュリティエンジニア
   - QAエンジニア
   - AIエンジニア
2. 指摘をCritical/Warning/Suggestionで分類
3. 重要な指摘はISSUES_STATUS.mdに課題として追加
4. レビュー結果を記録（DEVELOPMENT_LOG.md or レビュー専用文書）

### 成果物
- 指摘リスト
- 追加Issueまたは改善タスク

### 現実運用メモ
- 実装規模が小さい場合でも最低限「セキュリティ/QA/コード」観点は確認
- 重要なリスクは必ず文書化する（後追い修正を防ぐ）
- レビュー対応時は「実行コマンド/日時/環境」を記録する
- レビューは先にCritical/Warning/Suggestionのみ提示し、詳細は要求時に展開する

---

## 定義：完了条件（DoD）

- テストが書かれている
- 全テスト通過（uv run pytest）
- ruff/pyright 通過
- 手動テスト（必要時）
- docs/logs/DEVELOPMENT_LOG.md 更新
- docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md 作成
- docs/planning/DEVELOPMENT_PLAN.md / docs/planning/ISSUES_STATUS.md 更新
- マージ前チェック完了

### DoDテンプレート

```
DoDチェックリスト
- [ ] テストが書かれている
- [ ] 全テスト通過（uv run pytest）
- [ ] ruff/pyright 通過
- [ ] 手動テスト（必要時）
- [ ] docs/logs/DEVELOPMENT_LOG.md 更新
- [ ] docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md 作成
- [ ] docs/planning/DEVELOPMENT_PLAN.md / docs/planning/ISSUES_STATUS.md 更新
- [ ] マージ前チェック完了
```

---

## 会話ログ運用（トークン節約）

### 参照文書固定セット
- CLAUDE.md
- docs/planning/DEVELOPMENT_PLAN.md
- docs/planning/ISSUES_STATUS.md

### 会話ログの構成
- 先頭に「要約」セクションを置く（冒頭で結論が分かるようにする）
- 「要約 + 詳細」の二層構成にする
- 統合Issueは冒頭にクイックインデックスを付ける
- 作成日/作成時点（後追い作成含む）を明記する

### 出力制約
- 原則5〜7項目以内で要点を提示
- 詳細は要求時にのみ拡張
- 変更は差分のみ記載（全文再掲を避ける）
- テスト結果は合格件数のみ記載（失敗時のみ詳細）

## フロー別ドキュメント対応表

### 要求定義フロー

- docs/specs/VISION.md: 目的とゴールの整合確認
- docs/planning/ROADMAP.md: Phase位置と優先度の確認
- docs/planning/ISSUES_STATUS.md: 既存課題の重複確認
- docs/planning/DEVELOPMENT_PLAN.md: Issueの当たり付け

### 要件定義フロー

- docs/specs/REQUIREMENTS.md: 要件の明文化
- docs/specs/ARCHITECTURE.md: 設計反映
- docs/TEST_PLAN.md: テスト観点の追加
- docs/reference/DECISIONS.md: 判断の理由と前提の記録

### 開発フロー

- docs/logs/DEVELOPMENT_LOG.md: 実装記録の詳細
- docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md: 会話ログの記録
- docs/planning/DEVELOPMENT_PLAN.md: Issue状態更新
- docs/planning/ISSUES_STATUS.md: 課題状態更新
- CLAUDE.md: 必須手順の確認

### 開発中トラブル対応フロー

- docs/planning/ISSUES_STATUS.md: プロセス改善の記録
- docs/reference/TROUBLESHOOTING.md: 症状/原因/解決策の整理
- docs/logs/DEVELOPMENT_LOG.md: 対応記録

### レビューフロー

- CLAUDE.md: 専門家視点の確認
- docs/planning/ISSUES_STATUS.md: 指摘事項の課題化
- docs/logs/DEVELOPMENT_LOG.md: レビュー記録
- codex_review_md: レビュー結果の集約（本リポジトリの実例）

---

## ドキュメント別フロー対応表

### CLAUDE.md

- 要求定義フロー: 開発原則の確認
- 開発フロー: 必須手順とチェックリストの確認
- レビューフロー: 専門家視点の確認

### docs/specs/VISION.md

- 要求定義フロー: 目的・ゴールの整合確認

### docs/planning/ROADMAP.md

- 要求定義フロー: Phase/優先度の確認

### docs/planning/DEVELOPMENT_PLAN.md

- 要求定義フロー: Issueの当たり付け
- 開発フロー: Issue状態更新

### docs/planning/ISSUES_STATUS.md

- 要求定義フロー: 既存課題の重複確認
- 開発フロー: 課題状態更新
- 開発中トラブル対応フロー: プロセス改善の記録
- レビューフロー: 指摘事項の課題化

### docs/specs/REQUIREMENTS.md

- 要件定義フロー: 要件の明文化

### docs/specs/ARCHITECTURE.md

- 要件定義フロー: 設計反映

### docs/TEST_PLAN.md

- 要件定義フロー: テスト観点の追加

### docs/reference/DECISIONS.md

- 要件定義フロー: 判断の理由と前提の記録

### docs/logs/DEVELOPMENT_LOG.md

- 開発フロー: 実装記録
- 開発中トラブル対応フロー: 対応記録
- レビューフロー: レビュー記録

### docs/archive/conversations/CONVERSATION_LOG_ISSUE{N}.md

- 開発フロー: 会話ログの記録

### docs/reference/TROUBLESHOOTING.md

- 開発中トラブル対応フロー: 症状/原因/解決策の整理

### codex_review_md

- レビューフロー: レビュー結果の集約

---

## フロー図

### 要求定義フロー

```
課題・要望の入力
        |
        v
VISION/ROADMAP確認
        |
        v
要求を要約・対象特定
        |
        v
ISSUES_STATUS重複確認
        |
        v
Phase/Issueに紐付け
```

### 要件定義フロー

```
要求定義の結果
        |
        v
要件分解（価値/制約）
        |
        v
REQUIREMENTS更新
        |
        v
ARCHITECTURE更新
        |
        v
TEST_PLAN更新
        |
        v
Issue完了条件設定
```

### 開発フロー

```
Issue開始
   |
   v
ブランチ作成
   |
   v
テスト作成
   |
   v
実装
   |
   v
テスト/リント/型チェック
   |
   v
コミット・プッシュ
   |
   v
必須ドキュメント更新
   |
   v
mainにマージ
```

### 開発中トラブル対応フロー

```
問題発生
   |
   v
ISSUES_STATUS記録
   |
   v
TROUBLESHOOTING記録
   |
   v
DEVELOPMENT_LOG記録
   |
   v
対策実施
   |
   v
ISSUES_STATUS完了更新
```

### レビューフロー

```
実装完了
   |
   v
9専門家レビュー
   |
   v
Critical/Warning/Suggestion分類
   |
   v
重要指摘を課題化
   |
   v
レビュー記録
```

---

## 参考ドキュメント

- CLAUDE.md
- docs/planning/DEVELOPMENT_PLAN.md
- docs/planning/ISSUES_STATUS.md
- docs/logs/DEVELOPMENT_LOG.md
- docs/reference/TROUBLESHOOTING.md
- docs/specs/REQUIREMENTS.md
- docs/specs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/planning/ROADMAP.md
