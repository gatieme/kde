部分 LKML 地址可能只是讨论，没有 patch 或者 patchset

如下执行命令

``shell
python3 kde.py --level=simple --lkml 20260415000910.2h5misvwc45bdumu@airbuntu

python3运行 LKML agent (级别: simple)
分析 message-id: 20260415000910.2h5misvwc45bdumu@airbuntu

运行 LKML agent 失败: 没有找到可解析的补丁文件
``
这种情况下，我想要获取这个邮件列表的内容，以及大家相关的讨论。
要求总结出邮件的相关内容，以及其他专家的建议和讨论的结果。
在 lkml_agent 中增加这个功能。`
