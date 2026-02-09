# Changelog

All notable changes to QuantCoder CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-02-09

### Breaking Changes
- **Cloud LLM providers removed** — Anthropic, OpenAI, Mistral (cloud), and DeepSeek providers have been deleted. QuantCoder now runs exclusively on local models via Ollama.
- **No API keys required** — `load_api_key()` and `save_api_key()` are now no-ops. The CLI no longer prompts for API keys on startup.
- **ModelConfig simplified** — Removed `coordinator_provider`, `code_provider` (duplicate), `risk_provider`, `summary_provider`, `summary_model`, `ollama_model` fields. New fields: `code_model`, `reasoning_model`, `ollama_timeout`.
- **LLMFactory API changed** — Now uses task-based routing: `LLMFactory.create(task="coding")` instead of `LLMFactory.create("anthropic", api_key="...")`.
- **Dependencies removed** — `openai`, `anthropic`, `mistralai` packages no longer required.

### Added
- **Ollama-only local inference** — All LLM calls route through Ollama
  - `qwen2.5-coder:32b` for code generation, refinement, error fixing
  - `mistral` for reasoning, summarization, chat
- **Task-based model routing** — `LLMFactory.create(task=...)` automatically selects the right model
- **OllamaProvider enhancements** — `check_health()`, `list_models()`, configurable timeout (default 600s)
- **Backwards-compatible config loading** — Old config files with unknown fields are handled gracefully; `/v1` suffix stripped from `ollama_base_url`

### Changed (from pre-release)
- **Multi-Agent Architecture**: Specialized agents for algorithm generation
- **Autonomous Pipeline**: Self-improving strategy generation with learning database
- **Library Builder**: Batch strategy generation across 13+ categories
- **AlphaEvolve Evolution**: LLM-driven structural variation of algorithms
- **Tool System**: Pluggable architecture (search, download, summarize, generate, validate, backtest)
- **Rich Terminal UI**: Modern CLI with syntax highlighting, panels, progress indicators
- **MCP Integration**: QuantConnect Model Context Protocol for validation and backtesting
- **Configuration System**: TOML-based with dataclasses
- Package renamed from `quantcli` to `quantcoder`

### Removed
- Tkinter GUI (replaced by Rich terminal in pre-release)
- Legacy OpenAI SDK v0.28 support
- All cloud LLM providers (Anthropic, OpenAI, Mistral cloud, DeepSeek)
- Optional dependency groups `[openai]`, `[anthropic]`, `[mistral]`, `[all-llm]`

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
