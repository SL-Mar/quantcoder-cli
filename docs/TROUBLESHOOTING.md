# QuantCoder CLI Troubleshooting Guide

This guide covers common issues and their solutions when using QuantCoder CLI.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Issues](#configuration-issues)
3. [API Key Issues](#api-key-issues)
4. [Network Issues](#network-issues)
5. [Code Generation Issues](#code-generation-issues)
6. [Backtest Issues](#backtest-issues)
7. [Evolution Mode Issues](#evolution-mode-issues)
8. [Docker Issues](#docker-issues)
9. [Performance Issues](#performance-issues)

---

## Installation Issues

### Python Version Error

**Error:**
```
ERROR: quantcoder-cli requires Python >=3.10
```

**Solution:**
```bash
# Check your Python version
python --version

# If using pyenv
pyenv install 3.11.0
pyenv local 3.11.0

# Or use python3.11 explicitly
python3.11 -m pip install quantcoder-cli
```

### spaCy Model Not Found

**Error:**
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

### Permission Denied During Install

**Error:**
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Use user install
pip install --user quantcoder-cli

# Or use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install quantcoder-cli
```

---

## Configuration Issues

### Config File Not Found

**Error:**
```
Config file not found at ~/.quantcoder/config.toml
```

**Solution:**
```bash
# Create config directory
mkdir -p ~/.quantcoder

# Run any command to create default config
quantcoder config show
```

### Invalid Config Format

**Error:**
```
toml.decoder.TomlDecodeError: Invalid value
```

**Solution:**
```bash
# Backup and recreate config
mv ~/.quantcoder/config.toml ~/.quantcoder/config.toml.backup
quantcoder config show  # Creates new default config
```

### Config Permission Issues

**Error:**
```
PermissionError: [Errno 13] Permission denied: '~/.quantcoder/config.toml'
```

**Solution:**
```bash
# Fix permissions
chmod 755 ~/.quantcoder
chmod 644 ~/.quantcoder/config.toml
chmod 600 ~/.quantcoder/.env  # Env file should be restricted
```

---

## API Key Issues

### API Key Not Found

**Error:**
```
Error: No API key found for OPENAI_API_KEY
```

**Solutions (in order of preference):**

1. **Use system keyring (most secure):**
   ```bash
   # Store in OS credential manager
   python -c "import keyring; keyring.set_password('quantcoder', 'OPENAI_API_KEY', 'your-key-here')"
   ```

2. **Use environment variable:**
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

3. **Use .env file:**
   ```bash
   echo "OPENAI_API_KEY=your-key-here" >> ~/.quantcoder/.env
   chmod 600 ~/.quantcoder/.env
   ```

### Invalid API Key

**Error:**
```
anthropic.AuthenticationError: Invalid API key
```

**Solution:**
1. Verify key is correct (no extra spaces)
2. Check key hasn't expired
3. Verify key has required permissions
4. Re-generate key from provider dashboard

### Rate Limit Exceeded

**Error:**
```
openai.RateLimitError: Rate limit exceeded
```

**Solution:**
```bash
# Wait and retry (automatic with tenacity)
# Or reduce request frequency in config

# Check your usage limits at:
# OpenAI: https://platform.openai.com/usage
# Anthropic: https://console.anthropic.com/settings/billing
```

---

## Network Issues

### Connection Timeout

**Error:**
```
asyncio.TimeoutError: Connection timed out
aiohttp.ClientError: Cannot connect to host
```

**Solutions:**

1. **Check network connectivity:**
   ```bash
   ping api.crossref.org
   ping www.quantconnect.com
   curl -I https://api.anthropic.com
   ```

2. **Check firewall/proxy:**
   ```bash
   # If behind proxy
   export HTTP_PROXY=http://proxy:port
   export HTTPS_PROXY=http://proxy:port
   ```

3. **Increase timeout:**
   ```bash
   export QC_API_TIMEOUT=120  # Increase from 60s default
   ```

### SSL Certificate Error

**Error:**
```
ssl.SSLCertVerificationError: certificate verify failed
```

**Solution:**
```bash
# Update certificates
pip install --upgrade certifi

# On macOS
/Applications/Python\ 3.x/Install\ Certificates.command
```

### DNS Resolution Failed

**Error:**
```
aiohttp.ClientConnectorError: Cannot connect to host api.crossref.org
```

**Solution:**
```bash
# Check DNS
nslookup api.crossref.org

# Try Google DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

## Code Generation Issues

### Empty Code Generated

**Error:**
```
Error: Generated code is empty
```

**Possible causes and solutions:**

1. **Article has no extractable content:**
   - Try a different article
   - Check if PDF is text-based (not scanned image)

2. **LLM returned empty response:**
   - Check API key and quota
   - Try different LLM provider
   - Increase max_tokens in config

### Syntax Error in Generated Code

**Error:**
```
SyntaxError: invalid syntax
```

**Solution:**
```bash
# Use validation with auto-fix
quantcoder generate 1 --max-refine-attempts 3

# Or validate separately
quantcoder validate generated_code/algorithm.py --local-only
```

### Missing Imports in Generated Code

**Error:**
```
NameError: name 'QCAlgorithm' is not defined
```

**Solution:**
The generated code should include:
```python
from AlgorithmImports import *
```

If missing, add manually or regenerate with updated prompt.

---

## Backtest Issues

### QuantConnect Authentication Failed

**Error:**
```
QuantConnect API error: 401 Unauthorized
```

**Solution:**
```bash
# Verify credentials
curl -u "USER_ID:API_KEY" \
  "https://www.quantconnect.com/api/v2/authenticate"

# Re-enter credentials
quantcoder config set quantconnect_user_id YOUR_ID
quantcoder config set quantconnect_api_key YOUR_KEY
```

### Compilation Failed

**Error:**
```
Compilation failed: Build Error
```

**Common fixes:**

1. **Check for QuantConnect API changes:**
   - Review QuantConnect documentation
   - Update import statements

2. **Check for Python version mismatches:**
   - QuantConnect uses Python 3.8+
   - Avoid Python 3.10+ specific syntax

3. **View detailed errors:**
   ```bash
   quantcoder validate algorithm.py  # Shows detailed errors
   ```

### Backtest Timeout

**Error:**
```
QuantConnectTimeoutError: Backtest did not complete in 600 seconds
```

**Solution:**
1. Simplify algorithm (reduce date range, symbols)
2. Check for infinite loops in algorithm
3. Contact QuantConnect support if persistent

---

## Evolution Mode Issues

### No Variants Generated

**Error:**
```
Error: Failed to generate any variants
```

**Solution:**
1. Check LLM API connectivity
2. Verify baseline code is valid
3. Check evolution config parameters

### Elite Pool Empty

**Warning:**
```
Elite pool empty, falling back to baseline
```

**This is normal** in early generations. The elite pool populates as variants are evaluated and meet fitness thresholds.

### Evolution Stuck

**Symptom:** No improvement after many generations

**Solutions:**
1. Increase mutation rate:
   ```python
   config = EvolutionConfig(
       mutation_rate=0.5,  # Higher mutation
       max_mutation_rate=0.9
   )
   ```
2. Reduce fitness constraints
3. Try different baseline algorithm

---

## Docker Issues

### Container Won't Start

**Error:**
```
docker: Error response from daemon: Conflict
```

**Solution:**
```bash
# Remove existing container
docker rm quantcoder

# Start fresh
docker run -d --name quantcoder quantcoder-cli:latest
```

### Volume Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/home/quantcoder/.quantcoder'
```

**Solution:**
```bash
# Fix host directory permissions
sudo chown -R $(id -u):$(id -g) ~/.quantcoder

# Or run with correct user
docker run --user $(id -u):$(id -g) ...
```

### Out of Memory

**Error:**
```
Container killed due to OOM
```

**Solution:**
```bash
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

### Can't Connect to Ollama

**Error:**
```
Cannot connect to Ollama at localhost:11434
```

**Solution (when running in Docker):**
```bash
# Use host.docker.internal instead of localhost
export OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## Performance Issues

### Slow Article Search

**Symptom:** Search takes > 10 seconds

**Solutions:**
1. Check network latency to CrossRef
2. Reduce `max_results` parameter
3. Use caching if available

### High Memory Usage

**Symptom:** Memory grows over time

**Solutions:**
1. Process fewer articles in batch
2. Restart periodically for long-running processes
3. Increase container memory limit

### CPU Spikes During Evolution

**Symptom:** 100% CPU usage

**This is expected** during:
- Variant generation (LLM calls)
- Parallel evaluation

**Mitigation:**
```bash
# Reduce concurrent evaluations
# In evolution config:
max_concurrent = 2  # Reduce from 3
```

---

## Getting More Help

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json  # For structured logs
quantcoder search "test"
```

### Collect Diagnostic Information

```bash
# System info
python --version
pip show quantcoder-cli

# Configuration
quantcoder config show

# Health check
quantcoder health --json

# Recent logs
tail -100 ~/.quantcoder/quantcoder.log
```

### Report a Bug

Include in your bug report:
1. QuantCoder version: `quantcoder version`
2. Python version: `python --version`
3. OS: `uname -a` or Windows version
4. Full error message and stack trace
5. Steps to reproduce
6. Debug log output

Submit issues at: https://github.com/SL-Mar/quantcoder-cli/issues
