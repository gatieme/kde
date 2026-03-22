---
active: true
iteration: 1
session_id: 
max_iterations: 5
completion_promise: "DONE"
started_at: "2026-03-22T07:18:20Z"
---

这个仓库的代码包含了如下功能
1. lkml 目录实现了一个分析指定 LKML 社区补丁的 agent。
2. rss 目录是用 TRAE 生成的代码，它是用 langgraph 实现的一个 phoronix 和 lwn 解析的 AGENT。
3. patchwork 目录是用 shell 实现的解析 patchwork 工程的脚本。
4. cgit 目录是用分析内核 commit 的 agent
5. kde.py 计划是整个工程的入口。
6. test 目录下是整个项目的测试用例
项目根目录以及每个子目录的 README 中有对相关代码架构以及功能的解析。

请完成如下两个功能

功能一：
请根据当前最新代码和架构更新 REAMDE，包括整个项目的 README 以及各个 agent 以及子目录的 README；README 需要包括各个项目的项目介绍, 软件架构, 主要功能,
1. 架构图 - 所有模块都添加了清晰的 ASCII art 架构图
2. 工作流程 - 详细说明了每个 Agent 的工作流程和步骤
3. 技术细节 - 添加了状态类定义、API 说明、配置参数等
4. 使用示例 - 包含了完整的使用方法和示例命令
5. 代码规范 - 统一了命名约定和注释风格说明
6. 扩展计划 - 为每个模块添加了未来发展方向

功能二：
整个项目的 README 以及各个 agent 以及子目录的 README 中，包含了整个项目和各个 AGENT 的软件架构，
diagrams 目录下有 mermaid 和 excalidraw 架构图，但是并不美观。
请参考 README 中的架构图, 重新生成更美观的 mermaid 和 excalidraw 架构图，更新到 diagrams 目录下，并将 excalidraw 架构图更到到 README 中.

1. 请将生成的架构图保存在 diagrams 目录下. 包括 mermaid 代码, ASCII, svg, excalidraw 格式. 我发现之前的架构图中有 <br> 字样，这些无法正常显示为换行，请换种方式呈现。
2. 请通过 @beautiful-mermaid  @pretty-mermaid 生成 mermaid 代码, ASCII, svg 格式的架构图(要求保留 mermaid 代码到对应的 mmd 文件中, SVG 配色使用浅色)
3. 请通过 @excalidraw-diagram-generator 和 @excalidraw-diagram，以及 @excalidraw 几个 SKILLS 生成【手绘风格的架构图+Excalidraw动画】，保存原始 JSON 格式和 SVG 格式。要求手绘风格：Excalifont字体、roughness:手绘线条、轻配色；动画顺序：标题→XX层→XX层→连接线，每步时长500ms；画布0-1200x0-800，元素间距≥30px。若为复杂架构图，请通过 excalidraw 子代理委托规则执行。
4. 将最后生成的 excalidraw 手绘风格 SVG 架构图，更新到各个 README 中。


每个功能使用 @git-commit 提交这个提交一个 COMMIT，要求 COMMIT 描述为纯英文
