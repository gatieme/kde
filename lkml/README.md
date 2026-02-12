# LKML Agent

## 项目介绍

LKML Agent 是一个专门用于分析 Linux 内核邮件列表（LKML）补丁的智能工具，使用 langgraph 实现状态管理和工作流，能够自动下载、解析和分析指定的 LKML 补丁。

## 项目架构

### 核心组件

1. **lkml_agent.py** - 使用 langgraph 实现的 LKML 补丁分析 agent
2. **lkml.py** - 原始的 LKML 补丁分析实现
3. **get_b4_series.sh** - 辅助脚本，用于获取补丁系列
4. **cvt_lkml_to_lore.sh** - 辅助脚本，用于转换 LKML 到 LORE 格式

### 工作流程

LKML Agent 的工作流程由以下几个主要步骤组成：

1. **获取补丁** (`fetch_patch`) - 使用 b4 工具下载指定 message-id 的补丁
2. **解析信息** (`parse_patch`) - 提取补丁的基本信息（作者、日期、主题、版本等）
3. **生成摘要** (`generate_summary`) - 对补丁内容进行总结
4. **详细分析** (`analyze_patch`) - 在 detail 级别下对补丁进行深入分析
5. **输出结果** (`output_results`) - 根据级别参数输出分析结果

## 功能说明

### 主要功能

- **自动下载补丁** - 使用 b4 工具从 LKML 自动下载指定 message-id 的补丁
- **信息提取** - 解析补丁的基本信息，包括作者、日期、主题、版本等
- **智能分析** - 使用模型对补丁内容进行分析，生成摘要和详细分析
- **多级分析** - 支持 simple 和 detail 两个级别的分析深度
- **结果输出** - 以表格形式展示分析结果，包括补丁的基本信息和分析内容

### 技术实现

- **状态管理** - 使用 langgraph 实现状态管理和工作流
- **补丁下载** - 调用 b4 工具下载补丁
- **信息解析** - 使用正则表达式解析补丁信息
- **模型推理** - 集成模型推理模块，对补丁内容进行分析
- **结果展示** - 以 Markdown 表格形式展示分析结果

## 使用说明

### 通过 kde.py 调用

LKML Agent 主要通过 kde.py 进行调用，支持以下命令格式：

#### 简单模式（仅生成摘要）

```bash
python3 ../kde.py --level=simple --lkml <message-id>
```

#### 详细模式（生成摘要并进行深入分析）

```bash
python3 ../kde.py --level=detail --lkml <message-id>
```

### 直接调用

也可以直接调用 lkml_agent.py 进行测试：

```bash
python3 lkml_agent.py <message-id> [simple|detail]
```

### 参数说明

- `<message-id>` - LKML 补丁的 message-id，例如：`20260122161647.142704-2-realwujing@gmail.com`
- `--level=simple|detail` - 分析级别，simple 仅生成摘要，detail 进行深入分析

## 依赖关系

### 内部依赖

- **model/model_infer.py** - 模型推理实现
- **model/model_request.py** - 模型请求构建

### 外部依赖

- **b4** - 用于下载 LKML 补丁
- **langgraph** - 用于构建状态管理和工作流
- **openai** - 用于模型推理
- **tqdm** - 用于显示进度条

## 示例

### 分析 LKML 补丁（简单模式）

```bash
python3 ../kde.py --level=simple --lkml 20260122161647.142704-2-realwujing@gmail.com
```

### 分析 LKML 补丁（详细模式）

```bash
python3 ../kde.py --level=detail --lkml 20260122161647.142704-2-realwujing@gmail.com
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

## 扩展计划

### 功能扩展

- 添加对补丁系列的支持
- 增强补丁分析的深度和准确性
- 添加对补丁状态的跟踪（是否已合入主线）

### 性能优化

- 优化补丁下载和解析速度
- 改进模型推理效率
- 增加缓存机制减少重复操作

### 用户体验

- 添加更多命令行选项
- 提供更详细的输出格式
- 支持结果导出为不同格式
