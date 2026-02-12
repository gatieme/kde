# 实现计划

## 1. 创建 langgraph 版本的 LKML agent

### 1.1 新建文件 `lkml/lkml_agent.py`

* 使用 langgraph 构建状态管理和工作流

* 实现以下节点：

  * `fetch_patch`：使用 b4 工具下载指定 message-id 的补丁

  * `parse_patch`：解析补丁信息（作者、日期、主题等）

  * `analyze_patch`：分析补丁内容

  * `generate_summary`：生成补丁摘要

  * `output_results`：根据级别参数输出结果

### 1.2 实现功能

* 支持通过 message-id 下载补丁

* 解析补丁的基本信息

* 根据 `--simple` 或 `--detail` 级别输出不同详细程度的信息

* 集成模型推理功能，分析补丁内容

## 2. 修改 `kde.py` 作为项目入口

### 2.1 扩展命令行参数

* 添加 `--rss` 参数，用于调用 rss agent

* 保持现有的 `--lkml` 参数，用于调用新的 lkml agent

* 支持 `--simple` 和 `--detail` 级别参数

### 2.2 实现调用逻辑

* 根据参数调用对应的 agent

* 传递必要的参数（如 message-id、级别等）

* 处理返回结果并展示

## 3. 集成 rss agent

### 3.1 确保 rss agent 可被调用

* 检查现有的 rss agent 实现

* 确保其可以通过 kde.py 调用

## 4. 测试

### 4.1 测试 lkml agent

* 使用示例 message-id 测试功能

* 验证不同级别参数的输出

### 4.2 测试 rss agent

* 验证 rss agent 调用功能

### 4.3 测试整体集成

* 测试 kde.py 作为入口的完整流程

## 5. 文档和示例

### 5.1 更新文档

* 添加使用说明

* 提供示例命令

### 5.2 示例命令

```bash
# 使用 lkml agent 分析补丁（简单模式）
python3 kde.py --simple --lkml 20260122161647.142704-2-realwujing@gmail.com

# 使用 lkml agent 分析补丁（详细模式）
python3 kde.py --detail --lkml 20260122161647.142704-2-realwujing@gmail.com

# 使用 rss agent 分析文章
python3 kde.py --rss
```

##
