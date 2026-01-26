# QuantCoder v1.1.0

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/SL-Mar/quantcoder-cli/tree/beta)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-1.0+-green.svg)](https://github.com/openai/openai-python)

> **Note**
> This is the **beta** branch (v1.1.0) - Legacy development version with improved testing.
> For the latest v2.x features, see the `main` or `gamma` branch.
> For the original stable version, see `last-stable-version` branch (v1.0.0).

# QuantCoder (CLI Version)

> **Transform academic trading research into executable QuantConnect algorithms using AI.**

QuantCoder is a command-line tool that converts research papers into production-ready QuantConnect trading algorithms using natural language processing and large language models. Based on a dual-agent cognitive architecture, it extracts trading signals, risk management rules, and generates tested Python code.

## ✨ Key Features
As of November 2025, it is under refactoring with readiness expected in February 2026. 

---

- 📄 **PDF Processing**: Extract trading strategies from academic papers
- 🔍 **CrossRef Integration**: Search and download financial research articles
- 🤖 **AI-Powered Code Generation**: Uses GPT-4o to generate QuantConnect algorithms
- ✅ **Syntax Validation**: Automatic code validation and refinement
- 🎯 **Dual-Agent Architecture**: Separates strategy extraction from code generation
- 📊 **Rich Terminal UI**: Beautiful, interactive command-line interface

## 🚀 Installation

### Requirements
- **Python 3.9 or later**
- OpenAI API key

### Setup

```bash
# Clone the repository
git clone https://github.com/SL-Mar/quantcoder-legacy.git
cd quantcoder-legacy

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install QuantCoder
pip install -e .

# Download required NLP model
python -m spacy download en_core_web_sm

# Set your OpenAI API key
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

## 💡 Usage

### Interactive Mode

Launch the interactive CLI:

```bash
quantcli interactive
```

Or:

```bash
python -m quantcli.cli interactive
```

### Command-Line Interface

**Search for research articles:**

```bash
quantcli search "momentum trading strategies" --num 5
```

**List previously searched articles:**

```bash
quantcli list
```

**Download an article:**

```bash
quantcli download 1
```

**Process a PDF to generate algorithm:**

```bash
quantcli process path/to/research-paper.pdf
```

## 📚 Example Workflow

1. **Search for trading research:**
   ```bash
   quantcli search "mean reversion high frequency" --num 3
   ```

2. **Download an interesting paper:**
   ```bash
   quantcli download 1
   ```

3. **Generate QuantConnect algorithm:**
   ```bash
   quantcli process downloads/paper.pdf
   ```

4. **Review generated code in `generated_code/` directory**

5. **Copy to QuantConnect and backtest**

## 🏗️ Architecture

QuantCoder uses a dual-agent system:

1. **Extraction Agent**: Analyzes PDF, identifies trading signals and risk management rules
2. **Generation Agent**: Converts extracted information into QuantConnect Python code
3. **Validation Layer**: Checks syntax and refines code using AST analysis

## 📊 What's New in v1.0.0

### Major Improvements

✅ **Migrated to OpenAI SDK 1.x+** - Modern API with better error handling
✅ **LLMClient abstraction layer** - Easily swap LLM providers
✅ **Token usage tracking** - Monitor API costs
✅ **Test infrastructure** - pytest with coverage reporting
✅ **Improved logging** - Structured logs for debugging
✅ **Type hints** - Better code quality with mypy support

See [CHANGELOG.md](CHANGELOG.md) for full details.

## 🧪 Testing

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=quantcli --cov-report=html
```

## 📖 Success Stories

- ✅ **10K+ LinkedIn impressions** on first algorithm generated
- ✅ **79 GitHub stars** from quantitative trading community
- ✅ **21 forks** actively used by traders worldwide

Original case study: ["Outperforming the Market (1000% in 10 years)"](https://medium.com/coinmonks/how-to-outperform-the-market-fe151b944c77)

## 🔧 Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-api-key
```

Optional configuration:

```env
# Change default model (default: gpt-4o-2024-11-20)
OPENAI_MODEL=gpt-4-turbo-preview
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by ["Dual Agent Chatbots and Expert Systems Design"](https://towardsdev.com/dual-agent-chatbots-and-expert-systems-design-25e2cba434e9)
- Built for the [QuantConnect](https://www.quantconnect.com/) algorithmic trading platform
- Powered by [OpenAI GPT-4](https://openai.com/)

## 📧 Contact

**Author**: SL-MAR
**Email**: smr.laignel@gmail.com
**GitHub**: [@SL-Mar](https://github.com/SL-Mar)

---

⭐ **If QuantCoder helps your trading research, give it a star!** ⭐
