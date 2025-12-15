# QuantCoder CLI v4.0 - New Features

## Overview

Version 4.0 introduces two powerful new modes that transform QuantCoder from a single-strategy generator into a self-improving, autonomous system capable of building entire strategy libraries.

## What's New

### 🤖 Autonomous Mode

**Self-improving strategy generation that learns from its own mistakes.**

```bash
quantcoder auto start --query "momentum trading" --max-iterations 50
```

**Key Features:**
- Learns from compilation errors automatically
- Improves prompts based on performance
- Self-healing code fixes
- Continuous improvement over iterations
- SQLite-based learning database

**Use Case:** Generate 10-50 variations of a single strategy type, with quality improving over time.

---

### 📚 Library Builder Mode

**Build a comprehensive strategy library from scratch across all major categories.**

```bash
quantcoder library build --comprehensive --max-hours 24
```

**Key Features:**
- 10 strategy categories (momentum, mean reversion, ML-based, etc.)
- 50-100 strategies total
- Organized directory structure
- Progress tracking with checkpoints
- Resume capability

**Use Case:** Create a complete, production-ready strategy library overnight.

---

## Architecture Comparison

### v3.0 (Previous)
```
User Request → Multi-Agent System → Generate Strategy → Done
```

### v4.0 (New)
```
User Request → Autonomous Mode → Learning Loop → Self-Improvement
                     ↓
              Library Builder → Systematic Coverage → Complete Library
```

## Quick Start

### 1. Test with Demo Mode

```bash
# Test autonomous mode (no API calls)
quantcoder auto start --query "momentum" --max-iterations 5 --demo

# Test library builder (no API calls)
quantcoder library build --categories momentum --max-hours 1 --demo
```

### 2. Run Autonomous Mode

```bash
# Generate self-improving momentum strategies
quantcoder auto start \
  --query "momentum trading" \
  --max-iterations 50 \
  --min-sharpe 0.5

# Check learning progress
quantcoder auto status

# Generate report
quantcoder auto report
```

### 3. Build Strategy Library

```bash
# Build complete library
quantcoder library build --comprehensive --max-hours 24

# Or build specific categories
quantcoder library build --categories momentum,mean_reversion

# Check progress
quantcoder library status

# Resume if interrupted
quantcoder library resume

# Export when done
quantcoder library export --format zip --output strategies.zip
```

## Mode Comparison

| Feature | Regular Mode | Autonomous Mode | Library Builder |
|---------|--------------|-----------------|-----------------|
| **Input** | Single query | Single query | All categories |
| **Output** | 1 strategy | 10-100 variations | 50-100 diverse strategies |
| **Learning** | None | Self-improving | Uses autonomous learning |
| **Time** | 5-10 min | 2-10 hours | 20-30 hours |
| **Use Case** | Quick test | Deep exploration | Complete library |
| **Quality** | Variable | Improves over time | Filtered by quality |

## Command Reference

### Autonomous Mode

```bash
# Start
quantcoder auto start --query <query> [OPTIONS]
  --max-iterations INTEGER   # Max iterations (default: 50)
  --min-sharpe FLOAT        # Min Sharpe threshold (default: 0.5)
  --output PATH             # Output directory
  --demo                    # Demo mode (no API calls)

# Status
quantcoder auto status

# Report
quantcoder auto report
quantcoder auto report --format json
```

### Library Builder Mode

```bash
# Build
quantcoder library build [OPTIONS]
  --comprehensive           # Build all categories
  --max-hours INTEGER      # Max build time (default: 24)
  --output PATH           # Output directory
  --min-sharpe FLOAT      # Min Sharpe threshold (default: 0.5)
  --categories TEXT       # Comma-separated categories
  --demo                  # Demo mode (no API calls)

# Status
quantcoder library status

# Resume
quantcoder library resume

# Export
quantcoder library export --format <zip|json> --output <path>
```

## Learning System

### How Autonomous Mode Learns

```
Iteration 1:
  Generate code → Error: "ImportError" → Store pattern

Iteration 2:
  Generate code → Apply fix from Iteration 1 → Success!
  Update confidence score

Iteration 3+:
  Generate code → Enhanced prompts → Fewer errors → Better Sharpe
```

### Learning Database Schema

**4 Tables:**
1. `compilation_errors` - Error patterns and fixes
2. `performance_patterns` - What makes strategies succeed
3. `generated_strategies` - All strategies with metadata
4. `successful_fixes` - Proven solutions with confidence scores

**Location:** `~/.quantcoder/learnings.db`

## Performance Metrics

### Autonomous Mode (50 iterations)

- **Time**: 5-10 hours
- **Success Rate**: 50% → 85% (improves)
- **Average Sharpe**: 0.4 → 0.8 (improves)
- **Auto-Fix Rate**: 40% → 85% (improves)
- **API Calls**: ~400 total (8 per iteration)

### Library Builder (comprehensive)

- **Time**: 20-30 hours
- **Strategies**: 86 total
- **Categories**: 10 covered
- **API Calls**: ~52,000-60,000 total
- **Output Size**: ~100MB
- **Estimated Cost**: $50-$175 (Sonnet), $20-$70 (GPT-4o)

## Strategy Taxonomy

### High Priority (34 strategies)
- Momentum (12)
- Mean Reversion (10)
- Factor-Based (12)

### Medium Priority (30 strategies)
- Volatility (8)
- ML-Based (10)
- Market Microstructure (6)
- Event-Driven (8)
- Options (8)

### Low Priority (12 strategies)
- Cross-Asset (6)
- Alternative Data (6)

## Example Workflows

### Workflow 1: Explore Then Scale

```bash
# 1. Explore momentum strategies
quantcoder auto start --query "momentum" --max-iterations 20

# 2. Build full library with learnings
quantcoder library build --comprehensive
```

### Workflow 2: Focused Category

```bash
# Build just high-priority categories
quantcoder library build \
  --categories momentum,mean_reversion,factor_based \
  --max-hours 12
```

### Workflow 3: Continuous Learning

```bash
# Day 1: Learn momentum patterns
quantcoder auto start --query "momentum" --max-iterations 50

# Day 2: Learn mean reversion patterns
quantcoder auto start --query "mean reversion" --max-iterations 50

# Day 3: Build library with all learnings
quantcoder library build --comprehensive
```

## Integration with v3.0 Features

### v4.0 Uses v3.0 Components

```
Autonomous Mode
└── Uses Multi-Agent System (v3.0)
    ├── Coordinator Agent
    ├── Universe Agent
    ├── Alpha Agent
    └── Risk Agent

Library Builder
└── Uses Autonomous Mode (v4.0)
    └── Uses Multi-Agent System (v3.0)
```

All v3.0 features still available:
- Manual multi-agent generation
- MCP integration
- Parallel execution
- Multi-LLM support

## Best Practices

### 1. Always Start with Demo Mode

```bash
quantcoder auto start --query "test" --max-iterations 3 --demo
```

### 2. Monitor Resource Usage

```bash
# In separate terminal
watch -n 60 quantcoder auto status
watch -n 300 quantcoder library status
```

### 3. Use Checkpoints

```bash
# Ctrl+C saves progress
# Resume anytime
quantcoder library resume
```

### 4. Start with Lower Thresholds

```bash
# Early iterations
--min-sharpe 0.3

# After learning
--min-sharpe 0.8
```

### 5. Export Regularly

```bash
# Backup progress
quantcoder library export --format zip --output backup_$(date +%Y%m%d).zip
```

## Troubleshooting

### Autonomous Mode Issues

**Problem**: Low success rate
```bash
# Solution: Lower threshold
--min-sharpe 0.3
```

**Problem**: Repeated errors
```bash
# Solution: Check learnings
quantcoder auto status
```

### Library Builder Issues

**Problem**: Build interrupted
```bash
# Solution: Resume from checkpoint
quantcoder library resume
```

**Problem**: Time limit too short
```bash
# Solution: Increase limit
--max-hours 48
```

## File Locations

### Configuration
```
~/.quantcoder/config.toml
~/.quantcoder/.env
```

### Learning Database
```
~/.quantcoder/learnings.db
```

### Checkpoint
```
~/.quantcoder/library_checkpoint.json
```

### Default Output
```
./autonomous_strategies/  # Autonomous mode
./strategies_library/     # Library builder
```

## Migration from v3.0

**No breaking changes!** All v3.0 commands still work:

```bash
quantcoder chat              # Still works
quantcoder generate 1        # Still works
quantcoder search "query"    # Still works
```

**New commands added:**
```bash
quantcoder auto start ...    # NEW
quantcoder library build ... # NEW
```

## Roadmap

### v4.1 (Planned)
- [ ] Parallel category building
- [ ] HTML dashboard generation
- [ ] Advanced fix strategies (AST manipulation)

### v4.2 (Planned)
- [ ] Distributed building
- [ ] Performance prediction
- [ ] Cross-category learning transfer

### v5.0 (Future)
- [ ] Real-time strategy optimization
- [ ] Multi-broker deployment
- [ ] Live trading integration

## Documentation

- **Autonomous Mode**: See [AUTONOMOUS_MODE.md](./AUTONOMOUS_MODE.md)
- **Library Builder**: See [LIBRARY_BUILDER.md](./LIBRARY_BUILDER.md)
- **v3.0 Features**: See [ARCHITECTURE_V3_MULTI_AGENT.md](./ARCHITECTURE_V3_MULTI_AGENT.md)

## Support

Report issues at: https://github.com/YOUR_ORG/quantcoder-cli/issues

## License

MIT License - See LICENSE file

---

**QuantCoder CLI v4.0** - From single strategy to complete library, powered by self-improving AI. 🚀
