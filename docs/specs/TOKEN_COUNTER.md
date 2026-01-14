# Token Counter Design

## 目的

LLMのコンテキスト上限を超えないように、履歴の計測とトリム方針を明文化する。

## 対象

- AIプロバイダーの generate_with_context
- 会話履歴の結合処理

## 方針

- トークン数を概算する（厳密なモデル依存計測は後回し）
- 上限超過時は古い履歴から削除
- 重要メタ情報（system/指示）は優先的に残す

## 仕様（案）

- 入力: messages (role, content) のリスト
- 出力: トリム後の messages
- ルール:
  - system は原則保持
  - user/assistant は古い順に削除
  - 目標トークン数を超えた場合に削除を繰り返す

## 仕様（確定）

- 目標トークン数:
  - 既定: 6,000（安全側）
  - 設定: config.yaml の `ai.token_budget` で上書き
- トークン換算:
  - 1 token ≒ 4 chars（UTF-8の概算）
  - 概算式: `ceil(len(text) / 4)`
- 例外保持:
  - system は必ず保持
  - user/assistant は古い順に削除
  - 削除後も上限を超える場合は最新の user/assistant を残し、それ以外を削除

## 設計メモ

- 厳密なモデル別計測は後回し（実装コストが高いため）
- まずは運用事故を防ぐ簡易トリムで開始する
