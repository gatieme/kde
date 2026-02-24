# AGENTS.md - KDE Project Knowledge Base

**Generated:** 2026-02-24
**Commit:** Current working tree

## OVERVIEW

Python-based agent system for analyzing Linux kernel patches and news feeds. Uses LangGraph for workflow orchestration and ModelScope Qwen3-235B-A22B for AI analysis.

## STRUCTURE

```
kde/
├── kde.py              # Main CLI entrypoint
├── .env                # Environment configuration (OPENAI_API_KEY, etc.)
├── lkml/               # LKML patch analysis module
│   ├── lkml_agent.py  # LangGraph-based LKML agent
│   └── lkml.py        # Core patch analyzer
├── rss/                # RSS/news analysis module
│   ├── rss_agent.py  # LangGraph-based RSS agent
│   └── detect_anti_crawler.py
├── cgit/               # CGit commit analysis module
│   └── cgit_agent.py  # LangGraph-based CGit agent
├── model/              # AI model integration
│   ├── model_infer.py # ModelScope inference wrapper
│   └── model_request.py # Request builder
├── output/              # Unified cache directory for all agents
│   ├── cgit/          # CGit commit cache
│   ├── lkml/          # LKML patch cache
│   └── rss/           # RSS article cache
├── test/               # Test suite
│   ├── test_all.sh
│   ├── test_all_commands.py
│   └── test_*.sh      # Per-agent test scripts
└── patchwork/          # Patchwork integration scripts
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main entry point | kde.py | CLI orchestrator for all agents |
| LKML agent | lkml/lkml_agent.py | LangGraph workflow: fetch → parse → analyze → output |
| RSS agent | rss/rss_agent.py | Playwright integration, anti-crawler detection |
| CGit agent | cgit/cgit_agent.py | Commit analysis with patchset linking |
| Model inference | model/model_infer.py | ModelScope Qwen3-235B-A22B wrapper |
| Tests | test/*.sh, test/*.py | Shell scripts + Python harness |

## COMMANDS

```bash
# Run tests
./test/test_all.sh              # Full test suite
./test/test_lkml.sh            # LKML agent tests
./test/test_cgit.sh            # CGit agent tests
./test/test_rss.sh             # RSS agent tests

# Run agents
python kde.py lkml --level simple --verbose      # LKML analysis
python kde.py rss --level detail                  # RSS analysis
python kde.py cgit --level simple                # CGit analysis
```

## CONVENTIONS

**Naming:**
- Functions: `snake_case` (e.g., `fetch_patch`, `parse_commit`)
- Classes: `CamelCase` (e.g., `ModelInference`, `LKMLAgentState`)
- State classes: `CamelCase` + `State` suffix
- Constants: `UPPER_SNAKE_CASE` (e.g., `ALL_RSS_SOURCES`)

**Import pattern:**
```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model import ModelInference, ModelRequest
```

**Comments:** Bilingual - English for structure, Chinese for domain logic

**Error handling:** `try/except` with `sys.exit(1)` on fatal failures

## ANTI-PATTERNS (THIS PROJECT)

- No formal build system (no setup.py, pyproject.toml, Makefile)
- No CI/CD (no .github/workflows)
- Hardcoded test data in shell scripts
- Inconsistent __init__.py (cgit/, rss/, test/ missing)

## UNIQUE STYLES

- **Bilingual comments**: English for code structure, Chinese for domain logic
- **sys.path.append()**: For inter-module access (sibling directories)
- **LangGraph agents**: State-based workflow with fetch → parse → analyze → output pattern
- **ModelScope integration**: Qwen3-235B-A22B model via ModelScope API
- **Shell script tests**: Custom test framework with bash arrays + eval

## NOTES

- Cache directories created automatically in `output/`
- Use `git clean -fdX` to remove caches
- No requirements.txt - dependencies in README only
- Verbose levels: 0 (minimal), 1 (progress), 2 (detailed), 3 (full)
