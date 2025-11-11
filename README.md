# QuantCoder (CLI Version)

QuantCoder is a command-line tool that allows users to generate QuantConnect trading algorithms from research articles using natural language processing and large language models (LLMs). It was initiated in November 2023 and based on a cognitive architecture inspired by the article ["Dual Agent Chatbots and Expert Systems Design"](https://towardsdev.com/dual-agent-chatbots-and-expert-systems-design-25e2cba434e9)

The initial version successfully coded a blended momentum and mean-reversion strategy as described in ["Outperforming the Market (1000% in 10 years)"](https://medium.com/coinmonks/how-to-outperform-the-market-fe151b944c77?sk=7066045abe12d5cf88c7edc80ec2679c), which received over 10,000 impressions on LinkedIn.

As of November 2025, it is under refactoring with readiness expected in February 2026. 

---

## 🚀 First-Time Installation

> ✅ Requires **Python 3.8 or later**

### 🛠 Setup Instructions

```bash
# Clone the repository and switch to the legacy branch
git clone https://github.com/SL-Mar/QuantCoder.git
cd QuantCoder
git checkout quantcoder-legacy

# Create and activate a virtual environment
python -m venv .venv-legacy

# On Windows:
.\.venv-legacy\Scripts\activate
# On macOS/Linux:
source .venv-legacy/bin/activate

# Install dependencies and the CLI
pip install -e .
python -m spacy download en_core_web_sm
pip install openai==0.28
```

You may also freeze dependencies:

```bash
pip freeze > requirements-legacy.txt
```

---
🧠 LLM Configuration
By default, this project uses the OpenAI gpt-4o-2024-11-20 model for generating trading code from research articles.

## 💡 Usage

To launch the CLI tool in interactive mode:

```bash
python -m quantcli.cli interactive
```

Or if `quantcli` is recognized as a command:

```bash
quantcli interactive
```

---

## ⚠️ OpenAI SDK Compatibility

This legacy version uses the **OpenAI SDK v0.28**. Newer versions (`>=1.0.0`) are **not supported**.

If you encounter this error:

```
You tried to access openai.ChatCompletion, but this is no longer supported...
```

Fix it by running:

```bash
pip install openai==0.28
```

---

## 📁 Articles and Strategies

The folder 'Strategies and publications' contains articles and trading strategies generated using this CLI tool. These strategies may have been manually refined or enhanced using LLM-based methods. Use them at your own discretion — conduct thorough research and validate before live use.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


