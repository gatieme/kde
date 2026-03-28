# LKML Agent

## 项目介绍

LKML Agent 是一个专门用于分析 Linux 内核邮件列表（LKML）补丁的智能工具，使用 LangGraph 实现状态管理和工作流，能够自动下载、解析和分析指定的 LKML 补丁。

## 项目架构

### 整体架构图

![LKML Agent Architecture](../diagrams/lkml-agent.svg)

**手绘风格架构图**：

手绘风格架构图：

![Hand-drawn LKML Agent](diagrams/lkml-agent.excalidraw.svg)

要查看可编辑的 Excalidraw 原始文件，请打开：

1. 访问 https://excalidraw.com
2. 点击 "Open" 或拖放文件
3. 或使用 Excalidraw VS Code 扩展

**ASCII 架构图**：

```
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                               "LKML Agent Workflow"                                                                                                                                |
|                                                                                                                                                                                                                    |
|                                                                                                                                                                                                                    |
| +------------------------------------------------+     +-------------------------------------------------+     +---------------------------------------------------+     +----------------------------------------------------+     +--------------------------------------------+ |   +-------+
| |                                                |     |                                                 |     |                                                   |     |                                                    |     |                                            | |   |       |
| | "fetch_patch                                 |---->| "parse_patch                                |---->| "generate_summary                             |---->| "analyze_patch                               |---->| "output_results                             |---->| Cache |
| |  b4 am, progress bar, timeout"             |     |  extract author, date, subject"         |     |  AI summary, 300 char limit"             |     |  AI analysis, detail level only"          |     |  Markdown table output"                   |     |                                            | |   |       |
| |                                                |     |                                                 |     |                                                   |     |                                                    |     |                                            | |   |       |
| +------------------------------------------------+     +-------------------------------------------------+     +---------------------------------------------------+     +----------------------------------------------------+     +--------------------------------------------+ |   +-------+
|                                                                                                                                                                                                                    |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+----------------------------------------------------+
|                   "Disk Cache"                     |
| +------------------------------------------------+ |
| |                                                | |
| |  "output/lkml/<message-id>/                  | |
| |   .cover .mbx"                               | |
| |                                                | |
| +------------------------------------------------+ |
|                                                    |
+----------------------------------------------------+
```

### 核心组件

```
lkml/
├── lkml_agent.py       # LangGraph 工作流实现
├── lkml.py             # 核心补丁分析器（遗留）
├── __init__.py         # 模块初始化
├── get_b4_series.sh    # B4 系列获取辅助脚本
└── README.md           # 本文件
```

## 工作流程

LKML Agent 的工作流程由以下几个主要步骤组成：

| 步骤 | 函数 | 说明 |
|:----:|:-----|:-----|
| 1 | fetch_patch | 使用 b4 工具下载指定 message-id 的补丁 |
| 2 | parse_patch | 提取补丁的基本信息（作者、日期、主题、版本等） |
| 3 | generate_summary | 对补丁内容进行 AI 摘要生成 |
| 4 | analyze_patch | 在 detail 级别下对补丁进行深入分析 |
| 5 | output_results | 根据级别参数输出分析结果 |

## 功能说明

### 主要功能

- **自动下载补丁** - 使用 b4 工具从 LKML 自动下载指定 message-id 的补丁
- **信息提取** - 解析补丁的基本信息，包括作者、日期、主题、版本等
- **智能分析** - 使用模型对补丁内容进行分析，生成摘要和详细分析
- **多级分析** - 支持 simple 和 detail 两个级别的分析深度
- **结果输出** - 以表格形式展示分析结果，包括补丁的基本信息和分析内容
- **进度条显示** - 在 verbose 模式下显示补丁下载和分析的进度
- **详细日志控制** - 通过 verbose 级别控制日志输出的详细程度
- **超时处理** - 检测并处理 b4 下载超时情况
- **磁盘缓存** - 自动缓存补丁文件到 `output/lkml/<message-id>/` 目录

### 技术实现

- **状态管理** - 使用 LangGraph 实现状态管理和工作流
- **补丁下载** - 调用 b4 工具下载补丁，支持进度监控和超时检测
- **信息解析** - 使用正则表达式解析补丁信息
- **模型推理** - 集成模型推理模块，对补丁内容进行分析
- **结果展示** - 以 Markdown 表格形式展示分析结果
- **进度条实现** - 使用 tqdm 库实现进度条显示
- **日志控制** - 通过 verbose 级别参数控制日志输出
- **缓存系统** - 自动创建缓存目录并持久化存储补丁文件

### 状态类定义

```python
@dataclass
class LKMLAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    lkml_id: str = ""           # LKML message-id
    level: str = "simple"       # 分析级别
    work_dir: str = ""           # 工作目录
    cover_file: str = ""         # Cover 文件路径
    mbx_file: str = ""           # MailBox 文件路径
    date: str = ""               # 补丁日期
    author: str = ""             # 作者
    email: str = ""              # 邮箱
    version: str = ""            # 版本号
    subject: str = ""            # 主题
    web_url: str = ""            # Web URL
    archive_url: str = ""        # 归档 URL
    current: str = ""            # 当前补丁编号
    total: str = ""              # 总补丁数
    summary: str = "TODO"        # 摘要
    content: str = ""            # 补丁内容
    analysis: str = ""           # 详细分析
    verbose: int = 0             # 详细级别
```

## 使用说明

### 通过 kde.py 调用

LKML Agent 主要通过 kde.py 进行调用，支持以下命令格式：

#### 简单模式（仅生成摘要）

```bash
python3 ../kde.py --lkml <message-id> --level simple
```

#### 详细模式（生成摘要并进行深入分析）

```bash
python3 ../kde.py --lkml <message-id> --level detail
```

#### 详细模式（显示进度条）

```bash
python3 ../kde.py --lkml <message-id> --level detail -v
```

#### 详细模式（显示最详细的日志）

```bash
python3 ../kde.py --lkml <message-id> --level detail -vvv
```

### 直接调用

也可以直接调用 lkml_agent.py 进行测试：

```bash
python3 lkml_agent.py --message_id=<message-id> --level=simple
python3 lkml_agent.py --message_id=<message-id> --level=detail
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `<message-id>` | LKML 补丁的 message-id | - | 必填 |
| `simple|detail` | 分析级别 | simple, detail | simple |
| `-v, --verbose` | 详细模式，显示进度条和详细日志 | 多次使用增加详细程度 | 0 |

## 依赖关系

### 内部依赖

- **model/model_infer.py** - 模型推理实现
- **model/model_request.py** - 模型请求构建
- **utils/format_text_for_markdown.py** - 文本格式化工具
- **utils/process_monitor.py** - 进程监控工具

### 外部依赖

- **b4** - 用于下载 LKML 补丁
- **langgraph** - 用于构建状态管理和工作流
- **tqdm** - 用于显示进度条

## 示例

### 分析 LKML 补丁（简单模式）

```bash
python3 ../kde.py --lkml 20260122161647.142704-2-realwujing@gmail.com --level simple
```

### 分析 LKML 补丁（详细模式，显示进度条）

```bash
python3 ../kde.py --lkml 20260122161647.142704-2-realwujing@gmail.com --level detail -v
```

## 输出示例

### 简单模式输出

```
| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:---:|:----:|:---:|:----:|:---------:|:----:|
| 2026/01/22 | Real Wujing <realwujing@gmail.com> | [PATCH v1] Add new feature to Linux kernel | 这是一个关于在 Linux 内核中添加新特性的补丁，主要包含... | v1 ☐☑✓ | [LORE](https://lore.kernel.org/all/20260122161647.142704-2-realwujing@gmail.com) |
```

### 详细模式输出

在简单模式输出的基础上，还会包含对补丁的详细分析内容。

### 详细模式输出（带进度条）

当使用 `-v` 参数时，会显示补丁下载和分析的进度条，以及更详细的日志信息。

## 缓存机制

补丁下载后会自动缓存到 `output/lkml/<message-id>/` 目录：

```
output/lkml/
└── <message-id>/
    ├── <message-id>.cover   # Cover 文件
    └── <message-id>.mbx     # MailBox 文件
```

### 缓存特性

- **自动创建** - 缓存目录和文件自动创建
- **持久化存储** - 缓存文件持久化，可重复使用
- **按消息 ID 分组** - 每个补丁独立存储在各自的目录中
- **清理方便** - 使用 `git clean -fdX` 可以清理所有缓存

使用 `git clean -fdX` 可以清理所有缓存。

## 代码规范

### 命名约定

- **函数**: `snake_case` (例如：`fetch_patch`, `parse_patch`)
- **类**: `CamelCase` (例如：`LKMLAgentState`)
- **常量**: `UPPER_SNAKE_CASE`

### 注释风格

- **双语注释**: 英文用于代码结构，中文用于领域逻辑

## 扩展计划

### 功能扩展

- 添加对补丁系列的支持
- 增强补丁分析的深度和准确性
- 添加对补丁状态的跟踪（是否已合入主线）

### 性能优化

- 优化补丁下载和解析速度
- 改进模型推理效率
- 增强缓存机制（TTL、LRU）

### 用户体验

- 添加更多命令行选项
- 提供更详细的输出格式
- 支持结果导出为不同格式
- 增强进度条和日志的用户体验

## 许可证

MIT License
