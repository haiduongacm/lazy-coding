# Workflow

## Standard Workflow

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

4. Write minimal implementation (GREEN)
   cat > src/feature.py << 'EOF'
   def feature():
       return expected
   EOF

5. Watch it pass
   pytest tests/test_feature.py

6. Refactor if needed

7. Push through gate
   lazy-gate push

8. Return worktree
   lazy-pool return
```

## TDD Workflow

```
RED → Verify RED → GREEN → Verify GREEN → REFACTOR → Repeat
```

## Fleet Management

```
1. Dispatch task
   lazy-master dispatch "fix bug"

2. Monitor
   lazy-master status
   lazy-master liveness

3. Control if needed
   lazy-master control <id> interrupt

4. Guard before push
   lazy-master guard

5. Push through gate
   lazy-gate push
```
