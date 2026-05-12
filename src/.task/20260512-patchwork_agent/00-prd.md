这个仓库的代码包含了如下功能
1. lkml 目录实现了一个分析指定 LKML 社区补丁的 agent。
2. rss 目录是用 TRAE 生成的代码，它是用 langgraph 实现的一个 phoronix 和 lwn 解析的 AGENT。
3. patchwork 目录是用 shell 实现的解析 patchwork 工程的脚本。
4. cgit 目录是用分析内核 commit 的 agent
5. kde.py 计划是整个工程的入口。
6. test 目录下是整个项目的测试用例
项目根目录以及每个子目录的 README 中有对相关代码架构以及功能的解析。

请完成如下个功能
请根据已有的 agent 和脚本（主要是 @src/patchwork/get_patchwork_series.sh），在 patchwork 目录下基于 langgraph 实现一个 patchwork 的 AGENT。
1. 支持获取指定日期，指定 projects 的 id ，所有的补丁列表，并通过 lkml agent 对其进行分析。
2. 格式保持原来的输出格式，并参考 lkml_agent 的输出格式。
3. 在 test 用力补齐对应的测试用例，要求测试用例全部通过，功能才算完成。
参见 projects id 和邮件列表的索引参考 @src/patchwork/project/projects_list.md
请使用 superpowers brainstorm skill 对该任务进行 brainstorm，将 brainstorm 生成到 .task/20260512-patchwork_agent/01-brainstorm.md
