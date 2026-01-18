# R-issue11: クラウド移行設計変更（Fly.io → Oracle Cloud Free Tier）

## 要約

Fly.ioが無料で使えないことが判明したため、Phase 2 Step 5のクラウド移行先をOracle Cloud Free Tierに変更した。

## Agent

Claude Opus 4.5

## 日付

2026-01-17

---

## 背景

- 当初計画: Fly.ioでクラウドデプロイ（Phase 2 Step 5）
- 問題発覚: Fly.ioの無料枠が使えない（課金必須）
- 制約条件:
  - クラウド必須（ローカルPC常時稼働は不可）
  - リアルタイムが望ましいが、1時間おきでも許容
  - コスト: 無料または極めて低コスト

---

## 検討プロセス

### 1. 選択肢の洗い出し

| 選択肢 | 常時稼働 | コスト | スラッシュコマンド | 音声録音 |
|--------|---------|--------|-------------------|---------|
| Oracle Cloud Free Tier | ✅ | 永久無料 | ✅ | ✅ |
| GitHub Actions Batch | ❌ | 無料 | ❌ | ❌ |
| Railway | ✅ | 月$5限定 | ✅ | ✅ |
| Render.com | ⚠️ スリープ | 無料 | ⚠️ | ⚠️ |

### 2. 専門家視点での評価

9つの専門家視点（ソフトウェアエンジニア、Python開発者、コードレビュアー、UI/UXデザイナー、ドメインエキスパート、教育者、セキュリティエンジニア、QAエンジニア、AIエンジニア）で評価を実施。

**結論**: Oracle Cloud Free Tierを推奨
- コード変更: 0%（既存Dockerfileがそのまま動く）
- 機能維持: 全機能（スラッシュコマンド、音声録音、リアルタイム通知）
- リスク: 低（既存コードがそのまま動く）

### 3. ユーザー提案との整合性確認

ユーザー提案「無料POC → 有料A → 有料B」の段階移行設計との整合性を確認。

| フェーズ | ユーザー提案 | 実際の対応 |
|----------|--------------|------------|
| 無料POC | バッチ+NDJSON | Oracle Cloud Free Tier（常時稼働・SQLite） |
| 有料A | 常時稼働+PostgreSQL | Oracle CloudでPostgreSQL追加 |
| 有料B | Queue/Workers分割 | 必要時にAWS/GCPへ移行 |

**設計思想は維持**:
- ベンダ非依存: SQLite/PostgreSQLは移行可能
- Provider境界で差し替え可能: DB/Storage/AI層は抽象化済み
- Workspace分離は強制: 既存設計で担保済み

---

## 決定事項

1. **クラウド**: Oracle Cloud Free Tier（Fly.ioから変更）
2. **DB設計**: SQLite/SQLAlchemy維持（NDJSONへの変更なし）
3. **コード変更**: なし（既存Dockerfileをそのまま使用）

---

## 変更したファイル

| ファイル | 変更内容 |
|----------|----------|
| docs/planning/DEVELOPMENT_PLAN.md | Phase 2 Step 5をOracle Cloudに変更、セクション6.3更新 |
| docs/specs/ARCHITECTURE.md | セクション5.2をOracle Cloud構成に更新、5.3追加 |
| docs/rules/CORE_RULES.md | クラウド移行設計原則セクション追加 |
| docs/guides/DEPLOY_ORACLE.md | 新規作成（Oracle Cloudデプロイ手順） |
| fly.toml | 参考用コメント追加 |

---

## Issue更新内容

| Issue | 変更前 | 変更後 |
|-------|--------|--------|
| #22 | Dockerfile作成 | そのまま（✅完了） |
| #23 | fly.toml設定 | Oracle Cloud環境構築 |
| #24 | SQLite Volume対応 | OCI Block Volume対応 |
| #25 | Fly.ioデプロイ | Oracle Cloudデプロイ |

---

## 次のステップ

1. Oracle Cloud Free Tier登録
2. ARM A1インスタンス作成（docs/guides/DEPLOY_ORACLE.md参照）
3. Issue #23-25の実施
4. 本番稼働確認

---

## 参考リンク

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [計画ファイル](.claude/plans/prancy-wondering-zebra.md)
