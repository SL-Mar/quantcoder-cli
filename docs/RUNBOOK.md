# QuantCoder CLI Operational Runbook

This runbook provides operational procedures for running, monitoring, and troubleshooting QuantCoder CLI in production environments.

## Table of Contents

1. [Health Checks](#health-checks)
2. [Monitoring](#monitoring)
3. [Common Issues](#common-issues)
4. [Incident Response](#incident-response)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Escalation](#escalation)

---

## Health Checks

### Quick Health Check

```bash
# Basic health check
quantcoder health

# JSON output for scripting
quantcoder health --json
```

**Expected Output:**
```json
{
  "version": "2.0.0",
  "status": "healthy",
  "checks": {
    "config": {"status": "pass", "message": "Config loaded"},
    "api_keys": {"status": "pass", "message": "Found: OPENAI_API_KEY, ANTHROPIC_API_KEY"},
    "quantconnect": {"status": "pass", "message": "QuantConnect credentials configured"},
    "directories": {"status": "pass", "message": "All directories accessible"},
    "dependencies": {"status": "pass", "message": "All required packages available"}
  }
}
```

### Docker Health Check

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' quantcoder

# View health check logs
docker inspect --format='{{json .State.Health}}' quantcoder | jq
```

### Component Verification

```bash
# Verify API connectivity
quantcoder search "test" --max-results 1

# Verify LLM provider
quantcoder config show | grep provider

# Verify QuantConnect (if configured)
quantcoder validate --local-only "$(cat test_algorithm.py)"
```

---

## Monitoring

### Log Locations

| Log Type | Location | Rotation |
|----------|----------|----------|
| Application Log | `~/.quantcoder/quantcoder.log` | 10MB, 5 backups |
| Docker Logs | `docker logs quantcoder` | Container lifecycle |
| System Logs | `/var/log/syslog` | System default |

### Enable Debug Logging

```bash
# Environment variable
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json

# Or in docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
  - LOG_FORMAT=json
```

### Key Metrics to Monitor

1. **Error Rate**: Count of `logger.error()` messages
2. **API Latency**: Time between request and response
3. **Circuit Breaker State**: Open/Closed/Half-Open
4. **Memory Usage**: Container memory consumption
5. **Disk Usage**: `~/.quantcoder/` directory size

### Log Analysis Commands

```bash
# Recent errors
grep -i error ~/.quantcoder/quantcoder.log | tail -20

# API failures
grep "API request failed" ~/.quantcoder/quantcoder.log

# Circuit breaker events
grep "circuit" ~/.quantcoder/quantcoder.log

# JSON log parsing (if LOG_FORMAT=json)
cat ~/.quantcoder/quantcoder.log | jq 'select(.levelname == "ERROR")'
```

---

## Common Issues

### Issue: API Key Not Found

**Symptoms:**
- `Error: API key not configured`
- `Authentication failed`

**Resolution:**

```bash
# 1. Check if key is set
quantcoder config show | grep api_key

# 2. Set via keyring (recommended)
python -c "import keyring; keyring.set_password('quantcoder', 'OPENAI_API_KEY', 'your-key')"

# 3. Or via environment variable
export OPENAI_API_KEY="your-key"

# 4. Or via .env file
echo "OPENAI_API_KEY=your-key" >> ~/.quantcoder/.env
chmod 600 ~/.quantcoder/.env
```

### Issue: QuantConnect Authentication Failed

**Symptoms:**
- `QuantConnect API error: 401 Unauthorized`
- `Invalid credentials`

**Resolution:**

```bash
# 1. Verify credentials are set
quantcoder config show | grep quantconnect

# 2. Re-enter credentials
quantcoder config set quantconnect_user_id YOUR_USER_ID
quantcoder config set quantconnect_api_key YOUR_API_KEY

# 3. Test connectivity
curl -u "YOUR_USER_ID:YOUR_API_KEY" \
  "https://www.quantconnect.com/api/v2/authenticate"
```

### Issue: Circuit Breaker Open

**Symptoms:**
- `CircuitBreakerError: Circuit breaker is open`
- Rapid failures followed by immediate rejections

**Resolution:**

```bash
# 1. Wait for reset (60 seconds default)
sleep 60

# 2. Check underlying service status
curl -s "https://www.quantconnect.com/api/v2/authenticate" \
  -u "USER:KEY" | jq .success

# 3. If service is up, restart the application
docker restart quantcoder
```

### Issue: Timeout Errors

**Symptoms:**
- `asyncio.TimeoutError`
- `API request timed out`

**Resolution:**

```bash
# 1. Check network connectivity
ping api.crossref.org
ping www.quantconnect.com

# 2. Increase timeout (if network is slow)
# Edit config or set environment variable
export QC_API_TIMEOUT=120

# 3. Check for rate limiting
grep "429" ~/.quantcoder/quantcoder.log
```

### Issue: Memory Exhaustion

**Symptoms:**
- `MemoryError`
- Container OOM killed

**Resolution:**

```bash
# 1. Check container memory
docker stats quantcoder

# 2. Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G  # Increase from 2G

# 3. Reduce concurrent operations
# In evolution mode, reduce variants_per_generation
```

### Issue: Path Security Error

**Symptoms:**
- `PathSecurityError: Path resolves outside allowed directory`

**Resolution:**

```bash
# 1. Verify file paths are within allowed directories
# Allowed: ~/.quantcoder, ./downloads, ./generated_code

# 2. Check for symlinks that escape allowed directories
ls -la ~/downloads

# 3. Use absolute paths within allowed directories
quantcoder download 1 --output ~/downloads/article.pdf
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **P1** | Service unavailable | < 1 hour | All API calls failing, crash on startup |
| **P2** | Major feature broken | < 4 hours | Code generation fails, backtest broken |
| **P3** | Minor issue | < 24 hours | Slow performance, UI glitches |
| **P4** | Enhancement | Next release | Feature requests, minor improvements |

### P1 Incident Procedure

1. **Acknowledge** (within 15 minutes)
   ```bash
   # Check container status
   docker ps -a | grep quantcoder
   docker logs quantcoder --tail 100
   ```

2. **Diagnose** (within 30 minutes)
   ```bash
   # Get health status
   quantcoder health --json

   # Check recent errors
   grep ERROR ~/.quantcoder/quantcoder.log | tail -50

   # Check external services
   curl -s https://api.crossref.org/works?rows=1 | jq .status
   ```

3. **Mitigate** (within 1 hour)
   ```bash
   # Restart container
   docker restart quantcoder

   # Or rollback to previous version
   docker pull quantcoder-cli:previous-version
   docker stop quantcoder
   docker run -d --name quantcoder quantcoder-cli:previous-version
   ```

4. **Resolve & Document**
   - Update incident ticket with root cause
   - Create fix PR if code change needed
   - Update this runbook if new issue type

### Rollback Procedure

```bash
# 1. List available versions
docker images quantcoder-cli --format "{{.Tag}}"

# 2. Stop current container
docker stop quantcoder

# 3. Start previous version
docker run -d \
  --name quantcoder-rollback \
  -v ~/.quantcoder:/home/quantcoder/.quantcoder \
  -v ./downloads:/home/quantcoder/downloads \
  quantcoder-cli:previous-version

# 4. Verify rollback
docker exec quantcoder-rollback quantcoder health
```

---

## Maintenance Procedures

### Updating to New Version

```bash
# 1. Backup configuration
cp -r ~/.quantcoder ~/.quantcoder.backup

# 2. Pull new image
docker pull quantcoder-cli:latest

# 3. Stop old container
docker stop quantcoder

# 4. Start new container
docker run -d \
  --name quantcoder-new \
  -v ~/.quantcoder:/home/quantcoder/.quantcoder \
  quantcoder-cli:latest

# 5. Verify health
docker exec quantcoder-new quantcoder health

# 6. Remove old container (after verification)
docker rm quantcoder
docker rename quantcoder-new quantcoder
```

### Log Rotation

Logs rotate automatically (10MB, 5 backups). To force rotation:

```bash
# Manual rotation
mv ~/.quantcoder/quantcoder.log ~/.quantcoder/quantcoder.log.1
touch ~/.quantcoder/quantcoder.log
```

### Database Maintenance

```bash
# Check learning database size
du -h ~/.quantcoder/learning.db

# Backup database
cp ~/.quantcoder/learning.db ~/.quantcoder/learning.db.backup

# Vacuum database (reduce size)
sqlite3 ~/.quantcoder/learning.db "VACUUM;"
```

### Clearing Cache

```bash
# Clear article cache
rm ~/.quantcoder/articles.json

# Clear generated code (be careful!)
rm -rf ./generated_code/*

# Clear downloads
rm -rf ./downloads/*
```

---

## Escalation

### Contact Information

| Role | Contact | When to Escalate |
|------|---------|------------------|
| On-Call Engineer | TBD | P1/P2 incidents |
| Product Owner | SL-MAR <smr.laignel@gmail.com> | Feature decisions |
| Security Team | TBD | Security incidents |

### Escalation Triggers

- **Immediate**: Security breach, data loss, service unavailable > 1 hour
- **Same Day**: P2 issues, repeated P3 issues
- **Next Business Day**: P3/P4 issues, feature requests

### External Service Contacts

| Service | Status Page | Support |
|---------|-------------|---------|
| QuantConnect | https://www.quantconnect.com/status | support@quantconnect.com |
| CrossRef | https://status.crossref.org | support@crossref.org |
| Anthropic | https://status.anthropic.com | support@anthropic.com |
| OpenAI | https://status.openai.com | support@openai.com |

---

## Appendix: Useful Commands

```bash
# View container resource usage
docker stats quantcoder

# Execute command in container
docker exec -it quantcoder /bin/bash

# View real-time logs
docker logs -f quantcoder

# Export container logs
docker logs quantcoder > container_logs.txt 2>&1

# Check disk usage
du -sh ~/.quantcoder/*

# Test API connectivity
curl -v https://api.crossref.org/works?rows=1 2>&1 | head -20
```
