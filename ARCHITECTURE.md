# QuantCoder CLI - Application Architecture & Flowcharts

This document provides comprehensive flowcharts and diagrams describing how the QuantCoder CLI application works.

---

## Table of Contents

1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Entry Points & CLI Commands](#2-entry-points--cli-commands)
3. [Article Search Flow](#3-article-search-flow)
4. [PDF Download Flow](#4-pdf-download-flow)
5. [Article Processing Pipeline](#5-article-processing-pipeline)
6. [Code Generation & Refinement Flow](#6-code-generation--refinement-flow)
7. [GUI Workflow](#7-gui-workflow)
8. [Data/Entity Relationships](#8-dataentity-relationships)
9. [File Structure Reference](#9-file-structure-reference)

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           QUANTCODER CLI SYSTEM                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │    USER      │
                              └──────┬───────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
     ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
     │   CLI Mode     │    │  Interactive   │    │   GUI Mode     │
     │  (Terminal)    │    │   Commands     │    │  (Tkinter)     │
     └───────┬────────┘    └────────┬───────┘    └───────┬────────┘
             │                      │                    │
             └──────────────────────┼────────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │     cli.py         │
                         │   Entry Point      │
                         │  (Click Group)     │
                         └─────────┬──────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    search.py    │      │  processor.py   │      │     gui.py      │
│  CrossRef API   │      │ PDF Processing  │      │ Tkinter GUI     │
│    Search       │      │ & Code Gen      │      │                 │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  utils.py       │      │  External APIs  │      │   File System   │
│ - Logging       │      │ - OpenAI API    │      │ - articles.json │
│ - API Keys      │      │ - Unpaywall API │      │ - downloads/    │
│ - PDF Download  │      │ - CrossRef API  │      │ - generated_code│
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

### Component Descriptions

| Component | File | Responsibility |
|-----------|------|----------------|
| CLI Entry | `cli.py:21-62` | Click command group, routing, initialization |
| Search | `search.py:11-55` | CrossRef API integration, article discovery |
| Processor | `processor.py:563-642` | PDF processing, NLP analysis, code generation |
| GUI | `gui.py:21-343` | Tkinter-based interactive interface |
| Utilities | `utils.py:9-115` | Logging, API key management, PDF download |

---

## 2. Entry Points & CLI Commands

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINT                                         │
│                           quantcli/cli.py:282                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │   cli() function   │
                         │    cli.py:25       │
                         │                    │
                         │  1. Check --version│
                         │  2. setup_logging()│
                         │  3. load_api_key() │
                         └─────────┬──────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────────┐
        │                    CLI COMMANDS                             │
        └────────────────────────────────────────────────────────────┘
                                   │
    ┌──────────┬──────────┬────────┼────────┬──────────┬──────────┐
    ▼          ▼          ▼        ▼        ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────┐ ┌──────────┐ ┌────────┐ ┌───────────┐
│ search │ │  list  │ │download│ │summ-│ │generate- │ │  open- │ │interactive│
│        │ │        │ │        │ │arize│ │  code    │ │ article│ │           │
│:73-100 │ │:103-121│ │:125-160│ │:164 │ │:202-239  │ │:243-264│ │:267-280   │
│        │ │        │ │        │ │-198 │ │          │ │        │ │           │
└───┬────┘ └───┬────┘ └───┬────┘ └──┬──┘ └────┬─────┘ └───┬────┘ └─────┬─────┘
    │          │          │         │         │           │            │
    ▼          ▼          ▼         ▼         ▼           ▼            ▼
  search    articles   download  Article  Article      Open URL    launch_gui()
  _crossref  .json     _pdf()   Processor Processor   webbrowser  gui.py:337
```

### Command Flow Details

| Command | Function | Source | Description |
|---------|----------|--------|-------------|
| `search <query>` | `search()` | `cli.py:73` | Search CrossRef for articles |
| `list` | `list()` | `cli.py:103` | Display cached articles |
| `download <id>` | `download()` | `cli.py:125` | Download article PDF |
| `summarize <id>` | `summarize()` | `cli.py:164` | Generate AI summary |
| `generate-code <id>` | `generate_code_cmd()` | `cli.py:202` | Generate trading algorithm |
| `open-article <id>` | `open_article()` | `cli.py:243` | Open article in browser |
| `interactive` | `interactive()` | `cli.py:267` | Launch GUI mode |

---

## 3. Article Search Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ARTICLE SEARCH FLOW                                       │
│                     quantcli search "momentum trading"                           │
└─────────────────────────────────────────────────────────────────────────────────┘

         ┌─────────────────┐
         │ User Input:     │
         │ query + --num   │
         │   cli.py:73     │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ search_crossref │
         │  search.py:11   │
         └────────┬────────┘
                  │
                  ▼
    ┌──────────────────────────┐
    │   HTTP GET Request       │
    │ api.crossref.org/works   │
    │     search.py:29         │
    │                          │
    │  params: {               │
    │    query: <query>,       │
    │    rows: <num>           │
    │  }                       │
    └────────────┬─────────────┘
                 │
                 ▼
           ┌──────────◇──────────┐
           │  Response OK?       │
           └───────┬─────┬───────┘
                   │     │
              Yes  │     │  No
                   ▼     ▼
    ┌──────────────────┐ ┌──────────────────┐
    │ Parse JSON       │ │ Return empty []  │
    │ Extract items[]  │ │   search.py:55   │
    │  search.py:32    │ └──────────────────┘
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ For each item, extract:  │
    │  - id (index)            │
    │  - title                 │
    │  - authors               │
    │  - published date        │
    │  - URL                   │
    │  - DOI                   │
    │  - abstract              │
    │    search.py:34-50       │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  Return articles list    │
    │     search.py:52         │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │ Save to articles.json    │
    │     cli.py:89-90         │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │ Display results to user  │
    │     cli.py:91-94         │
    └────────────┬─────────────┘
                 │
                 ▼
           ┌──────────◇──────────┐
           │ Save to HTML?       │
           │    cli.py:97        │
           └───────┬─────┬───────┘
                   │     │
              Yes  │     │  No
                   ▼     ▼
    ┌──────────────────┐ ┌──────────────────┐
    │ save_to_html()   │ │      Done        │
    │ search.py:57-108 │ └──────────────────┘
    │ Opens browser    │
    └──────────────────┘
```

---

## 4. PDF Download Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PDF DOWNLOAD FLOW                                      │
│                         quantcli download <id>                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

         ┌─────────────────┐
         │  User Input:    │
         │  article_id     │
         │   cli.py:125    │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ Load articles.json │
         │    cli.py:138-139  │
         └────────┬───────────┘
                  │
                  ▼
           ┌──────────◇──────────┐
           │ Article exists?     │
           │   cli.py:140-142    │
           └───────┬─────┬───────┘
                   │     │
              Yes  │     │  No
                   │     ▼
                   │  ┌──────────────────┐
                   │  │ "Article not     │
                   │  │  found" error    │
                   │  └──────────────────┘
                   ▼
         ┌─────────────────────┐
         │ Get article details │
         │ URL + DOI           │
         │   cli.py:144-151    │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │   download_pdf()    │
         │    utils.py:70      │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │  HTTP GET article   │
         │  URL directly       │
         │   utils.py:89       │
         └────────┬────────────┘
                  │
                  ▼
           ┌──────────◇──────────┐
           │ Content-Type:       │
           │ application/pdf?    │
           │   utils.py:92       │
           └───────┬─────┬───────┘
                   │     │
              Yes  │     │  No
                   ▼     ▼
    ┌──────────────────┐ ┌──────────────────────────┐
    │ Save PDF to      │ │ Try Unpaywall API        │
    │ downloads/       │ │ get_pdf_url_via_unpaywall│
    │ article_<id>.pdf │ │   utils.py:99-102        │
    │  utils.py:93-96  │ └────────────┬─────────────┘
    └────────┬─────────┘              │
             │                        ▼
             │              ┌──────────◇──────────┐
             │              │ PDF URL found?      │
             │              │   utils.py:103      │
             │              └───────┬─────┬───────┘
             │                 Yes  │     │  No
             │                      ▼     ▼
             │       ┌──────────────────┐ ┌──────────────────┐
             │       │ Download from    │ │ Return False     │
             │       │ Unpaywall URL    │ │ Offer manual     │
             │       │  utils.py:104-109│ │ browser open     │
             │       └────────┬─────────┘ │  cli.py:156-160  │
             │                │           └──────────────────┘
             └────────────────┼───────────────────┐
                              │                   │
                              ▼                   │
                   ┌────────────────────┐         │
                   │ Return True        │◀────────┘
                   │ "PDF downloaded"   │
                   │   cli.py:154       │
                   └────────────────────┘
```

### Unpaywall API Integration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        UNPAYWALL API LOOKUP                                      │
│                       utils.py:40-68                                             │
└─────────────────────────────────────────────────────────────────────────────────┘

         ┌─────────────────┐
         │     DOI         │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────────────────┐
         │  GET api.unpaywall.org/v2 │
         │       /{doi}               │
         │  params: { email }         │
         │     utils.py:53-58         │
         └────────────┬───────────────┘
                      │
                      ▼
               ┌──────────◇──────────┐
               │ is_oa = true AND    │
               │ best_oa_location    │
               │ .url_for_pdf exists?│
               │   utils.py:61       │
               └───────┬─────┬───────┘
                  Yes  │     │  No
                       ▼     ▼
        ┌──────────────────┐ ┌──────────────────┐
        │ Return PDF URL   │ │ Return None      │
        │  utils.py:62     │ │  utils.py:65     │
        └──────────────────┘ └──────────────────┘
```

---

## 5. Article Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ARTICLE PROCESSING PIPELINE                                   │
│                 ArticleProcessor.extract_structure()                             │
│                        processor.py:579-601                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌───────────────┐
│   PDF File    │
│  (Input)      │
└───────┬───────┘
        │
        ▼
┌───────────────────────────────────────┐
│         1. PDFLoader                  │
│         processor.py:38-62            │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ pdfplumber.open(pdf_path)       │  │
│  │ For each page:                  │  │
│  │   text += page.extract_text()   │  │
│  └─────────────────────────────────┘  │
│                                       │
│  Output: raw_text (string)            │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      2. TextPreprocessor              │
│         processor.py:64-94            │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ Remove URLs                     │  │
│  │ Remove "Electronic copy..." text│  │
│  │ Remove standalone numbers       │  │
│  │ Normalize multiple newlines     │  │
│  │ Remove header/footer patterns   │  │
│  └─────────────────────────────────┘  │
│                                       │
│  Output: preprocessed_text            │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      3. HeadingDetector               │
│         processor.py:96-124           │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ spacy.load("en_core_web_sm")    │  │
│  │ For each sentence:              │  │
│  │   If 2-10 words AND title-cased │  │
│  │     → Mark as heading           │  │
│  └─────────────────────────────────┘  │
│                                       │
│  Output: headings[] (list)            │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      4. SectionSplitter               │
│         processor.py:126-150          │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ For each line:                  │  │
│  │   If line in headings:          │  │
│  │     current_section = line      │  │
│  │   Else:                         │  │
│  │     sections[current] += line   │  │
│  └─────────────────────────────────┘  │
│                                       │
│  Output: sections{} (dict)            │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      5. KeywordAnalyzer               │
│         processor.py:152-210          │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ Trading Signal Keywords:        │  │
│  │   buy, sell, signal, trend,     │  │
│  │   sma, momentum, rsi, macd...   │  │
│  │                                 │  │
│  │ Risk Management Keywords:       │  │
│  │   drawdown, volatility, risk,   │  │
│  │   stop-loss, position sizing... │  │
│  │                                 │  │
│  │ Filter out irrelevant patterns  │  │
│  │ Categorize each sentence        │  │
│  └─────────────────────────────────┘  │
│                                       │
│  Output: {                            │
│    'trading_signal': [...],           │
│    'risk_management': [...]           │
│  }                                    │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│         EXTRACTED DATA                │
│                                       │
│  {                                    │
│    'trading_signal': [                │
│       "Buy when RSI < 30...",         │
│       "Use 50-day SMA crossover..."   │
│    ],                                 │
│    'risk_management': [               │
│       "Set stop-loss at 10% ATR...",  │
│       "Limit position to 1% risk..."  │
│    ]                                  │
│  }                                    │
└───────────────────────────────────────┘
```

---

## 6. Code Generation & Refinement Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     CODE GENERATION FLOW                                         │
│               ArticleProcessor.extract_structure_and_generate_code()             │
│                          processor.py:603-642                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌───────────────┐
│ Extracted     │
│ Data (dict)   │
└───────┬───────┘
        │
        ▼
┌───────────────────────────────────────┐
│    1. GENERATE SUMMARY                │
│       OpenAIHandler.generate_summary  │
│          processor.py:219-263         │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     OpenAI API Call                               │
│                                                                   │
│  Model: gpt-4o-2024-11-20                                         │
│  System: "You are an algorithmic trading expert."                 │
│                                                                   │
│  Prompt Template (processor.py:227-244):                          │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ "Provide a clear and concise summary of the following       │  │
│  │  trading strategy and its associated risk management rules. │  │
│  │                                                             │  │
│  │  ### Trading Strategy Overview:                             │  │
│  │  {trading_signals}                                          │  │
│  │                                                             │  │
│  │  ### Risk Management Rules:                                 │  │
│  │  {risk_management}                                          │  │
│  │                                                             │  │
│  │  Summarize the details in a practical format."              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  max_tokens: 1000, temperature: 0.5                               │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
                     ┌────────────────────┐
                     │      SUMMARY       │
                     │   (300 words max)  │
                     └──────────┬─────────┘
                                │
                                ▼
┌───────────────────────────────────────┐
│    2. GENERATE CODE                   │
│       OpenAIHandler.generate_qc_code  │
│          processor.py:265-319         │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     OpenAI API Call                               │
│                                                                   │
│  Model: gpt-4o-2024-11-20                                         │
│  System: "You are a helpful assistant specialized in             │
│           generating QuantConnect algorithms in Python."         │
│                                                                   │
│  Prompt Template (processor.py:273-299):                          │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ "Convert the following trading strategy into a complete,    │  │
│  │  error-free QuantConnect Python algorithm.                  │  │
│  │                                                             │  │
│  │  ### Trading Strategy Summary: {summary}                    │  │
│  │                                                             │  │
│  │  ### Requirements:                                          │  │
│  │  1. Initialize Method - dates, cash, universe, indicators   │  │
│  │  2. OnData Method - buy/sell logic                          │  │
│  │  3. Risk Management - position sizing, stop-loss            │  │
│  │  4. Ensure Compliance - QuantConnect methods only"          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  max_tokens: 1500, temperature: 0.3                               │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
                     ┌────────────────────┐
                     │   GENERATED CODE   │
                     │   (Python)         │
                     └──────────┬─────────┘
                                │
                                ▼
┌───────────────────────────────────────┐
│    3. VALIDATE CODE                   │
│       CodeValidator.validate_code     │
│          processor.py:358-378         │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ ast.parse(code)                 │  │
│  │ Check for SyntaxError           │  │
│  └─────────────────────────────────┘  │
└───────────────┬───────────────────────┘
                │
                ▼
         ┌──────────◇──────────┐
         │   Code Valid?       │
         │ processor.py:622    │
         └───────┬─────┬───────┘
            Yes  │     │  No
                 │     ▼
                 │  ┌──────────────────────────────────────┐
                 │  │     4. REFINE CODE (Loop)            │
                 │  │     CodeRefiner.refine_code          │
                 │  │        processor.py:380-392          │
                 │  │                                      │
                 │  │  ┌────────────────────────────────┐  │
                 │  │  │ attempt = 0                    │  │
                 │  │  │ while !valid && attempt < 6:  │  │
                 │  │  │   code = openai.refine_code() │  │
                 │  │  │   valid = validate(code)      │  │
                 │  │  │   attempt++                   │  │
                 │  │  └────────────────────────────────┘  │
                 │  │                                      │
                 │  │  OpenAI Prompt (processor.py:326-332)│
                 │  │  "The following code may have syntax │
                 │  │   or logical errors. Please fix..."  │
                 │  └──────────────────────────────────────┘
                 │                    │
                 │                    ▼
                 │         ┌──────────◇──────────┐
                 │         │ Max attempts (6)?   │
                 │         │ processor.py:622    │
                 │         └───────┬─────┬───────┘
                 │                 │     │
                 │            No   │     │  Yes
                 │                 │     ▼
                 │                 │  ┌──────────────────┐
                 │                 │  │ "Code could not  │
                 │                 │  │  be generated"   │
                 │                 │  │ processor.py:633 │
                 │                 │  └──────────────────┘
                 ▼                 │
         ┌────────────────────┐    │
         │   VALID CODE       │◀───┘
         │                    │
         │  ┌──────────────┐  │
         │  │ Display in   │  │
         │  │ GUI or save  │  │
         │  │ to file      │  │
         │  └──────────────┘  │
         └────────────────────┘
```

---

## 7. GUI Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            GUI WORKFLOW                                          │
│                       quantcli interactive                                       │
│                          gui.py:337-343                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

         ┌─────────────────┐
         │  launch_gui()   │
         │  gui.py:337     │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────────────┐
         │   QuantCLIGUI.__init__  │
         │      gui.py:22-111      │
         │                         │
         │  Create main window:    │
         │  - Search Frame         │
         │  - Results Treeview     │
         │  - Action Buttons       │
         └────────┬────────────────┘
                  │
                  ▼
         ┌─────────────────────────┐
         │   Tkinter Main Loop     │
         │      gui.py:343         │
         └────────┬────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────┐
    │              GUI ACTIONS                         │
    └─────────────────────────────────────────────────┘
              │           │           │
              ▼           ▼           ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────────┐
    │   Search    │ │ Summarize│ │ Generate     │
    │   Button    │ │  Button  │ │ Code Button  │
    │ gui.py:113  │ │gui.py:164│ │ gui.py:198   │
    └──────┬──────┘ └────┬─────┘ └──────┬───────┘
           │             │              │
           ▼             ▼              ▼
┌────────────────┐ ┌───────────────┐ ┌────────────────┐
│perform_search()│ │summarize_     │ │ generate_code()│
│  gui.py:113    │ │  article()    │ │   gui.py:198   │
│                │ │ gui.py:164    │ │                │
│ 1. Get query   │ │               │ │ 1. Select .txt │
│ 2. Call search_│ │ 1. Select PDF │ │    summary file│
│    crossref()  │ │ 2. ArticlePro-│ │ 2. Read summary│
│ 3. Update      │ │    cessor()   │ │ 3. generate_qc_│
│    Treeview    │ │ 3. extract_   │ │    code()      │
│ 4. Store       │ │    structure()│ │ 4. validate &  │
│    articles[]  │ │ 4. generate_  │ │    refine loop │
└────────────────┘ │    summary()  │ │ 5. display_    │
                   │ 5. Save .txt  │ │    code()      │
                   │ 6. display_   │ └────────────────┘
                   │    summary()  │
                   └───────────────┘
```

### GUI Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Quant Coder v0.3 - SL Mar 2024                           [─][□][×]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│            Quantitative research from articles                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Search Query: [________________] Number of Results: [5] │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│                       [ Search ]                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Double-click an article to open it in your web browser. │    │
│  ├────────┬────────────────────────────────┬───────────────┤    │
│  │ Index  │ Title                          │ Authors       │    │
│  ├────────┼────────────────────────────────┼───────────────┤    │
│  │ 0      │ Momentum Trading Strategies... │ J. Smith      │    │
│  │ 1      │ Mean Reversion in Stock...     │ A. Johnson    │    │
│  │ 2      │ Algorithmic Trading with...    │ M. Williams   │    │
│  └────────┴────────────────────────────────┴───────────────┘    │
│                                                                 │
│  [ Open Article ]  [ Summarize Article ]  [ Generate Code ]     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Data/Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DATA/ENTITY RELATIONSHIPS                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


                    ┌─────────────────────────────────┐
                    │         CrossRef API            │
                    │     (External Service)          │
                    └──────────────┬──────────────────┘
                                   │
                                   │ HTTP Response
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ARTICLE                                             │
│                         (articles.json)                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  {                                                                              │
│    "id": "1",                    ──────▶  Index for user reference              │
│    "title": "...",               ──────▶  Article title                         │
│    "authors": "John Doe, ...",   ──────▶  Comma-separated author names          │
│    "published": 2024,            ──────▶  Publication year                      │
│    "URL": "https://doi.org/...", ──────▶  Link to article page                  │
│    "DOI": "10.1234/...",         ──────▶  Used for Unpaywall lookup             │
│    "abstract": "..."             ──────▶  Article abstract                      │
│  }                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Download
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PDF FILE                                            │
│                       downloads/article_<id>.pdf                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Binary PDF content from publisher or Unpaywall                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Process (PDFLoader, TextPreprocessor,
                                   │          HeadingDetector, SectionSplitter,
                                   │          KeywordAnalyzer)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EXTRACTED DATA                                          │
│                         (In-memory dict)                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  {                                                                              │
│    "trading_signal": [           ──────▶  Sentences about trading signals       │
│      "Buy when RSI crosses...",                                                 │
│      "Use 50-day SMA..."                                                        │
│    ],                                                                           │
│    "risk_management": [          ──────▶  Sentences about risk management       │
│      "Set stop-loss at 10%...",                                                 │
│      "Position size = 1% risk..."                                               │
│    ]                                                                            │
│  }                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ OpenAI API (generate_summary)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SUMMARY                                             │
│                    downloads/article_<id>_summary.txt                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Plain text summary of trading strategy (≤300 words)                            │
│                                                                                 │
│  "The strategy uses a momentum-based approach combining RSI and SMA             │
│   indicators. Entry signals occur when RSI crosses above 30 while price         │
│   is above the 50-day moving average..."                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ OpenAI API (generate_qc_code)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         GENERATED CODE                                           │
│                    generated_code/algorithm_<id>.py                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  from AlgorithmImports import *                                                 │
│                                                                                 │
│  class MomentumStrategy(QCAlgorithm):                                           │
│      def Initialize(self):                                                      │
│          self.SetStartDate(2020, 1, 1)                                          │
│          self.SetEndDate(2024, 1, 1)                                            │
│          self.SetCash(100000)                                                   │
│          self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol           │
│          self.rsi = self.RSI(self.symbol, 14)                                   │
│          self.sma = self.SMA(self.symbol, 50)                                   │
│                                                                                 │
│      def OnData(self, data):                                                    │
│          if not self.rsi.IsReady or not self.sma.IsReady:                       │
│              return                                                             │
│          # Trading logic...                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘


                           RELATIONSHIP DIAGRAM

    ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
    │ CrossRef │──1:N──│ Article  │──1:1──│   PDF    │──1:1──│ Extracted│
    │   API    │       │  (.json) │       │  (.pdf)  │       │   Data   │
    └──────────┘       └──────────┘       └──────────┘       └────┬─────┘
                                                                  │
                                                             1:1  │
                                                                  ▼
    ┌──────────┐                                            ┌──────────┐
    │  OpenAI  │◀─────────────────────────────────────────▶│  Summary │
    │   API    │                                            │  (.txt)  │
    └────┬─────┘                                            └────┬─────┘
         │                                                       │
         │                                                  1:1  │
         │                                                       ▼
         │                                                 ┌──────────┐
         └────────────────────────────────────────────────▶│Generated │
                                                           │Code (.py)│
                                                           └──────────┘
```

---

## 9. File Structure Reference

```
quantcoder-cli/
├── quantcli/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # CLI entry point & commands (283 lines)
│   │   ├── cli()             # Line 25 - Main Click group
│   │   ├── search()          # Line 73 - Search command
│   │   ├── list()            # Line 103 - List command
│   │   ├── download()        # Line 125 - Download command
│   │   ├── summarize()       # Line 164 - Summarize command
│   │   ├── generate_code_cmd()# Line 202 - Generate code command
│   │   ├── open_article()    # Line 243 - Open article command
│   │   └── interactive()     # Line 267 - Launch GUI
│   │
│   ├── processor.py          # PDF processing & code gen (642 lines)
│   │   ├── PDFLoader         # Line 38 - PDF text extraction
│   │   ├── TextPreprocessor  # Line 64 - Text cleaning
│   │   ├── HeadingDetector   # Line 96 - NLP heading detection
│   │   ├── SectionSplitter   # Line 126 - Section splitting
│   │   ├── KeywordAnalyzer   # Line 152 - Trading signal extraction
│   │   ├── OpenAIHandler     # Line 212 - LLM interactions
│   │   ├── CodeValidator     # Line 358 - AST syntax validation
│   │   ├── CodeRefiner       # Line 380 - Code error fixing
│   │   ├── GUI               # Line 394 - Result display window
│   │   └── ArticleProcessor  # Line 563 - Main orchestrator
│   │
│   ├── search.py             # CrossRef API integration (109 lines)
│   │   ├── search_crossref() # Line 11 - API search
│   │   └── save_to_html()    # Line 57 - HTML export
│   │
│   ├── gui.py                # Tkinter GUI (344 lines)
│   │   ├── QuantCLIGUI       # Line 21 - Main GUI class
│   │   │   ├── perform_search()     # Line 113
│   │   │   ├── summarize_article()  # Line 164
│   │   │   ├── generate_code()      # Line 198
│   │   │   └── display_code()       # Line 246
│   │   └── launch_gui()      # Line 337 - GUI launcher
│   │
│   └── utils.py              # Utilities (115 lines)
│       ├── setup_logging()   # Line 9 - Configure logging
│       ├── load_api_key()    # Line 25 - Load OpenAI key
│       ├── get_pdf_url_via_unpaywall()  # Line 40
│       └── download_pdf()    # Line 70 - Download PDF file
│
├── downloads/                # Downloaded PDFs and summaries
│   ├── article_1.pdf
│   └── article_1_summary.txt
│
├── generated_code/           # Generated trading algorithms
│   └── algorithm_1.py
│
├── articles.json             # Cached search results
├── output.html               # HTML search results view
├── quantcli.log              # Application log file
├── setup.py                  # Package configuration
├── requirements-legacy.txt   # Dependencies (OpenAI v0.28)
└── README.md                 # Project documentation
```

---

## Summary

QuantCoder CLI transforms academic research articles into executable QuantConnect trading algorithms through a multi-stage pipeline:

1. **Search**: Query CrossRef API for relevant trading research
2. **Download**: Fetch PDFs via direct links or Unpaywall
3. **Process**: Extract text, detect structure, identify trading signals
4. **Summarize**: Use GPT-4 to create strategy summaries
5. **Generate**: Convert summaries to QuantConnect Python code
6. **Validate**: Check syntax and refine until valid

The application supports both command-line and GUI interfaces, with all operations logged for debugging.
