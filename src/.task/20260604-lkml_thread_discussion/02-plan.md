# LKML Discussion Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 LKML agent 中新增 discussion 模式，支持对不含 patch 的纯讨论邮件进行线程分析、摘要生成和详细解读。

**Architecture:** 双流程并列模式。在 `lkml_agent.py` 中新增 `DiscussionAgentState` 状态类和 5 个 discussion workflow 节点，与现有 `patch` 流程完全隔离。CLI 层新增 `--mode=discussion` 参数。两个流程共享缓存目录和 `ModelInference` 推理接口，但不共享状态类、fetch/parse 逻辑和 prompt。

**Tech Stack:** Python, LangGraph, b4 (mbox), mailbox 标准库, ModelScope Qwen3-235B-A22B

---

## File Structure

| 文件 | 改动类型 | 责任 |
|------|----------|------|
| `model/model_request.py` | 修改 | 新增 `discussion_summary` 和 `discussion_analysis` prompt 类型 |
| `lkml/lkml_agent.py` | 修改 | 新增 `DiscussionAgentState`、5 个节点函数、`build_discussion_agent`、`run_discussion_agent` |
| `kde.py` | 修改 | 新增 `--mode` 参数、新增 `lkml_discussion_run` 函数、修改 `lkml_run` 调用逻辑 |
| `lkml/__init__.py` | 修改 | 导出 `run_discussion_agent` |
| `test/test_lkml.sh` | 修改 | 新增 3 个 discussion 测试场景 |

**不改动的文件:** `lkml/lkml.py`, `lkml/get_b4_series.sh`, `model/model_infer.py`, `cgit/cgit_agent.py`, `model/__init__.py`

---

### Task 1: 新增 discussion prompt 到 ModelRequest

**Files:**
- Modify: `model/model_request.py:1-93`

- [ ] **Step 1: 在 model_request.py 中新增 discussion_summary prompt**

在 `messages_analysis` 定义之后，新增两个 prompt 列表：

```python
messages_discussion_summary = [
    {
        'role': 'system',
        'content': '你是 Linux 内核社区讨论分析专家。请根据以下 LKML 邮件线程内容，总结讨论的主题、各专家的关键观点、以及最终结论或共识/分歧。要求：1) 明确说明讨论的核心议题 2) 列出主要参与者的立场和关键论据 3) 总结讨论结果（达成共识或仍存分歧）4) 300 字以内',
    },
    {
        'role': 'user',
        'content': '''以下是 LKML 邮件线程的完整内容，请按照系统设定的要求，用中文对该讨论进行总结，字数控制在 300 字以内。'''
    }
]

messages_discussion_analysis = [
    {
        'role': 'system',
        'content': '你是 Linux 内核社区讨论深度分析专家。请根据以下 LKML 邮件线程内容，进行全面深入的分析：1) 讨论的核心议题和背景 2) 每个关键参与者的观点、论据和立场 3) 技术层面的争议焦点 4) 讨论中的共识和分歧点 5) 最终走向和建议 6) 对内核开发的影响评估',
    },
    {
        'role': 'user',
        'content': '''以下是 LKML 那件线程的完整内容，请按照系统设定的要求，用中文对该讨论进行全面深入的分析。'''
    }
]
```

- [ ] **Step 2: 更新 model_request_type 列表和 messages_mapping 字典**

将 `model_request_type` 从 `["summary", "analysis"]` 改为：

```python
model_request_type = ["summary", "analysis", "discussion_summary", "discussion_analysis"]
```

将 `messages_mapping` 从两项扩展为四项：

```python
messages_mapping = {
    "summary": messages_summary,
    "analysis": messages_analysis,
    "discussion_summary": messages_discussion_summary,
    "discussion_analysis": messages_discussion_analysis,
}
```

- [ ] **Step 3: 验证 ModelRequest 可接受新的 request 类型**

Run: `python3 -c "from model.model_request import ModelRequest; mr = ModelRequest('discussion_summary', 'test content'); print('discussion_summary OK'); mr2 = ModelRequest('discussion_analysis', 'test content'); print('discussion_analysis OK')"`

Expected: 输出 `discussion_summary OK` 和 `discussion_analysis OK`，无报错

- [ ] **Step 4: Commit**

```bash
git add model/model_request.py
git commit -m "feat(model): add discussion_summary and discussion_analysis prompt types"
```

---

### Task 2: 新增 DiscussionAgentState 和 discussion workflow 到 lkml_agent.py

**Files:**
- Modify: `lkml/lkml_agent.py:1-369`

这是最大的改动。按子步骤拆分：

- [ ] **Step 1: 新增 DiscussionAgentState dataclass**

在 `LKMLAgentState` 类定义之后（约第 42 行），新增：

```python
@dataclass
class DiscussionAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    lkml_id: str = ""              # 原始 message-id
    level: str = "simple"          # simple / detail
    work_dir: str = ""             # 缓存工作目录 output/lkml/<id>/
    mbx_file: str = ""             # b4 mbox 下载的 .mbx 文件路径
    thread_emails: List[Dict] = field(default_factory=list)  # 解析出的所有邮件列表
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

注意使用 `field(default_factory=list)` 替代 `List[Dict] = []`，避免 dataclass 可变默认值陷阱。

- [ ] **Step 2: 新增 fetch_thread 节点函数**

在 `output_results` 函数之后，新增：

```python
def fetch_thread(state: DiscussionAgentState) -> DiscussionAgentState:
    """用 b4 mbox 下载线程 mbox 文件"""
    if state.verbose >= 2:
        print("=== 下载 LKML 讨论线程 ===\n")

    if not state.work_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_root = os.path.join(repo_root, "output", "lkml")
        state.work_dir = os.path.join(cache_root, state.lkml_id)
    os.makedirs(state.work_dir, exist_ok=True)

    original_dir = os.getcwd()
    os.chdir(state.work_dir)

    try:
        command = ["b4", "mbox", state.lkml_id]

        if state.verbose >= 2:
            print(f"执行命令: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if state.verbose >= 3:
            for line in process.stdout:
                print(line, end='')
        elif state.verbose >= 1:
            with tqdm(total=100, desc="LKML 线程下载进度", unit="%") as pbar:
                monitor_process_with_progress(process, pbar, state.verbose)
        else:
            try:
                output = process.communicate(timeout=300)[0]
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
                raise Exception("下载讨论线程超时（300秒），进程已终止")

        returncode = process.wait()
        if returncode != 0:
            # b4 mbox 失败，尝试 curl fallback
            if state.verbose >= 1:
                print(f"b4 mbox 失败（返回码: {returncode}），尝试 curl fallback...")
            import gzip
            import shutil
            import urllib.request
            mbox_url = f"https://lore.kernel.org/all/{state.lkml_id}/t.mbox.gz"
            gz_path = os.path.join(state.work_dir, "thread.mbox.gz")
            try:
                urllib.request.urlretrieve(mbox_url, gz_path)
                with gzip.open(gz_path, 'rb') as f_in:
                    mbx_path = os.path.join(state.work_dir, "thread.mbx")
                    with open(mbx_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                if state.verbose >= 1:
                    print("curl fallback 成功")
            except Exception as e:
                raise Exception(f"下载讨论线程失败: b4 mbox 返回 {returncode}, curl fallback 也失败: {e}")

        # 查找下载的 .mbx 文件
        files = os.listdir(state.work_dir)
        mbx_files = [f for f in files if f.endswith('.mbx')]

        if mbx_files:
            state.mbx_file = os.path.join(state.work_dir, mbx_files[0])
            if state.verbose >= 2:
                print(f"找到 MailBox 文件: {state.mbx_file}")
        else:
            raise Exception("下载讨论线程失败：没有找到 .mbx 文件")

    finally:
        os.chdir(original_dir)

    return state
```

- [ ] **Step 3: 新增邮件正文提取辅助函数**

在 `fetch_thread` 函数之后，新增辅助函数 `_extract_email_body`：

```python
def _extract_email_body(msg) -> str:
    """从邮件对象提取正文，去除引用和签名"""
    import html as html_module

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors='replace')
                    break
            elif content_type == 'text/html' and not body:
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                if payload:
                    html_content = payload.decode(charset, errors='replace')
                    body = html_module.unescape(re.sub(r'<[^>]+>', '', html_content))
    else:
        content_type = msg.get_content_type()
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(charset, errors='replace')
            if content_type == 'text/html':
                body = html_module.unescape(re.sub(r'<[^>]+>', '', decoded))
            else:
                body = decoded

    # 去掉引用部分（以 > 开头的行）
    lines = body.split('\n')
    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('>'):
            continue
        filtered.append(line)
    body = '\n'.join(filtered)

    # 去掉签名部分（-- 分隔符后的内容）
    sig_idx = body.find('\n-- \n')
    if sig_idx >= 0:
        body = body[:sig_idx]

    return body.strip()
```

- [ ] **Step 4: 新增 parse_thread 节点函数**

在 `_extract_email_body` 之后，新增：

```python
def parse_thread(state: DiscussionAgentState) -> DiscussionAgentState:
    """用 Python mailbox 模块解析 mbox 文件，提取邮件列表"""
    import mailbox

    if state.verbose >= 2:
        print("=== 解析讨论线程 ===\n")

    if not state.mbx_file:
        raise Exception("没有找到可解析的 mbox 文件")

    mbox = mailbox.mbox(state.mbx_file)
    emails = []
    original_email = None

    for msg in mbox:
        subject = msg["Subject"] or ""
        # 去掉 Re: 前缀以获取纯主题
        clean_subject = re.sub(r'^Re:\s*', '', subject).strip()

        from_str = msg["From"] or ""
        # 提取作者名和邮箱
        from_match = re.match(r'(.*)\s*<(.*)>', from_str)
        if from_match:
            author_name = from_match.group(1).strip()
            author_email = from_match.group(2).strip()
        else:
            author_name = from_str
            author_email = from_str

        date_str = msg["Date"] or ""
        message_id = msg["Message-Id"] or ""
        # Message-Id 通常被 <> 包裹，去掉
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]

        in_reply_to = msg.get("In-Reply-To", "") or ""
        if in_reply_to.startswith('<') and in_reply_to.endswith('>'):
            in_reply_to = in_reply_to[1:-1]

        references = msg.get("References", "") or ""

        body = _extract_email_body(msg)

        email_data = {
            "subject": clean_subject,
            "from_name": author_name,
            "from_email": author_email,
            "date": date_str,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "body": body,
        }
        emails.append(email_data)

        # 识别原始邮件：没有 In-Reply-To 的邮件
        if not in_reply_to:
            if original_email is None or not original_email.get("in_reply_to"):
                original_email = email_data

    if not emails:
        raise Exception("mbox 文件中没有找到任何邮件")

    state.thread_emails = emails

    # 设置原始邮件的元数据
    if original_email:
        state.subject = original_email["subject"]
        state.author = original_email["from_name"]
        state.email = original_email["from_email"]
        state.date = original_email["date"]

        # 格式化日期
        try:
            date_value = int(datetime.datetime.strptime(
                original_email["date"], '%a, %d %b %Y %H:%M:%S %z'
            ).timestamp())
            state.date = datetime.datetime.fromtimestamp(date_value).strftime('%Y/%m/%d')
        except (ValueError, OSError):
            # 日期解析失败，保留原始字符串
            pass

        state.web_url = f"https://lore.kernel.org/all/{original_email['message_id']}"
        state.archive_url = state.web_url

    state.reply_count = len(emails) - 1  # 原始邮件不算回复

    if state.verbose >= 2:
        print(f"讨论主题: {state.subject}")
        print(f"原始作者: {state.author} <{state.email}>")
        print(f"日期: {state.date}")
        print(f"邮件总数: {len(emails)}")
        print(f"回复数: {state.reply_count}")
        print(f"链接: {state.web_url}")

    return state
```

- [ ] **Step 5: 新增 generate_discussion_summary 节点函数**

在 `parse_thread` 之后，新增：

```python
def generate_discussion_summary(state: DiscussionAgentState) -> DiscussionAgentState:
    """AI 生成讨论摘要"""
    if state.verbose >= 2:
        print("=== 生成讨论摘要 ===\n")

    try:
        # 将线程邮件格式化为结构化文本
        formatted_thread = _format_thread_emails(state.thread_emails)

        if not formatted_thread:
            raise Exception("没有找到可分析的讨论内容")

        # 截断过长线程（只取前 20 封 + 最后 3 封结论性回复）
        if len(state.thread_emails) > 23:
            truncated_emails = state.thread_emails[:20] + state.thread_emails[-3:]
            formatted_thread = _format_thread_emails(truncated_emails)

        model_req = ModelRequest("discussion_summary", formatted_thread)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.summary = model_infer.get_answer()
        if state.verbose >= 2:
            print("讨论摘要生成完成")
            print(f"摘要: {state.summary[:100]}...")

    except Exception as e:
        print(f"生成讨论摘要失败: {e}")
        state.summary = "无法生成讨论摘要"

    return state
```

- [ ] **Step 6: 新增 _format_thread_emails 辅助函数**

在 `generate_discussion_summary` 之后，新增：

```python
def _format_thread_emails(thread_emails: List[Dict]) -> str:
    """将邮件列表格式化为结构化文本，供 AI 分析"""
    parts = []
    for i, email_data in enumerate(thread_emails):
        if i == 0 and not email_data.get("in_reply_to"):
            # 原始邮件
            parts.append(f"[原始邮件]")
            parts.append(f"作者: {email_data['from_name']} <{email_data['from_email']}>")
            parts.append(f"日期: {email_data['date']}")
            parts.append(f"主题: {email_data['subject']}")
            parts.append(f"内容: {email_data['body']}")
        else:
            # 回复邮件
            parts.append(f"\n[回复 {i}] by {email_data['from_name']} <{email_data['from_email']}> on {email_data['date']}")
            parts.append(f"内容: {email_data['body']}")
        parts.append("")  # 空行分隔

    return '\n'.join(parts)
```

- [ ] **Step 7: 新增 analyze_discussion 节点函数**

在 `_format_thread_emails` 之后，新增：

```python
def analyze_discussion(state: DiscussionAgentState) -> DiscussionAgentState:
    """AI 详细分析讨论内容（仅 detail 级别）"""
    if state.verbose >= 2:
        print("=== 分析讨论内容 ===\n")

    # 只有 detail 级别才进行详细分析
    if state.level != "detail":
        return state

    try:
        formatted_thread = _format_thread_emails(state.thread_emails)

        if len(state.thread_emails) > 23:
            truncated_emails = state.thread_emails[:20] + state.thread_emails[-3:]
            formatted_thread = _format_thread_emails(truncated_emails)

        model_req = ModelRequest("discussion_analysis", formatted_thread)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.analysis = model_infer.get_answer()
        if state.verbose >= 2:
            print("讨论分析完成")

    except Exception as e:
        print(f"分析讨论内容失败: {e}")

    return state
```

- [ ] **Step 8: 新增 output_discussion 节点函数**

在 `analyze_discussion` 之后，新增：

```python
def output_discussion(state: DiscussionAgentState) -> DiscussionAgentState:
    """格式化输出讨论结果到终端"""
    if state.verbose >= 2:
        print("=== 输出讨论结果 ===\n")

    print()
    print("| 时间 | 作者 | 主题 | 讨论摘要 | 回复数 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:-----:|:----:|")

    formatted_summary = format_text_for_markdown(state.summary)

    print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {formatted_summary} | {state.reply_count} | [{state.date}, LORE]({state.archive_url}) |")

    # detail 级别，打印详细分析
    if state.level == "detail" and state.analysis:
        if state.verbose >= 2:
            print("\n=== 详细讨论分析 ===\n")
        if state.verbose >= 3:
            print(state.analysis)

    return state
```

- [ ] **Step 9: 新增 build_discussion_agent 和 run_discussion_agent 函数**

在 `output_discussion` 之后，新增：

```python
def build_discussion_agent():
    """构建 discussion workflow"""
    workflow = StateGraph(DiscussionAgentState)

    workflow.add_node("fetch_thread", fetch_thread)
    workflow.add_node("parse_thread", parse_thread)
    workflow.add_node("generate_discussion_summary", generate_discussion_summary)
    workflow.add_node("analyze_discussion", analyze_discussion)
    workflow.add_node("output_discussion", output_discussion)

    workflow.set_entry_point("fetch_thread")
    workflow.add_edge("fetch_thread", "parse_thread")
    workflow.add_edge("parse_thread", "generate_discussion_summary")
    workflow.add_edge("generate_discussion_summary", "analyze_discussion")
    workflow.add_edge("analyze_discussion", "output_discussion")
    workflow.add_edge("output_discussion", END)

    return workflow.compile()

def run_discussion_agent(lkml_id: str, level: str = "simple", work_dir: str = None, verbose: int = 0):
    """运行 discussion agent 分析纯讨论邮件线程"""
    if verbose >= 1:
        print()
        print("---------------------")
        print("运行 LKML Discussion agent (级别: " + level + ")")
        print("分析 message-id: " + lkml_id)
        print("---------------------")
        print()

    agent = build_discussion_agent()

    initial_state = DiscussionAgentState(
        messages=[{"role": "system", "content": "你是一个 LKML 讨论分析智能体，负责下载、解析和分析 Linux 内核邮件列表中的讨论线程。"}],
        lkml_id=lkml_id,
        level=level,
        work_dir=work_dir,
        verbose=verbose
    )

    result = agent.invoke(initial_state)
    return result
```

- [ ] **Step 10: 更新 lkml_agent.py 的 parse_args 函数支持 --mode**

将现有 `parse_args` 函数（约第 340-365 行）修改为：

```python
def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(
        description="LKML 补丁/讨论分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=simple              # 补丁简要分析
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=detail              # 补丁详细分析
  python lkml_agent.py --message_id=20260415000910.2h5misvwc45bdumu@airbuntu --mode=discussion --level=simple  # 讨论简要分析
  python lkml_agent.py --message_id=20260415000910.2h5misvwc45bdumu@airbubuntu --mode=discussion --level=detail # 讨论详细分析
"""
    )
    parser.add_argument(
        "--message_id",
        type=str,
        required=True,
        help="指定 LKML 那件的 message-id"
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["simple", "detail"],
        default="simple",
        help="分析级别: simple (简要分析) 或 detail (详细分析)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["patch", "discussion"],
        default="patch",
        help="分析模式: patch (补丁分析) 或 discussion (讨论分析)"
    )
    return parser.parse_args()
```

同时修改 `__main__` 部分（约第 367-369 行）：

```python
if __name__ == "__main__":
    args = parse_args()
    if args.mode == "discussion":
        run_discussion_agent(args.message_id, args.level)
    else:
        run_lkml_agent(args.message_id, args.level)
```

- [ ] **Step 11: 验证 lkml_agent.py 语法正确**

Run: `python3 -c "import ast; ast.parse(open('lkml/lkml_agent.py').read()); print('语法检查通过')"`

Expected: 输出 `语法检查通过`，无报错

- [ ] **Step 12: Commit**

```bash
git add lkml/lkml_agent.py
git commit -m "feat(lkml): add DiscussionAgentState and discussion workflow nodes"
```

---

### Task 3: 新增 --mode 参数和 discussion runner 到 kde.py

**Files:**
- Modify: `kde.py:1-168`

- [ ] **Step 1: 在 kde.py 中新增 lkml_discussion_run 函数**

在 `lkml_run` 函数之后（约第 26 行），新增：

```python
def lkml_discussion_run(lkml_message_id, level, verbose=0):
    """运行 LKML Discussion agent 分析讨论线程"""
    try:
        from lkml.lkml_agent import run_discussion_agent
        run_discussion_agent(lkml_id=lkml_message_id, level=level, verbose=verbose)
    except Exception as e:
        print(f"运行 LKML Discussion agent 失败: {e}")
        sys.exit(1)
```

- [ ] **Step 2: 在 argparse 中新增 --mode 参数**

在 `parser.add_argument('--level', ...)` 之后（约第 86 行），新增：

```python
    # 添加模式参数（仅用于 lkml）
    parser.add_argument('--mode', type=str, default='patch',
                       choices=['patch', 'discussion'],
                       help='LKML 分析模式: patch (补丁分析) 或 discussion (讨论分析)')
```

- [ ] **Step 3: 修改 lkml 调用逻辑以支持 mode 参数**

将现有的 lkml 调用代码（约第 104-113 行）修改为：

```python
    if args.lkml:
        # 运行 LKML agent
        level = args.level
        if level not in ['simple', 'detail']:
            level = 'simple'

        mode = args.mode
        if mode not in ['patch', 'discussion']:
            mode = 'patch'

        if mode == 'discussion':
            print(f"运行 LKML Discussion agent (级别: {level})")
            print(f"分析 message-id: {args.lkml}")
            print(f"模式: discussion")
            print()
            lkml_discussion_run(lkml_message_id=args.lkml, level=level, verbose=args.verbose)
        else:
            print(f"运行 LKML agent (级别: {level})")
            print(f"分析 message-id: {args.lkml}")
            print()
            lkml_run(lkml_message_id=args.lkml, level=level, verbose=args.verbose)
```

- [ ] **Step 4: 验证 kde.py CLI 参数解析**

Run: `python3 kde.py --help`

Expected: 输出中包含 `--mode` 参数说明，选项为 `patch` 和 `discussion`

- [ ] **Step 5: Commit**

```bash
git add kde.py
git commit -m "feat(cli): add --mode parameter and discussion runner"
```

---

### Task 4: 更新 lkml/__init__.py 导出

**Files:**
- Modify: `lkml/__init__.py:1-4`

- [ ] **Step 1: 新增 run_discussion_agent 导出**

将现有内容：

```python
# -*- coding: utf-8 -*-

# lkml/__init__.py
from .lkml import LKML
```

改为：

```python
# -*- coding: utf-8 -*-

# lkml/__init__.py
from .lkml import LKML
from .lkml_agent import run_lkml_agent, run_discussion_agent
```

- [ ] **Step 2: 验证导出正确**

Run: `python3 -c "from lkml import run_lkml_agent, run_discussion_agent; print('导出验证通过')"`

Expected: 输出 `导出验证通过`，无报错

- [ ] **Step 3: Commit**

```bash
git add lkml/__init__.py
git commit -m "feat(lkml): export run_discussion_agent in __init__.py"
```

---

### Task 5: 更新 test_lkml.sh 新增 discussion 测试场景

**Files:**
- Modify: `test/test_lkml.sh:1-86`

- [ ] **Step 1: 确定测试用的纯讨论邮件 message-id**

需要找一个真实的 LKML 纯讨论邮件（不含 patch）。使用 PRD 中提到的邮件：

`20260415000910.2h5misvwc45bdumu@airbuntu`

先验证此邮件确实可通过 b4 mbox 下载：

Run: `b4 mbox 20260415000910.2h5misvwc45bdumu@airbuntu --outdir /tmp/test_discussion && ls /tmp/test_discussion/*.mbx`

Expected: 成功下载 .mbx 文件

如果此 message-id 不可用，需要找一个替代的纯讨论邮件 ID。

- [ ] **Step 2: 在 test_lkml.sh 中新增 discussion 测试命令**

在 `test_commands` 数组末尾新增 3 条命令：

```bash
    # Discussion 模式测试
    "python3 \"$PROJECT_ROOT/kde.py\" --level=simple --mode=discussion --lkml 20260415000910.2h5misvwc45bdumu@airbuntu"
    "python3 \"$PROJECT_ROOT/kde.py\" --level=detail --mode=discussion --lkml 20260415000910.2h5misvwc45bdumu@airbuntu"
    "python3 \"$PROJECT_ROOT/lkml/lkml_agent.py\" --message_id=20260415000910.2h5misvwc45bdumu@airbuntu --level=simple --mode=discussion"
```

在 `test_names` 数组末尾新增：

```bash
    "Discussion 简单模式测试（通过 kde.py）"
    "Discussion 详细模式测试（通过 kde.py）"
    "Discussion 直接调用测试"
```

在 `test_descriptions` 数组末尾新增：

```bash
    "通过 kde.py 测试 LKML Discussion agent 的简单模式分析"
    "通过 kde.py 测试 LKML Discussion agent 的详细模式分析"
    "直接调用 lkml_agent.py 测试 Discussion 简单模式分析"
```

- [ ] **Step 3: Commit**

```bash
git add test/test_lkml.sh
git commit -m "test(lkml): add discussion mode test cases"
```

---

### Task 6: 端到端验证

**Files:** 无新增/修改

- [ ] **Step 1: 通过 kde.py 运行 discussion 简单模式**

Run: `python3 kde.py --level=simple --mode=discussion --lkml 20260415000910.2h5misvwc45bdumu@airbuntu -v`

Expected: 成功输出 Markdown 表格，包含主题、摘要、回复数、链接列

- [ ] **Step 2: 通过 kde.py 运行 discussion 详细模式**

Run: `python3 kde.py --level=detail --mode=discussion --lkml 20260415000910.2h5misvwc45bdumu@airbuntu -vv`

Expected: 成功输出表格 + 详细分析内容

- [ ] **Step 3: 通过 kde.py 运行原有 patch 模式，验证未受影响**

Run: `python3 kde.py --level=simple --lkml 20260122161647.142704-2-realwujing@gmail.com -v`

Expected: 输出与之前一致，"是否合入主线" 列仍存在，patch 流程不受影响

- [ ] **Step 4: 验证默认 mode 为 patch**

Run: `python3 kde.py --level=simple --lkml 20260122161647.142704-2-realwujing@gmail.com -v`

Expected: 不指定 `--mode` 时默认执行 patch 流程，行为与步骤 3 一致

---

## Self-Review Checklist

### 1. Spec Coverage

| 需求 | 对应 Task |
|------|-----------|
| 对不含 patch 的邮件获取完整线程讨论内容 | Task 2 (fetch_thread + parse_thread) |
| 总结讨论的核心主题 | Task 2 (generate_discussion_summary) |
| 列出各专家的关键观点和建议 | Task 1 (discussion_summary prompt) + Task 2 (generate_discussion_summary) |
| 总结讨论的最终结论或共识/分歧 | Task 1 (discussion_summary prompt) |
| detail 级别详细分析 | Task 1 (discussion_analysis prompt) + Task 2 (analyze_discussion) |
| --mode CLI 参数 | Task 3 |
| 与 patch 流程隔离 | Task 2 (独立状态类和 workflow) |
| 输出格式适配（回复数 vs 是否合入主线） | Task 2 (output_discussion) |
| b4 mbox 下载 + curl fallback | Task 2 (fetch_thread) |
| mailbox 模块解析 | Task 2 (parse_thread) |
| 截断过长线程（>23 封邮件） | Task 2 (generate_discussion_summary + analyze_discussion) |
| 测试场景覆盖 | Task 5 |
| __init__.py 导出 | Task 4 |

✅ 所有需求已覆盖

### 2. Placeholder Scan

扫描计划中的关键术语：
- ✅ 无 "TBD"、"TODO"、"implement later"
- ✅ 无 "add appropriate error handling" 泛化描述
- ✅ 无 "write tests for the above" 无代码占位
- ✅ 所有代码步骤均包含完整代码

### 3. Type Consistency

- `DiscussionAgentState.thread_emails`: Task 2 定义为 `List[Dict] = field(default_factory=list)`，Task 2/5/6 中 `parse_thread` 写入、`_format_thread_emails` 读取、截断逻辑使用，类型一致
- `DiscussionAgentState.summary`: Task 2 定义为 `str = "TODO"`，`generate_discussion_summary` 写入 `model_infer.get_answer()` 返回值，类型一致
- `DiscussionAgentState.reply_count`: Task 2 定义为 `int = 0`，`parse_thread` 设置为 `len(emails) - 1`，`output_discussion` 读取，类型一致
- `ModelRequest("discussion_summary", ...)` / `ModelRequest("discussion_analysis", ...)`：Task 1 定义 prompt 类型，Task 2 中 `generate_discussion_summary` 和 `analyze_discussion` 使用，名称一致

✅ 类型一致性验证通过