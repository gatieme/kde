# Test Suite

**Generated:** 2026-02-24

## OVERVIEW

Custom shell-based test framework with Python harness for testing all agents.

## STRUCTURE

```
test/
├── test_all.sh              # Master test runner
├── test_lkml.sh             # LKML agent tests
├── test_rss.sh              # RSS agent tests
├── test_cgit.sh             # CGit agent tests
├── test_verbose.sh          # Verbose mode tests
├── test.sh                  # General test script
├── test_all_commands.py     # Python test harness
├── test_cgit_workflow_order.py
├── test_cache_directories.py
├── test_b4_robustness.py
├── test_b4_timeout.py
└── test_progress_descriptions.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Test orchestration | test_all.sh | Calls test_lkml.sh, test_rss.sh, test_cgit.sh |
| Python harness | test_all_commands.py | Python-based test runner |
| Agent-specific tests | test_*.sh | Per-agent test scripts |
| Integration tests | test_*.py | Workflow, cache, timeout tests |

## CONVENTIONS

- Bash arrays + eval for test execution
- Hardcoded test data (message IDs, commit IDs)
- Bilingual comments (Chinese primary)
- No __init__.py (not a Python package)

## ANTI-PATTERNS

- No pytest or unittest framework
- Hardcoded test data in scripts
- No test fixtures or mocking
- No CI/CD integration

## UNIQUE STYLES

- Shell script-based test framework
- Manual test data management
- Direct agent invocation tests
- Bilingual test output
