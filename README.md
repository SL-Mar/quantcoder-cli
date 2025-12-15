# QuantCoder v2.0

> **AI-powered CLI for generating QuantConnect trading algorithms from research articles**

QuantCoder is a command-line tool that allows users to generate QuantConnect trading algorithms from research articles using natural language processing and large language models (LLMs). It was initiated in November 2023 and based on a cognitive architecture inspired by the article ["Dual Agent Chatbots and Expert Systems Design"](https://towardsdev.com/dual-agent-chatbots-and-expert-systems-design-25e2cba434e9)

The initial version successfully coded a blended momentum and mean-reversion strategy as described in ["Outperforming the Market (1000% in 10 years)"](https://medium.com/coinmonks/how-to-outperform-the-market-fe151b944c77?sk=7066045abe12d5cf88c7edc80ec2679c), which received over 10,000 impressions on LinkedIn.

## 🌟 Version 2.0 - Complete Refactoring

**Refactored in December 2025** - Inspired by [Mistral's Vibe CLI](https://github.com/mistralai/mistral-vibe) architecture.

### New Features:
- 🤖 **Interactive Chat Interface** with conversational AI
- 🛠️ **Tool-Based Architecture** for modularity and extensibility
- ⚙️ **Configuration System** with TOML support
- 🎨 **Modern Terminal UI** with Rich library
- 📝 **Programmable Mode** via `--prompt` flag
- 💾 **Persistent Context** and conversation history

👉 **[See full v2.0 documentation →](README_v2.md)** 

---

## 🚀 Installation (v2.0)

> ✅ Requires **Python 3.10 or later**

### Quick Start

```bash
# Clone the repository
git clone https://github.com/SL-Mar/quantcoder-cli.git
cd quantcoder-cli

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Download SpaCy model
python -m spacy download en_core_web_sm
```

### First Run

```bash
# Launch interactive mode
quantcoder

# Or use the short alias
qc
```

On first run, you'll be prompted for your OpenAI API key.

---

## 💡 Usage (v2.0)

### Interactive Mode

```bash
quantcoder> search "momentum trading strategies"
quantcoder> download 1
quantcoder> summarize 1
quantcoder> generate 1
```

### Direct Commands

```bash
quantcoder search "algorithmic trading" --num 5
quantcoder download 1
quantcoder summarize 1
quantcoder generate 1
```

### Programmatic Mode

```bash
quantcoder --prompt "Find articles about mean reversion"
```

---

## 📚 Legacy Version (v0.3)

For the original version with OpenAI SDK v0.28:

```bash
git checkout quantcoder-legacy
```

See legacy documentation for setup instructions.

---

## 📁 Articles and Strategies

The folder 'Strategies and publications' contains articles and trading strategies generated using this CLI tool. These strategies may have been manually refined or enhanced using LLM-based methods. Use them at your own discretion — conduct thorough research and validate before live use.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


