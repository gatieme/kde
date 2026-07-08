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
│   ├── lkml.py        # Core patch analyzer (legacy)
│   └── AGENTS.md      # Module-specific docs
├── rss/                # RSS/news analysis module
│   ├── rss_agent.py  # LangGraph-based RSS agent
│   ├── detect_anti_crawler.py
│   └── AGENTS.md      # Module-specific docs
├── cgit/               # CGit commit analysis module
│   └── cgit_agent.py  # LangGraph-based CGit agent
├── model/              # AI model integration
│   ├── model_infer.py # ModelScope inference wrapper
│   └── model_request.py # Request builder
├── utils/              # Cross-module utilities
│   ├── text_formatter.py # Markdown formatting
│   ├── http_fetcher.py  # HTTP request wrappers
│   ├── process_monitor.py # Process tracking
│   └── AGENTS.md      # Module-specific docs
├── patchwork/          # Patchwork integration module
│   ├── patchwork_agent.py # LangGraph-based Patchwork agent
│   ├── get_patchwork_project.sh
│   ├── get_patchwork_series.sh
│   └── batch.sh
├── output/              # Unified cache directory for all agents
│   ├── cgit/          # CGit commit cache
│   ├── lkml/          # LKML patch cache
│   ├── rss/           # RSS article cache
│   └── patchwork/     # Patchwork series cache
├── test/               # Test suite
│   ├── test_all.sh
│   ├── test_all_commands.py
│   ├── test_*.sh      # Per-agent test scripts
│   └── test_*.py      # Python unit tests
└── diagrams/           # Architecture diagrams
    ├── lkml/           # LKML Agent diagrams
    ├── rss/            # RSS Agent diagrams
    ├── cgit/           # CGit Agent diagrams
    ├── patchwork/      # Patchwork diagrams
    └── (root)          # System-level: architecture, kde-overview, cache-system, model-inference, test-suite
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
- Memory files stored in `.memory/` following conventions:
  - Planning: `.memory/optimization/`
  - Implementation: `.memory/implementation/`
  - Testing: `.memory/testing/`
