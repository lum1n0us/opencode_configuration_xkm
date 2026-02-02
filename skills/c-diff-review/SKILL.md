---
name: c-diff-review
description: "AI-powered manual review of C project code diffs with natural language rules in human-readable markdown format. Uses AI assistant for flexible rule matching instead of rigid pattern matching. Supports rules with examples and complex requirements like platform abstraction policies. Use when reviewing C code changes (.diff files) for comprehensive analysis with easily customizable markdown rules."
applyTo: "**/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.cxx, **/*.hpp"
excludeAgent: ["coding-agent"]
---

## Prerequisites

**Parameters:**
- `inter_dir`: Directory for temporary files and build outputs
- `--repo_path`: Path to WAMR git repository (defaults to current directory)

This skill expects these files in the inter_dir:
- `changes.diff` - Complete diff of all changes

# Triage-Focused Code Review for Runtime Systems

This skill focuses on **low-hanging fruit detection** and **complexity identification** for embedded/runtime systems. It assumes clang-tidy handles basic style, formatting, and common bug patterns.

## Review Language

When performing a code review, respond in **English** regardless of the language used in the code comments or identifiers.

## Static Analysis Integration

**Assumed to be handled by clang-tidy:**
- Code style and formatting issues
- Basic memory leak detection
- Simple naming convention violations
- Standard library API misuse patterns
- Basic thread safety violations
- SOLID principle violations
- Simple error handling patterns

**Manual review required for:**
- Context-dependent correctness issues
- Domain-specific logic validation
- Performance under realistic load conditions
- Security threat modeling beyond basic API patterns
- Real-time and embedded system constraints

## Triage Quick Checks

Focus on obvious patterns indicating problems requiring investigation:

### 🔴 CRITICAL FLAGS (Block merge)

**Runtime System Violations:**
- Memory allocation in interrupt handlers or real-time paths
- Unbounded loops without timeout or iteration limits
- Direct hardware register access bypassing abstraction layer
- Multiple free() calls on same pointer without null assignment
- Variable-length arrays in embedded/constrained memory contexts

**Security Red Flags:**
- Authentication/security checks that can be bypassed under time pressure
- Hardware configuration writes without privilege validation
- Race conditions between interrupt and main thread on security state
- Missing timeout on hardware wait conditions (infinite blocking)
- Cryptographic operations in interrupt context (timing attack potential)

**Resource Management Issues:**
- Dynamic allocation patterns that could exhaust memory pools
- Missing rate limiting on external interrupt sources
- Busy-wait loops preventing power management sleep modes
- Peripheral access without corresponding power management

### 🟡 INVESTIGATE FLAGS (Human review required)

**Memory Access Patterns:**
- Structures likely to cause cache line splits or false sharing
- Unaligned access patterns in performance-critical code
- Large structure copying instead of pointer passing
- Frequent malloc/free pairs that should use memory pools

**Concurrency Complexity:**
- Functions with more than 5 volatile variable accesses
- Complex synchronization patterns beyond basic locks
- Interrupt handlers longer than 20 lines
- Priority inversion potential in real-time code

**Hardware Abstraction Issues:**
- Hardware abstraction layer implementations requiring validation
- Boot sequence and initialization order dependencies
- DMA operations and memory coherency requirements
- Power management state transition logic

## Complexity Identification (Flag for Human Review)

Mark these patterns for mandatory expert review:

**Algorithm & Logic Complexity:**
- State machines with more than 8 states or complex transition logic
- Mathematical computations requiring precision validation
- Protocol parsing implementations (network, serial, or binary formats)
- Functions implementing cryptographic operations or security primitives

**System Integration Complexity:**
- Cross-module communication with timing dependencies
- Real-time scheduling or interrupt priority management
- Hardware timing requirements for non-obvious operations
- Error recovery mechanisms that affect system state consistency

**Performance-Critical Paths:**
- Code in real-time constraints requiring timing analysis
- Cache-sensitive algorithms in performance-critical sections
- O(n²) or worse algorithms on potentially large datasets
- Recursive functions without explicit depth limits in real-time code

## Runtime System Standards

**WebAssembly Runtime Specific (WAMR):**
- New features must have WASM_ENABLE_XXX feature flag with default in core/config.h
- Build flags must follow WAMR_BUILD_XXX pattern in build-scripts/config_common.cmake
- Feature documentation required in doc/build_wamr.md
- Public API changes require backward compatibility validation and clear documentation

**Embedded System Focus:**
- Global variables avoided unless necessary with clear ownership documentation
- Hardware timing requirements documented for operations affecting real-time behavior
- Memory alignment requirements specified for DMA and atomic operations
- Interrupt latency impact assessed for any interrupt handler modifications

**Security for System Software:**
- Input validation chains for data from external sources
- Privilege escalation prevention in hardware access functions
- Constant-time algorithms for security-critical operations
- Resource exhaustion protection against denial-of-service attacks

## Review Priorities

### 🔴 CRITICAL (Block merge)
**Safety and correctness issues that static analysis cannot detect:**
- Logic errors in safety-critical control paths
- Resource exhaustion attack vectors
- Real-time constraint violations
- Hardware security mechanism bypasses
- Incorrect algorithm implementations affecting system correctness

### 🟡 INVESTIGATE (Human expert required)
**Complex patterns requiring domain knowledge:**
- Algorithm correctness in mathematical computations
- Architecture compliance and design pattern usage
- Performance characteristics under realistic load conditions
- Synchronization correctness in complex concurrent scenarios
- Hardware abstraction layer design and implementation

### 🟢 OPTIMIZE (Non-blocking suggestions)
**System-specific optimization opportunities:**
- Power consumption reduction in battery-powered systems
- Cache efficiency improvements for performance-critical code
- Memory usage optimization for resource-constrained targets
- Startup time and initialization sequence optimization

## Review Comment Format

**For Critical Issues:**
```
🔴 **[CATEGORY]: [Brief issue description]**
Location: file.c:line_number
Risk: [Safety/Security/Correctness impact]
Action: [Block merge/Immediate fix required]
```

**For Complex Areas:**
```
🟡 **EXPERT REVIEW NEEDED: [Domain]**
Location: file.c:lines_X-Y
Reason: [Why human expertise required]
Suggest: [Security expert/Performance analysis/Domain specialist]
```

**For Optimizations:**
```
🟢 **OPTIMIZATION: [Area]**
Location: file.c:line_number
Benefit: [Performance/Power/Memory improvement potential]
Priority: [Low/Medium based on system constraints]
```

## Automated Flagging Patterns

**Immediate red flags (grep-able patterns):**
- Memory allocation in interrupt context: `malloc.*interrupt|interrupt.*malloc`
- Unbounded loops: `while.*{` without `timeout|max|limit|break`
- Complex volatile operations: `volatile.*=.*volatile`
- Direct hardware access: `0x[0-9A-F]{8,}`
- Safety-critical code debt: `TODO.*security|FIXME.*safety|HACK.*critical`

**Complexity flags (entire function review needed):**
- Functions containing cryptographic primitives or security operations
- Real-time scheduling or interrupt priority manipulation
- Hardware initialization sequences and register configuration
- Multi-threaded synchronization beyond simple mutex usage
- Error handling paths that could leave system in inconsistent state

## General Review Principles

When performing a code review, follow these principles:

1. **Be specific**: Reference exact lines, files, and provide concrete examples
2. **Provide context**: Explain WHY something is an issue and the potential impact
3. **Suggest solutions**: Indicate direction for fixes, not just what's wrong
4. **Be constructive**: Focus on improving the code and system reliability
5. **Recognize complexity**: Acknowledge when issues require domain expertise
6. **Be pragmatic**: Prioritize issues that affect safety, security, or correctness
7. **Flag for experts**: Don't attempt to solve complex domain-specific problems

## Focus Areas Summary

**This skill prioritizes:**
- Obvious safety and security issues that automated tools miss
- Complex algorithmic and system integration patterns requiring human expertise
- Runtime system specific concerns (real-time, embedded, performance)
- Resource management issues in constrained environments
- Hardware abstraction and low-level system correctness

**This skill does NOT focus on:**
- Style and formatting (handled by clang-tidy)
- Basic API misuse patterns (caught by static analysis)
- Simple refactoring opportunities
- Generic software engineering principles
- Issues that don't affect system behavior or safety