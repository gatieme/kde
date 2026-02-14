# AGENTS.md - KDE Project Agent Guidelines

## Project Overview

Python-based agent system for analyzing Linux kernel patches and news feeds. Uses LangGraph for workflow orchestration and OpenAI models for AI analysis.

**Main Entry Point**: `kde.py` - CLI orchestrator for LKML, CGit, and RSS agents

## Directory Structure

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
│   ├── model_infer.py # OpenAI inference wrapper
│   └── model_request.py # Request builder
├── test/               # Test suite
│   ├── test_all.sh
│   ├── test_all_commands.py
│   └── test_*.sh      # Per-agent test scripts
└── patchwork/          # Patchwork integration scripts
```

## Build, Lint, and Test Commands

### Running Tests
```bash
# Run full test suite
./test/test_all.sh

# Run specific agent tests
./test/test_lkml.sh
./test/test_cgit.sh
./test/test_rss.sh
./test/test_verbose.sh

# Run single test via Python
python test/test_all_commands.py  # Modify to select specific test
```

### Running Agents
```bash
# LKML analysis
python kde.py lkml --level simple --verbose

# RSS analysis
python kde.py rss --level detail

# CGit analysis
python kde.py cgit --level simple
```

**Note**: No formal build system (no Makefile, CMakeLists.txt, pyproject.toml). Tests are shell scripts + Python harness.

## Code Style Guidelines

### Naming Conventions
- **Functions**: `snake_case` (e.g., `fetch_patch`, `parse_commit`, `analyze_articles`)
- **Classes**: `CamelCase` with descriptive names (e.g., `ModelInference`, `ModelRequest`)
- **State Classes**: `CamelCase` with `State` suffix (e.g., `AgentState`, `LKMLAgentState`, `CGitAgentState`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `ALL_RSS_SOURCES`)

### Import Patterns
```python
# Standard library first
import sys
import argparse

# Local imports with path manipulation for inter-module access
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model import ModelInference, ModelRequest
```

### Type Annotations
Use Python type hints and `@dataclass` for state containers:
```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AgentState:
    messages: List[str]
    current_step: Optional[str] = None
```

### Error Handling
```python
try:
    result = agent.run()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
```
- Use `try/except` with meaningful error messages
- Exit with `sys.exit(1)` on fatal failures
- Propagate exceptions with context for debugging

### Documentation Comments
- **Code structure**: English comments
- **Domain logic**: Chinese comments (bilingual approach)
- **Functions**: Brief docstrings for entry points

```python
def run_lkml_agent(args):
    """Run LKML analysis agent with given arguments."""
    # 下载补丁文件 - Download patch file
    patch_path = fetch_patch(args.url)
```

## Agent Development Patterns

### Standard Agent Lifecycle
1. **State definition**: Create `@dataclass AgentState` with required fields
2. **Build function**: `build_xxx_agent()` returns LangGraph StateGraph
3. **Run function**: `run_xxx_agent(args)` orchestrates execution
4. **Workflow nodes**: `fetch`, `parse`, `analyze`, `output`

### Model Integration
```python
from model import ModelInference, ModelRequest

model = ModelInference()
request = ModelRequest()
request.set_content("Analyze this patch")
response = model.infer(request)
```

## Environment Setup

Copy `.env` template and configure:
```bash
cp .env.example .env
# Edit .env to set OPENAI_API_KEY and other required variables
```

## Testing Guidelines

- Add new tests to `test/test_all_commands.py`
- Create corresponding shell script in `test/` if needed
- Test both simple and detail levels for agents
- Verify verbose mode output

## Key Dependencies

- Python 3.8+
- LangGraph for workflow orchestration
- OpenAI API for model inference
- Playwright (for RSS tests)
