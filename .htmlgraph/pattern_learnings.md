# Pattern Learning Report

Generated: 2026-01-13T04:57:03.496688

## Recommendations

## Anti-Patterns

### Low Success Pattern: Bash → Bash → Bash

This pattern has only a 0.0% success rate across 1394 occurrences. Consider alternative approaches.

**Impact Score**: 100.0

### Low Success Pattern: Read → Read → Read

This pattern has only a 0.0% success rate across 519 occurrences. Consider alternative approaches.

**Impact Score**: 100.0

### Low Success Pattern: Edit → Edit → Edit

This pattern has only a 0.0% success rate across 256 occurrences. Consider alternative approaches.

**Impact Score**: 100.0

### Low Success Pattern: Bash → Bash → Read

This pattern has only a 0.0% success rate across 189 occurrences. Consider alternative approaches.

**Impact Score**: 100.0

### Low Success Pattern: Bash → Read → Read

This pattern has only a 0.0% success rate across 181 occurrences. Consider alternative approaches.

**Impact Score**: 100.0

## Optimization Opportunities

### Multiple Read Operations Detected

Pattern 'Read → Read → Read' contains 3 Read operations. Consider delegating exploration to a subagent to reduce context usage.

**Impact Score**: 5190.0

### Multiple Read Operations Detected

Pattern 'Bash → Read → Read' contains 2 Read operations. Consider delegating exploration to a subagent to reduce context usage.

**Impact Score**: 1810.0

### Multiple Read Operations Detected

Pattern 'Read → Read → Bash' contains 2 Read operations. Consider delegating exploration to a subagent to reduce context usage.

**Impact Score**: 1470.0

### Multiple Read Operations Detected

Pattern 'Read → Bash → Read' contains 2 Read operations. Consider delegating exploration to a subagent to reduce context usage.

**Impact Score**: 1070.0

### Multiple Read Operations Detected

Pattern 'Read → Read → Grep' contains 2 Read operations. Consider delegating exploration to a subagent to reduce context usage.

**Impact Score**: 830.0

## All Detected Patterns

- **Bash → Bash → Bash** (frequency: 1394, success: 0.0%)
- **Read → Read → Read** (frequency: 519, success: 0.0%)
- **Edit → Edit → Edit** (frequency: 256, success: 0.0%)
- **Bash → Bash → Read** (frequency: 189, success: 0.0%)
- **Bash → Read → Read** (frequency: 181, success: 0.0%)
- **Read → Read → Bash** (frequency: 147, success: 0.0%)
- **Read → Bash → Bash** (frequency: 147, success: 0.0%)
- **Edit → Bash → Bash** (frequency: 115, success: 0.0%)
- **Bash → Read → Bash** (frequency: 113, success: 0.0%)
- **Read → Bash → Read** (frequency: 107, success: 0.0%)
- **Read → Edit → Edit** (frequency: 85, success: 0.0%)
- **Read → Read → Grep** (frequency: 83, success: 0.0%)
- **Edit → Edit → Bash** (frequency: 77, success: 0.0%)
- **Read → Read → Edit** (frequency: 75, success: 0.0%)
- **Grep → Grep → Grep** (frequency: 75, success: 0.0%)
- **Grep → Read → Read** (frequency: 73, success: 0.0%)
- **Bash → Bash → TodoWrite** (frequency: 65, success: 0.0%)
- **Glob → Read → Read** (frequency: 62, success: 0.0%)
- **Read → Grep → Read** (frequency: 62, success: 0.0%)
- **TodoWrite → Bash → Bash** (frequency: 59, success: 0.0%)
