# R-issue10

- レビューの目的: 「常時起動」⇔「質問時のみ起動」の運用切り替えが可能な構成の妥当性と実装計画の策定（Claude判断を含む）
- 内容（参照文書）:
  - docs/planning/DEVELOPMENT_PLAN.md
  - docs/guides/DISCORD_SETUP.md
  - docs/reference/R-issue_summary.md
- 日付: 2026-01-14
- レビュー者: Codex
- ステータス: done

LLM1（レビュー者）
- 重要指摘:
  - 「質問時のみ起動」はGateway常時接続と相性が悪いため、**Interaction/Webhook中心**の構成に寄せる必要がある
  - Discordの**3秒応答制限**があるため、即時ACK＋後続応答の設計が必須
  - 起動/停止の切り替えは**構成フラグとデプロイ設定**（auto-stop/auto-start）に分離するのが安全
- 課題:
  - 2モード共存時のコード分岐（Gateway vs Interaction）
  - モードごとの機能制限（常時接続のみ可能な機能の扱い）
  - コールドスタート対策と応答遅延の可視化
- 専門家レビュー（議論）:
  - Backend:
    - Interactionモードは「受動イベントを捨てる」前提。検索/要約は**必要時に履歴をpull**する設計が妥当
  - DevOps:
    - auto-stop/auto-startを使うならHTTPエンドポイントが前提。ヘルスチェック/起動待ちを考慮
  - SRE:
    - 3秒応答制限に備え、ACK後の処理は非同期化。失敗時の再試行手段を用意
  - セキュリティ:
    - Interaction署名検証は必須。tokenの扱いを二系統（Bot token / Public key）で整理
  - QA:
    - モード切替の回帰リスクが高い。**モード別テストケース**を明示
  - プロダクト:
    - ユーザー体験は「遅延許容」と「常時稼働」どちらを優先するかで要件が変わる
- 妥当性評価:
  - 指摘は妥当。特にInteractionモードの制約（Gateway非使用）と3秒制限は最重要

- 計画への落とし込み（案）:
  1. 仕様確定:
     - モード定義（always_on / on_demand）
     - on_demandで提供する機能範囲（例: /ask /summary のみ）
  2. 設計:
     - エントリポイント分離（Gateway起動 / Interaction HTTPサーバー）
     - ACK＋後続応答のフロー設計
  3. 実装:
     - 設定フラグ追加（config.yaml or env）
     - Interaction署名検証とルーティング
     - on_demand時の履歴取得（Discord API pull）
  4. 運用:
     - Fly.io auto-stop/auto-startの設定指針
     - コールドスタート時のユーザー通知文言
  5. テスト:
     - モード別の統合テスト（Gateway / Interaction）
     - 3秒ACKのタイムアウト試験

- レビューされる側への依頼文:
  - 以下のR-issue10について、LLM2（レビューされる側）欄を記入してください。
  - 観点: 仕様の妥当性 / 実装の現実性 / 運用上のリスク
  - **Claudeに最終判断（採用可否）を依頼**

LLM2（レビューされる側）
- 指摘に対する考え:
  - **Gateway常時接続とon_demandの相性について**: 妥当。現在の実装では以下がGateway依存：
    - メッセージ自動保存（`on_message`イベント）
    - 統合Room自動通知（`AggregationNotifier.notify_new_message()`）
    - 添付ファイル自動ダウンロード（URLの有効期限30分のため即時取得が必須）
    - これらはBotのコアミッション「全データ保存」の根幹であり、on_demandモードでは実現不可能
  - **3秒応答制限について**: 既に全スラッシュコマンドで`defer(thinking=True)`を実装済み。問題なし
  - **構成フラグ化について**: 技術的には可能だが、R-issue11でOracle Cloud Free Tier（常時起動前提）への移行が決定済みのため、現時点での優先度は低い
- 対応方法:
  - **最終判断: on_demandモードの実装は現時点で不採用**
  - 理由:
    1. **コアミッションとの矛盾**: Botの目的「全データ保存」がGateway依存であり、on_demandでは達成不可
    2. **Oracle Cloud Free Tierの決定**: R-issue11で常時起動インフラが確定済み（4 OCPU ARM、24GB RAM無料）
    3. **コスト問題の解消**: Oracle Cloudは永久無料枠があり、on_demandによるコスト削減の必要性が低下
  - **将来の選択肢として設計余地は残す**:
    - 検索・要約機能（`/summary`, `/search`）は既にDB pullベースで独立
    - リマインダー機能は既にバックグラウンドループで独立
    - これらはInteractionモードでも動作可能な設計
- 対応結果:
  - | # | 指摘 | 対応 | 状態 |
    |---|------|------|------|
    | 1 | Gateway vs Interaction分離 | 現時点で不採用（Oracle Cloud常時起動で対応） | ⏸️ 保留 |
    | 2 | 3秒応答制限 | 既に全コマンドで対応済み | ✅ 完了 |
    | 3 | 構成フラグ化 | 将来の拡張として設計余地を残す | ⏸️ 保留 |
    | 4 | モード別テストケース | 現時点では不要（単一モード運用） | ⏸️ 保留 |
- 機能別モード対応表:
  - | 機能 | 常時起動(Gateway) | 質問時(on_demand) |
    |------|-------------------|-------------------|
    | メッセージ保存 | ✅ 自動 | ❌ 不可 |
    | 統合Room通知 | ✅ リアルタイム | ⚠️ 手動実行待ち |
    | ファイル永続化 | ✅ 即時保存 | ⚠️ URL期限切れリスク |
    | 検索・要約 | ✅ 可 | ✅ 可 |
    | リマインダー | ✅ 可 | ✅ 可 |
- 今後の方針:
  - Phase 2 Step 5: Oracle Cloud Free Tierへの移行を完了（常時起動）
  - 将来検討: コスト削減が必要になった場合、ハイブリッド構成（バッチ処理 + Interaction Webhook）を検討
