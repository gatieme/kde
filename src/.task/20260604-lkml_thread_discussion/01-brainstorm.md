# LKML Discussion Agent — Brainstorm Design

**日期**: 2026-06-04
**状态**: 已批准

---

## 1. 背景

### 1.1 问题

LKML agent 当前是纯 patch 分析流水线：

```
fetch_patch (b4 am) → parse_patch (regex) → generate_summary → analyze_patch → output_results
```

当邮件不含 patch（纯讨论邮件）时，`b4 am` 返回 "No patches found"，不生成 `.cover`/`.mbx` 文件，导致 `parse_patch` 报错 "没有找到可解析的补丁文件" 并崩溃。没有 fallback 或讨论分析路径。

### 1.2 需求

对不含 patch 的 LKML 邮件，获取完整线程讨论内容，总结：
- 讨论的核心主题
- 各专家的关键观点和建议
- 讨论的最终结论或共识/分歧

---

## 2. 技术调研结论

### 2.1 b4 工具对讨论邮件的行为

| 子命令 | 纯讨论邮件 | 行为 |
|--------|-----------|------|
| `b4 am` | **无效** | "No patches found" 并退出，不生成任何文件 |
| `b4 mbox` | **有效** | 下载完整线程 mbox，无条件保存 `.mbx` 文件 |

**结论**: 对纯讨论邮件改用 `b4 mbox` 替代 `b4 am`。

### 2.2 lore.kernel.org API

仅 `b4/0.8.0` UA 可访问 `/all/{msgid}/t.mbox.gz`（线程 mbox gzip）。其他端点（`/raw`, `/T/`）被 403 拒绝。无需直接请求 lore.kernel.org，`b4 mbox` 已内置此逻辑。

### 2.3 Python mailbox 模块

标准库 `mailbox.mbox` 可解析 mbox 格式文件，逐封提取邮件头和正文，是线程解析的理想工具。

---

## 3. 方案选择

**选定方案 A：双流程模式**

在 `lkml_agent.py` 中新增 `discussion` 模式的 workflow，与现有 `patch` 模式并列。两个流程共享缓存目录和推理接口，但不共享状态类、fetch/parse 逻辑和 prompt。

**理由**:
- 两个流程完全隔离，patch 流程不受影响
- Discussion 流程可独立设计 prompt 和输出格式
- 后续维护清晰，避免条件分支交织

**备选方案**（未选用）:
- 方案 B: 单流程条件分支 — 改动最少但可读性差
- 方案 C: 独立 discussion_agent.py — 过度拆分，代码重复

---

## 4. 设计详情

### 4.1 CLI 参数

**改动位置**: `kde.py`

```bash
# 现有用法不变（默认 patch 模式）
python3 kde.py --level=simple --lkml <message-id>

# 新增讨论模式
python3 kde.py --level=simple --mode=discussion --lkml <message-id>
```

参数定义：
- `--mode`: 可选值 `patch`（默认）/ `discussion`
- 仅与 `--lkml` 配合有效
- `--level` 语义不变：`simple` 只生成摘要，`detail` 生成摘要+详细分析

### 4.2 Discussion Agent 状态

```python
@dataclass
class DiscussionAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    lkml_id: str = ""              # 原始 message-id
    level: str = "simple"          # simple / detail
    work_dir: str = ""             # 缓存工作目录 output/lkml/<id>/
    mbx_file: str = ""             # b4 mbox 下载的 .mbx 文件路径
    thread_emails: List[Dict] = [] # 解析出的所有邮件列表
    subject: str = ""              # 讨论主题
    author: str = ""               # 原始邮件作者
    email: str = ""                # 原始邮件作者邮箱
    date: str = ""                 # 原始邮件日期
    web_url: str = ""              # lore.kernel.org 链接
    archive_url: str = ""          # 归档链接
    reply_count: int = 0           # 回复数量
    summary: str = "TODO"          # AI 生成的讨论摘要
    analysis: str = ""             # AI 详细分析 (仅 detail)
    verbose: int = 0
```

### 4.3 Discussion Workflow

```
fetch_thread → parse_thread → generate_discussion_summary → analyze_discussion → output_discussion → END
```

| 节点 | 功能 | 核心逻辑 |
|------|------|----------|
| `fetch_thread` | 用 `b4 mbox` 下载线程 mbox | 在 work_dir 执行 b4 mbox；扫描找 .mbx 文件 |
| `parse_thread` | 用 Python mailbox 模块解析 | 提取每封邮件的 Subject/From/Date/Message-Id/In-Reply-To/正文；构建邮件列表 |
| `generate_discussion_summary` | AI 生成讨论摘要 | 新 prompt `"discussion_summary"`：主题+关键观点+结论 |
| `analyze_discussion` | AI 详细分析 (仅 detail) | 新 prompt `"discussion_analysis"`：参与者观点映射+共识/分歧分析 |
| `output_discussion` | 格式化输出到终端 | Markdown 表格 + 讨论要点列表 |

### 4.4 线程获取 (`fetch_thread`)

```python
cmd = f"b4 mbox {state.lkml_id}"
result = subprocess.run(cmd, shell=True, cwd=state.work_dir, capture_output=True, ...)
```

错误处理：
- b4 mbox 失败 → 尝试直接 curl `https://lore.kernel.org/all/<msgid>/t.mbox.gz` 作为 fallback
- 下载后无 .mbx 文件 → `raise Exception("下载讨论线程失败")`

### 4.5 线程解析 (`parse_thread`)

使用 Python `mailbox` 模块解析 mbox 文件：

```python
import mailbox

mbox = mailbox.mbox(state.mbx_file)
emails = []
for msg in mbox:
    email_data = {
        "subject": msg["Subject"].replace("Re: ", "").strip(),
        "from": msg["From"],
        "date": msg["Date"],
        "message_id": msg["Message-Id"],
        "in_reply_to": msg.get("In-Reply-To", ""),
        "references": msg.get("References", ""),
        "body": extract_body(msg),
    }
    emails.append(email_data)
```

正文提取策略：
- 优先取 `text/plain` 部分
- 如果只有 `text/html`，去除 HTML 标签
- 去掉引用部分（`> ...` 开头的行），只保留新增内容
- 去掉签名部分（`-- ` 分隔符后的内容）

识别原始邮件：没有 In-Reply-To 或 References 的邮件。按日期排序后提取其元数据为 state.subject/author/email/date。

### 4.6 AI Prompt

**`discussion_summary`** (simple 级别):

> 你是 Linux 内核社区讨论分析专家。请根据以下 LKML 邮件线程内容，总结讨论的主题、各专家的关键观点、以及最终结论或共识/分歧。要求：1) 明确说明讨论的核心议题 2) 列出主要参与者的立场和关键论据 3) 总结讨论结果（达成共识或仍存分歧）4) 300 字以内

**`discussion_analysis`** (detail 级别):

> 你是 Linux 内核社区讨论深度分析专家。请根据以下 LKML 邮件线程内容，进行全面深入的分析：1) 讨论的核心议题和背景 2) 每个关键参与者的观点、论据和立场 3) 技术层面的争议焦点 4) 讨论中的共识和分歧点 5) 最终走向和建议 6) 对内核开发的影响评估

输入构建：将 thread_emails 格式化为结构化文本：

```
[原始邮件]
作者: xxx <xxx@email>
日期: 2026-04-15
主题: xxx
内容: xxx

[回复 1] by xxx <xxx@email> on 2026-04-15
内容: xxx

[回复 2] by xxx <xxx@email> on 2026-04-16
内容: xxx
...
```

### 4.7 输出格式 (`output_discussion`)

Markdown 表格，与 patch 分析框架一致但调整列含义：

```markdown
| 时间 | 作者 | 主题 | 讨论摘要 | 回复数 | 链接 |
|:---:|:----:|:---:|:----:|:-----:|:----:|
| 2026/04/15 | Author <email> | [Subject](web_url) | formatted_summary | 5 | [2026/04/15, LORE](archive_url) |
```

与 patch 输出的差异：
- "是否合入主线" 列 → "回复数" 列
- 其他列保持不变

detail 级别额外输出：在表格下方追加详细分析内容。

---

## 5. 文件改动范围

| 文件 | 改动类型 | 改动内容 |
|------|----------|----------|
| `kde.py` | 修改 | 新增 `--mode` 参数；新增 `run_discussion_agent` 函数 |
| `lkml/lkml_agent.py` | 修改 | 新增 `DiscussionAgentState`；新增 5 个 discussion workflow 节点；新增 `build_discussion_agent` |
| `model/model_request.py` | 修改 | 新增 `discussion_summary` 和 `discussion_analysis` prompt 类型 |
| `lkml/__init__.py` | 修改 | 导出新增的 discussion agent 构建函数 |

**不改动的文件**:
- `lkml/lkml.py` — legacy 类不动
- `lkml/get_b4_series.sh` — shell 脚本不动
- `model/model_infer.py` — 推理接口不变
- `cgit/cgit_agent.py` — CGit agent 不变

---

## 6. 测试策略

在 `test/test_lkml.sh` 中新增测试场景：

| # | 名称 | 命令 |
|---|------|------|
| 4 | Discussion 简单模式 | `python3 kde.py --level=simple --mode=discussion --lkml <discussion-id>` |
| 5 | Discussion 详细模式 | `python3 kde.py --level=detail --mode=discussion --lkml <discussion-id>` |
| 6 | Discussion 直接调用 | `python3 lkml/lkml_agent.py --message_id=<id> --level=simple --mode=discussion` |

需要找一个真实的纯讨论邮件 message-id 作为测试数据。

---

## 7. 共享与隔离

**共享**:
- `output/lkml/<id>/` 缓存目录结构
- `ModelInference` 推理接口
- `kde.py` 的 CLI 入口

**不共享**:
- 状态类（独立的 `DiscussionAgentState` vs `LKMLAgentState`）
- fetch/parse 逻辑（`b4 mbox` + `mailbox` 模块 vs `b4 am` + regex）
- AI prompt（讨论专用 vs 补丁专用）
- 输出格式细节（"回复数" 列 vs "是否合入主线" 列）

---

## 8. 风险与回滚

| 风险 | 应对 | 回滚方式 |
|------|------|----------|
| b4 mbox 对某些邮件下载失败 | curl fallback 到 lore.kernel.org t.mbox.gz | git revert 相关改动 |
| mbox 文件包含大量邮件（50+），AI 输入过长 | 截断：只取前 20 封邮件 + 最后几封结论性回复 | 调整截断参数 |
| HTML-only 邮件正文提取不完整 | 简单 HTML 标签去除 + 容错处理 | 改用更复杂的 HTML parser |
| b4 mbox 下载超时 | 设置 300s 超时 + 重试 | 与 patch 模式超时策略一致 |