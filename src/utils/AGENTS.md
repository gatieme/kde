# Utils Module

**Generated:** 2026-06-05

## OVERVIEW

Cross-module utility functions for text formatting, HTTP requests, and process monitoring.

## STRUCTURE

```
utils/
├── text_formatter.py    # Markdown table formatting
├── http_fetcher.py      # HTTP request utilities
├── process_monitor.py   # Process tracking
└── __init__.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Text formatting | text_formatter.py | `format_text_for_markdown()` |
| HTTP utilities | http_fetcher.py | Request wrappers |
| Process monitoring | process_monitor.py | Process lifecycle |

## CONVENTIONS

- Functions: `snake_case` (e.g., `chinese_to_english_punctuation`)
- Pure functions: No side effects, deterministic output
- Used by all agents: lkml, rss, cgit, patchwork

## UNIQUE STYLES

- Chinese punctuation conversion for markdown compatibility
- Newline → `<br>` replacement for table display
- Chain of transformations: punctuation → spacing → newline