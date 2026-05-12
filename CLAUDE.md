# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目目录结构

**重要**：所有源代码已移动到 `src/` 目录下。

```
kde/
├── src/                    # 源代码目录（所有 Python 代码）
│   ├── kde.py             # 主入口，CLI 命令行接口
│   ├── lkml/              # LKML 补丁分析模块
│   │   ├── lkml_agent.py  # LangGraph 工作流
│   │   └── lkml.py        # 核心补丁分析器
│   ├── rss/               # RSS 文章分析模块
│   │   ├── rss_agent.py   # LangGraph 工作流
│   │   └── detect_anti_crawler.py
│   ├── cgit/              # CGit commit 分析模块
│   │   └── cgit_agent.py # LangGraph 工作流
│   ├── model/             # AI 模型集成
│   │   ├── model_infer.py # ModelScope 推理封装
│   │   └── model_request.py # 请求构建器
│   ├── utils/             # 工具模块
│   ├── test/              # 测试套件
│   └── output/            # 缓存目录
└── patchwork/             # PatchWork 集成脚本
```

## 常用命令

**注意**：所有命令需要在项目根目录下执行，因为 `src/kde.py` 会正确处理路径。

### 分析 LKML 补丁

```bash
# 简单模式（仅摘要）
python src/kde.py --lkml <message-id> --level simple

# 详细模式（摘要 + 深度分析）
python src/kde.py --lkml <message-id> --level detail

# 带进度条
python src/kde.py --lkml <message-id> --level detail -v

# 最详细日志
python src/kde.py --lkml <message-id> --level detail -vvv
```

### 分析 CGit Commit

```bash
# 简单模式
python src/kde.py --cgit <commit-id> --level simple

# 详细模式
python src/kde.py --cgit <commit-id> --level detail -v
```

### 分析 RSS 文章

```bash
# 所有源
python src/kde.py --rss

# 特定源
python src/kde.py --rss phoronix
python src/kde.py --rss lwn

# 限制文章数（通过 --level 参数）
python src/kde.py --rss phoronix --level 5
```

### 运行测试

```bash
cd src/test
./test_all.sh

# 专项测试
./test_lkml.sh
./test_cgit.sh
./test_rss.sh
./test_verbose.sh
```

## 核心架构

### LangGraph 状态机工作流

项目使用 LangGraph StateGraph 构建三个主要 Agent：

- **LKML Agent** (`src/lkml/lkml_agent.py`) - 分析 Linux 内核邮件列表补丁
- **CGit Agent** (`src/cgit/cgit_agent.py`) - 分析 Linux 内核 Git 提交
- **RSS Agent** (`src/rss/rss_agent.py`) - 分析技术文章（Phoronix、LWN）

每个 Agent 使用 `@dataclass` 定义状态类（如 `LKMLAgentState`），通过 `StateGraph` 定义节点和边，状态通过 `add_messages` 自动累积。

### 模型推理模块

- **ModelInference** (`src/model/model_infer.py`) - 封装 ModelScope API 调用
  - 使用 OpenAI 兼容客户端连接 ModelScope
  - 支持流式推理和 tqdm 进度条
  - 温度固定为 0（贪心解码）
  - 可通过 `extra_body` 控制思考过程

- **ModelRequest** (`src/model/model_request.py`) - 请求构建器
  - 提供统一的消息构建接口
  - 支持不同分析类型的 prompt 模板

### 缓存系统

所有缓存统一存储在 `src/output/` 目录：

- `src/output/lkml/<message-id>/` - LKML 补丁（.cover, .mbx 文件）
- `src/output/rss/<hash-id>.txt` - RSS 文章（基于 URL 的 MD5 哈希）
- `src/output/cgit/<commit-id>/` - CGit commit 文件

清理缓存：`git clean -fdX src/output/`

## Verbose 级别

| 级别 | 参数 | 行为 |
|------|------|------|
| 0 | 无 | 仅简洁状态消息 |
| 1 | `-v` | 进度条和基本日志 |
| 2 | `-vv` | 详细日志和处理信息 |
| 3 | `-vvv` | 最详细调试信息，包括所有命令输出 |

## 环境配置

项目使用 `.env` 文件配置环境变量（使用 python-dotenv 加载）：

```bash
# ModelScope API Key（必需）
OPENAI_API_KEY=your-modelscope-api-key
```

**重要**：不要在代码中硬编码 API 密钥，始终使用 `os.getenv()` 从环境变量读取。

## 代码规范

### 命名约定

- 函数：`snake_case` (如 `fetch_patch`, `parse_commit`)
- 类：`CamelCase` (如 `ModelInference`, `LKMLAgentState`)
- 状态类：`CamelCase` + `State` 后缀 (如 `LKMLAgentState`, `CGitAgentState`)
- 常量：`UPPER_SNAKE_CASE` (如 `ALL_RSS_SOURCES`, `KERNEL_KEYWORDS`)

### 导入模式

子模块导入父目录模块时使用相对路径：

```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model import ModelInference, ModelRequest
from utils import format_text_for_markdown
```

### 注释风格

- 代码结构注释：英文
- 领域逻辑注释：中文
- 文档字符串：中文

## 工具依赖

- `b4` - LKML 补丁下载
- `wget` - CGit commit 下载
- `playwright` - RSS 反爬虫绕过（需要 `playwright install`）

## 重要实现细节

### LKML Agent 工作流

1. **fetch_patch** - 使用 `b4 am` 下载补丁到 `src/output/lkml/<message-id>/`
2. **parse_patch** - 解析 .cover/.mbx 文件提取元数据
3. **generate_summary** - AI 生成摘要（300 字限制）
4. **analyze_patch** - 仅在 detail `level` 执行深度 AI 分析
5. **output_results** - Markdown 表格输出

### CGit Agent 工作流

1. **fetch_commit** - `wget` 从 git.kernel.org 下载 commit
2. **parse_commit** - 解析 commit 元数据
3. **analyze_commit** - AI 摘要和分析
4. **check_patchset** - 提取 Link 字段的 patchset 链接
5. **run_lkml_analysis** - 递归调用 LKML Agent 分析关联的 patchset
6. **output_results** - Markdown 表格输出

### RSS Agent 工作流

1. **detect_protection** - 检测 Cloudflare、Turnstile 等反爬虫机制
2. **fetch_rss_feeds** - 使用 feedparser 获取 RSS 订阅
3. **fetch_article_content** - 三种后端：requests → httpx → Playwright
4. **analyze_articles** - 识别内核关键词和补丁链接
5. **generate_summaries** - AI 生成摘要（内核文章详细，其他简洁）
6. **output_results** - Markdown 格式输出

### 反爬虫绕过

RSS Agent 使用多层策略绕过反爬虫：

- 真实浏览器指纹（Playwright）
- 鼠标移动和滚动模拟
- Cookie 和 localStorage 持久化
- 多步骤导航（Google → 目标）

## 项目特性

### 独特风格

- **双语文本注释** - 代码结构用英文，领域逻辑用中文
- **sys.path.append()** - 用于兄弟目录间的模块访问
- **LangGraph Agents** - 统一的工作流模式：fetch → parse → analyze → output
- **Shell 脚本测试** - 自定义测试框架，使用 bash 数组 + eval

### 项目约束

- 没有正式构建系统（无 setup.py、pyproject.toml、Makefile）
- 没有 CI/CD（无 .github/workflows）
- 没有 requirements.txt（依赖在 README 中列出）
- 部分目录缺少 __init__.py（cgit/、rss/、test/）

### 内存文件存储

项目使用 `.memory/` 目录存储会话记忆：

- `.memory/optimization/` - 优化相关记忆
- `.memory/implementation/` - 实现相关记忆
- `.memory/testing/` - 测试相关记忆
