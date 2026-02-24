# Model Inference Module

**Generated:** 2026-02-24

## OVERVIEW

AI model integration layer using ModelScope Qwen3-235B-A22B for text analysis and inference.

## STRUCTURE

```
model/
├── model_infer.py    # ModelScope OpenAI-compatible wrapper
├── model_request.py  # Request builder
├── model_api.py       # API utilities
└── __init__.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Model client | model_infer.py:8-25 | OpenAI client with ModelScope base URL |
| Inference method | model_infer.py:27+ | Streaming with tqdm progress bar |
| Model configuration| model_infer.py:22 | Qwen3-235B-A22B model ID |
| Request builder | model_request.py | ModelRequest class for prompt building |

## CONVENTIONS

- Model: Qwen3-235B-A22B via ModelScope API
- Temperature: 0 (greedy decoding)
- Streaming enabled with tqdm progress bars
- Verbose levels control progress display

## ANTI-PATTERNS

- Hardcoded API key in model_infer.py:11
- No environment variable fallback for model ID

## UNIQUE STYLES

- ModelScope API with OpenAI-compatible client
- Streaming inference with progress visualization
- Thinking control via extra_body parameter
