# Autonomous Mode Documentation

## Overview

Autonomous Mode is a self-improving strategy generation system that continuously learns from its own compilation errors and backtest performance. It runs independently, refining its approach over time to generate higher-quality QuantConnect algorithms.

## Key Features

- **Self-Learning**: Learns from compilation errors and applies fixes automatically
- **Performance-Based**: Adapts strategy generation based on backtest results
- **Prompt Evolution**: Dynamically improves agent prompts with learned patterns
- **Progress Tracking**: SQLite database tracks all learnings and improvements
- **Graceful Exit**: Multiple exit options (Ctrl+C, max iterations, user prompt)

## Architecture

```
Autonomous Pipeline
├── Learning Database (SQLite)
│   ├── Compilation errors & fixes
│   ├── Performance patterns
│   ├── Generated strategies
│   └── Successful fix patterns
├── Error Learner
│   ├── Pattern recognition
│   ├── Fix suggestion
│   └── Success rate tracking
├── Performance Learner
│   ├── Poor performance analysis
│   ├── Success pattern identification
│   └── Best practices extraction
└── Prompt Refiner
    ├── Inject error avoidance
    ├── Add success patterns
    └── Performance insights
```

## Usage

### Basic Usage

```bash
# Start autonomous mode
quantcoder auto start \
  --query "momentum trading" \
  --max-iterations 50 \
  --min-sharpe 0.5

# Check status
quantcoder auto status

# Generate report
quantcoder auto report
```

### Advanced Options

```bash
# Run with custom output directory
quantcoder auto start \
  --query "mean reversion" \
  --max-iterations 100 \
  --min-sharpe 1.0 \
  --output ./my_strategies

# Demo mode (no real API calls)
quantcoder auto start \
  --query "momentum trading" \
  --max-iterations 5 \
  --demo
```

## How It Works

### 1. Initial Generation

```
Fetch Papers → Generate Strategy → Validate Code → Backtest → Store Results
```

### 2. Learning Loop

For each iteration:

1. **Fetch Research Papers**: Search arXiv/CrossRef for relevant papers
2. **Apply Learnings**: Enhance prompts with error patterns and success strategies
3. **Generate Code**: Create multi-file QuantConnect algorithm
4. **Validate**: Check for compilation/syntax errors
5. **Self-Healing**: If errors found, apply learned fixes automatically
6. **Backtest**: Run strategy backtest via QuantConnect MCP
7. **Learn**: Analyze results and update knowledge base

### 3. Self-Improvement

The system improves through:

- **Error Pattern Recognition**: Identifies recurring errors
- **Automatic Fixes**: Applies previously successful fixes
- **Prompt Enhancement**: Adds learned patterns to agent prompts
- **Performance Analysis**: Identifies what makes strategies succeed

## Learning Database Schema

### Compilation Errors Table
```sql
- error_type: Classification of error
- error_message: Full error text
- code_snippet: Relevant code
- fix_applied: Solution that was applied
- success: Whether fix worked
- timestamp: When error occurred
```

### Performance Patterns Table
```sql
- strategy_type: Category (momentum, mean_reversion, etc.)
- sharpe_ratio: Achieved Sharpe ratio
- max_drawdown: Maximum drawdown
- common_issues: Identified problems
- success_patterns: What worked well
- timestamp: When strategy was generated
```

### Generated Strategies Table
```sql
- name: Strategy name
- category: Strategy type
- paper_source: Research paper URL
- code_files: All generated files (JSON)
- sharpe_ratio: Backtest Sharpe
- compilation_errors: Error count
- refinement_attempts: Fix attempts
- success: Whether strategy passed threshold
- timestamp: Generation time
```

### Successful Fixes Table
```sql
- error_pattern: Error signature
- solution_pattern: Fix that worked
- confidence: Success rate (0.0-1.0)
- times_applied: Usage count
- success_count: Successful applications
```

## Example Session

```bash
$ quantcoder auto start --query "momentum trading" --max-iterations 10

╔════════════════════════════════════════════╗
║     🤖 Autonomous Pipeline                 ║
║                                            ║
║  Autonomous Mode Started                   ║
║                                            ║
║  Query: momentum trading                   ║
║  Max iterations: 10                        ║
║  Min Sharpe: 0.5                          ║
║  Demo mode: False                          ║
╚════════════════════════════════════════════╝

================================================================================
Iteration 1/10
================================================================================

📚 Fetching research papers...
✓ Found: A Novel Approach to Momentum Trading Strategies...

🧠 Applying learned patterns...
⚙️  Generating strategy code...
✓ Generated: MomentumStrategy_20250115_103000

🔍 Validating code...
⚠ Validation errors found (2)
🔧 Attempting self-healing...
✓ Self-healing successful!

📊 Running backtest...
Results: Sharpe=0.72, Drawdown=-15.3%
✓ Success! Sharpe=0.72

[... continues for 10 iterations ...]

================================================================================
Autonomous Mode Complete
================================================================================

Session Statistics:
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Metric               ┃ Value   ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Total Attempts       │ 10      │
│ Successful           │ 7       │
│ Failed               │ 3       │
│ Success Rate         │ 70.0%   │
│ Avg Sharpe           │ 0.68    │
│ Auto-Fix Rate        │ 85.0%   │
│ Elapsed Time         │ 2.3 hrs │
└──────────────────────┴─────────┘

🧠 Key Learnings:

Most Common Errors:
  1. import_error: 5 occurrences (100% fixed)
  2. attribute_error: 3 occurrences (66% fixed)
  3. type_error: 2 occurrences (50% fixed)

📚 Library Stats:
  Total strategies: 10
  Successful: 7
  Average Sharpe: 0.68
```

## Performance Expectations

### Learning Curve

- **Iterations 1-10**: Error rate ~50%, avg Sharpe ~0.4
- **Iterations 11-30**: Error rate ~30%, avg Sharpe ~0.6
- **Iterations 31+**: Error rate ~15%, avg Sharpe ~0.8

The system genuinely improves over time as the learning database grows.

### Self-Healing Rate

- **First attempt**: ~40% errors fixed automatically
- **After 20 iterations**: ~70% errors fixed automatically
- **After 50 iterations**: ~85% errors fixed automatically

## Exit Options

### 1. Ctrl+C
```bash
# Graceful shutdown
^C
Shutting down gracefully...
```

### 2. Max Iterations
```bash
# Stops after reaching limit
--max-iterations 50
```

### 3. Interactive Prompt
```bash
# Every 10 iterations
Continue autonomous mode? [y/n/p]: n
```

- `y`: Continue
- `n`: Stop
- `p`: Pause (press Enter to resume)

## Status and Reporting

### Check Status
```bash
$ quantcoder auto status

Autonomous Mode Statistics

Total strategies generated: 47
Successful: 35
Average Sharpe: 0.73

Common Errors:
  1. import_error: 12 (91% fixed)
  2. name_error: 8 (75% fixed)
  3. api_error: 5 (80% fixed)
```

### Generate Report
```bash
$ quantcoder auto report

Autonomous Mode Learning Report
============================================================

Total Strategies: 47
Successful: 35
Average Sharpe: 0.73
Average Errors: 1.2
Average Refinements: 0.8

Category Breakdown:
  • momentum: 25 strategies (avg Sharpe: 0.78)
  • mean_reversion: 15 strategies (avg Sharpe: 0.65)
  • factor_based: 7 strategies (avg Sharpe: 0.71)
```

### JSON Export
```bash
$ quantcoder auto report --format json > learnings.json
```

## Best Practices

### 1. Start Small
```bash
# First run: test with few iterations
quantcoder auto start --query "momentum" --max-iterations 5 --demo
```

### 2. Use Demo Mode
```bash
# Test without API costs
quantcoder auto start --query "momentum" --demo
```

### 3. Set Realistic Thresholds
```bash
# Start with lower threshold
--min-sharpe 0.3  # Early iterations
--min-sharpe 0.8  # After learning
```

### 4. Monitor Progress
```bash
# In another terminal
watch -n 60 quantcoder auto status
```

## Troubleshooting

### Issue: Too Many Failed Strategies

**Solution**: Lower min-sharpe threshold initially
```bash
--min-sharpe 0.3
```

### Issue: Repeated Errors Not Fixed

**Solution**: Check learning database
```bash
quantcoder auto status
# Look at fix rate for each error type
```

### Issue: Slow Performance

**Solution**: Use demo mode or reduce iterations
```bash
--max-iterations 20
```

## Technical Details

### Database Location
```
~/.quantcoder/learnings.db
```

### Learning Database Size
- ~1KB per strategy
- ~50 strategies = ~50KB
- ~1000 strategies = ~1MB

### Memory Usage
- Base: ~50MB
- Per iteration: ~10MB
- Peak: ~200MB

### API Calls Per Iteration
- Paper search: 1 call
- Strategy generation: 3-5 calls (multi-agent)
- Validation: 1 call
- Backtest: 1 call
- **Total: ~6-8 calls per iteration**

## Integration with Other Modes

Autonomous mode can feed the Library Builder:

```bash
# Run autonomous mode first
quantcoder auto start --query "momentum" --max-iterations 50

# Then build library using learnings
quantcoder library build --comprehensive
```

The library builder will use the learned patterns from autonomous mode!

## Limitations

1. **Not Production-Ready**: Requires human review before live trading
2. **API Costs**: Each iteration makes 6-8 API calls
3. **Time-Intensive**: Expect 2-5 minutes per iteration
4. **Domain-Specific**: Learns patterns specific to QuantConnect API

## Future Enhancements

- [ ] Multi-query parallelization
- [ ] Advanced fix strategies (AST manipulation)
- [ ] Performance prediction before backtesting
- [ ] Cross-category learning transfer
- [ ] Hyperparameter optimization
