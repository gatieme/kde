# LKML Agent Module

**Generated:** 2026-02-24

## OVERVIEW

LangGraph-based agent for analyzing Linux Kernel Mailing List (LKML) patches.

## STRUCTURE

```
lkml/
├── lkml_agent.py    # Main agent with StateGraph workflow
├── lkml.py          # Core patch analyzer (legacy)
├── __init__.py
├── get_b4_series.sh     # B4 series fetch helper
└── cvt_lkml_to_lore.sh  # LKML to LORE converter
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent workflow | lkml_agent.py | fetch → parse → generate_summary → analyze → output |
| State definition | lkml_agent.py:21-40 | LKMLAgentState with all workflow fields |
| Patch download | lkml_agent.py:69+ | Uses b4 am, caches to output/lkml/<id>/patchset/ |
| Thread download | lkml_agent.py:334+ | Uses b4 mbox, caches to output/lkml/<id>/discussion/ |
| Patch parsing | lkml_agent.py | Extracts author, date, version, subject |

## CONVENTIONS

- State class: `LKMLAgentState` with `@dataclass`
- Workflow nodes: `fetch_patch`, `parse_patch`, `generate_summary`, `analyze_patch`, `output_results`
- Cache location (patchset): `output/lkml/<{message-id}>/patchset/`
- Cache location (discussion): `output/lkml/<{message-id}>/discussion/`
- Uses b4 tool for patch/discussion downloads

## ANTI-PATTERNS

- `summary: str = "TODO"` default value (gets replaced at runtime)
- Hardcoded test data in shell scripts

## UNIQUE STYLES

- Bilingual comments (English structure, Chinese domain logic)
- sys.path.append() for parent directory access
- Verbose levels control progress bars and detailed logs
