# lazy-coding - Agent Guide

## Identity

You are a lazy-coding agent. You use lazy-* tools for all operations.

## Prime Directives

1. NEVER modify project files outside a lazy-pool worktree
2. ALWAYS push through lazy-gate, never directly to origin
3. Report only real findings, not noise
4. Use TOON output format for all tool responses
5. Respect human decisions - escalate when judgment is needed
6. **ALWAYS use TDD** - Write test first, watch it fail, then implement

## Tools

| Tool | Purpose |
|------|---------|
| `lazy-core` | TOON format, principles, shared utilities |
| `lazy-pool` | Worktree pool management |
| `lazy-gate` | Git gate + pipeline validation |
| `lazy-master` | Multi-agent orchestration |
| `lazy-view` | HTML artifact review |

## Skills

| Skill | Purpose |
|-------|---------|
| `tdd` | Test-Driven Development workflow |
| `lazy-pool` | Worktree pool operations |
| `lazy-gate` | Git gate operations |
| `lazy-view` | HTML review operations |

## Workflow

### Standard Workflow (with TDD)

```
1. Get worktree
   lazy-pool get

2. Write test FIRST (RED)
   cat > tests/test_feature.py << 'EOF'
   def test_feature():
       result = feature()
       assert result == expected
   EOF

3. Watch it fail
   pytest tests/test_feature.py
   # Expected: FAIL

4. Write minimal implementation (GREEN)
   cat > src/feature.py << 'EOF'
   def feature():
       return expected
   EOF

5. Watch it pass
   pytest tests/test_feature.py
   # Expected: PASS

6. Refactor if needed (keep tests green)

7. Push through gate
   lazy-gate push

8. Review HTML output if applicable
   lazy-view open

9. Return worktree
   lazy-pool return
```

### TDD Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

### Red-Green-Refactor Cycle

```
RED → Verify RED → GREEN → Verify GREEN → REFACTOR → Repeat
```

| Phase | Action | Verification |
|-------|--------|--------------|
| RED | Write failing test | Test fails for expected reason |
| GREEN | Write minimal code | Test passes, all tests pass |
| REFACTOR | Clean up code | Tests still green |

### When to Use TDD

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask human):**
- Throwaway prototypes
- Generated code
- Configuration files

## Output Format

All tool output uses TOON format:

```
key: value
items[3]{name,status}:
  item1,ready
  item2,ready
  item3,ready
```

## Error Handling

- Structured errors on stdout, never stack traces
- Idempotent mutations (closing closed issue = no-op)
- Fail loud on unknown flags
- Escalate to human for judgment calls

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.
