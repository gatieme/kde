# CGit Agent

## 项目介绍

CGit Agent 是一个专门用于分析 Linux 内核 git commit 的智能工具，使用 LangGraph 实现状态管理和工作流，能够自动下载、解析和分析指定的 commit，并从 commit 中提取 patchset 链接进行关联分析。

## 项目架构

### 整体架构图

![CGit Agent Architecture](../diagrams/cgit/cgit-agent.svg)

**手绘风格架构图**：

手绘风格架构图：

![Hand-drawn CGit Agent](../diagrams/cgit/cgit-agent.excalidraw.svg)

要查看可编辑的 Excalidraw 原始文件，请打开：

1. 访问 https://excalidraw.com
2. 点击 "Open" 或拖放文件
3. 或使用 Excalidraw VS Code 扩展

**ASCII 架构图**：

```
+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                                     "CGit Agent Workflow"                                                                                                                                                      |
|                                                                                                                                                                                                                                                                                                                                |
|                                                                                                                                                                                                                                                                                                                                |
| +--------------------------------------------+     +--------------------------------------------------+     +----------------------------------------------+     +------------------------------------------+     +-------------------------------------------------------+     +--------------------------------------------+ |   +-------+
| |                                            |     |                                                  |     |                                              |     |                                          |     |                                                       |     |                                            | |   |       |
| |  "fetch_commit                             |---->| "parse_commit                                |---->| "analyze_commit                               |---->| "output_results                             |---->| "check_patchset                             |---->| "run_lkml_analysis                         |---->| Cache |
| |   wget, git.kernel.org"                  |     |   extract author, date, subject"         |     |   AI summary, AI analysis"                |     |   Markdown table output"                   |     |   三级回退提取 Link → Lore → patch"       |     |   提取 message-id, 递归 LKML Agent"     |     |                                            | |   |       |
| |                                            |     |                                                  |     |                                              |     |                                          |     |                                                       |     |                                            | |   |       |
| +--------------------------------------------+     +--------------------------------------------------+     +----------------------------------------------+     +------------------------------------------+     +-------------------------------------------------------+     +--------------------------------------------+ |   +-------+
|                                                                                                                                                                               |                              ↑ has_patchset=False                          |
+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------→ 跳过，直接 END ------------------------------|
                                                                                                                                                                                                                                                                                                                                |
                                                                                                                                                                               +------------------------------------------------+
                                                                                                                                                                               |               "条件分支说明"                    |
                                                                                                                                                                               | check_patchset → has_patchset?                  |
                                                                                                                                                                               |   True  → run_lkml_analysis → END               |
                                                                                                                                                                               |   False → 直接 END（跳过 run_lkml_analysis）    |
                                                                                                                                                                               +------------------------------------------------+

+------------------------------------------------+
|               "LKML Agent Call"                |
| +--------------------------------------------+ |
| |                                            | |
| |      "LKML Agent                            | |
| |       recursive call"                        | |
| |                                            | |
| +--------------------------------------------+ |
|                                                |
+------------------------------------------------+

+------------------------------------------------+
|                 "Disk Cache"                   |
| +--------------------------------------------+ |
| |                                            | |
| | "output/cgit/<commit-id>/                  | |
| |  commit file"                              | |
| |                                            | |
| +--------------------------------------------+ |
|                                                |
+------------------------------------------------+
```

### 核心组件

```
cgit/
├── __init__.py          # 包初始化（不存在）
├── cgit_agent.py        # LangGraph 工作流实现
├── get_cgit_patch.sh    # CGit patch 获取辅助脚本
└── README.md            # 本文件
```

## 工作流程

CGit Agent 的工作流程由以下几个主要步骤组成：

| 步骤 | 函数 | 说明 |
|:----:|:-----|:-----|
| 1 | fetch_commit | 从 cgit 下载指定 commit ID 的内容 |
| 2 | parse_commit | 提取 commit 的基本信息（作者、日期、主题等） |
| 3 | analyze_commit | 对 commit 内容进行分析，生成摘要 |
| 4 | output_results | 以 Markdown 表格形式输出分析结果 |
| 5 | check_patchset | 从 commit 中提取 patchset 链接（三级回退机制） |
| 6 | run_lkml_analysis | 使用 LKML Agent 分析关联的 patchset（条件执行） |

### check_patchset 三级回退机制

`check_patchset` 节点负责从 commit 内容中检测是否存在关联的 patchset 链接，采用三级回退策略：

| 回退级别 | 匹配目标 | 正则表达式 | 说明 |
|:--------:|:---------|:-----------|:-----|
| 第一级 | `Link:` 字段 | `Link:\s*(?:<)?(https?://[^>\s]+)(?:>)?` | 从 commit 内容中提取 `Link` 标签，支持带尖括号和不带尖括号两种格式 |
| 第二级 | Lore.kernel.org 链接 | `https?://lore\.kernel\.org/.*` | 将 Link 转换为 Lore 链接格式，直接匹配 lore.kernel.org 域名下的链接 |
| 第三级 | 其他补丁链接 | `https?://.*patch.*` | 从 Lore 链接提取其他补丁的 message-id，兜底匹配包含 "patch" 关键词的链接 |

- 如果三级均未匹配到 patchset 链接，`has_patchset` 设为 `False`，跳过后续 `run_lkml_analysis` 节点
- 匹配成功时，`patchset_link` 保存提取到的链接，`has_patchset` 设为 `True`

### run_lkml_analysis 详细说明

`run_lkml_analysis` 节点是 CGit Agent 与 LKML Agent 的集成点，负责从 patchset 链接中提取 message-id 并递归调用 `run_lkml_agent()` 分析关联的 patchset。

**message-id 提取策略**（按优先级尝试）：

| 优先级 | 链接格式 | 提取方式 | 示例 |
|:------:|:---------|:---------|:-----|
| 1 | Lore.kernel.org 链接 | `https?://lore\.kernel\.org/all/(.*)` | `https://lore.kernel.org/all/20250621235745.3994-1-atomlin@atomlin.co` → message-id = `20250621235745.3994-1-atomlin@atomlin.co` |
| 2 | patch.msgid.link 链接 | `https?://[^/]+/(.*)` | `https://patch.msgid.link/20260114130528.GB831285@noisy.programming.kicks-ass.net` → message-id = `20260114130528.GB831285@noisy.programming.kicks-ass.net` |
| 3 | 直接使用链接 | 无正则匹配 | 将完整链接作为 message-id 传入 `run_lkml_agent()` |

**条件执行逻辑**：
- 仅当 `has_patchset = True` 且 `patchset_link` 不为空时执行分析
- 如果无 patchset 链接，跳过该节点，直接结束工作流

## 功能说明

### 主要功能

- **自动下载 commit** - 从 cgit 自动下载指定 commit ID 的内容
- **信息提取** - 解析 commit 的基本信息，包括作者、日期、主题等
- **智能分析** - 使用模型对 commit 内容进行分析，生成摘要
- **patchset 关联** - 使用三级回退机制从 commit 中提取 patchset 链接，并递归调用 LKML Agent 进行关联分析
- **多级分析** - 支持 simple 和 detail 两个级别的分析深度
- **结果输出** - 以表格形式展示分析结果，包括 commit 的基本信息和分析内容
- **进度条显示** - 在 verbose 模式下显示 commit 下载和分析的进度
- **详细日志控制** - 通过 verbose 级别控制日志输出的详细程度
- **磁盘缓存** - 自动缓存 commit 文件到 `output/cgit/<commit-id>/` 目录

### 技术实现

- **状态管理** - 使用 LangGraph 实现状态管理和工作流
- **commit 下载** - 使用 wget 从 cgit 下载 commit 内容
- **信息解析** - 使用正则表达式解析 commit 信息
- **patchset 检测** - 使用三级回退正则表达式从 commit 中提取 patchset 链接（Link 字段 → Lore 链接 → 其他补丁链接），无 patchset 时跳过 LKML 分析节点
- **模型推理** - 集成模型推理模块，对 commit 内容进行分析
- **结果展示** - 以 Markdown 表格形式展示分析结果
- **进度条实现** - 使用 tqdm 库实现进度条显示
- **日志控制** - 通过 verbose 级别参数控制日志输出
- **缓存系统** - 自动创建缓存目录并持久化存储 commit 文件

### 状态类定义

```python
@dataclass
class CGitAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    commit_id: str = ""              # Commit ID
    level: str = "simple"            # 分析级别（simple / detail）
    work_dir: str = ""               # 工作目录（缓存路径）
    commit_file: str = ""            # Commit 文件路径
    date: str = ""                   # 日期（格式: YYYY/MM/DD）
    author: str = ""                 # 作者
    email: str = ""                  # 邮箱
    subject: str = ""                # 主题（已清理 Re:/Fwd:）
    web_url: str = ""                # Web URL（cgit 链接）
    content: str = ""                # Commit 原始内容
    summary: str = "TODO"            # AI 生成的摘要
    analysis: str = ""               # AI 详细分析（仅 detail 级别）
    patchset_link: str = ""          # Patchset 链接（从 check_patchset 提取）
    has_patchset: bool = False       # 是否存在 patchset 链接
    verbose: int = 0                 # 详细日志级别（0-3）
```

## 使用说明

### 通过 kde.py 调用

CGit Agent 主要通过 kde.py 进行调用，支持以下命令格式：

#### 简单模式（仅生成摘要）

```bash
python3 ../kde.py --cgit <commit-id> --level simple
```

#### 详细模式（生成摘要并进行深入分析）

```bash
python3 ../kde.py --cgit <commit-id> --level detail
```

#### 详细模式（显示进度条）

```bash
python3 ../kde.py --cgit <commit-id> --level detail -v
```

#### 详细模式（显示最详细的日志）

```bash
python3 ../kde.py --cgit <commit-id> --level detail -vvv
```

### 直接调用

也可以直接调用 cgit_agent.py 进行测试：

```bash
python3 cgit_agent.py --commit_id=<commit-id> --level=simple
python3 cgit_agent.py --commit_id=<commit-id> --level=detail
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `<commit-id>` | Git commit 的 ID | - | 必填 |
| `simple|detail` | 分析级别 | simple, detail | simple |
| `-v, --verbose` | 详细模式，显示进度条和详细日志 | 多次使用增加详细程度 | 0 |

## 依赖关系

### 内部依赖

- **model/model_infer.py** - 模型推理实现
- **model/model_request.py** - 模型请求构建
- **lkml/lkml_agent.py** - LKML Agent 实现，用于分析 patchset
- **utils/format_text_for_markdown.py** - 文本格式化工具
- **utils/process_monitor.py** - 进程监控工具

### 外部依赖

- **wget** - 用于下载 cgit commit
- **langgraph** - 用于构建状态管理和工作流
- **tqdm** - 用于显示进度条

## 示例

### 分析 CGit commit（简单模式）

```bash
python3 ../kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level simple
```

### 分析 CGit commit（详细模式，显示进度条）

```bash
python3 ../kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level detail -v
```

## 输出示例

### 简单模式输出

```
---
| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:-----:|:----:|:----:|:----:|:------------:|:----:|
| 2026/02/14 | John Doe <john.doe@example.com> | [commit subject](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=53439363c0a111f11625982b69c88ee2ce8608ec) | 这是一个关于 Linux 内核的 commit，主要包含... | v1 ☐☑✓ | [CGIT](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=53439363c0a111f11625982b69c88ee2ce8608ec) |
```

### 详细模式输出

在简单模式输出的基础上，还会包含对 commit 的详细分析内容，以及关联的 patchset 分析结果。

### 详细模式输出（带进度条）

当使用 `-v` 参数时，会显示 commit 下载和分析的进度条，以及更详细的日志信息。

## 缓存机制

Commit 下载后会自动缓存到 `output/cgit/<commit-id>/` 目录：

```
output/cgit/
└── <commit-id>/
    └── <commit-id>  # Commit 文件
```

### 缓面特性

- **自动创建** - 缓存目录和文件自动创建
- **持久化存储** - 缓存文件持久化，可重复使用
- **按 commit ID 分组** - 每个 commit 独立存储在各自的目录中
- **清理方便** - 使用 `git clean -fdX` 可以清理所有缓存

使用 `git clean -fdX` 可以清理所有缓存。

## 代码规范

### 命名约定

- **函数**: `snake_case` (例如：`fetch_commit`, `parse_commit`)
- **类**: `CamelCase` (例如：`CGitAgentState`)
- **常量**: `UPPER_SNAKE_CASE`

### 注释风格

- **双语注释**: 英文用于代码结构，中文用于领域逻辑

## 扩展计划

### 功能扩展

- 添加对 commit 系列的支持
- 增强 commit 分析的深度和准确性
- 添加对 commit 状态的跟踪（是否已合入主线）

### 性能优化

- 优化 commit 下载和解析速度
- 改进模型推理效率
- 增强缓存机制（TTL、LRU）

### 用户体验

- 添加更多命令行选项
- 提供更详细的输出格式
- 支持结果导出为不同格式
- 增强进度条和日志的用户体验

## 许可证

MIT License
