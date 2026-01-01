# QuantCoder CLI v2.0 - Architecture Documentation (Gamma Branch)

This document provides comprehensive flowcharts and diagrams describing the architecture of QuantCoder CLI v2.0 (gamma branch).

---

## Table of Contents

1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Entry Points & Execution Modes](#2-entry-points--execution-modes)
3. [Tool System Architecture](#3-tool-system-architecture)
4. [Multi-Agent Orchestration](#4-multi-agent-orchestration)
5. [Autonomous Pipeline (Self-Improving)](#5-autonomous-pipeline-self-improving)
6. [Library Builder System](#6-library-builder-system)
7. [Chat Interface Flow](#7-chat-interface-flow)
8. [LLM Provider Abstraction](#8-llm-provider-abstraction)
9. [Data Flow & Entity Relationships](#9-data-flow--entity-relationships)
10. [File Structure Reference](#10-file-structure-reference)

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        QUANTCODER CLI v2.0 (GAMMA BRANCH)                            │
│                     AI-Powered QuantConnect Algorithm Generator                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────┐
                                    │   USER   │
                                    └────┬─────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         │                               │                               │
         ▼                               ▼                               ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│  Interactive    │           │  Programmatic   │           │    Direct       │
│  Chat Mode      │           │  Mode (--prompt)│           │    Commands     │
│                 │           │                 │           │  (search, etc.) │
└────────┬────────┘           └────────┬────────┘           └────────┬────────┘
         │                             │                             │
         └─────────────────────────────┼─────────────────────────────┘
                                       │
                                       ▼
                            ┌────────────────────┐
                            │      cli.py        │
                            │   (Click Group)    │
                            │   Entry Point      │
                            └─────────┬──────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   TOOL SYSTEM   │    │  MULTI-AGENT    │    │  ADVANCED MODES │
    │   (tools/*.py)  │    │   SYSTEM        │    │                 │
    │                 │    │  (agents/*.py)  │    │  ┌───────────┐  │
    │ • SearchArticles│    │                 │    │  │Autonomous │  │
    │ • Download      │    │ • Coordinator   │    │  │Pipeline   │  │
    │ • Summarize     │    │ • Universe      │    │  └───────────┘  │
    │ • GenerateCode  │    │ • Alpha         │    │  ┌───────────┐  │
    │ • Validate      │    │ • Risk          │    │  │Library    │  │
    │ • ReadFile      │    │ • Strategy      │    │  │Builder    │  │
    │ • WriteFile     │    │                 │    │  └───────────┘  │
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │   LLM PROVIDERS    │
                         │   (llm/*.py)       │
                         │                    │
                         │ • OpenAI (GPT-4)   │
                         │ • Anthropic        │
                         │ • Mistral          │
                         │ • DeepSeek         │
                         └─────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
           ┌────────────┐  ┌────────────┐  ┌────────────┐
           │ CrossRef   │  │ Unpaywall  │  │QuantConnect│
           │ API        │  │ API        │  │ MCP        │
           │ (Search)   │  │ (PDF)      │  │ (Validate) │
           └────────────┘  └────────────┘  └────────────┘
```

### Component Summary

| Layer | Components | Source Files |
|-------|------------|--------------|
| Entry | CLI, Chat | `cli.py:40-510`, `chat.py:27-334` |
| Tools | Search, Download, Summarize, Generate, Validate | `tools/*.py` |
| Agents | Coordinator, Universe, Alpha, Risk, Strategy | `agents/*.py` |
| Advanced | Autonomous Pipeline, Library Builder | `autonomous/*.py`, `library/*.py` |
| LLM | Multi-provider abstraction | `llm/providers.py` |
| Core | PDF Processing, Article Processor | `core/processor.py`, `core/llm.py` |

---

## 2. Entry Points & Execution Modes

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                            │
│                           quantcoder/cli.py                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────────┐
                            │  $ quantcoder       │
                            │  or $ qc            │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │    main()           │
                            │    cli.py:45        │
                            │                     │
                            │ 1. setup_logging()  │
                            │ 2. Config.load()    │
                            │ 3. load_api_key()   │
                            └──────────┬──────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
   ┌────────▼────────┐      ┌──────────▼──────────┐    ┌──────────▼──────────┐
   │ --prompt flag?  │      │ Subcommand given?   │    │ No args (default)   │
   │                 │      │                     │    │                     │
   │ ProgrammaticChat│      │ Execute subcommand  │    │ InteractiveChat     │
   │ cli.py:81-86    │      │                     │    │ cli.py:88-90        │
   └─────────────────┘      └──────────┬──────────┘    └─────────────────────┘
                                       │
    ┌──────────────────────────────────┼──────────────────────────────────┐
    │                                  │                                  │
    ▼                                  ▼                                  ▼
┌──────────────┐              ┌──────────────┐              ┌──────────────────┐
│   STANDARD   │              │  AUTONOMOUS  │              │    LIBRARY       │
│   COMMANDS   │              │    MODE      │              │    BUILDER       │
│              │              │              │              │                  │
│ • search     │              │ • auto start │              │ • library build  │
│ • download   │              │ • auto status│              │ • library status │
│ • summarize  │              │ • auto report│              │ • library resume │
│ • generate   │              │   cli.py:    │              │ • library export │
│ • config     │              │   276-389    │              │   cli.py:392-506 │
│   cli.py:    │              │              │              │                  │
│   109-270    │              │              │              │                  │
└──────────────┘              └──────────────┘              └──────────────────┘
```

### CLI Commands Reference

| Command | Function | Source | Description |
|---------|----------|--------|-------------|
| `quantcoder` | `main()` | `cli.py:45` | Launch interactive mode |
| `quantcoder --prompt "..."` | `ProgrammaticChat` | `cli.py:81` | Non-interactive query |
| `quantcoder search <query>` | `search()` | `cli.py:113` | Search CrossRef API |
| `quantcoder download <id>` | `download()` | `cli.py:141` | Download article PDF |
| `quantcoder summarize <id>` | `summarize()` | `cli.py:162` | Generate AI summary |
| `quantcoder generate <id>` | `generate_code()` | `cli.py:189` | Generate QC algorithm |
| `quantcoder auto start` | `auto_start()` | `cli.py:293` | Autonomous generation |
| `quantcoder library build` | `library_build()` | `cli.py:414` | Build strategy library |

---

## 3. Tool System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         TOOL SYSTEM (Mistral Vibe Pattern)                           │
│                                tools/base.py                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                ┌───────────────┐
                                │  Tool (ABC)   │
                                │  base.py:27   │
                                │               │
                                │ + name        │
                                │ + description │
                                │ + execute()   │
                                │ + is_enabled()│
                                └───────┬───────┘
                                        │
                                        │ inherits
        ┌───────────────┬───────────────┼───────────────┬───────────────┐
        │               │               │               │               │
        ▼               ▼               ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│SearchArticles │ │DownloadArticle│ │SummarizeArticle│ │ GenerateCode │ │ ValidateCode  │
│   Tool        │ │    Tool       │ │     Tool      │ │    Tool      │ │    Tool       │
│               │ │               │ │               │ │              │ │               │
│article_tools  │ │article_tools  │ │article_tools  │ │ code_tools   │ │  code_tools   │
│   .py         │ │   .py         │ │   .py         │ │    .py       │ │     .py       │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬──────┘ └───────┬───────┘
        │                 │                 │                 │                 │
        ▼                 ▼                 ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  CrossRef     │ │  Unpaywall    │ │ OpenAI API    │ │ OpenAI API    │ │  AST Parser   │
│    API        │ │    API        │ │ (Summarize)   │ │ (Generate)    │ │  (Validate)   │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘


                            TOOL EXECUTION FLOW

         ┌──────────────────┐
         │   User Command   │
         │  "search query"  │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  Tool Selection  │
         │  chat.py:129     │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  tool.execute()  │
         │   **kwargs       │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   ToolResult     │
         │   base.py:11     │
         │                  │
         │ • success: bool  │
         │ • data: Any      │
         │ • error: str     │
         │ • message: str   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  Display Result  │
         │  (Rich Console)  │
         └──────────────────┘
```

### Tool Result Flow Example

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      GENERATE CODE TOOL FLOW                                         │
│                     tools/code_tools.py                                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

         ┌─────────────────┐
         │ execute(        │
         │   article_id=1, │
         │   max_attempts=6│
         │ )               │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ Load article PDF    │
         │ from downloads/     │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ ArticleProcessor    │
         │ .extract_structure()│
         │ core/processor.py   │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ LLMHandler          │
         │ .generate_summary() │
         │ core/llm.py         │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ LLMHandler          │
         │ .generate_qc_code() │
         └────────┬────────────┘
                  │
                  ▼
    ┌─────────────────────────────────┐
    │     VALIDATION & REFINEMENT     │
    │            LOOP                 │
    │                                 │
    │  ┌────────────────────────┐     │
    │  │ CodeValidator          │     │
    │  │ .validate_code()       │     │
    │  │  (AST parse check)     │     │
    │  └───────────┬────────────┘     │
    │              │                  │
    │         ◇────┴────◇             │
    │      Valid?    Invalid?         │
    │         │          │            │
    │         ▼          ▼            │
    │    ┌────────┐  ┌───────────┐    │
    │    │ Return │  │ Refine    │    │
    │    │ Code   │  │ with LLM  │    │
    │    └────────┘  │ (max 6x)  │    │
    │                └─────┬─────┘    │
    │                      │          │
    │                      ▼          │
    │              Loop back to       │
    │              validation         │
    └─────────────────────────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │   ToolResult(       │
         │     success=True,   │
         │     data={          │
         │       'summary':...,│
         │       'code':...    │
         │     }               │
         │   )                 │
         └─────────────────────┘
```

---

## 4. Multi-Agent Orchestration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AGENT SYSTEM                                           │
│                      agents/coordinator_agent.py                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────────────┐
                          │   User Request           │
                          │   "Create momentum       │
                          │    strategy with RSI"    │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │   CoordinatorAgent       │
                          │   coordinator_agent.py:14│
                          │                          │
                          │   Responsibilities:      │
                          │   • Analyze request      │
                          │   • Create execution plan│
                          │   • Spawn agents         │
                          │   • Integrate results    │
                          │   • Validate via MCP     │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │ Step 1: Create Plan      │
                          │ _create_execution_plan() │
                          │   coordinator_agent.py:83│
                          │                          │
                          │ Uses LLM to determine:   │
                          │ • Required components    │
                          │ • Execution order        │
                          │ • Key parameters         │
                          │ • Parallel vs Sequential │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │ Execution Plan (JSON):   │
                          │ {                        │
                          │  "components": {         │
                          │    "universe": "...",    │
                          │    "alpha": "...",       │
                          │    "risk": "..."         │
                          │  },                      │
                          │  "execution_strategy":   │
                          │    "parallel"            │
                          │ }                        │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │ Step 2: Execute Plan     │
                          │ _execute_plan()          │
                          │  coordinator_agent.py:153│
                          └────────────┬─────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        │      PARALLEL EXECUTION      │      SEQUENTIAL EXECUTION    │
        │      (strategy="parallel")   │      (strategy="sequential") │
        │                              │                              │
        ▼                              │                              ▼
┌───────────────────────────────────┐  │  ┌───────────────────────────────────┐
│      ParallelExecutor             │  │  │         Sequential Execution       │
│      execution/parallel_executor  │  │  │                                   │
│                                   │  │  │  Universe ──▶ Alpha ──▶ Risk      │
│  ┌─────────────┐ ┌─────────────┐  │  │  │     │          │         │        │
│  │ Universe    │ │   Alpha     │  │  │  │     ▼          ▼         ▼        │
│  │  Agent      │ │   Agent     │  │  │  │ Universe.py  Alpha.py  Risk.py   │
│  │             │ │             │  │  │  │                                   │
│  │ (Parallel)  │ │ (Parallel)  │  │  │  └───────────────────────────────────┘
│  └──────┬──────┘ └──────┬──────┘  │  │
│         │               │         │  │
│         └───────┬───────┘         │  │
│                 │                 │  │
│                 ▼                 │  │
│        ┌───────────────┐          │  │
│        │  Risk Agent   │          │  │
│        │  (Sequential) │          │  │
│        └───────┬───────┘          │  │
│                │                  │  │
└────────────────┼──────────────────┘  │
                 │                     │
                 ▼                     │
        ┌───────────────────────────────────┐
        │       Strategy Agent              │
        │       strategy_agent.py           │
        │                                   │
        │  Integrates all components into   │
        │  Main.py                          │
        │                                   │
        │  • Imports Universe, Alpha, Risk  │
        │  • Initialize() method            │
        │  • OnData() method                │
        │  • Wiring of components           │
        └───────────────┬───────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │      Generated Files              │
        │                                   │
        │  ┌──────────┐  ┌──────────┐       │
        │  │ Main.py  │  │ Alpha.py │       │
        │  └──────────┘  └──────────┘       │
        │  ┌──────────┐  ┌──────────┐       │
        │  │Universe.py│ │ Risk.py  │       │
        │  └──────────┘  └──────────┘       │
        └───────────────┬───────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │ Step 3: Validate via MCP          │
        │ _validate_and_refine()            │
        │   coordinator_agent.py:257        │
        │                                   │
        │ • Send to QuantConnect MCP        │
        │ • Check compilation               │
        │ • If errors: use LLM to fix       │
        │ • Retry up to 3 times             │
        └───────────────────────────────────┘
```

### Agent Class Hierarchy

```
                              ┌──────────────────┐
                              │   BaseAgent      │
                              │   base.py:28     │
                              │                  │
                              │ + llm: Provider  │
                              │ + config         │
                              │ + agent_name     │
                              │ + agent_descr    │
                              │ + execute()      │
                              │ + _generate_llm()│
                              │ + _extract_code()│
                              └────────┬─────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ CoordinatorAgent│         │  UniverseAgent  │         │   AlphaAgent    │
│                 │         │                 │         │                 │
│ Orchestrates    │         │ Generates       │         │ Generates       │
│ multi-agent     │         │ Universe.py     │         │ Alpha.py        │
│ workflow        │         │                 │         │                 │
│                 │         │ Stock selection │         │ Trading signals │
│                 │         │ & filtering     │         │ Entry/exit logic│
└─────────────────┘         └─────────────────┘         └─────────────────┘
         │
         ├─────────────────────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐         ┌─────────────────┐
│   RiskAgent     │         │ StrategyAgent   │
│                 │         │                 │
│ Generates       │         │ Generates       │
│ Risk.py         │         │ Main.py         │
│                 │         │                 │
│ Position sizing │         │ Integrates all  │
│ Stop-loss logic │         │ components      │
└─────────────────┘         └─────────────────┘
```

---

## 5. Autonomous Pipeline (Self-Improving)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS SELF-IMPROVING PIPELINE                                │
│                       autonomous/pipeline.py                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

$ quantcoder auto start --query "momentum trading" --max-iterations 50

                           ┌──────────────────────┐
                           │  AutonomousPipeline  │
                           │    pipeline.py:54    │
                           │                      │
                           │ • LearningDatabase   │
                           │ • ErrorLearner       │
                           │ • PerformanceLearner │
                           │ • PromptRefiner      │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   run() Main Loop    │
                           │    pipeline.py:82    │
                           │                      │
                           │ while iteration <    │
                           │   max_iterations:    │
                           └──────────┬───────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         SINGLE ITERATION (_run_iteration)                            │
│                              pipeline.py:143-258                                     │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  STEP 1: FETCH PAPERS                                                         │  │
│  │  ┌─────────────────┐                                                          │  │
│  │  │ _fetch_papers() │───▶ CrossRef/arXiv API ───▶ List of Papers               │  │
│  │  │  pipeline.py:260│                                                          │  │
│  │  └─────────────────┘                                                          │  │
│  │           │                                                                    │  │
│  │           ▼                                                                    │  │
│  │  STEP 2: APPLY LEARNED PATTERNS                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐                  │  │
│  │  │ PromptRefiner.get_enhanced_prompts_for_agents()         │                  │  │
│  │  │                                                         │                  │  │
│  │  │ • Retrieves successful patterns from database           │                  │  │
│  │  │ • Enhances prompts with learned fixes                   │                  │  │
│  │  │ • Applies error avoidance patterns                      │                  │  │
│  │  └─────────────────────────────────────────────────────────┘                  │  │
│  │           │                                                                    │  │
│  │           ▼                                                                    │  │
│  │  STEP 3: GENERATE STRATEGY                                                    │  │
│  │  ┌─────────────────┐                                                          │  │
│  │  │_generate_strategy│───▶ Multi-Agent System ───▶ Strategy Code              │  │
│  │  │ pipeline.py:269 │                                                          │  │
│  │  └─────────────────┘                                                          │  │
│  │           │                                                                    │  │
│  │           ▼                                                                    │  │
│  │  STEP 4: VALIDATE & LEARN FROM ERRORS                                         │  │
│  │  ┌─────────────────────────────────────────────────────────┐                  │  │
│  │  │ _validate_and_learn()              pipeline.py:282      │                  │  │
│  │  │                                                         │                  │  │
│  │  │  ┌─────────────◇─────────────┐                          │                  │
│  │  │  │    Validation Passed?     │                          │                  │  │
│  │  │  └───────┬───────────┬───────┘                          │                  │
│  │  │     Yes  │           │  No                              │                  │
│  │  │          │           ▼                                  │                  │
│  │  │          │  ┌─────────────────────────┐                 │                  │
│  │  │          │  │ SELF-HEALING            │                 │                  │
│  │  │          │  │ _apply_learned_fixes()  │                 │                  │
│  │  │          │  │  pipeline.py:302        │                 │                  │
│  │  │          │  │                         │                 │                  │
│  │  │          │  │ • ErrorLearner.analyze  │                 │                  │
│  │  │          │  │ • Apply suggested_fix   │                 │                  │
│  │  │          │  │ • Re-validate           │                 │                  │
│  │  │          │  └────────────┬────────────┘                 │                  │
│  │  │          │               │                              │                  │
│  │  │          └───────────────┤                              │                  │
│  │  └──────────────────────────┼──────────────────────────────┘                  │
│  │           │                 │                                                  │
│  │           ▼                 ▼                                                  │
│  │  STEP 5: BACKTEST                                                             │
│  │  ┌─────────────────┐                                                          │  │
│  │  │   _backtest()   │───▶ QuantConnect MCP ───▶ {sharpe, drawdown, return}    │  │
│  │  │ pipeline.py:322 │                                                          │  │
│  │  └─────────────────┘                                                          │  │
│  │           │                                                                    │  │
│  │           ▼                                                                    │  │
│  │  STEP 6: LEARN FROM PERFORMANCE                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐                  │  │
│  │  │                                                         │                  │  │
│  │  │  ┌─────────────◇─────────────┐                          │                  │  │
│  │  │  │ Sharpe >= min_sharpe?     │                          │                  │  │
│  │  │  └───────┬───────────┬───────┘                          │                  │  │
│  │  │     Yes  │           │  No                              │                  │  │
│  │  │          ▼           ▼                                  │                  │
│  │  │  ┌───────────────┐ ┌───────────────────────┐            │                  │
│  │  │  │ SUCCESS!      │ │ PerformanceLearner    │            │                  │
│  │  │  │               │ │ .analyze_poor_perf()  │            │                  │
│  │  │  │ identify_     │ │                       │            │                  │
│  │  │  │ success_      │ │ • Identify issues     │            │                  │
│  │  │  │ patterns()    │ │ • Store for learning  │            │                  │
│  │  │  └───────────────┘ └───────────────────────┘            │                  │
│  │  │                                                         │                  │  │
│  │  └─────────────────────────────────────────────────────────┘                  │  │
│  │           │                                                                    │  │
│  │           ▼                                                                    │  │
│  │  STEP 7: STORE STRATEGY                                                       │  │
│  │  ┌─────────────────┐                                                          │  │
│  │  │ _store_strategy │───▶ LearningDatabase + Filesystem                        │  │
│  │  │ pipeline.py:337 │                                                          │  │
│  │  └─────────────────┘                                                          │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                               │
│                                      ▼                                               │
│                           ┌──────────────────────┐                                   │
│                           │  _should_continue()  │                                   │
│                           │   pipeline.py:368    │                                   │
│                           │                      │                                   │
│                           │ • Check max_iters    │                                   │
│                           │ • User prompt (10x)  │                                   │
│                           │ • Check paused flag  │                                   │
│                           └──────────┬───────────┘                                   │
│                                      │                                               │
└──────────────────────────────────────┼───────────────────────────────────────────────┘
                                       │
                                       ▼
                           ┌──────────────────────┐
                           │ _generate_final_     │
                           │   report()           │
                           │  pipeline.py:399     │
                           │                      │
                           │ • Session stats      │
                           │ • Common errors      │
                           │ • Key learnings      │
                           │ • Library summary    │
                           └──────────────────────┘
```

### Learning System Components

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         LEARNING SUBSYSTEM                                           │
│                        autonomous/database.py                                        │
│                        autonomous/learner.py                                         │
│                        autonomous/prompt_refiner.py                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                     LearningDatabase (SQLite)                        │
│                        database.py                                   │
│                                                                      │
│  Tables:                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐ │
│  │ generated_strategies│ │   error_patterns  │  │ success_patterns │ │
│  │                   │  │                   │  │                   │ │
│  │ • name            │  │ • error_type      │  │ • pattern         │ │
│  │ • category        │  │ • count           │  │ • strategy_type   │ │
│  │ • sharpe_ratio    │  │ • fixed_count     │  │ • avg_sharpe      │ │
│  │ • max_drawdown    │  │ • suggested_fix   │  │ • usage_count     │ │
│  │ • code_files      │  │ • success_rate    │  │                   │ │
│  │ • paper_source    │  │                   │  │                   │ │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
         │                          │                          │
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  ErrorLearner   │       │ PerformanceLearner│     │  PromptRefiner  │
│   learner.py    │       │    learner.py    │       │ prompt_refiner  │
│                 │       │                  │       │      .py        │
│ • analyze_error │       │ • analyze_poor_  │       │                 │
│ • get_common_   │       │   performance    │       │ • get_enhanced_ │
│   errors        │       │ • identify_      │       │   prompts_for_  │
│ • record_fix    │       │   success_       │       │   agents        │
│                 │       │   patterns       │       │                 │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## 6. Library Builder System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         LIBRARY BUILDER SYSTEM                                       │
│                            library/builder.py                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

$ quantcoder library build --comprehensive --max-hours 24

                          ┌──────────────────────┐
                          │   LibraryBuilder     │
                          │    builder.py:31     │
                          │                      │
                          │ • CoverageTracker    │
                          │ • checkpoint_file    │
                          │ • STRATEGY_TAXONOMY  │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ _display_build_plan()│
                          │                      │
                          │ Shows:               │
                          │ • Categories to build│
                          │ • Target strategies  │
                          │ • Estimated time     │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ Check for checkpoint │
                          │ Resume if exists?    │
                          └──────────┬───────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         CATEGORY BUILD LOOP                                          │
│                          builder.py:103-146                                          │
│                                                                                      │
│   for priority in ["high", "medium", "low"]:                                         │
│       for category_name, category_config in priority_cats.items():                   │
│                                                                                      │
│   ┌───────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                               │  │
│   │   STRATEGY_TAXONOMY (library/taxonomy.py):                                    │  │
│   │                                                                               │  │
│   │   ┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐   │  │
│   │   │    MOMENTUM     │  MEAN REVERSION │    FACTOR       │   VOLATILITY    │   │  │
│   │   │  (high priority)│ (high priority) │ (high priority) │ (medium)        │   │  │
│   │   │                 │                 │                 │                 │   │  │
│   │   │ min_strategies: │ min_strategies: │ min_strategies: │ min_strategies: │   │  │
│   │   │      20         │      15         │      15         │      10         │   │  │
│   │   │                 │                 │                 │                 │   │  │
│   │   │ queries:        │ queries:        │ queries:        │ queries:        │   │  │
│   │   │ - momentum      │ - mean reversion│ - value factor  │ - volatility    │   │  │
│   │   │ - trend follow  │ - pairs trading │ - momentum      │ - VIX trading   │   │  │
│   │   │ - crossover     │ - stat arb      │ - quality       │ - options       │   │  │
│   │   └─────────────────┴─────────────────┴─────────────────┴─────────────────┘   │  │
│   │                                                                               │  │
│   │   ┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐   │  │
│   │   │   ML-BASED      │  EVENT-DRIVEN   │    SENTIMENT    │   OPTIONS       │   │  │
│   │   │ (medium)        │ (medium)        │ (low priority)  │ (low priority)  │   │  │
│   │   │                 │                 │                 │                 │   │  │
│   │   │ min_strategies: │ min_strategies: │ min_strategies: │ min_strategies: │   │  │
│   │   │      10         │      10         │       5         │       5         │   │  │
│   │   └─────────────────┴─────────────────┴─────────────────┴─────────────────┘   │  │
│   │                                                                               │  │
│   └───────────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                               │
│                                      ▼                                               │
│   ┌───────────────────────────────────────────────────────────────────────────────┐  │
│   │ _build_category()                  builder.py:154-217                         │  │
│   │                                                                               │  │
│   │  for query in category_config.queries:                                        │  │
│   │      for i in range(attempts_per_query):                                      │  │
│   │                                                                               │  │
│   │          ┌──────────────────────────────────────────────┐                     │  │
│   │          │ _generate_one_strategy()  builder.py:219    │                     │  │
│   │          │                                              │                     │  │
│   │          │ 1. Fetch papers                              │                     │  │
│   │          │ 2. Get enhanced prompts                      │                     │  │
│   │          │ 3. Generate strategy (Autonomous Pipeline)   │                     │  │
│   │          │ 4. Validate                                  │                     │  │
│   │          │ 5. Backtest                                  │                     │  │
│   │          │ 6. Check Sharpe >= min_sharpe               │                     │  │
│   │          │ 7. Save to library                          │                     │  │
│   │          └──────────────────────────────────────────────┘                     │  │
│   │                                                                               │  │
│   │          ┌──────────────────────────────────────────────┐                     │  │
│   │          │ coverage.update()                            │                     │  │
│   │          │ Save checkpoint after each category          │                     │  │
│   │          └──────────────────────────────────────────────┘                     │  │
│   │                                                                               │  │
│   └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ _generate_library_   │
                          │   report()           │
                          │  builder.py:316      │
                          │                      │
                          │ Generates:           │
                          │ • index.json         │
                          │ • README.md          │
                          │ • Per-category stats │
                          └──────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  OUTPUT STRUCTURE    │
                          │                      │
                          │  strategies_library/ │
                          │  ├── index.json      │
                          │  ├── README.md       │
                          │  ├── momentum/       │
                          │  │   ├── Strategy1/  │
                          │  │   │   ├── Main.py │
                          │  │   │   ├── Alpha.py│
                          │  │   │   └── meta.json│
                          │  │   └── Strategy2/  │
                          │  ├── mean_reversion/ │
                          │  └── factor_based/   │
                          └──────────────────────┘
```

---

## 7. Chat Interface Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CHAT INTERFACE                                             │
│                             chat.py                                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

                     ┌──────────────────────────────────┐
                     │                                  │
                     │    InteractiveChat (REPL)        │
                     │         chat.py:27               │
                     │                                  │
                     │  ┌────────────────────────────┐  │
                     │  │  prompt_toolkit Features:  │  │
                     │  │  • FileHistory             │  │
                     │  │  • AutoSuggestFromHistory  │  │
                     │  │  • WordCompleter           │  │
                     │  └────────────────────────────┘  │
                     │                                  │
                     └──────────────┬───────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────────┐
                     │         run() Loop               │
                     │          chat.py:55              │
                     │                                  │
                     │   while True:                    │
                     │     user_input = prompt()        │
                     └──────────────┬───────────────────┘
                                    │
                                    ▼
                     ┌────────────────◇────────────────┐
                     │      Input Type Detection       │
                     │        chat.py:69-95            │
                     └───────────────┬─────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Special Command │       │  Tool Command   │       │ Natural Language│
│                 │       │                 │       │                 │
│ exit, quit      │       │ search <query>  │       │ "Find articles  │
│ help            │       │ download <id>   │       │  about trading" │
│ clear           │       │ summarize <id>  │       │                 │
│ config          │       │ generate <id>   │       │                 │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Handle         │       │  execute_tool() │       │ process_natural │
│  directly       │       │   chat.py:129   │       │ _language()     │
│                 │       │                 │       │  chat.py:191    │
│ - Show help     │       │ tool.execute()  │       │                 │
│ - Clear screen  │       │ Display result  │       │ LLMHandler.chat │
│ - Exit loop     │       │                 │       │ Maintain context│
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────────┐
                     │       Rich Console Output        │
                     │                                  │
                     │  ┌────────────────────────────┐  │
                     │  │  Panel (Markdown)          │  │
                     │  │  Syntax (code highlighting)│  │
                     │  │  Status (spinners)         │  │
                     │  │  Table (search results)    │  │
                     │  └────────────────────────────┘  │
                     └──────────────────────────────────┘


                         PROGRAMMATIC CHAT

         ┌──────────────────────────────────┐
         │                                  │
         │    ProgrammaticChat              │
         │         chat.py:290              │
         │                                  │
         │  • auto_approve = True           │
         │  • Single process() call         │
         │  • No interaction needed         │
         │                                  │
         └──────────────┬───────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────┐
         │         process(prompt)          │
         │          chat.py:307             │
         │                                  │
         │  1. Build messages context       │
         │  2. Call LLMHandler.chat()       │
         │  3. Return response string       │
         └──────────────────────────────────┘
```

---

## 8. LLM Provider Abstraction

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       LLM PROVIDER ABSTRACTION                                       │
│                          llm/providers.py                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────────┐
                          │    LLMProvider       │
                          │    (Abstract Base)   │
                          │                      │
                          │ + chat(messages)     │
                          │ + get_model_name()   │
                          └──────────┬───────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ OpenAIProvider│         │AnthropicProvider│       │ MistralProvider│
│               │         │               │         │               │
│ Models:       │         │ Models:       │         │ Models:       │
│ • gpt-4o      │         │ • claude-3    │         │ • mistral-    │
│ • gpt-4       │         │ • claude-3.5  │         │   large       │
│ • gpt-3.5     │         │               │         │ • codestral   │
└───────────────┘         └───────────────┘         └───────────────┘
        │                            │                            │
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │     LLMFactory       │
                          │                      │
                          │ + create(provider,   │
                          │         api_key)     │
                          │                      │
                          │ + get_recommended_   │
                          │   for_task(task)     │
                          │                      │
                          │ Task recommendations:│
                          │ • "coding" → Mistral │
                          │ • "reasoning" →      │
                          │     Anthropic        │
                          │ • "risk" → OpenAI    │
                          │ • "general" → OpenAI │
                          └──────────────────────┘


                         TASK-BASED LLM SELECTION
                    (coordinator_agent.py:164-173)

         ┌──────────────────────────────────────────────────────┐
         │                                                      │
         │  # Different LLMs for different agent tasks          │
         │                                                      │
         │  code_llm = LLMFactory.create(                       │
         │      LLMFactory.get_recommended_for_task("coding"),  │  ──▶ Mistral/Codestral
         │      api_key                                         │
         │  )                                                   │
         │                                                      │
         │  risk_llm = LLMFactory.create(                       │
         │      LLMFactory.get_recommended_for_task("risk"),    │  ──▶ OpenAI GPT-4
         │      api_key                                         │
         │  )                                                   │
         │                                                      │
         └──────────────────────────────────────────────────────┘
```

---

## 9. Data Flow & Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW OVERVIEW                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘


    ┌──────────────────┐
    │    CrossRef      │
    │      API         │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐           ┌──────────────────┐
    │    ARTICLE       │           │    PDF FILE      │
    │                  │──────────▶│                  │
    │ • title          │  download │ downloads/       │
    │ • authors        │           │ article_N.pdf    │
    │ • DOI            │           └────────┬─────────┘
    │ • URL            │                    │
    │ • abstract       │                    │ extract
    └──────────────────┘                    ▼
                              ┌──────────────────────────┐
                              │    EXTRACTED DATA        │
                              │                          │
                              │ {                        │
                              │   'trading_signal': [...],│
                              │   'risk_management': [...]│
                              │ }                        │
                              └────────────┬─────────────┘
                                           │
                                           │ LLM
                                           ▼
                              ┌──────────────────────────┐
                              │       SUMMARY            │
                              │                          │
                              │  Plain text strategy     │
                              │  description             │
                              └────────────┬─────────────┘
                                           │
                                           │ Multi-Agent
                                           ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        GENERATED STRATEGY                                │
    │                                                                         │
    │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
    │  │    Main.py     │  │   Alpha.py     │  │  Universe.py   │            │
    │  │                │  │                │  │                │            │
    │  │ QCAlgorithm    │  │ Alpha signals  │  │ Stock filter   │            │
    │  │ Initialize()   │  │ Entry/exit     │  │ Selection      │            │
    │  │ OnData()       │  │ indicators     │  │ criteria       │            │
    │  └────────────────┘  └────────────────┘  └────────────────┘            │
    │                                                                         │
    │  ┌────────────────┐  ┌────────────────┐                                │
    │  │    Risk.py     │  │  metadata.json │                                │
    │  │                │  │                │                                │
    │  │ Position sizing│  │ • sharpe_ratio │                                │
    │  │ Stop-loss      │  │ • max_drawdown │                                │
    │  │ Risk limits    │  │ • paper_source │                                │
    │  └────────────────┘  └────────────────┘                                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ store
                                           ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                       LEARNING DATABASE (SQLite)                         │
    │                                                                         │
    │  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  │
    │  │generated_strategies│  │   error_patterns   │  │ success_patterns │  │
    │  │                    │  │                    │  │                  │  │
    │  │ • name             │  │ • error_type       │  │ • pattern        │  │
    │  │ • category         │  │ • count            │  │ • strategy_type  │  │
    │  │ • sharpe_ratio     │  │ • fixed_count      │  │ • avg_sharpe     │  │
    │  │ • success          │  │ • suggested_fix    │  │                  │  │
    │  └────────────────────┘  └────────────────────┘  └──────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


                       ENTITY RELATIONSHIPS

    ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
    │ CrossRef │──1:N──│ Article  │──1:1──│   PDF    │──1:1──│ Extracted│
    │   API    │       │          │       │          │       │   Data   │
    └──────────┘       └──────────┘       └──────────┘       └────┬─────┘
                                                                  │
                                                             1:1  │
                                                                  ▼
                                                            ┌──────────┐
                                                            │  Summary │
                                                            └────┬─────┘
                                                                 │
                                                            1:N  │
                                                                 ▼
    ┌──────────┐                                     ┌───────────────────┐
    │   LLM    │◀────────────────────────────────────│Generated Strategy │
    │ Providers│                                     │  (Multi-file)     │
    └──────────┘                                     └─────────┬─────────┘
                                                               │
                                                          1:1  │
                                                               ▼
                                                    ┌────────────────────┐
                                                    │  Learning Database │
                                                    │  (Feedback Loop)   │
                                                    └────────────────────┘
```

---

## 10. File Structure Reference

```
quantcoder-cli/                               # Root directory
├── quantcoder/                                # Main package (6,919 lines)
│   │
│   ├── cli.py                                 # CLI entry point (510 lines)
│   │   ├── main()                             # Line 45 - Click group
│   │   ├── search()                           # Line 113
│   │   ├── download()                         # Line 141
│   │   ├── summarize()                        # Line 162
│   │   ├── generate_code()                    # Line 189
│   │   ├── auto_start()                       # Line 293
│   │   └── library_build()                    # Line 414
│   │
│   ├── chat.py                                # Chat interfaces (334 lines)
│   │   ├── InteractiveChat                    # Line 27
│   │   │   ├── run()                          # Line 55
│   │   │   ├── process_input()                # Line 96
│   │   │   ├── execute_tool()                 # Line 129
│   │   │   └── process_natural_language()     # Line 191
│   │   └── ProgrammaticChat                   # Line 290
│   │
│   ├── config.py                              # Configuration management
│   │   ├── Config                             # Main config class
│   │   ├── ModelConfig                        # LLM settings
│   │   ├── UIConfig                           # Terminal UI
│   │   └── ToolsConfig                        # Tool settings
│   │
│   ├── agents/                                # Multi-agent system
│   │   ├── base.py                            # BaseAgent (118 lines)
│   │   │   ├── AgentResult                    # Line 10
│   │   │   └── BaseAgent                      # Line 28
│   │   ├── coordinator_agent.py               # Orchestrator (338 lines)
│   │   │   ├── CoordinatorAgent               # Line 14
│   │   │   ├── _create_execution_plan()       # Line 83
│   │   │   ├── _execute_plan()                # Line 153
│   │   │   └── _validate_and_refine()         # Line 257
│   │   ├── universe_agent.py                  # Universe.py generation
│   │   ├── alpha_agent.py                     # Alpha.py generation
│   │   ├── risk_agent.py                      # Risk.py generation
│   │   └── strategy_agent.py                  # Main.py integration
│   │
│   ├── autonomous/                            # Self-improving pipeline
│   │   ├── pipeline.py                        # AutonomousPipeline (486 lines)
│   │   │   ├── AutoStats                      # Line 26
│   │   │   ├── AutonomousPipeline             # Line 54
│   │   │   ├── run()                          # Line 82
│   │   │   ├── _run_iteration()               # Line 143
│   │   │   └── _generate_final_report()       # Line 399
│   │   ├── database.py                        # LearningDatabase (SQLite)
│   │   ├── learner.py                         # ErrorLearner, PerformanceLearner
│   │   └── prompt_refiner.py                  # Dynamic prompt enhancement
│   │
│   ├── library/                               # Library builder
│   │   ├── builder.py                         # LibraryBuilder (493 lines)
│   │   │   ├── LibraryBuilder                 # Line 31
│   │   │   ├── build()                        # Line 55
│   │   │   ├── _build_category()              # Line 154
│   │   │   └── _generate_one_strategy()       # Line 219
│   │   ├── taxonomy.py                        # STRATEGY_TAXONOMY (13+ categories)
│   │   └── coverage.py                        # CoverageTracker, checkpointing
│   │
│   ├── tools/                                 # Tool system
│   │   ├── base.py                            # Tool, ToolResult (73 lines)
│   │   ├── article_tools.py                   # SearchArticles, Download, Summarize
│   │   ├── code_tools.py                      # GenerateCode, ValidateCode
│   │   └── file_tools.py                      # ReadFile, WriteFile
│   │
│   ├── llm/                                   # LLM abstraction
│   │   └── providers.py                       # LLMProvider, LLMFactory
│   │                                          # (OpenAI, Anthropic, Mistral, DeepSeek)
│   │
│   ├── core/                                  # Core processing
│   │   ├── processor.py                       # ArticleProcessor, PDF pipeline
│   │   └── llm.py                             # LLMHandler (OpenAI)
│   │
│   ├── execution/                             # Parallel execution
│   │   └── parallel_executor.py               # ParallelExecutor, AgentTask
│   │
│   ├── mcp/                                   # QuantConnect integration
│   │   └── quantconnect_mcp.py                # MCP client for validation
│   │
│   └── codegen/                               # Multi-file generation
│       └── multi_file.py                      # Main, Alpha, Universe, Risk
│
├── tests/                                     # Test suite
├── docs/                                      # Documentation
├── pyproject.toml                             # Dependencies & config
├── requirements.txt                           # Current dependencies
└── README.md                                  # Project documentation
```

---

## Summary

The **gamma branch** of QuantCoder CLI v2.0 represents a sophisticated multi-agent architecture designed for autonomous, self-improving strategy generation:

### Key Architectural Features

| Feature | Description | Source |
|---------|-------------|--------|
| **Tool System** | Pluggable tools with consistent execute() interface | `tools/base.py` |
| **Multi-Agent** | Coordinator orchestrates Universe, Alpha, Risk, Strategy agents | `agents/*.py` |
| **Parallel Execution** | AsyncIO + ThreadPool for concurrent agent execution | `execution/parallel_executor.py` |
| **Autonomous Pipeline** | Self-improving loop with error learning | `autonomous/pipeline.py` |
| **Library Builder** | Systematic multi-category strategy generation | `library/builder.py` |
| **LLM Abstraction** | Multi-provider support (OpenAI, Anthropic, Mistral) | `llm/providers.py` |
| **Learning System** | SQLite database tracks errors, fixes, success patterns | `autonomous/database.py` |
| **MCP Integration** | QuantConnect validation and backtesting | `mcp/quantconnect_mcp.py` |

### Execution Modes

1. **Interactive** - REPL with command completion and history
2. **Programmatic** - Single-shot queries via `--prompt`
3. **Direct Commands** - Traditional CLI (search, download, generate)
4. **Autonomous** - Self-improving continuous generation
5. **Library Builder** - Comprehensive multi-category strategy library

### Design Patterns Used

- **Factory Pattern** - LLMFactory for provider creation
- **Strategy Pattern** - BaseAgent, Tool abstractions
- **Coordinator Pattern** - CoordinatorAgent orchestration
- **Repository Pattern** - LearningDatabase for persistence
- **Builder Pattern** - LibraryBuilder for complex construction
- **Pipeline Pattern** - AutonomousPipeline for iterative refinement
