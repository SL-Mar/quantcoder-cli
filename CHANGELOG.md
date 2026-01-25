# Changelog

All notable changes to QuantCoder CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - v2.0 (develop branch)

### Added
- **Multi-Agent Architecture**: Specialized agents for algorithm generation
  - `CoordinatorAgent` - Orchestrates multi-agent workflow
  - `UniverseAgent` - Generates stock selection logic (Universe.py)
  - `AlphaAgent` - Generates trading signals (Alpha.py)
  - `RiskAgent` - Generates risk management (Risk.py)
  - `StrategyAgent` - Integrates components (Main.py)
- **Autonomous Pipeline**: Self-improving strategy generation
  - `AutonomousPipeline` - Continuous generation loop
  - `LearningDatabase` - SQLite storage for patterns
  - `ErrorLearner` - Analyzes and learns from errors
  - `PerformanceLearner` - Tracks successful patterns
  - `PromptRefiner` - Dynamically improves prompts
- **Library Builder**: Batch strategy generation system
  - 13+ strategy categories (momentum, mean reversion, factor, etc.)
  - Checkpointing for resumable builds
  - Coverage tracking and reporting
- **Multi-LLM Support**: Provider abstraction layer
  - OpenAI (GPT-4, GPT-4o)
  - Anthropic (Claude 3, 3.5)
  - Mistral (Mistral Large, Codestral)
  - DeepSeek
- **Tool System**: Pluggable tool architecture (Mistral Vibe pattern)
  - `SearchArticlesTool`, `DownloadArticleTool`
  - `SummarizeArticleTool`, `GenerateCodeTool`
  - `ValidateCodeTool`, `ReadFileTool`, `WriteFileTool`
- **Rich Terminal UI**: Modern CLI experience
  - Interactive REPL with command history
  - Syntax highlighting for generated code
  - Progress indicators and panels
  - Markdown rendering
- **Parallel Execution**: AsyncIO + ThreadPool for concurrent agent execution
- **MCP Integration**: QuantConnect Model Context Protocol for validation
- **Configuration System**: TOML-based configuration with dataclasses

### Changed
- Package renamed from `quantcli` to `quantcoder`
- Complete architectural rewrite
- CLI framework enhanced with multiple execution modes
- Removed Tkinter GUI in favor of Rich terminal interface

### Removed
- Tkinter GUI (replaced by Rich terminal)
- Legacy OpenAI SDK v0.28 support

---

## [1.1.0] - Beta Release

### Added
- **LLM Client Abstraction** (`llm_client.py`)
  - `LLMClient` class with modern OpenAI SDK v1.x+ support
  - `LLMResponse` dataclass for standardized responses
  - Token usage tracking
  - `simple_prompt()` convenience method
- **QuantConnect Static Validator** (`qc_validator.py`)
  - `QuantConnectValidator` class for code analysis
  - Division by zero detection
  - Missing `.IsReady` indicator checks
  - `None` value risk detection in comparisons
  - `max()/min()` on potentially None values
  - Portfolio access pattern validation
  - Severity levels (error, warning, info)
  - Formatted report generation
- **Unit Tests** (`tests/test_llm_client.py`)
  - LLMClient initialization tests
  - Chat completion tests
  - Error handling tests
- **Documentation**
  - `TESTING_GUIDE.md` - Comprehensive testing documentation
  - `MAIN_VS_BETA.md` - Branch comparison guide
  - `.env.example` - Environment variable template

### Changed
- `processor.py`: Refactored to use `LLMClient` instead of direct OpenAI calls
- `processor.py`: Enhanced code generation prompts with defensive programming requirements
  - Added runtime safety check requirements
  - Added `IsReady` check reminders
  - Added None guard requirements
  - Added zero-division protection patterns
- `cli.py`: Added verbose flag handling improvements
- `setup.py`: Updated dependencies for OpenAI v1.x+
- `requirements.txt`: Added explicit dependency versions

### Fixed
- Lazy loading for Tkinter imports (better startup performance)
- Improved error handling in PDF download

### Dependencies
- Upgraded OpenAI SDK from v0.28 to v1.x+
- Added pytest for testing

---

## [1.0.0] - Legacy Release

### Features
- **Article Search**: CrossRef API integration
  - Search by query keywords
  - Configurable result count
  - HTML export of results
- **PDF Download**: Multiple download methods
  - Direct URL download
  - Unpaywall API fallback for open access
  - Manual browser fallback
- **NLP Processing**: spaCy-based text analysis
  - PDF text extraction (pdfplumber)
  - Text preprocessing (URL removal, normalization)
  - Heading detection (title-cased sentences)
  - Section splitting
  - Keyword analysis for trading signals and risk management
- **Code Generation**: OpenAI GPT-4 integration
  - Strategy summarization
  - QuantConnect algorithm generation
  - AST validation
  - Iterative refinement (up to 6 attempts)
- **Tkinter GUI**: Desktop interface
  - Search panel with results table
  - Summary display with copy/save
  - Code display with syntax highlighting (Monokai theme)
- **CLI Commands**
  - `search <query>` - Search articles
  - `list` - Show cached results
  - `download <id>` - Download PDF
  - `summarize <id>` - Generate summary
  - `generate-code <id>` - Generate algorithm
  - `open-article <id>` - Open in browser
  - `interactive` - Launch GUI

### Dependencies
- Python 3.8+
- OpenAI SDK v0.28 (legacy)
- pdfplumber 0.10+
- spaCy 3.x with en_core_web_sm
- Click 8.x
- python-dotenv
- Pygments
- InquirerPy

---

## Branch History

```
main ────●──────────────────────────────●──────────────▶
         │                              │
       v1.0                           v1.1
      (legacy)                    (LLM client +
                                   validator)
                                        ▲
                                        │
beta ───────────────────────────────────┘

develop ──────────────────────────────────────────────▶
   ▲                                              (v2.0)
   │
gamma ─┘
```

---

## Migration Notes

### v1.0 → v1.1

1. Update OpenAI SDK:
   ```bash
   pip uninstall openai
   pip install openai>=1.0.0
   ```

2. Ensure `OPENAI_API_KEY` environment variable is set

3. No CLI command changes required

### v1.1 → v2.0 (future)

1. Package renamed:
   ```bash
   pip uninstall quantcli
   pip install quantcoder
   ```

2. CLI command prefix changes:
   ```bash
   # Old
   quantcli search "query"

   # New
   quantcoder search "query"
   ```

3. New commands available:
   ```bash
   quantcoder auto start --query "..."
   quantcoder library build
   ```

---

## Links

- [Version Guide](VERSIONS.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [GitHub Repository](https://github.com/SL-Mar/quantcoder-cli)
