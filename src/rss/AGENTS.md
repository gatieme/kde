# RSS Agent Module

**Generated:** 2026-02-24

## OVERVIEW

LangGraph-based agent for analyzing technical RSS feeds (Phoronix, LWN) with anti-crawler detection.

## STRUCTURE

```
rss/
├── rss_agent.py           # Main agent with StateGraph workflow
├── dual_rss_agent.py      # Dual-source agent (legacy)
├── detect_anti_crawler.py # Anti-crawler detection utilities
└── README.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent workflow | rss_agent.py | detect → fetch → analyze → generate → output |
| State definition | rss_agent.py:46+ | AgentState with articles, summaries |
| RSS sources | rss_agent.py:29-42 | ALL_RSS_SOURCES (Phoronix, LWN) |
| Anti-crawler | detect_anti_crawler.py | Cloudflare, Turnstile detection |

## CONVENTIONS

- State class: `AgentState` with `@dataclass`
- Workflow nodes: `detect_protection`, `fetch_rss_feeds`, `fetch_article_content`, `analyze_articles`, `generate_summaries`, `output_results`
- Cache location: `output/rss/{hash-id}.txt`
- Uses Playwright for anti-crawler bypass

## ANTI-PATTERNS

- No __init__.py (module not importable)
- Hardcoded RSS sources in code

## UNIQUE STYLES

- Playwright integration for browser automation
- Multiple HTTP backends (requests, httpx, Playwright)
- AI summary generation with kernel vs non-kernel distinction
- Cloudflare/Turnstile detection and bypass
