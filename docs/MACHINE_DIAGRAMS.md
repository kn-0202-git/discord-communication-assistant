# Machine Diagrams (Existing Components)

This document captures deployment-style diagrams for existing components. The diagrams focus on machine/process boundaries and external services.

## 1. System Nodes (Current Target)

```mermaid
flowchart LR
  subgraph Discord[Discord Platform]
    WS_A[Workspace A]\nRooms
    WS_B[Workspace B]\nRooms
  end

  subgraph UserPC[Local PC]
    BOT[Bot Process]\n(discord.py)
    DB[(SQLite DB)]
    FS[(Local Filesystem)]
    BOT --> DB
    BOT --> FS
  end

  subgraph AI[AI Providers]
    OPENAI[OpenAI API]
    ANTHROPIC[Anthropic API]
    GOOGLE[Google API]
    GROQ[Groq API]
    LOCAL[Local LLM]
  end

  WS_A -->|Discord API| BOT
  WS_B -->|Discord API| BOT
  BOT -->|API calls| OPENAI
  BOT -->|API calls| ANTHROPIC
  BOT -->|API calls| GOOGLE
  BOT -->|API calls| GROQ
  BOT -->|API calls| LOCAL
```

## 2. Local Runtime (Phase 1)

```mermaid
flowchart TB
  subgraph Discord[Discord]
    API[Discord API]
  end

  subgraph LocalPC[Local PC (macOS/Windows)]
    BOT[Bot Process]\n(discord.py)
    DB[(SQLite DB)]
    STORE[(Local Storage)]
    BOT --> DB
    BOT --> STORE
  end

  subgraph AI[AI Providers]
    AIP[External AI APIs]
  end

  API --> BOT
  BOT --> AIP
```

## 3. Cloud Runtime (Phase 3)

```mermaid
flowchart TB
  subgraph Discord[Discord]
    API[Discord API]
  end

  subgraph Drive[Google Drive]
    GDRIVE[Drive API]
  end

  subgraph Fly[Fly.io (Docker)]
    BOT[Bot Process]\n(discord.py)
    DB[(PostgreSQL)]
    STORE[(Cloud Storage)]
    BOT --> DB
    BOT --> STORE
  end

  subgraph AI[AI Providers]
    AIP[External AI APIs]
  end

  API --> BOT
  GDRIVE --> STORE
  BOT --> AIP
```

## 4. Internal Component Boundaries (Bot Process)

```mermaid
flowchart LR
  subgraph Bot[Bot Process]
    LISTEN[Listeners]
    CMDS[Commands]
    CORE[Core]
  end

  subgraph Core[Core]
    DB[(Database)]
    ST[(Storage)]
    AI[AI Services]
  end

  LISTEN --> CORE
  CMDS --> CORE
  CORE --> DB
  CORE --> ST
  CORE --> AI
```

## 5. 人間にわかりやすいMAP（日本語）

```mermaid
mindmap
  root((Discord連携Bot))
    Discord
      Workspace A
        Room 1(技術相談)
        Room 2(事務連絡)
        Room 6(統合Room)
      Workspace B
        Room 3(技術相談)
        Room 4(納品管理)
        Room 6(統合Room)
    Botプロセス
      受信(メッセージ/ファイル/通話)
      コマンド
        summary(要約)
        search(検索)
        ask(資料回答)
        record(録音切替)
        save(保存)
      Core
        Database
        Storage
        AI Services
    保存先
      SQLite(ローカルDB)
      Local Files(ローカル保存)
      PostgreSQL(クラウド)
      Cloud Storage
      Google Drive
    AIプロバイダ
      OpenAI
      Anthropic
      Google
      Groq
      Local LLM
```
