# Utils Module

## 项目介绍

Utils Module 是 KDE 项目的跨模块工具集，提供文本格式化、HTTP 请求和进程监控功能。所有 agent（lkml、rss、cgit、patchwork）均依赖此模块完成 Markdown 格式化、网页内容抓取和子进程管理等公共任务。

## 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Utils Module                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ text_formatter   │  │ http_fetcher     │            │
│  │ 4步格式化管道    │  │ 3种HTTP后端      │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                         │
│  ┌──────────────────┐                                   │
│  │ process_monitor  │                                   │
│  │ 子进程监控+超时  │                                   │
│  └──────────────────┘                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

```
utils/
├── __init__.py            # 模块初始化，导出10个公共函数
├── text_formatter.py      # Markdown文本格式化（104行）
├── http_fetcher.py        # HTTP请求封装（129行）
├── process_monitor.py     # 进程监控（88行）
├── AGENTS.md              # 模块知识库
└── README.md              # 本文件
```

## 功能说明

### text_formatter.py - 文本格式化管道

`format_text_for_markdown(text)` 实现 4 步格式化管道，将 AI 模型输出转换为 Markdown 表格兼容格式：

| 步骤 | 函数 | 说明 |
|:----:|:-----|:-----|
| 1 | `chinese_to_english_punctuation(text)` | 中文标点→英文标点（逗号、句号、括号等） |
| 2 | `clean_bracket_spaces(text)` | 清除括号内空格（`( )`→`()`），修复 AI 输出瑕疵 |
| 3 | `add_space_after_punctuation(text)` | 标点后加空格（上下文感知：括号不加、标识符内点不加） |
| 4 | `replace_newline_with_br(text)` | `\n`→`<br>`，连续换行合并为单个 `<br>` |

**上下文感知逻辑**：
- 括号标点 `()[]<>`：不加空格
- 标识符内的点（邮箱 `user@host.dom`、版本号 `v1.2.3`）：不加空格
- 终止标点（逗号、句号等）：后置空格

**`clean_email_subject(subject)`** — 剥离邮件标题前缀，保留实质内容：

| 输入 | 输出 |
|:-----|:-----|
| `Re: [PATCH 1/6] sched/proxy: Remove...` | `[PATCH 1/6] sched/proxy: Remove...` |
| `Re: Re: [PATCH v2] mm: fix` | `[PATCH v2] mm: fix` |
| `Fwd: some discussion topic` | `some discussion topic` |

> `[PATCH...]` 前缀是补丁标题的实质内容，不应剥离；`Re:/Fwd:` 只是回复标记，应去除。

### http_fetcher.py - HTTP 请求封装

`fetch_article_with_method(article, method, verbose)` 按 method 分发到三种 HTTP 后端：

| 后端 | 函数 | 特点 |
|:----:|:-----|:-----|
| `requests` | `_fetch_with_requests` | 标准 HTTP 请求，模拟浏览器 User-Agent，15 秒超时 |
| `httpx` | `_fetch_with_httpx` | 现代 HTTP 客户端，自动跟随重定向，15 秒超时 |
| `playwright` | `_fetch_with_playwright` | Playwright 真实浏览器模拟，反爬虫能力强，30 秒超时 |

**`_extract_article_body(soup)`** — 从 BeautifulSoup 对象提取正文，尝试 4 种 CSS 选择器（按优先级）：

| 优先级 | 选择器 | 说明 |
|:------:|:-------|:-----|
| 1 | `div.content` (class) | 最常见的文章容器 |
| 2 | `div#content` (id) | ID 选择器兜底 |
| 3 | `article` | HTML5 语义标签 |
| 4 | `main` | HTML5 语义标签兜底 |

**Playwright 反爬虫策略**：
- 隐藏自动化特征（`--disable-blink-features=AutomationControlled`）
- 模拟真实浏览器环境（User-Agent、地理位置、语言、时区）
- 自动检测验证码页面并等待

### process_monitor.py - 进程监控

`monitor_process_with_progress(process, pbar, verbose)` — 监控子进程 stdout 输出并更新 tqdm 进度条：

- **进度提取**：从输出中解析百分比（`(\d+)%`）更新进度条
- **增量更新**：识别 `Download`/`Fetch`/`Applying` 等关键词进行微步更新
- **超时机制**：连续 30 秒（6×5 秒）无输出 → 调用 `handle_process_timeout` 终止进程

**`handle_process_timeout(process, verbose)`** — 进程超时处理：

1. 检查进程是否已自行退出（`poll()`）
2. 若仍在运行，打印警告并调用 `terminate()` 终止
3. 等待 5 秒后确认终止

### __init__.py 导出列表

模块初始化文件导出 10 个公共函数，分为三组：

| 分组 | 函数 | 来源文件 |
|:----:|:-----|:---------|
| 文本格式化(5) | `chinese_to_english_punctuation` | text_formatter.py |
| | `add_space_after_punctuation` | text_formatter.py |
| | `replace_newline_with_br` | text_formatter.py |
| | `clean_email_subject` | text_formatter.py |
| | `format_text_for_markdown` | text_formatter.py |
| 进程监控(2) | `monitor_process_with_progress` | process_monitor.py |
| | `handle_process_timeout` | process_monitor.py |
| HTTP获取(1) | `fetch_article_with_method` | http_fetcher.py |

> 注意：`clean_bracket_spaces` 是内部步骤函数，未在 `__init__.py` 中导出。

## 使用说明

### 文本格式化

```python
from utils import format_text_for_markdown, clean_email_subject

# 4 步格式化管道
text = "这是一个测试，包含中文标点。换行内容\n第二行"
formatted = format_text_for_markdown(text)
# → "这是一个测试, 包含英文标点. 换行内容<br>第二行"

# 清理邮件标题
subject = "Re: [PATCH 1/6] sched/proxy: Remove proxy"
cleaned = clean_email_subject(subject)
# → "[PATCH 1/6] sched/proxy: Remove proxy"
```

### HTTP 请求

```python
from utils import fetch_article_with_method

article = {"link": "https://example.com/article", "title": "Test"}

# 使用 requests（标准模式）
content = fetch_article_with_method(article, "requests", verbose=1)

# 使用 httpx（现代 HTTP 客户端）
content = fetch_article_with_method(article, "httpx", verbose=1)

# 使用 playwright（反爬虫模式）
content = fetch_article_with_method(article, "playwright", verbose=1)
```

### 进程监控

```python
from utils import monitor_process_with_progress, handle_process_timeout
from tqdm import tqdm

process = subprocess.Popen(["cmd"], stdout=subprocess.PIPE, text=True)
pbar = tqdm(total=100, desc="任务进度")

# 监控子进程输出并更新进度条
monitor_process_with_progress(process, pbar, verbose=1)
```

## 依赖关系

### 外部依赖

| 依赖 | 用途 | 使用模块 |
|:-----|:-----|:---------|
| **requests** | HTTP 请求 | http_fetcher.py |
| **httpx** | 现代 HTTP 客户端 | http_fetcher.py |
| **playwright** | 真实浏览器模拟 | http_fetcher.py |
| **tqdm** | 进度条显示 | process_monitor.py |
| **beautifulsoup4** | HTML 解析 | http_fetcher.py |

## 代码规范

### 命名约定

- **函数**: `snake_case` (例如：`chinese_to_english_punctuation`, `fetch_article_with_method`)
- **私有函数**: `_snake_case` 前缀 (例如：`_fetch_with_requests`, `_extract_article_body`)

### 注释风格

- **双语注释**: 英文用于代码结构，中文用于领域逻辑
- **纯函数优先**: 无副作用，确定性输出

## 扩展计划

### 功能扩展

- 添加更多格式化规则（如 URL 自动链接、代码块处理）
- 支持更多 HTTP 方法（如 POST、PUT）
- 添加 HTTP 请求缓存机制

### 性能优化

- 改进超时机制（从固定 30 秒改为可配置参数）
- 优化 Playwright 启动性能
- 添加异步 HTTP 请求支持

### 用户体验

- 统一错误处理和日志格式
- 添加更详细的 verbose 输出
- 支持自定义 CSS 选择器列表

## 许可证

MIT License
