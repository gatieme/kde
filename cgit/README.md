# CGit Agent

## 项目介绍

CGit Agent 是一个专门用于分析 Linux 内核 git commit 的智能工具，使用 langgraph 实现状态管理和工作流，能够自动下载、解析和分析指定的 commit，并从 commit 中提取 patchset 链接进行关联分析。

## 项目架构

### 核心组件

1. **cgit_agent.py** - 使用 langgraph 实现的 CGit commit 分析 agent
2. **get_cgit_patch.sh** - 辅助脚本，用于获取 cgit patch

### 工作流程

CGit Agent 的工作流程由以下几个主要步骤组成：

1. **获取 commit** (`fetch_commit`) - 从 cgit 下载指定 commit ID 的内容
2. **解析信息** (`parse_commit`) - 提取 commit 的基本信息（作者、日期、主题等）
3. **分析内容** (`analyze_commit`) - 对 commit 内容进行分析，生成摘要
4. **检查 patchset** (`check_patchset`) - 从 commit 中提取 patchset 链接
5. **运行 LKML 分析** (`run_lkml_analysis`) - 使用 LKML Agent 分析关联的 patchset
6. **输出结果** (`output_results`) - 根据级别参数输出分析结果

## 功能说明

### 主要功能

- **自动下载 commit** - 从 cgit 自动下载指定 commit ID 的内容
- **信息提取** - 解析 commit 的基本信息，包括作者、日期、主题等
- **智能分析** - 使用模型对 commit 内容进行分析，生成摘要
- **patchset 关联** - 从 commit 中提取 patchset 链接并进行关联分析
- **多级分析** - 支持 simple 和 detail 两个级别的分析深度
- **结果输出** - 以表格形式展示分析结果，包括 commit 的基本信息和分析内容
- **进度条显示** - 在 verbose 模式下显示 commit 下载和分析的进度
- **详细日志控制** - 通过 verbose 级别控制日志输出的详细程度

### 技术实现

- **状态管理** - 使用 langgraph 实现状态管理和工作流
- **commit 下载** - 使用 wget 从 cgit 下载 commit 内容
- **信息解析** - 使用正则表达式解析 commit 信息
- **patchset 检测** - 使用正则表达式从 commit 中提取 patchset 链接
- **模型推理** - 集成模型推理模块，对 commit 内容进行分析
- **结果展示** - 以 Markdown 表格形式展示分析结果
- **进度条实现** - 使用 tqdm 库实现进度条显示
- **日志控制** - 通过 verbose 级别参数控制日志输出

## 使用说明

### 通过 kde.py 调用

CGit Agent 主要通过 kde.py 进行调用，支持以下命令格式：

#### 简单模式（仅生成摘要）

```bash
python3 ../kde.py cgit <commit-id> simple
```

#### 详细模式（生成摘要并进行深入分析）

```bash
python3 ../kde.py cgit <commit-id> detail
```

#### 详细模式（显示进度条）

```bash
python3 ../kde.py cgit <commit-id> detail -v
```

#### 详细模式（显示最详细的日志）

```bash
python3 ../kde.py cgit <commit-id> detail -vvv
```

### 直接调用

也可以直接调用 cgit_agent.py 进行测试：

```bash
python3 cgit_agent.py --commit_id=<commit-id> --level=simple
python3 cgit_agent.py --commit_id=<commit-id> --level=detail
```

### 参数说明

- `<commit-id>` - Git commit 的 ID，例如：`53439363c0a111f11625982b69c88ee2ce8608ec`
- `simple|detail` - 分析级别，simple 仅生成摘要，detail 进行深入分析
- `-v, --verbose` - 详细模式，显示进度条和详细日志

## 依赖关系

### 内部依赖

- **model/model_infer.py** - 模型推理实现
- **model/model_request.py** - 模型请求构建
- **lkml/lkml_agent.py** - LKML Agent 实现，用于分析 patchset

### 外部依赖

- **wget** - 用于下载 cgit commit
- **langgraph** - 用于构建状态管理和工作流
- **openai** - 用于模型推理
- **tqdm** - 用于显示进度条

## 示例

### 分析 CGit commit（简单模式）

```bash
python3 ../kde.py cgit 53439363c0a111f11625982b69c88ee2ce8608ec simple
```

### 分析 CGit commit（详细模式，显示进度条）

```bash
python3 ../kde.py cgit 53439363c0a111f11625982b69c88ee2ce8608ec detail -v
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

## 扩展计划

### 功能扩展

- 添加对 commit 系列的支持
- 增强 commit 分析的深度和准确性
- 添加对 commit 状态的跟踪（是否已合入主线）

### 性能优化

- 优化 commit 下载和解析速度
- 改进模型推理效率
- 增加缓存机制减少重复操作

### 用户体验

- 添加更多命令行选项
- 提供更详细的输出格式
- 支持结果导出为不同格式
- 增强进度条和日志的用户体验

## 许可证

本项目仅供学习和研究使用。