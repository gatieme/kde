# RSS Agent

## 项目介绍

RSS Agent 是一个基于 LangGraph 开发的智能 RSS 分析工具，用于自动获取、分析和总结 LWN 和 Phoronix 的技术文章。

## 项目架构

### 整体架构图

![RSS Agent Architecture](../diagrams/rss-agent.svg)

**手绘风格架构图**：

手绘风格架构图：

![Hand-drawn RSS Agent](diagrams/rss-agent.excalidraw.svg)

要查看可编辑的 Excalidraw 原始文件，请打开：

1. 访问 https://excalidraw.com
2. 点击 "Open" 或拖放文件
3. 或使用 Excalidraw VS Code 扩展

**ASCII 架构图**：

```
+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                                                                              "RSS Agent Workflow"                                                                                                                                                                                               |

|                                                                                                                                                                                                                                                                                                                                                                                                                 |
|                                                                                                                                                                                                                                                                                                                                                                                                                 |
| +----------------------------------------------------------------------------------------------------------+     +------------------------------------------------+     +---------------------------------------------------------+     +-----------------------------------------------------+     +-----------------------------------------------------+     +---------------------------------------------+ |   +-------+
| |                                                                                                          |     |                                                |     |                                                         |     |                                                     |     |                                                     |     |                                             | |   |       |
| |                          "detect_protection                                                                 |---->| "fetch_rss_feeds                             |---->| "fetch_article_content                         |---->| "analyze_articles                             |---->| "generate_summaries                          |---->| "output_results                             |---->| Cache |
| |                           Cloudflare, Turnstile, CAPTCHA"                          |     |   feedparser, multi-source"                 |     |   requests, httpx, Playwright"              |     |   kernel keywords, patch links"            |     |   AI summary, classification                |     |   Markdown format output"                   |     |                                             | |   |       |
| |                                                                                                          |     |                                                |     |                                                         |     |                                                     |     |                                                     |     |                                             | |   |       |
| +----------------------------------------------------------------------------------------------------------+     +------------------------------------------------+     +---------------------------------------------------------+     +-----------------------------------------------------+     +-----------------------------------------------------+     +---------------------------------------------+ |   +-------+
|                                                                                                                                                                                                      |                                                                                                                                                                                                          |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

|                                                                                                                                                                                                        |
+--------------------------------------------------------------------------------------------------------------+                                                                                       |
|                                            "Anti-Crawler Bypass"                                             |                                                                                       |
| +----------------------------------------------------------------------------------------------------------+ |                                                                                       |                                  +-----------------------------------------------------+
| |                                                                                                          | |                                                                                       |                                  |                                                     |
| | "Real browser fingerprint                                                                              | |                                                                                       +--------------------------------->|                     AntiCrawler                     |
| |  Mouse scroll simulation                                                                               | |                                                                                                                          |                                                     |
| |  Cookie localStorage                                                                                 | |                                                                                                                          +-----------------------------------------------------+
| |  Multi-step navigation"                                                                                | |
| |                                                                                                          | |
|+--------------------------------------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------------------------------------+
|                                                "Disk Cache"                                                  |
| +----------------------------------------------------------------------------------------------------------+ |
| |                                                                                                          | |
| |                         "output/rss/<hash-id>.txt                                                              | |
| |                          MD5 hash of article link"                                                              | |
| |                                                                                                          | |
| +----------------------------------------------------------------------------------------------------------+ |
|                                                                                                              |
+--------------------------------------------------------------------------------------------------------------+
```

### 核心组件

```
rss/
├── rss_agent.py           # LangGraph 工作流（主 agent）
├── dual_rss_agent.py      # 双源分析 agent（旧版，使用 OpenAI API，已被 rss_agent.py 取代）
├── detect_anti_crawler.py # 反爬虫检测独立脚本
├── __init__.py            # 不存在（模块不可通过 import rss 直接导入）
└── README.md              # 本文件
```

## 工作流程

RSS Agent 的工作流程由以下几个主要步骤组成：

| 步骤 | 函数 | 说明 |
|:----:|:-----|:-----|
| 1 | detect_protection | 检测网站的反爬虫机制（Cloudflare、Turnstile） |
| 2 | fetch_rss_feeds | 获取 RSS 订阅内容 |
| 3 | fetch_article_content | 获取文章完整内容 |
| 4 | analyze_articles | 分析文章内容，检测是否涉及 Linux 内核 |
| 5 | generate_summaries | 使用 AI 生成文章摘要 |
| 6 | output_results | 以 Markdown 格式输出分析结果 |

## 功能说明

### 主要功能

- **智能防爬虫检测** - 自动检测并选择最佳访问方式（Cloudflare、requests、httpx、Playwright）
- **Cloudflare Bypass** - 集成 Cloudflare SDK,支持 Browser Rendering API 绕过反爬虫
- **多 HTTP 后端** - 提供四种访问方式: Cloudflare API、requests、httpx、Playwright 真实浏览器
- **多源支持** - 支持 Phoronix 和 LWN 两个技术新闻源
- **内核识别** - 自动识别涉及 Linux 内核的文章
- **补丁链接提取** - 提取邮件列表中的补丁相关链接
- **AI 摘要生成** - 使用 ModelScope Qwen3-235B-A22B 模型生成高质量摘要
- **灵活配置** - 支持命令行参数自定义
- **进度条显示** - 在 verbose 模式下显示操作进度
- **详细日志控制** - 通过 verbose 级别控制日志输出的详细程度
- **磁盘缓存** - 文章内容自动缓存到 `output/rss/` 目录

### 技术实现

- **状态管理** - 使用 LangGraph 实现状态管理和工作流
- **反爬虫绕过** - 四层防御机制:
  - **Cloudflare API** - 使用 Cloudflare SDK 和 Browser Rendering API
  - **requests** - 标准 HTTP 请求库,配合优化的 Headers
  - **httpx** - 现代 HTTP 客户端,支持 HTTP/2
  - **Playwright** - 真实浏览器模拟,支持 JavaScript 执行、Cookie、LocalStorage
- **多 HTTP 后端** - 自动检测和选择最佳访问方式，提供四种后端：
  - **`fetch_with_cloudflare`** - Cloudflare Browser Rendering API，需配置 `CLOUDFLARE_API_KEY`，通过 Cloudflare Workers 在边缘节点渲染页面，绕过 Cloudflare 自身的反爬虫保护
  - **`fetch_with_requests`** - 标准 HTTP 请求，配合优化 Headers（User-Agent、Accept 等），适用于无反爬虫机制的站点
  - **`fetch_with_httpx`** - 现代 HTTP 客户端，支持 HTTP/2，异步友好，作为 requests 的升级替代
  - **`fetch_with_playwright`** - 真实浏览器模拟，支持 JavaScript 执行、Cookie、LocalStorage，具备反自动化检测伪装（UA/地理位置/时区），适用于 Cloudflare/Turnstile 保护的站点
- **内容解析** - 使用 feedparser 和 BeautifulSoup4 解析 RSS 和 HTML
- **模型推理** - 集成 ModelScope Qwen3-235B-A22B 模型进行摘要生成
- **结果展示** - 以 Markdown 格式展示分析结果
- **进度条实现** - 使用 tqdm 库实现进度条显示
- **日志控制** - 通过 verbose 级别参数控制日志输出
- **缓存系统** - 基于文章链接哈希的磁盘缓存,支持持久化存储

### 反爬虫检测脚本（detect_anti_crawler.py）

`detect_anti_crawler.py` 是一个独立的反爬虫检测脚本，用于探测目标站点的防护机制，决定后续应采用哪种 HTTP 后端。

**四层递进检测**：

| 层级 | 方式 | 说明 |
|:----:|:-----|:-----|
| 1 | 基础 HTTP 请求 | 资源路径直连，不携带任何特殊 Header，测试站点是否裸露可访问 |
| 2 | 带 UA 的 HTTP 请求 | 添加标准浏览器 User-Agent，模拟普通浏览器访问 |
| 3 | 完整浏览器头 HTTP 请求 | 模拟完整浏览器请求头（Accept、Accept-Language、Referer 等），接近真实浏览器指纹 |
| 4 | Playwright 浏览器请求 | 使用真实浏览器发起请求，支持 JavaScript 执行，最接近人类用户行为 |

**检测标志**：

- **Cloudflare 防护** - 响应中包含 Cloudflare 特征（如 `cf-ray` Header、Cloudflare 错误页）
- **Turnstile 验证** - 页面中包含 Turnstile CAPTCHA 验证组件
- **"verifying you are human"** - 页面中出现人机验证文本，标志站点有强反自动化机制

### 旧版双源分析 Agent（dual_rss_agent.py）

`dual_rss_agent.py` 是早期版本的双源分析 agent，使用 OpenAI API 进行摘要生成。该文件已被基于 LangGraph 和 ModelScope 的 `rss_agent.py` 完全取代，保留仅作参考。

**与当前 rss_agent.py 的主要差异**：

| 特性 | dual_rss_agent.py（旧版） | rss_agent.py（当前） |
|------|--------------------------|---------------------|
| 工作流引擎 | 无（线性流程） | LangGraph StateGraph |
| 模型 API | OpenAI API | ModelScope Qwen3-235B-A22B |
| 状态管理 | 函数参数传递 | AgentState dataclass |
| 反爬虫处理 | 无 | 四层检测 + 四种 HTTP 后端 |

### 状态类定义

```python
@dataclass
class AgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    articles: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    protection_info: Dict[str, Any] = field(default_factory=dict)
    work_dir: str = ""
```

## 使用说明

> **注意**：`--level` 参数在 RSS 模块中用于**限制分析的文章数量**（而非分析级别），等同于 `--max-articles`。例如 `--level 5` 表示只分析 5 篇文章。

### 通过 kde.py 调用

RSS Agent 主要通过 kde.py 进行调用，支持以下命令格式：

#### 分析 Phoronix 文章（默认 3 篇）

```bash
python3 ../kde.py --rss phoronix
```

#### 分析 LWN 文章，限制 5 篇

```bash
python3 ../kde.py --rss lwn --level 5
```

#### 分析 Phoronix 文章，显示进度条

```bash
python3 ../kde.py --rss phoronix --level 5 -v
```

#### 分析 Phoronix 文章，显示最详细的日志

```bash
python3 ../kde.py --rss phoronix --level 5 -vvv
```

#### 分析所有源

```bash
python3 ../kde.py --rss
```

### 直接调用

也可以直接调用 rss_agent.py 进行测试：

```bash
# 获取所有源的所有文章
python3 rss_agent.py --resource Phoronix LWN

# 只获取 Phoronix 的文章
python3 rss_agent.py --resource Phoronix

# 只获取 LWN 的文章
python3 rss_agent.py --resource LWN

# 限制获取的文章数量
python3 rss_agent.py --max-articles 5

# 组合使用
python3 rss_agent.py --resource Phoronix --max-articles 10
```

### 参数说明

| 参数 | 短参数 | 说明 | 可选值 | 默认值 |
|------|--------|------|--------|--------|
| `--resource` | `-r` | 指定 RSS 源 | Phoronix, LWN | Phoronix, LWN |
| `--max-articles` | `-n` | 限制获取的文章数量 | 整数 | 无限制默认 3 |
| `-v, --verbose` | `-v` | 详细模式，显示进度条和详细日志 | 多次使用增加详细程度 | 0 |

## 依赖关系

### 内部依赖

- **model/model_infer.py** - 模型推理实现
- **model/model_request.py** - 模型请求构建
- **utils/format_text_for_markdown.py** - 文本格式化工具

### 外部依赖

- **langgraph** - 用于构建状态管理和工作流
- **feedparser** - 用于 RSS 解析
- **requests/httpx** - 用于 HTTP 请求
- **BeautifulSoup4** - 用于 HTML 解析
- **Playwright** - 用于浏览器自动化和反爬虫绕过
- **tqdm** - 用于显示进度条

## 缓存机制

文章内容会自动缓存到 `output/rss/` 目录：

```
output/rss/
└── {hash-id}.txt   # 基于文章链接的 MD5 哈希

### 缓存特性

- **自动创建** - 缓存目录和文件自动创建
- **持久化存储** - 缓存文件持久化，可重复使用
- **哈希命名** - 基于文章链接的 MD5 哈希命名，避免重复
- **元数据包含** - 缓存文件包含标题、链接、来源、时间等元数据
- **清理方便** - 使用 `git clean -fdX` 可以清理所有缓存

### 缓存文件格式

```
标题: {article_title}
链接: {article_link}
来源: {article_source}
时间: {published_date}

{separator}

{article_content}
```

## 注意事项

1. **网络连接** - 确保网络连接正常，能够访问 Phoronix 和 LWN
2. **API 配置** - 确保 ModelScope API 密钥正确配置（`OPENAI_API_KEY`）
3. **Cloudflare API 配置** - 如需使用 Cloudflare Bypass,需配置以下环境变量:
   - `CLOUDFLARE_API_KEY` - Cloudflare API Token 或 Global API Key
   - `CLOUDFLARE_EMAIL` - Cloudflare Email (如使用 Global API Key)
   - `CLOUDFLARE_ACCOUNT_ID` - Cloudflare Account ID (可选)
4. **Playwright 浏览器** - 如需使用 Playwright 真实浏览器模拟,需安装浏览器:
   ```bash
   playwright install
   ```
5. **防爬虫限制** - 某些网站可能限制自动化访问，建议合理设置请求间隔
6. **文章数量** - 大量文章获取可能需要较长时间，建议使用 `--max-articles` 限制数量
7. **缓存管理** - 文章内容会自动缓存到磁盘，重复运行时会使用缓存

## Cloudflare Bypass 配置

### 使用 Cloudflare API Token (推荐)

```bash
# 在 .env 文件中添加:
CLOUDFLARE_API_KEY=your-cloudflare-api-token
```

### 使用 Global API Key

```bash
# 在 .env 文件中添加:
CLOUDFLARE_API_KEY=your-global-api-key
CLOUDFLARE_EMAIL=your-email@example.com
```

### 配置说明

- **API Token** - 推荐,安全性更高,支持细粒度权限控制
- **Global API Key** - 传统方式,需要 Email + API Key 组合
- **Browser Rendering API** - 需要 Cloudflare Workers 或特殊订阅支持

## 代码规范

### 命名约定

- **函数**: `snake_case` (例如：`fetch_rss_feeds`, `analyze_articles`)
- **类**: `CamelCase` (例如：`AgentState`)
- **常量**: `UPPER_SNAKE_CASE`

### 注释风格

- **双语注释**: 英文用于代码结构，中文用于领域逻辑

## 扩展计划

### 功能扩展

- 扩展支持的 RSS 源（更多技术网站）
- 增强文章分类和标签功能
- 添加文章去重和相似度检测
- 支持自定义摘要模板

### 性能优化

- 优化文章下载和解析速度
- 改进模型推理效率
- 增强缓存机制（TTL、LRU）
- 支持并发下载多篇文章

### 用户体验

- 添加更多命令行选项
- 提供更详细的输出格式
- 支持结果导出为不同格式
- 增强进度条和日志的用户体验

## 许可证

MIT License
